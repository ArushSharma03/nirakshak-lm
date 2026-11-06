"""Run milestone processing against a snapshot of original stored evidence."""

from pathlib import Path
import hashlib
from app.schemas.analysis import Analysis, AnalysisRequest, DecisionResult, ProfileRequest, ViewAnalysis
from app.engine.profiles import select_profile
from app.services.calibration import calibrate
from app.services.decision import judge_fields
from app.services.extraction import extract, fuse
from app.services.marker_detector import detect_marker
from app.services.ocr import recognize, detail_regions
from app.core.config import settings


def analyze_record(record: dict, request: AnalysisRequest) -> Analysis:
    views = {}
    candidates = []
    warnings = []
    for view in ("front", "rear", "side"):
        image = record.get("images", {}).get(view)
        if not image:
            warnings.append(f"{view}: no captured evidence.")
            continue
        raw = Path(image["filepath"]).read_bytes()
        calibration = calibrate(detect_marker(raw), view in request.coplanar_views)
        ocr = recognize(raw)
        view_candidates = []
        for result in ocr:
            view_candidates.extend(extract(result, view, calibration))
            if result.status != "ok":
                warnings.append(f"{view}/{result.provider}: {result.message}")
        # Dense declaration panels can hide small quantities in whole-page transcription.
        # Rescan at most four regions, stopping at the first anchored quantity.
        declaration_panel = any("manufactur" in line.text.casefold() or "mrp" in line.text.casefold()
                                for result in ocr for line in result.lines)
        if settings.XIAOMI_OCR_ENABLED and declaration_panel and not any(c.field == "net_quantity" for c in view_candidates):
            for detail in detail_regions(raw):
                ocr.append(detail)
                found = extract(detail, view, calibration)
                view_candidates.extend(found)
                if detail.status != "ok":
                    warnings.append(f"{view}/{detail.provider}: {detail.message}")
                    break
                if any(c.field == "net_quantity" for c in found):
                    break
        candidates.extend(view_candidates)
        views[view] = ViewAnalysis(file_hash=hashlib.sha256(raw).hexdigest(), calibration=calibration, ocr=ocr)
        if calibration.status != "available":
            warnings.append(f"{view}: {calibration.reason}")
    fields = fuse(candidates)
    profile = select_profile(ProfileRequest(category=record["product_category"], origin=request.origin, as_of=request.as_of))
    old_analysis = record.get("analysis") or {}
    old_decision = old_analysis.get("decision") or {}
    if not request.use_jev:
        decision = DecisionResult(status="unavailable", model=settings.TYPESAFE_MODEL, message="Jev disabled for this run to avoid API charges.")
    elif old_analysis.get("fields") == [f.model_dump(mode="json") for f in fields] and old_decision.get("status") == "ok" and old_decision.get("model") == settings.TYPESAFE_MODEL:
        decision = DecisionResult.model_validate(old_decision)
    else:
        decision = judge_fields(fields)
    return Analysis(views=views, fields=fields, profile=profile, warnings=warnings, decision=decision)

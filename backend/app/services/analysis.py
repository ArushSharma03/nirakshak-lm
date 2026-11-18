"""Run milestone processing against a snapshot of original stored evidence."""

from pathlib import Path
import hashlib
import re
from app.schemas.analysis import Analysis, AnalysisRequest, DecisionResult, ProfileRequest, ViewAnalysis
from app.engine.profiles import select_profile
from app.services.checks import check_declarations
from app.services.decision import judge_fields
from app.services.extraction import ANCHORS, canonical, extract, fuse
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
        file_hash = hashlib.sha256(raw).hexdigest()
        if request.reuse_ocr:
            saved = (record.get("analysis") or {}).get("views", {}).get(view)
            if not saved or saved.get("file_hash") != file_hash:
                raise ValueError(f"No matching saved OCR for {view}. Run a fresh photo analysis.")
            ocr = ViewAnalysis.model_validate(saved).ocr
        else:
            ocr = recognize(raw)
        view_candidates = []
        for result in ocr:
            if result.provider != "tesseract":
                view_candidates.extend(extract(result, view))
            if result.status != "ok":
                warnings.append(f"{view}/{result.provider}: {result.message}")
        # Locate missing declarations from geometry; never use Tesseract as their value.
        missing = set(ANCHORS) - {c.field for c in view_candidates}
        geometry_runs = [(result, extract(result, view)) for result in ocr if result.provider == "tesseract"]
        numeric_locations = {candidate.field for _, geometry in geometry_runs for candidate in geometry}
        targets = [(field, line.box) for field in ("net_quantity", "manufacturer", "consumer_care", "country_of_origin", "generic_name", "mrp", "date") if field in missing
            and (field not in ("mrp", "date") or field in numeric_locations)
            for result in ocr if result.provider == "tesseract"
            for line in result.lines if line.box is not None and re.search(ANCHORS[field], line.text, re.I)]
        declaration_panel = any("manufactur" in line.text.casefold() or "mrp" in line.text.casefold()
                                for result in ocr for line in result.lines)
        incomplete_manufacturer = "manufacturer" in missing and any(result.provider == "xiaomi" and result.status == "partial"
            and re.search(r"\bmfg\b|\bmanufactur", result.raw_text or "\n".join(line.text for line in result.lines), re.I) for result in ocr)
        primary_available = any(result.provider == "xiaomi" and result.status in ("ok", "partial") for result in ocr)
        if not request.reuse_ocr and settings.XIAOMI_OCR_ENABLED and primary_available and (targets or incomplete_manufacturer or declaration_panel and "net_quantity" in missing):
            goals = {field for field, _ in targets} or {"net_quantity"}
            if incomplete_manufacturer:
                goals.add("manufacturer")
                scans = detail_regions(raw, boxes=[box for _, box in targets], include_quadrants=True)
            else:
                scans = detail_regions(raw, boxes=[box for _, box in targets]) if targets else detail_regions(raw)
            for detail in scans:
                ocr.append(detail)
                found = extract(detail, view)
                view_candidates.extend(found)
                if detail.status != "ok":
                    warnings.append(f"{view}/{detail.provider}: {detail.message}")
                if detail.status not in ("ok", "partial"):
                    break
                if goals <= {c.field for c in view_candidates}:
                    break
        # Tesseract supplies geometry only for values also read by the primary model.
        primary_values = {(c.field, canonical(c.field, c.value)) for c in view_candidates}
        for result, geometry in geometry_runs:
            view_candidates.extend(c for c in geometry
                                   if (c.field, canonical(c.field, c.value)) in primary_values)
            if geometry:
                warnings.append(f"{view}: Tesseract is used only for matching declaration geometry; its transcript is not an independent reading.")
        candidates.extend(view_candidates)
        views[view] = ViewAnalysis(file_hash=file_hash, ocr=ocr)
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
    checks = check_declarations(profile, fields, views, record.get("images", {}))
    return Analysis(version="1.2.0", views=views, fields=fields, profile=profile, warnings=warnings, decision=decision, checks=checks)

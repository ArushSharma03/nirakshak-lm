"""Run milestone processing against a snapshot of original stored evidence."""

from pathlib import Path
import hashlib
import re
from app.schemas.analysis import Analysis, AnalysisRequest, DecisionResult, ProfileRequest, ViewAnalysis
from app.engine.profiles import select_profile
from app.services.checks import check_declarations
from app.services.coding_window import coding_window
from app.services.decision import QUESTION_SET, judge_fields, placements, transcript_lines
from app.services.extraction import ANCHORS, canonical, country_from_maker, extract, fuse
from app.services.label_facts import label_origin, name_options, product_type_evidence, title_lines
from app.services.ocr import detail_regions, orientation, recognize, rotated_reads, turned

# "MFG Date, Expiry, Batch No. & MRP: Coded on the Pack", "See print on pack for: MRP ...".
# A turned read that found a coding print: "EXP: OF AUG 2027 MRP RS: 30.00", "MFG: 09APR2025 UBD: ...".
_CODING_HEADING = re.compile(r"\b(?:exp|ubd|use\s+by|mf[gd]|mrp|b\.?\s*no|lot)\b", re.I)
_CODED_ON_PACK = re.compile(r"coded\s+on|see\s+print|printed\s+on\s+(?:the\s+)?(?:pack|crimp)|see\s+coding", re.I)
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
        # Saved turned reads (reuse_ocr) are applied after the upright ones, under the same fill-only rule.
        turned_reads = [result for result in ocr if result.provider.startswith("xiaomi_rot")]
        ocr = [result for result in ocr if not result.provider.startswith("xiaomi_rot")]
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
        # A "complete" primary read can still skip small print. Tesseract's word count shows how much
        # text the panel holds even when its spelling is too garbled to match an anchor.
        wordy = sum(len(re.findall(r"[A-Za-z]{3,}", line.text)) >= 2 for result in ocr if result.provider == "tesseract" for line in result.lines)
        primary_lines = sum(len(result.lines) for result in ocr if result.provider == "xiaomi")
        sparse = wordy >= 8 and wordy > 2 * primary_lines
        sparse_goals = missing & {"net_quantity", "manufacturer", "consumer_care", "mrp"}
        if not request.reuse_ocr and settings.XIAOMI_OCR_ENABLED and primary_available and (targets or incomplete_manufacturer or declaration_panel and "net_quantity" in missing or sparse and sparse_goals):
            goals = {field for field, _ in targets} or {"net_quantity"}
            if sparse:
                warnings.append(f"{view}: the primary read looks incomplete ({primary_lines} lines against {wordy} text lines located); scanning label sections.")
                goals |= sparse_goals
                scans = detail_regions(raw, boxes=[box for _, box in targets], include_quadrants=True)
            elif incomplete_manufacturer:
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
        # Coding prints often run sideways (Potata's side panel, ACT II's batch strip). Read the photo turned
        # when MRP or date is still missing: by OSD's angle, or both ways when the label points to a printed code.
        still_missing = {"mrp", "date"} - {c.field for c in [*candidates, *view_candidates]}
        if not request.reuse_ocr and settings.XIAOMI_OCR_ENABLED and primary_available and still_missing:
            printed = "\n".join(line.text for result in ocr if result.provider != "tesseract" for line in result.lines)
            turn = orientation(raw)
            degrees = [turn] if turn else [90, 270] if _CODED_ON_PACK.search(printed) else []
            turned_reads = list(rotated_reads(raw, degrees))
            # A whole turned photo is downscaled, so a found coding print can still lose its smallest part
            # ("MFG:08 AUG 2026" before "EXP:07 AUG 2027"). Scan that orientation in enlarged sections.
            for rotated in list(turned_reads):
                coding = any(_CODING_HEADING.search(line.text) for line in rotated.lines)
                if not coding or "date" in {c.field for c in [*candidates, *view_candidates, *(x for r in turned_reads for x in extract(r, view))]}:
                    continue
                turn = int(rotated.provider.removeprefix("xiaomi_rot"))
                for detail in detail_regions(turned(raw, turn)):
                    detail.provider = f"xiaomi_rot{turn}_{detail.provider.removeprefix('xiaomi_')}"
                    turned_reads.append(detail)
                    if any(c.field == "date" for c in extract(detail, view)) or detail.status not in ("ok", "partial"):
                        break
        # A turned read also re-reads the upright text sideways and worse ("tedbar@atfoods.com"),
        # so it only fills fields this panel has not already read.
        upright_fields = {c.field for c in view_candidates}
        for rotated in turned_reads:
            ocr.append(rotated)
            view_candidates.extend(c for c in extract(rotated, view) if c.field not in upright_fields)
            if rotated.status != "ok":
                warnings.append(f"{view}/{rotated.provider}: {rotated.message}")
        # Coding windows print values apart from their headings; read them across every primary scan of this panel.
        panel = [(result.provider, line.text) for result in ocr
                 if result.provider != "tesseract" and result.status in ("ok", "partial") for line in result.lines]
        view_candidates.extend(coding_window(panel, view, {c.field for c in view_candidates}))
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
    if (derived := country_from_maker(fields)) is not None:
        candidates.append(derived)
        fields = fuse(candidates)
    lines = transcript_lines(views)
    old_analysis = record.get("analysis") or {}
    old_decision = old_analysis.get("decision") or {}
    use_jev = request.use_jev if request.use_jev is not None else settings.TYPESAFE_API_KEY is not None
    if not use_jev:
        decision = DecisionResult(status="unavailable", model=settings.TYPESAFE_MODEL, message="Jev disabled for this run to avoid API charges.")
    # Jev's inputs derive only from the OCR runs, so identical runs reuse the paid answer.
    elif old_analysis.get("views") == {v: a.model_dump(mode="json") for v, a in views.items()} and old_decision.get("status") == "ok" and old_decision.get("model") == settings.TYPESAFE_MODEL \
            and old_decision.get("question_set") == QUESTION_SET:
        decision = DecisionResult.model_validate(old_decision)
    else:
        decision = judge_fields(fields, lines, name_options(views), title_lines(views)[:30])
    placed = placements(decision, lines, candidates)
    if not any(c.field == "generic_name" for c in candidates) and (product := product_type_evidence(decision, views)):
        placed.append(product)
    if placed:
        candidates.extend(placed)
        if (derived := country_from_maker(fuse(candidates))) is not None:
            candidates.append(derived)
        fields = fuse(candidates)
    origin, origin_reason = (request.origin, None) if request.origin is not None else label_origin(fields, [text for _, text in lines])
    profile = select_profile(ProfileRequest(category=record["product_category"], origin=origin, as_of=request.as_of))
    if origin_reason:
        profile.reason = f"{origin_reason} {profile.reason}"
    checks = check_declarations(profile, fields, views, record.get("images", {}))
    return Analysis(version="1.2.0", views=views, fields=fields, profile=profile, warnings=warnings, decision=decision, checks=checks)

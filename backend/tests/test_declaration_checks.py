"""Check failures and uncertainty at deterministic and real HTTP/storage boundaries."""

from datetime import date
import hashlib
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.engine.profiles import select_profile
from app.schemas.analysis import Analysis, Box, Calibration, Candidate, DecisionResult, ProfileRequest, ViewAnalysis
from app.services.checks import check_declarations, quantity, valid_date
from app.services.extraction import fuse
from app.services import inspection_store as store
from app.core.config import settings


def sample(value="100g", field="net_quantity", view="rear", **extra):
    return Candidate(field=field, value=value, view=view, provider="fixture", source_text=f"Printed declaration: {value}", **extra)


def context(origin="domestic"):
    profile = select_profile(ProfileRequest(category="food_grocery", origin=origin, as_of=date(2026, 11, 16)))
    calibration = Calibration(status="available", reason="Synthetic 1 pixel/mm fixture", pixels_per_mm=1,
        homography=[[1, 0, 0], [0, 1, 0], [0, 0, 1]])
    views = {"rear": ViewAnalysis(file_hash="fixture", calibration=calibration, ocr=[])}
    images = {"rear": {"quality_assessment": {"overall_status": "Pass"}}}
    return profile, views, images


def result(candidates, kind, field="net_quantity", **kwargs):
    profile, views, images = context(**kwargs)
    return next(r for r in check_declarations(profile, fuse(candidates), views, images).results if r.kind == kind and r.field == field)


def test_missing_reading_never_proves_absence_and_setup_is_not_evidence():
    check = result([], "presence")
    assert check.status == "insufficient_evidence" and not check.evidence
    assert "not proof" in check.reason


@pytest.mark.parametrize("value,expected", [("100 g", True), ("1kg", True), ("1000ml", True), ("2 pcs", True), ("1.5 pcs", False), ("0g", False), ("-2g", False), ("100 gm garbage", False), ("2 stone", False)])
def test_units_reject_invalid_amounts_and_unknown_units(value, expected):
    assert (quantity(value) is not None) == expected


def test_equivalent_units_agree_but_real_conflicts_are_retained():
    assert result([sample("1kg"), sample("1000 g")], "consistency").status == "pass"
    check = result([sample("100g"), sample("200g")], "consistency")
    assert check.status == "fail" and len(check.evidence) == 2
    assert check.citation and check.source_url
    assert result([sample("100" )], "units").status == "fail"


@pytest.mark.parametrize("value,expected", [("02/2025", True), ("29/02/2024", True), ("31/02/2025", False), ("17/11/2026", False), ("12/2026", False), ("02/25", None)])
def test_dates_distinguish_valid_invalid_future_and_ambiguous(value, expected):
    assert valid_date(value, date(2026, 11, 16)) is expected


def test_name_fragment_and_unknown_profile_do_not_pass_completeness():
    assert result([sample("Example Foods", field="manufacturer")], "completeness", field="manufacturer").status == "insufficient_evidence"
    assert result([sample()], "presence", origin="unknown").status == "insufficient_evidence"


def test_capture_readability_is_separate_from_legal_readability():
    profile, views, images = context()
    images["rear"]["quality_assessment"]["overall_status"] = "Retake Recommended"
    checks = check_declarations(profile, fuse([sample()]), views, images).results
    check = next(r for r in checks if r.field == "net_quantity" and r.kind == "readability")
    assert check.status == "fail" and "printed label" in check.reason


def test_readability_consumes_real_quality_assessor_contract():
    from app.services.marker_detector import generate_reference_marker_image
    from app.services.quality_assessor import assess_image_quality
    profile, views, images = context()
    # A small marker image is an inadequate label capture, with genuine quality output.
    quality = assess_image_quality(generate_reference_marker_image(size_px=100))
    assert quality["overall_status"] == "Retake Recommended"
    images["rear"]["quality_assessment"] = quality
    checks = check_declarations(profile, fuse([sample()]), views, images).results
    assert next(r for r in checks if r.field == "net_quantity" and r.kind == "readability").status == "fail"


def test_no_placement_guess_and_no_line_height_substitution():
    profile, views, images = context()
    rule = next(r for r in profile.rules if r.field == "net_quantity")
    candidates = [sample(height_mm=99, box=Box(x0=0, y0=0, x1=100, y1=99))]
    report = check_declarations(profile, fuse(candidates), views, images)
    assert all(r.status == "insufficient_evidence" for r in report.results if r.field == "net_quantity" and r.kind in ("placement", "character_height"))
    rule.minimum_glyph_height_mm = 2
    rule.required_view = "rear"
    rule.constraints_verified = True
    report = check_declarations(profile, fuse(candidates), views, images)
    assert next(r for r in report.results if r.field == "net_quantity" and r.kind == "character_height").status == "insufficient_evidence"
    assert next(r for r in report.results if r.field == "net_quantity" and r.kind == "placement").status == "pass"


@pytest.mark.parametrize("height,status", [(1, "fail"), (1.9996, "fail"), (2, "pass"), (3, "pass")])
def test_verified_glyph_threshold_with_coplanar_geometry(height, status):
    profile, views, images = context()
    rule = next(r for r in profile.rules if r.field == "net_quantity")
    rule.constraints_verified = True
    rule.minimum_glyph_height_mm = 2
    fields = fuse([sample(glyph_box=Box(x0=1, y0=1, x1=5, y1=1+height))])
    check = next(r for r in check_declarations(profile, fields, views, images).results if r.field == "net_quantity" and r.kind == "character_height")
    assert check.status == status and check.measured_mm == pytest.approx(height) and check.required_mm == 2
    views["rear"].calibration = Calibration(status="unavailable", reason="No marker")
    check = next(r for r in check_declarations(profile, fields, views, images).results if r.field == "net_quantity" and r.kind == "character_height")
    assert check.status == "insufficient_evidence"


def test_glyph_coverage_is_per_photo_not_per_duplicate_ocr_provider():
    profile, views, images = context()
    rule = next(r for r in profile.rules if r.field == "net_quantity")
    rule.constraints_verified = True
    rule.minimum_glyph_height_mm = 2
    measured = sample(glyph_box=Box(x0=1, y0=1, x1=5, y1=4))
    unlocated = sample().model_copy(update={"provider": "xiaomi"})
    fields = fuse([measured, unlocated])
    check = next(r for r in check_declarations(profile, fields, views, images).results if r.field == "net_quantity" and r.kind == "character_height")
    assert check.status == "pass" and len(check.evidence) == 2
    conflicting = fuse([measured, sample("200g")])
    check = next(r for r in check_declarations(profile, conflicting, views, images).results if r.field == "net_quantity" and r.kind == "character_height")
    assert check.status == "insufficient_evidence" and "conflicting" in check.reason
    views["front"] = views["rear"].model_copy(deep=True)
    fields = fuse([measured, unlocated, sample(view="front")])
    check = next(r for r in check_declarations(profile, fields, views, images).results if r.field == "net_quantity" and r.kind == "character_height")
    assert check.status == "insufficient_evidence"


def test_http_rechecks_legacy_ocr_without_provider_and_invalidates_on_removal(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(store, "FALLBACK_FILE", str(tmp_path / "inspections.json"))
    monkeypatch.setattr(store, "_MEMORY_INSPECTIONS", {})
    monkeypatch.setattr(store, "is_database_available", lambda: False)
    monkeypatch.setattr(settings, "TYPESAFE_API_KEY", None)
    from app.services import analysis as pipeline
    monkeypatch.setattr(pipeline, "recognize", lambda raw: pytest.fail("Recheck must not run OCR"))
    client = TestClient(app)
    assert client.post('/inspections/missing/checks').status_code == 404
    record = store.create_inspection_record({"product_name": "Check fixture", "product_category": "food_grocery"})
    base = f"/inspections/{record['id']}"
    assert client.post(base + '/checks').status_code == 409
    raw = b"immutable evidence"
    image = tmp_path / "label.jpg"
    image.write_bytes(raw)
    profile, views, images = context()
    views["rear"].file_hash = hashlib.sha256(raw).hexdigest()
    images["rear"].update(filepath=str(image), file_hash=views["rear"].file_hash)
    record["images"] = images
    record["views_captured"]["rear"] = True
    analysis = Analysis(views=views, fields=fuse([sample(box=Box(x0=0, y0=0, x1=50, y1=10))]), profile=profile, warnings=[],
        decision=DecisionResult(status="unavailable", model="fixture", message="No model call"))
    record["analysis"] = analysis.model_dump(mode="json", exclude={"checks"})
    response = client.post(base + '/checks', json={"origin": "domestic", "as_of": "2026-11-16"})
    assert response.status_code == 200, response.text
    saved = response.json()["analysis"]
    assert saved["checks"]["results"] and saved["fields"] == analysis.model_dump(mode="json")["fields"]
    assert response.json()["final_outcome"] == "Manual Review Required"
    store._MEMORY_INSPECTIONS.clear()
    store._load_persisted_fallback()
    assert client.get(base).json()["analysis"] == saved
    annotation = {"field": "net_quantity", "view": "rear", "box": {"x0": 1, "y0": 1, "x1": 4, "y1": 4}}
    annotated = client.post(base + '/checks', json={"glyph_measurements": [annotation]})
    assert annotated.status_code == 200, annotated.text
    height = next(c for c in annotated.json()["analysis"]["checks"]["results"] if c["field"] == "net_quantity" and c["kind"] == "character_height")
    assert height["measured_mm"] == 3 and height["status"] == "insufficient_evidence"
    assert client.post(base + '/checks', json={"glyph_measurements": [annotation, annotation]}).status_code == 422
    cleared = client.post(base + '/checks', json={"clear_glyph_measurements": True})
    assert cleared.status_code == 200
    assert all(c["measured_mm"] is None for c in cleared.json()["analysis"]["checks"]["results"])
    annotation["view"] = "front"
    assert client.post(base + '/checks', json={"glyph_measurements": [annotation]}).status_code == 422
    annotation["view"] = "rear"
    annotation["box"]["x1"] = 999
    assert client.post(base + '/checks', json={"glyph_measurements": [annotation]}).status_code == 422
    image.write_bytes(b"changed evidence")
    assert client.post(base + '/checks').status_code == 409
    image.write_bytes(raw)
    assert client.delete(base + '/images/rear').status_code == 200
    assert client.get(base).json()["analysis"] is None
    assert client.post(base + '/checks').status_code == 409

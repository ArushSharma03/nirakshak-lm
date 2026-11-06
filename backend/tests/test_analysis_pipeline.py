"""Milestone tests at geometry, model-contract and HTTP persistence boundaries."""

from datetime import date
from pathlib import Path
import copy
import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr, ValidationError
import httpx

from app.core.config import settings
from app.engine.profiles import RuleSet, load_rules, select_profile
from app.main import app
from app.schemas.analysis import Analysis, AnalysisRequest, Box, Calibration, Candidate, OCRLine, OCRResult, OCRWord, ProfileRequest
from app.services import analysis as pipeline
from app.services.calibration import calibrate, physical_height
from app.services.decision import judge_fields
from app.services.extraction import extract, fuse
from app.services.marker_detector import detect_marker, generate_reference_marker_image
from app.services.ocr import tesseract_ocr
from app.services import inspection_store as store


def uncalibrated():
    return Calibration(status="unavailable", reason="No marker")


def candidate(value, view="front", confidence=0.9):
    return Candidate(field="net_quantity", value=value, view=view, provider="test", source_text=f"Net quantity: {value}", confidence=confidence)


def test_known_marker_scale_and_confirmation():
    marker = detect_marker(generate_reference_marker_image(size_px=300))
    assert calibrate(marker, False).status == "unavailable"
    calibration = calibrate(marker, True)
    assert calibration.status == "available"
    assert calibration.pixels_per_mm == pytest.approx(6, abs=0.04)
    assert physical_height(Box(x0=100, y0=100, x1=200, y1=130), calibration) == pytest.approx(5, abs=0.05)
    assert physical_height(None, calibration) is None
    assert physical_height(Box(x0=1, y0=1, x1=10, y1=10), uncalibrated()) is None


def test_oblique_and_nonstandard_markers_do_not_calibrate():
    marker = detect_marker(generate_reference_marker_image())
    marker.marker_id = 3
    assert calibrate(marker, True).status == "unavailable"
    marker.marker_id = 0
    marker.bounding_box = [0, 0, 100, 0, 100, 40, 0, 40]
    assert calibrate(marker, True).status == "unavailable"


def test_public_packaging_pattern_does_not_become_reference_marker():
    raw = (Path(__file__).resolve().parents[2] / "evaluation/fixtures/parle-g-rear.jpg").read_bytes()
    marker = detect_marker(raw)
    assert not marker.detected
    assert marker.estimated_ppm is None


def test_tsv_quotes_are_literal_ocr_text(monkeypatch):
    from types import SimpleNamespace
    import subprocess
    tsv = "level\tpage_num\tblock_num\tpar_num\tline_num\tleft\ttop\twidth\theight\tconf\ttext\n"
    tsv += '5\t1\t1\t1\t1\t10\t10\t10\t10\t90\t"quoted\n'
    tsv += '5\t1\t1\t1\t2\t10\t30\t10\t10\t90\tquantity\n'
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: SimpleNamespace(stdout=tsv.encode()))
    result = tesseract_ocr(b"fixture")
    assert [line.text for line in result.lines] == ['"quoted', 'quantity']


def test_contextual_manufacturer_continuation_keeps_anchor_without_inventing_boxes():
    ocr = OCRResult(provider="xiaomi", model="test", status="ok", lines=[
        OCRLine(text="MANUFACTURED BY:"), OCRLine(text="Sample Foods Pvt Ltd"),
        OCRLine(text="MRP:"), OCRLine(text="Nutrition 42"),
    ])
    found = extract(ocr, "rear", uncalibrated())
    assert len(found) == 1 and found[0].field == "manufacturer"
    assert found[0].source_text == "MANUFACTURED BY:\nSample Foods Pvt Ltd"
    assert found[0].box is None and found[0].confidence is None


def test_spatial_and_hindi_extraction_does_not_borrow_distant_values():
    ocr = OCRResult(provider="test", model="test", status="ok", lines=[
        OCRLine(text="Net quantity:", box=Box(x0=10, y0=10, x1=140, y1=30)),
        OCRLine(text="100 g", box=Box(x0=12, y0=35, x1=80, y1=55), confidence=0.85),
        OCRLine(text="शुद्ध मात्रा: २०० ग्राम"),
        OCRLine(text="MRP:"), OCRLine(text="Nutrition 42"),
    ])
    found = extract(ocr, "rear", uncalibrated())
    assert [c.value for c in found] == ["100 g", "200 ग्राम"]
    assert found[0].box.y0 == 35
    assert found[1].confidence is None


def test_fusion_retains_conflicts_even_when_confidence_is_high():
    fields = fuse([candidate("100 g"), candidate("100g", "rear", 0.95)])
    qty = next(f for f in fields if f.field == "net_quantity")
    assert qty.status == "observed"
    assert qty.evidence[0].view == "rear"
    fields = fuse([candidate("100 g", confidence=0.99), candidate("200 g", "rear", 0.3)])
    qty = next(f for f in fields if f.field == "net_quantity")
    assert qty.status == "conflict" and qty.value is None
    assert len(qty.evidence) == 2
    assert next(f for f in fields if f.field == "mrp").status == "missing"


def test_profile_origin_dates_and_unsupported_categories():
    request = ProfileRequest(category="food_grocery", origin="imported", as_of=date(2026, 11, 6))
    profile = select_profile(request)
    assert profile.status == "selected"
    assert "import-origin" in [r.id for r in profile.rules]
    assert "import-origin" not in [r.id for r in select_profile(request.model_copy(update={"origin": "domestic"})).rules]
    assert select_profile(request.model_copy(update={"origin": "unknown"})).status == "review_required"
    assert select_profile(request.model_copy(update={"category": "beverage"})).status == "unsupported"
    assert select_profile(request.model_copy(update={"as_of": date(2010, 1, 1)})).status == "unsupported"


def test_rule_versions_switch_at_exclusive_end_date():
    data = load_rules().model_dump(mode="json")
    old = data["rules"][0]
    old["effective_to"] = "2026-01-01"
    newer = dict(old, version="2026", effective_from="2026-01-01", effective_to=None)
    data["rules"].append(newer)
    rules = RuleSet.model_validate(data)
    request = ProfileRequest(category="food_grocery", origin="domestic", as_of=date(2026, 1, 1))
    assert [r.version for r in select_profile(request, rules).rules if r.id == old["id"]] == ["2026"]
    data["rules"][-1]["effective_from"] = "2025-01-01"
    with pytest.raises(ValidationError, match="Overlapping"):
        RuleSet.model_validate(data)


def test_jev_missing_key_and_invalid_candidate_are_explicit(monkeypatch):
    fields = fuse([candidate("100 g")])
    monkeypatch.setattr(settings, "TYPESAFE_API_KEY", None)
    assert judge_fields(fields).status == "unavailable"
    monkeypatch.setattr(settings, "TYPESAFE_API_KEY", SecretStr("test-key"))
    def invalid(*args, **kwargs):
        return httpx.Response(200, request=httpx.Request("POST", "https://api.typesafe.ai/v1/systemone"), json={
            "model": "jev-test", "answers": {"net_quantity": {"type": "choice", "choice": "invented", "confidence": 1,
            "probabilities": {"invented": 1}}}, "usage": {"input_tokens": 10, "output_tokens": 1}})
    monkeypatch.setattr(httpx, "post", invalid)
    assert judge_fields(fields).status == "failed"


def test_numeric_height_uses_value_word_instead_of_anchor():
    calibration = calibrate(detect_marker(generate_reference_marker_image(size_px=300)), True)
    ocr = OCRResult(provider="test", model="test", status="ok", lines=[OCRLine(
        text="Net quantity: 100 g", box=Box(x0=10, y0=10, x1=220, y1=50), words=[
            OCRWord(text="Net", box=Box(x0=10, y0=10, x1=50, y1=50), confidence=0.9),
            OCRWord(text="quantity:", box=Box(x0=55, y0=10, x1=140, y1=50), confidence=0.9),
            OCRWord(text="100", box=Box(x0=145, y0=20, x1=190, y1=38), confidence=0.8),
            OCRWord(text="g", box=Box(x0=195, y0=20, x1=220, y1=44), confidence=0.7),
        ])])
    found = extract(ocr, "front", calibration)[0]
    assert found.box.x0 == 145
    assert found.height_mm == pytest.approx(3, abs=0.05)
    assert found.confidence == pytest.approx(0.75)


def test_valid_jev_suggestion_retains_conflicting_evidence(monkeypatch):
    fields = fuse([candidate("100 g"), candidate("200 g", "rear")])
    monkeypatch.setattr(settings, "TYPESAFE_API_KEY", SecretStr("test-key"))
    calls = []
    def respond(*args, **kwargs):
        calls.append(kwargs["json"])
        return httpx.Response(200, request=httpx.Request("POST", "https://api.typesafe.ai/v1/systemone"), json={
            "model": settings.TYPESAFE_MODEL, "usage": {"input_tokens": 10, "output_tokens": 1},
            "answers": {"net_quantity": {"type": "choice", "choice": "none", "confidence": 0.8,
                "probabilities": {"candidate_0": 0.1, "candidate_1": 0.1, "none": 0.8}}}})
    monkeypatch.setattr(httpx, "post", respond)
    result = judge_fields(fields)
    assert result.status == "ok" and result.answers["net_quantity"].choice == "none"
    assert len(calls) == 1
    assert next(f for f in fields if f.field == "net_quantity").status == "conflict"


def test_jev_opt_out_and_successful_reuse_do_not_call_provider(monkeypatch):
    monkeypatch.setattr(pipeline, "judge_fields", lambda fields: pytest.fail("Unexpected paid request"))
    request = AnalysisRequest(as_of=date(2026, 11, 6))
    record = {"product_category": "food_grocery"}
    first = pipeline.analyze_record(record, request)
    assert first.decision.status == "unavailable"
    record["analysis"] = first.model_dump(mode="json")
    record["analysis"]["decision"].update(status="ok", model=settings.TYPESAFE_MODEL)
    assert pipeline.analyze_record(record, request.model_copy(update={"use_jev": True})).decision.status == "ok"


def test_detail_recovery_stops_on_quantity_and_keeps_source_provenance(tmp_path, monkeypatch):
    image = tmp_path / "label.png"
    image.write_bytes(generate_reference_marker_image())
    monkeypatch.setattr(settings, "XIAOMI_OCR_ENABLED", True)
    monkeypatch.setattr(pipeline, "recognize", lambda raw: [OCRResult(provider="xiaomi", model="test", status="ok",
        lines=[OCRLine(text="MANUFACTURED BY: Example Foods")])])
    def details(raw):
        yield OCRResult(provider="xiaomi_detail_0", model="test", status="ok", lines=[OCRLine(text="NET WEIGHT: 70g")],
            message="Detail scan of original-image region [0, 0, 100, 100].")
        pytest.fail("Detail scans must stop once the quantity is recovered")
    monkeypatch.setattr(pipeline, "detail_regions", details)
    analysis = pipeline.analyze_record({"product_category": "food_grocery", "images": {"rear": {"filepath": str(image)}}},
        AnalysisRequest(as_of=date(2026, 11, 6)))
    quantity = next(field for field in analysis.fields if field.field == "net_quantity")
    assert quantity.value == "70g" and quantity.evidence[0].provider == "xiaomi_detail_0"
    assert quantity.evidence[0].box is None and quantity.evidence[0].height_mm is None


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(store, "FALLBACK_FILE", str(tmp_path / "inspections.json"))
    monkeypatch.setattr(store, "_MEMORY_INSPECTIONS", {})
    monkeypatch.setattr(store, "is_database_available", lambda: False)
    monkeypatch.setattr(settings, "XIAOMI_OCR_ENABLED", False)
    monkeypatch.setattr(settings, "TYPESAFE_API_KEY", None)
    return TestClient(app)


def test_http_capture_analyze_reload_and_retake(client):
    record = client.post("/inspections/", json={"product_name": "Cookies"}).json()
    inspection_id = record["id"]
    assert client.post(f"/inspections/{inspection_id}/analyze", json={"as_of": "2026-11-06"}).status_code == 409
    image = np.full((500, 1100, 3), 255, np.uint8)
    cv2.putText(image, "Net quantity: 100 g", (40, 200), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 0), 3)
    _, png = cv2.imencode(".png", image)
    assert client.post("/inspections/missing/images", data={"view_type": "front"}, files={"file": ("test.png", png.tobytes())}).status_code == 404
    assert client.post(f"/inspections/{inspection_id}/images", data={"view_type": "front"}, files={"file": ("bad.png", b"bad")}).status_code == 422
    upload = client.post(f"/inspections/{inspection_id}/images", data={"view_type": "front"}, files={"file": ("test.png", png.tobytes())})
    assert upload.status_code == 200
    response = client.post(f"/inspections/{inspection_id}/analyze", json={"as_of": "2026-11-06", "origin": "domestic"})
    assert response.status_code == 200, response.text
    analysis = response.json()["analysis"]
    qty = next(f for f in analysis["fields"] if f["field"] == "net_quantity")
    assert qty["value"] == "100 g", analysis
    assert qty["evidence"][0]["box"] is not None
    assert analysis["views"]["front"]["calibration"]["status"] == "unavailable"
    assert analysis["decision"]["status"] == "unavailable"
    assert response.json()["final_outcome"] == "Manual Review Required"
    store._MEMORY_INSPECTIONS.clear()
    store._load_persisted_fallback()
    assert client.get(f"/inspections/{inspection_id}").json()["analysis"] == analysis
    stale = Analysis.model_validate(analysis)
    replacement = client.post(f"/inspections/{inspection_id}/images", data={"view_type": "front"}, files={"file": ("test.png", png.tobytes())})
    assert replacement.json()["analysis"] is None
    assert client.delete(f"/inspections/{inspection_id}/images/front").json()["views_captured"]["front"] is False
    with pytest.raises(ValueError, match="Evidence changed"):
        store.save_analysis(inspection_id, stale)

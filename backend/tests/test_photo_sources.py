"""Photo processing provenance and source lookup at OCR and HTTP boundaries."""

from datetime import date
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.quality_assessor import assess_image_quality
from app.services import analysis as pipeline
from app.schemas.analysis import AnalysisRequest, OCRResult, OCRLine, Calibration
from app.services.extraction import extract
from app.services.marker_detector import generate_reference_marker_image


def test_clipped_image_cannot_hide_failed_metrics_behind_high_average():
    image = np.zeros((720, 1280, 3), dtype=np.uint8)
    image[:, 1::2] = 255
    result = assess_image_quality(image)
    assert result["overall_status"] == "Retake Recommended"
    assert result["composite_score"] <= 59
    assert not result["is_acceptable"]


def test_warning_resolution_cannot_receive_pass_band_score():
    image = np.full((600, 800, 3), 180, dtype=np.uint8)
    image[:, 1::2] = 60
    result = assess_image_quality(image)
    assert result["overall_status"] == "Warning"
    assert result["composite_score"] <= 79


def test_source_search_retains_limitations_and_exact_official_links():
    with TestClient(app) as client:
        index = client.get("/profiles/regulations").json()
        assert len(index["documents"]) == 41
        source_ids = {source["id"] for source in index["sources"]}
        assert all(doc["source_id"] in source_ids for doc in index["documents"])
        result = client.get("/profiles/regulations", params={"q": "  2026  "}).json()
        assert result["retrieved_on"] == index["retrieved_on"]
        assert result["unknowns"] == index["unknowns"]
        assert result["documents"]
        assert all("2026" in str(doc) for doc in result["documents"])
        assert client.get("/profiles/regulations", params={"q": "no-such-regulation"}).json()["documents"] == []
        assert client.get("/profiles/regulations", params={"q": "x" * 201}).status_code == 422


@pytest.mark.parametrize("reading,expected_providers", [("100g", ["xiaomi"]), ("70g", ["tesseract", "xiaomi"])])
def test_tesseract_cannot_supply_or_override_primary_reading(tmp_path, monkeypatch, reading, expected_providers):
    image = tmp_path / "label.png"
    image.write_bytes(generate_reference_marker_image())
    monkeypatch.setattr(pipeline, "recognize", lambda _: [
        OCRResult(provider="xiaomi", model="test", status="ok", lines=[OCRLine(text="NET WEIGHT: 70g")]),
        OCRResult(provider="tesseract", model="test", status="ok", lines=[
            OCRLine(text=f"NET WEIGHT: {reading}", confidence=.9), OCRLine(text="MRP: Rs 50")]),
    ])
    result = pipeline.analyze_record({"product_category": "food_grocery", "images": {"rear": {"filepath": str(image)}}}, AnalysisRequest(as_of=date(2026, 11, 12)))
    fields = {field.field: field for field in result.fields}
    assert fields["net_quantity"].value == "70g"
    assert fields["mrp"].status == "missing"
    assert [c.provider for c in fields["net_quantity"].evidence] == expected_providers
    assert result.views["rear"].ocr[1].lines[0].text == f"NET WEIGHT: {reading}"


def test_primary_unavailable_does_not_silently_use_tesseract(tmp_path, monkeypatch):
    image = tmp_path / "label.png"
    image.write_bytes(generate_reference_marker_image())
    monkeypatch.setattr(pipeline, "recognize", lambda _: [
        OCRResult(provider="xiaomi", model="test", status="unavailable", message="Checkpoint unavailable"),
        OCRResult(provider="tesseract", model="test", status="ok", lines=[OCRLine(text="NET WEIGHT: 100g")]),
    ])
    result = pipeline.analyze_record({"product_category": "food_grocery", "images": {"rear": {"filepath": str(image)}}}, AnalysisRequest(as_of=date(2026, 11, 12)))
    assert all(field.status == "missing" for field in result.fields)
    assert any("Checkpoint unavailable" in warning for warning in result.warnings)


@pytest.mark.parametrize("text,field,value", [
    ("MFD & USE BY:", None, None),
    ("MFD.-USE BY-MFG.By:", None, None),
    ("NESTLÉ CONSUMER CARE,", None, None),
    ("Mfg. By: Nestlé India Limited,", "manufacturer", "Nestlé India Limited"),
    ("Mfg. & Mkt. by: PEPSICO INDIA HOLDINGS PVT. LTD.", "manufacturer", "PEPSICO INDIA HOLDINGS PVT. LTD"),
    ("Mfg. by: Foods Ltd, 15/16 Industrial Area", "manufacturer", "Foods Ltd, 15/16 Industrial Area"),
    ("MFG DATE: 12/11/2026", "date", "12/11/2026"),
    ("MFD: 11/2026", "date", "11/2026"),
    ("Packed on: 2026-11-12", "date", "2026-11-12"),
    ("MFG: NOV 2026", "date", "NOV 2026"),
])
def test_real_wrapper_labels_do_not_become_dates_or_punctuation_values(text, field, value):
    result = extract(OCRResult(provider="xiaomi", model="test", status="ok", lines=[OCRLine(text=text)]), "rear", Calibration(status="unavailable", reason="No marker"))
    assert [(c.field, c.value) for c in result] == ([] if field is None else [(field, value)])

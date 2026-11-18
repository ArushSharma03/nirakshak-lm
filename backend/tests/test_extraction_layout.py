"""Regression cases for mixed columns, empty labels and incomplete OCR adapters."""

from types import SimpleNamespace
import io
import cv2
import numpy as np
from pathlib import Path
from fastapi.testclient import TestClient
import pytest

from app.schemas.analysis import Box, Calibration, OCRLine, OCRResult
from app.services.extraction import canonical, extract, fuse, price
from app.services import ocr
from app.services import inspection_store as store
from app.services import analysis as pipeline
from app.main import app
from app.schemas.analysis import AnalysisRequest


def located(text, x=10, y=10, width=140, height=20):
    return OCRLine(text=text, box=Box(x0=x, y0=y, x1=x + width, y1=y + height))


def fields(lines, status="ok"):
    return {f.field: f for f in fuse(extract(OCRResult(provider="test", model="fixture", status=status, lines=lines),
        "rear", Calibration(status="unavailable", reason="No marker")))}


def test_contact_block_follows_geometry_across_interleaved_columns():
    result = fields([
        located("NESTLE CONSUMER CARE,"),
        located("NUTRITIONAL INFORMATION", x=400, y=30),
        located("1800 103 1947", y=62),
        located("WECARE@IN.NESTLE.COM", y=36),
        located("NET QUANTITY: 70g", y=100),
    ])
    care = result["consumer_care"]
    assert care.value == "WECARE@IN.NESTLE.COM\n1800 103 1947"
    assert care.evidence[0].source_text == "NESTLE CONSUMER CARE,\nWECARE@IN.NESTLE.COM\n1800 103 1947"
    assert care.evidence[0].box == Box(x0=10, y0=36, x1=150, y1=82)
    assert care.evidence[0].confidence is None
    assert result["net_quantity"].value == "70g"


def test_split_numeric_value_can_be_right_of_label_and_out_of_order():
    result = fields([located("70 g", x=170), located("Net weight:"), located("100 g", x=500)])
    assert result["net_quantity"].value == "70 g"
    assert result["net_quantity"].evidence[0].box.x0 == 170


@pytest.mark.parametrize("neighbor", [located("100 g", x=400, y=36), located("Nutrition 100 g", y=36), located("100 g", y=200)])
def test_numeric_heading_does_not_borrow_other_column_nutrition_or_distant_value(neighbor):
    assert fields([located("NET QTY:"), neighbor])["net_quantity"].status == "missing"


@pytest.mark.parametrize("text", ["MRP: see batch 12345", "MRP: Nutrition 42", "MFG: see address 15/11/2026", "NET WEIGHT: per 100g", "Mfg. By: [Refer letter after Use by and see below]", "MFD.-USE BY-MFG.By:\nRefiner letter after Use by and see below"])
def test_instructional_text_and_later_numbers_are_not_declarations(text):
    assert all(f.status == "missing" for f in fields([OCRLine(text=text)]).values())


def test_same_line_declarations_end_at_next_heading():
    result = fields([OCRLine(text="Manufactured by: Sample Foods Ltd MRP: Rs 50 Net quantity: 100g")])
    assert result["manufacturer"].value == "Sample Foods Ltd"
    assert result["mrp"].value == "rs 50"
    assert result["net_quantity"].value == "100g"
    assert fields([OCRLine(text="Mfg. By: See's Foods Ltd MRP: see side panel")])["manufacturer"].value == "See's Foods Ltd"


def test_fusion_and_checks_share_equivalent_quantity_units_without_merging_dimensions():
    assert canonical("net_quantity", "0.1kg") == canonical("net_quantity", "100g")
    assert canonical("net_quantity", "1l") == canonical("net_quantity", "1000ml")
    assert canonical("net_quantity", "100g") != canonical("net_quantity", "100ml")
    result = fields([OCRLine(text="Net weight: 0.1kg"), OCRLine(text="Net quantity: 100g")])
    assert result["net_quantity"].status == "observed"
    assert len(result["net_quantity"].evidence) == 2


def test_alternate_real_headings_and_wrapped_contacts():
    result = fields([OCRLine(text="MANUFACTURED IN OMAN BY AL SALAN FOOD INDUSTRIES"),
        OCRLine(text="THE CONSUMER SERVICES MANAGER,"), OCRLine(text="Sample Foods Ltd"),
        OCRLine(text="OR CALL US AT 1800 22 4020"), OCRLine(text="OR EMAIL US AT help@example.com"),
        OCRLine(text="*Based on internal grading and quality parameters.")])
    assert result["manufacturer"].value == "AL SALAN FOOD INDUSTRIES"
    assert result["consumer_care"].value.endswith("help@example.com")
    assert "Based" not in result["consumer_care"].value


def test_duplicate_spotting_regions_do_not_multiply_evidence():
    line = located("Net quantity: 100g")
    assert len(fields([line, line.model_copy(deep=True)])["net_quantity"].evidence) == 1


@pytest.mark.parametrize("printed,expected", [("₹1,000.50", "1000.5"), ("Rs 1,00,000", "100000"), ("₹1,234,567.00", "1234567"), ("Rs 50.00", "50")])
def test_currency_groups_are_preserved_and_normalized_without_float_rounding(printed, expected):
    value = fields([OCRLine(text=f"MRP: {printed}")])["mrp"].value
    assert value is not None and canonical("mrp", value) == expected
    assert price(value) is not None


@pytest.mark.parametrize("printed", ["18%", "18 %", "1,00", "50.999", "-50"])
def test_invalid_price_does_not_become_a_valid_numeric_prefix(printed):
    assert fields([OCRLine(text=f"MRP: {printed}")])["mrp"].status == "missing"


def test_named_text_labels_can_continue_but_negative_quantity_cannot_become_positive():
    result = fields([OCRLine(text="Country of origin:"), OCRLine(text="India"),
        OCRLine(text="Generic name:"), OCRLine(text="Biscuits"), OCRLine(text="Net quantity: -100g")])
    assert result["country_of_origin"].value == "India"
    assert result["generic_name"].value == "Biscuits"
    assert result["net_quantity"].status == "missing"


@pytest.mark.parametrize("last_token,text,status,quantity,price", [(2, "NET WEIGHT: 100g\nMRP: 99", "ok", "100g", "99"), (8, "NET WEIGHT: 100g\nMRP: 99", "partial", "100g", None), (8, "LET", "partial", None, None)])
def test_xiaomi_cutoff_retains_only_complete_lines(monkeypatch, last_token, text, status, quantity, price):
    torch = pytest.importorskip("torch")
    from PIL import Image
    seen_sizes = []
    class Inputs(dict):
        def to(self, device):
            return self
    def prepare(messages, **kwargs):
        seen_sizes.append(messages[0]["content"][0]["image"].size)
        assert kwargs["processor_kwargs"]["images_kwargs"]["size"]["longest_edge"] == ocr.settings.OCR_MAX_PIXELS
        return Inputs(input_ids=torch.tensor([[0]]))
    processor = SimpleNamespace(
        apply_chat_template=prepare,
        batch_decode=lambda *a, **kw: [text],
    )
    model = SimpleNamespace(device="cpu", generation_config=SimpleNamespace(eos_token_id=2),
        generate=lambda **kw: torch.tensor([[0, 4, last_token]]))
    monkeypatch.setattr(ocr.settings, "XIAOMI_OCR_ENABLED", True)
    monkeypatch.setattr(ocr, "_xiaomi", lambda: (processor, model))
    image = Image.new("RGB", (80, 40), "white")
    exif = image.getexif()
    exif[274] = 6
    stream = io.BytesIO()
    image.save(stream, format="JPEG", exif=exif)
    raw = stream.getvalue()
    result = ocr.xiaomi_ocr(raw)
    assert seen_sizes == [(40, 80)]
    assert cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR).shape[:2] == (80, 40)
    assert result.status == status
    assert result.raw_text == text
    extracted = fields(result.lines, status=result.status)
    assert extracted["net_quantity"].value == quantity
    assert extracted["mrp"].value == price


def test_malformed_tesseract_row_cannot_crash_or_poison_valid_geometry(monkeypatch):
    tsv = "level\tpage_num\tblock_num\tpar_num\tline_num\tleft\ttop\twidth\theight\tconf\ttext\n"
    tsv += "5\t1\t1\t1\t1\t10\t10\t20\t10\t90\tNet\n"
    tsv += "5\t1\t1\t1\t1\tbad\t10\t20\t10\tnan\tbad\n"
    monkeypatch.setattr(ocr.subprocess, "run", lambda *a, **kw: SimpleNamespace(stdout=tsv.encode()))
    _, encoded = cv2.imencode(".png", np.full((100, 100, 3), 255, dtype=np.uint8))
    result = ocr.tesseract_ocr(encoded.tobytes())
    assert result.status == "partial" and result.lines[0].text == "Net"
    assert "Skipped 1" in result.message


def test_tesseract_receives_display_oriented_pixels_instead_of_exif_metadata(monkeypatch):
    from PIL import Image
    image = Image.new("RGB", (80, 40), "white")
    exif = image.getexif()
    exif[274] = 6
    stream = io.BytesIO()
    image.save(stream, format="JPEG", exif=exif)
    def run(*args, **kwargs):
        decoded = cv2.imdecode(np.frombuffer(kwargs["input"], np.uint8), cv2.IMREAD_COLOR)
        assert decoded.shape[:2] == (80, 40)
        assert kwargs["input"].startswith(b"\x89PNG")
        return SimpleNamespace(stdout=b"level\ttext\n")
    monkeypatch.setattr(ocr.subprocess, "run", run)
    assert ocr.tesseract_ocr(stream.getvalue()).status == "ok"


def test_detail_reads_are_bounded_and_crop_original_geometry(monkeypatch):
    image = np.full((600, 1000, 3), 255, dtype=np.uint8)
    _, encoded = cv2.imencode(".png", image)
    sizes = []
    def read(raw):
        sizes.append(cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR).shape[:2])
        return OCRResult(provider="xiaomi", model="fixture", status="ok", lines=[])
    monkeypatch.setattr(ocr, "xiaomi_ocr", read)
    box = Box(x0=100, y0=400, x1=300, y1=430)
    scans = list(ocr.detail_regions(encoded.tobytes(), boxes=[box, box]))
    assert sizes == [(210, 460)] and len(scans) == 1
    assert "[40, 310, 500, 520]" in scans[0].message
    assert scans[0].lines == []
    boxes = [Box(x0=100 + i * 50, y0=400, x1=300 + i * 50, y1=430) for i in range(5)]
    assert len(list(ocr.detail_regions(encoded.tobytes(), boxes=boxes))) == 4


def test_partial_transcript_persists_through_api_and_rechecks_without_repeating_ocr(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(store, "FALLBACK_FILE", str(tmp_path / "records.json"))
    monkeypatch.setattr(store, "_MEMORY_INSPECTIONS", {})
    monkeypatch.setattr(store, "is_database_available", lambda: False)
    monkeypatch.setattr(ocr.settings, "XIAOMI_OCR_ENABLED", False)
    calls = []
    def recognize(raw):
        calls.append(raw)
        return [OCRResult(provider="xiaomi", model="fixture", status="partial", message="Cutoff",
            lines=[OCRLine(text="NET WEIGHT: 100g")], raw_text="NET WEIGHT: 100g\nMRP: 9")]
    monkeypatch.setattr(pipeline, "recognize", recognize)
    raw = (Path(__file__).resolve().parents[2] / "evaluation/fixtures/wrappers/good-day.jpg").read_bytes()
    client = TestClient(app)
    record = client.post("/inspections/", json={"product_name": "Partial OCR evidence"}).json()
    base = f"/inspections/{record['id']}"
    assert client.post(base + "/images", data={"view_type": "rear"}, files={"file": ("source.jpg", raw, "image/jpeg")}).status_code == 200
    assert client.post(base + "/analyze", json={"as_of": "2026-11-17", "reuse_ocr": True}).status_code == 409
    response = client.post(base + "/analyze", json={"origin": "imported", "as_of": "2026-11-17", "use_jev": False})
    assert response.status_code == 200, response.text
    saved = response.json()["analysis"]
    assert saved["views"]["rear"]["ocr"][0]["status"] == "partial"
    assert saved["views"]["rear"]["ocr"][0]["raw_text"].endswith("MRP: 9")
    assert next(f for f in saved["fields"] if f["field"] == "mrp")["status"] == "missing"
    store._MEMORY_INSPECTIONS.clear()
    store._load_persisted_fallback()
    assert client.get(base).json()["analysis"] == saved
    checked = client.post(base + "/checks", json={"origin": "imported", "as_of": "2026-11-17"})
    assert checked.status_code == 200 and len(calls) == 1
    assert checked.json()["analysis"]["fields"] == saved["fields"]
    monkeypatch.setattr(ocr.settings, "XIAOMI_OCR_ENABLED", True)
    monkeypatch.setattr(pipeline, "recognize", lambda _: pytest.fail("Saved extraction must not run OCR"))
    monkeypatch.setattr(pipeline, "detail_regions", lambda *a, **kw: pytest.fail("Saved extraction must not run detail OCR"))
    rebuilt = client.post(base + "/analyze", json={"as_of": "2026-11-17", "origin": "imported", "reuse_ocr": True})
    assert rebuilt.status_code == 200 and rebuilt.json()["analysis"]["fields"] == saved["fields"]
    assert rebuilt.json()["analysis"]["views"] == saved["views"]
    image_path = Path(store.get_inspection_record(record["id"])["images"]["rear"]["filepath"])
    image_path.write_bytes(b"changed source")
    assert client.post(base + "/analyze", json={"as_of": "2026-11-17", "reuse_ocr": True}).status_code == 409
    assert client.delete(base + "/images/rear").json()["analysis"] is None
    assert client.post(base + "/checks").status_code == 409


def test_partial_manufacturer_continues_after_blank_quantity_crop(tmp_path, monkeypatch):
    _, encoded = cv2.imencode(".png", np.full((600, 1000, 3), 255, dtype=np.uint8))
    image = tmp_path / "label.png"
    image.write_bytes(encoded.tobytes())
    heading = located("NET QTY:")
    monkeypatch.setattr(ocr.settings, "XIAOMI_OCR_ENABLED", True)
    monkeypatch.setattr(pipeline, "recognize", lambda _: [
        OCRResult(provider="xiaomi", model="fixture", status="partial", lines=[OCRLine(text="NET QTY:")], raw_text="NET QTY:\nMfg. & Mkt. by"),
        OCRResult(provider="tesseract", model="fixture", status="ok", lines=[heading]),
    ])
    def details(raw, *, boxes, include_quadrants):
        assert boxes == [heading.box] and include_quadrants
        yield OCRResult(provider="xiaomi_detail_0", model="fixture", status="ok", lines=[OCRLine(text="NET QTY:")])
        yield OCRResult(provider="xiaomi_detail_1", model="fixture", status="ok", lines=[OCRLine(text="Mfg. & Mkt. by: Sample Foods Ltd")])
    monkeypatch.setattr(pipeline, "detail_regions", details)
    result = pipeline.analyze_record({"product_category": "food_grocery", "images": {"rear": {"filepath": str(image)}}}, AnalysisRequest(as_of="2026-11-17"))
    by_field = {f.field: f for f in result.fields}
    assert by_field["net_quantity"].status == "missing"
    assert by_field["manufacturer"].value == "Sample Foods Ltd"
    assert len(result.views["rear"].ocr) == 4


def test_missing_price_gets_a_primary_read_even_when_quantity_was_already_found(tmp_path, monkeypatch):
    _, encoded = cv2.imencode(".png", np.full((600, 1000, 3), 255, dtype=np.uint8))
    image = tmp_path / "label.png"
    image.write_bytes(encoded.tobytes())
    heading = located("MRP: Rs 50")
    monkeypatch.setattr(ocr.settings, "XIAOMI_OCR_ENABLED", True)
    monkeypatch.setattr(pipeline, "recognize", lambda _: [
        OCRResult(provider="xiaomi", model="fixture", status="ok", lines=[OCRLine(text="Net weight: 100g")]),
        OCRResult(provider="tesseract", model="fixture", status="ok", lines=[heading]),
    ])
    def details(raw, *, boxes):
        assert boxes == [heading.box]
        yield OCRResult(provider="xiaomi_detail_0", model="fixture", status="ok", lines=[OCRLine(text="MRP: Rs 50")])
    monkeypatch.setattr(pipeline, "detail_regions", details)
    result = pipeline.analyze_record({"product_category": "food_grocery", "images": {"rear": {"filepath": str(image)}}}, AnalysisRequest(as_of="2026-11-17"))
    by_field = {f.field: f for f in result.fields}
    assert by_field["net_quantity"].value == "100g" and by_field["mrp"].value == "rs 50"
    assert {c.provider for c in by_field["mrp"].evidence} == {"xiaomi_detail_0", "tesseract"}

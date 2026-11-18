"""A photo is the only input: name and origin come from the label."""

from datetime import date

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.schemas.analysis import Analysis, DecisionAnswer, DecisionResult, OCRLine, OCRResult, Profile, ProfileRequest, ViewAnalysis
from app.services import inspection_store as store
from app.services.coding_window import coding_window
from app.services.extraction import extract, fuse
from app.services.label_facts import label_name, label_origin, name_options


def analysis_of(*lines: str) -> Analysis:
    ocr = OCRResult(provider="xiaomi", model="test", status="ok", lines=[OCRLine(text=line) for line in lines])
    request = ProfileRequest(category="food_grocery", as_of=date(2026, 11, 6))
    return Analysis(views={"front": ViewAnalysis(file_hash="x", ocr=[ocr])}, fields=fuse(extract(ocr, "front")),
        profile=Profile(status="review_required", reason="", inputs=request), warnings=[],
        decision=DecisionResult(status="unavailable", model="test", message=""))


@pytest.mark.parametrize(("lines", "name"), [
    # Real rear-panel transcripts from evaluation/live-pipeline-results.json and public-image-result.json.
    (["Parle-G Gluco BISCUITS", "INGREDIENTS: WHEAT FLOUR (57%)", "Net wt. 70 g"], "Parle-G Gluco BISCUITS · 70 g"),
    (["LET'S TALK", "NESTLE CONSUMER CARE,", "P.O. BAG NO. 2, NEW DELHI-110001", "WECARE@IN.NESTLE.COM", "1800 103 1947", "GOOD TO KNOW"], None),
    (["Lay's is a Trade Mark of PepsiCo, Inc.", "THE CONSUMER SERVICES MANAGER,", "Manufactured by: PepsiCo India Holdings Pvt. Ltd.,"], "PepsiCo India Holdings Pvt. Ltd"),
    (["Nutrition Facts", "Saturated Fat 0.5g (12%)", "Net Weight: 100 g"], "100 g"),
])
def test_label_name_skips_panel_boilerplate(lines, name):
    assert label_name(analysis_of(*lines)) == name


def test_jev_name_picks_split_a_logo_line_into_brand_and_product():
    # Live Xiaomi reads of the Amul and Snack Factory fronts in this session's trial.
    amul = analysis_of("Amul PASTEURISED BUTTER utterly butterly delicious", "Net Weight: 500 g")
    options = name_options(amul.views)
    assert {"Amul", "PASTEURISED BUTTER"} <= set(options) and all(not any(c.isdigit() for c in o) for o in options)
    amul.decision = DecisionResult(status="ok", model="test", message="", answers={
        "name_brand": pick(options, "Amul", .9), "name_product": pick(options, "PASTEURISED BUTTER", .8)})
    assert label_name(amul) == "Amul PASTEURISED BUTTER · 500 g"

    makhana = analysis_of("Snack Factory Snack better! �", "MAKHANA", "POPPED FOX NUTS", "SALT & BLACK PEPPER")
    options = name_options(makhana.views)
    assert "MAKHANA POPPED FOX NUTS" in options
    makhana.decision = DecisionResult(status="ok", model="test", message="", answers={
        "name_brand": pick(options, "Snack Factory", .9), "name_product": pick(options, "MAKHANA POPPED FOX NUTS", .3)})
    assert label_name(makhana) == "Snack Factory"  # a weak product pick is ignored
    makhana.decision.answers = {}
    assert label_name(makhana) == "Snack Factory Snack better!"  # no Jev: first title line, replacement glyph dropped


def test_sparse_primary_read_scans_label_sections(monkeypatch, tmp_path):
    from app.services import analysis as pipeline
    from app.schemas.analysis import AnalysisRequest, Box
    # Amul rear in this session: Xiaomi kept 3 large lines; Tesseract located garbled small print.
    garbled = ["by: Kaien Deri 00-0", "sive Mak Producers", "Union Ud. Anaed", "ih Marteting Federation", "Sonal inleemation pet",
               "Keep under refrigeration", "Ingredients Butter common salt", "CONTAINS PERMITTED NATURAL", "We appreciate your feedback"]
    monkeypatch.setattr(settings, "XIAOMI_OCR_ENABLED", True)
    monkeypatch.setattr(pipeline, "recognize", lambda raw: [
        OCRResult(provider="xiaomi", model="t", status="ok", lines=[OCRLine(text=t) for t in ("Net Weight: 500 g", "Lic. No. 10012021000071", "BEST BEFORE TWELVE MONTHS")]),
        OCRResult(provider="tesseract", model="t", status="ok", lines=[OCRLine(text=t, box=Box(x0=1, y0=1 + i * 20, x1=200, y1=15 + i * 20)) for i, t in enumerate(garbled)])])
    calls = []
    def details(raw, *, boxes=None, include_quadrants=False):
        calls.append(include_quadrants)
        yield OCRResult(provider="xiaomi_detail_0", model="t", status="ok", lines=[OCRLine(text="Manufactured by: Kaira District Co-operative Milk Producers' Union Ltd., Anand 388 001, India.")])
    monkeypatch.setattr(pipeline, "detail_regions", details)
    image = tmp_path / "rear.png"
    image.write_bytes(photo())
    analysis = pipeline.analyze_record({"product_category": "food_grocery", "images": {"rear": {"filepath": str(image)}}},
                                       AnalysisRequest(as_of=date(2026, 11, 6)))
    assert calls == [True]
    maker = next(f for f in analysis.fields if f.field == "manufacturer")
    assert maker.status == "observed" and maker.value.startswith("Kaira District")
    assert analysis.profile.inputs.origin == "domestic"


def test_tax_inclusive_price_is_mrp_and_contact_block_stops_at_last_contact():
    # Live Xiaomi lines from the Bingo Tedhe Medhe rear in this session's trial.
    fields = {f.field: f for f in analysis_of(
        "PROPRIETARY FOOD - NAMKEEN (15.1)", "₹20.00 incl. of all taxes", "FOR FEEDBACK/COMPLAINT CONTACT:",
        "CONSUMER CARE OFFICE, ITC LIMITED,", "ITC GREEN CENTER, NO.18, PANASWADI", "MAIN ROAD, BENGALURU 560005.",
        "Email: itccares@itc.in", "Phone: 1800 425 444 444", "QUALITY GUARANTEED.", "LOCATOR", "₹ PER g:", "3.5/RR223 J6 /0.29").fields}
    assert fields["mrp"].status == "observed" and fields["mrp"].value == "₹20.00"
    care = fields["consumer_care"].value
    assert care.endswith("Phone: 1800 425 444 444") and "QUALITY" not in care


def window(*lines: str) -> dict[str, str]:
    """Fields the full panel reading finds: anchored extraction, then the coding-window reader."""
    found = extract(OCRResult(provider="xiaomi", model="t", status="ok", lines=[OCRLine(text=t) for t in lines]), "rear")
    found += coding_window([("xiaomi", t) for t in lines], "rear", {c.field for c in found})
    return {f.field: f.value for f in fuse(found) if f.status == "observed"}


@pytest.mark.parametrize(("lines", "expected"), [
    # Snack Factory Makhana rear (live Xiaomi lines).
    (["MRP Rs. (INCL. OF ALL TAXES), USP, BATCH NO., MFD.", "USE BY, SERVINGS PER PACK & NET WT. SEE BELOW",
      "Rs. 125.00, Rs 2.02/9, MMSPGRT", "24 AUG. 26, 23 MAY 27, 6.0", "NET WEIGHT: 62 g"],
     {"mrp": "Rs. 125.00", "date": "24 AUG. 26", "net_quantity": "62 g"}),
    # Haldiram's Mint Lachha rear: headings and values in separate columns.
    (["NET QUANTITY :", "MFG. DATE :", "USE BY :", "BATCH NO.:", "MRP ₹ (INCL. OF", "ALL TAXES ) ; USP :", "SERVINGS PER PACK :",
      "200g", "06/09/26", "02/02/27", "RAFI06C", "Rs. 65.00", "Rs.0.33 Per g", "10"],
     {"mrp": "Rs. 65.00", "date": "06/09/26", "net_quantity": "200g"}),
    # SuperYou rear: dot-matrix stamp between its headings.
    (["Mfg. Date ; Exp. Date :", "BATCH No.", "13/08/2026", "12/08/2027", "PA050826022", "Rs. 300.00", "Rs. 1.5 Per g",
      "MRP Rs. (incl. of all taxes)", "Unit Sale Price Rs.", "NET WEIGHT: 200 g"],
     {"mrp": "Rs. 300.00", "date": "13/08/2026", "net_quantity": "200 g"}),
    # Bingo Tedhe Medhe retake: OCR reads the O of OCT as zero.
    (["₹20.00 incl. of all taxes", "NS/BN/", "₹ PER g:", "3.5/RR223 J6 /0.29", "230CT26/20APR27", "MFD.", "/USE BY:", "70g", "NET WT.:"],
     {"mrp": "₹20.00", "date": "230CT26", "net_quantity": "70g"}),
])
def test_coding_windows_read_values_by_type(lines, expected):
    found = window(*lines)
    assert {k: found.get(k) for k in expected} == expected


def test_contact_blocks_keep_their_email_and_skip_lead_in_text():
    # Amul rear (live): the email itself contains "customercare" and used to end the block.
    amul = window("We appreciate your feedback. Contact our Customer Care Executive at:", "1800 258 3333 (Toll free) [6 AM - 9 PM]",
                  "customercare@amul.coop", "GCMWF Ltd., Anand - 388 001")
    assert amul["consumer_care"].startswith("1800 258 3333") and "customercare@amul.coop" in amul["consumer_care"]
    # Snack Factory rear (live): "CONSUMER COMPLAINTS / FEEDBACK" heading.
    baba = window("CONSUMER COMPLAINTS / FEEDBACK", "POST CRO AT CORPORATE OFFICE:", "155 SECTOR - 60, NOIDA - 201301, (U.P.),",
                  "E-MAIL FEEDBACK@BABA.IN | WEBSITE:", "PH: 1800-180-1929 (TOLL FREE)")
    assert baba["consumer_care"].startswith("155 SECTOR") and "1800-180-1929" in baba["consumer_care"]


@pytest.mark.parametrize(("line", "name"), [
    ("READY-TO-EAT SAVOURIES (PROPRIETARY FOOD)", "READY-TO-EAT SAVOURIES"),  # Mint Lachha (live)
    ("(15.1) MICROWAVE POPCORN - READY TO COOK CORN PRODUCT A PROPRIETARY FOOD", "MICROWAVE POPCORN - READY TO COOK CORN PRODUCT"),
])
def test_generic_name_printed_before_its_class(line, name):
    assert window(line)["generic_name"] == name


def test_headings_never_match_inside_an_email():
    # Mint Lachha (live): "CUSTOMERCARE@HALDIRAM.COM" produced the value "@HALDIRAM.COM".
    found = window("THE CONSUMER SERVICE MANAGER,", "HALDIRAM SNACKS FOOD PRIVATE LIMITED", "C-31, SECTOR-62, NOIDA-201307,",
                   "OR CALL US AT: 0120-2400286", "OR E-MAIL US AT:", "CUSTOMERCARE@HALDIRAM.COM", "VISIT US AT: WWW.HALDIRAM.COM")
    assert found["consumer_care"].startswith("HALDIRAM SNACKS FOOD PRIVATE LIMITED")
    assert "0120-2400286" in found["consumer_care"] and "CUSTOMERCARE@HALDIRAM.COM" in found["consumer_care"]


def test_company_names_containing_consumer_care_stay_manufacturers():
    # SuperYou rear (live): the manufacturer was cut to "P. PRAYAGH" at "CONSUMER CARE".
    found = window("MANUFACTURED BY: P. PRAYAGH CONSUMER CARE PVT LTD UNIT I, SURVEY NO. 527 528, TELANGANA - 509216 INDIA",
                   "CUSTOMER CARE hypedesk@superyou.in +91 06554 50140")
    assert found["manufacturer"].startswith("P. PRAYAGH CONSUMER CARE PVT LTD")
    assert found["consumer_care"] == "hypedesk@superyou.in +91 06554 50140"
    # Tedhe Medhe retake (live): OCR misread "FEEDBACK" and "CONSUMER" around the contact block.
    itc = window("PACK/COMPLAINT CONTACT:", "NURSE CARE OFFICE, ITC LIMITED,", "GREEN CENTER, NO.18, BANASWADI",
                 "INDIA, BENGALURU- 560005.", "itccares@itc.in", "1800 425 444 444", "QUALITY GUARANTEED.")
    assert itc["consumer_care"].startswith("NURSE CARE OFFICE, ITC LIMITED") and itc["consumer_care"].endswith("1800 425 444 444")


def test_country_comes_from_a_declaration_or_the_makers_address_but_never_an_importers():
    from app.services.extraction import country_from_maker
    assert window("PRODUCT OF INDIA")["country_of_origin"] == "India"
    amul = fuse(extract(OCRResult(provider="xiaomi", model="t", status="ok", lines=[OCRLine(
        text="Manufactured by: Kaira District Co-operative Milk Producer Union Ltd., Anand 388 001, India.")]), "rear"))
    assert country_from_maker(amul).value == "India"
    imported = fuse(extract(OCRResult(provider="xiaomi", model="t", status="ok", lines=[OCRLine(
        text="Imported by: PRAN BEVERAGES (INDIA) PVT. LTD., West Tripura-799008")]), "rear"))
    assert country_from_maker(imported) is None


@pytest.mark.parametrize(("lines", "expected"), [
    # Potata turned read (live): "07" read as "OF"; the expiry is still a month and year.
    (["EXP: OF AUG 2027 MRP RS: 30.00."], {"expiry": "AUG 2027", "mrp": "RS 30.00"}),
    (["MFG:08 AUG 2026 EXP:07 AUG 2027 MRP RS:30.00;"], {"date": "08 AUG 2026", "expiry": "07 AUG 2027"}),
    (["MFG: 09APR2025 UBD: 08APR2026"], {"date": "09APR2025", "expiry": "08APR2026"}),  # ACT II strip
    (["BEST BEFORE TWELVE MONTHS FROM PACKAGING WHEN STORED REFRIGERATED"], {"expiry": "TWELVE MONTHS FROM PACKAGING"}),  # Amul
    # Coding windows: the latest stamped date is the expiry.
    (["Mfg. Date ; Exp. Date :", "13/08/2026", "12/08/2027"], {"date": "13/08/2026", "expiry": "12/08/2027"}),
    (["230CT26/20APR27", "MFD.", "/USE BY:"], {"date": "230CT26", "expiry": "20APR27"}),
])
def test_expiry_is_its_own_field(lines, expected):
    found = window(*lines)
    assert {k: found.get(k) for k in expected} == expected


def test_live_readings_that_only_looked_like_conflicts():
    # Mint Lachha (live): the upright read shifted columns; "USE BY : 06/09/26" is the MFG date.
    mint = window("MFG. DATE : 06/09/26 28", "USE BY : 06/09/26 R", "USE BY : 02/03/27 28")
    assert mint["date"] == "06/09/26" and mint["expiry"] == "02/03/27"
    # Amul (live): a crop cut the shelf life short.
    amul = window("BEST BEFORE TWELVE MONTHS FROM PACKAGING WHEN STORED REFRIGERATED", "BEST BEFORE TWELVE MONTHS FROM")
    assert amul["expiry"] == "TWELVE MONTHS FROM PACKAGING"
    # Potata (live): "(Imported by)" after a company in the importer list is not a heading.
    potata = window("IMP BY: PRAN BEVERAGES", "Imported by) Growth", "Pvt. Ltd. (Imported by) New Town")
    assert potata["manufacturer"] == "PRAN BEVERAGES"


def test_potata_turned_section_scans_agree():
    # Live zoomed scans of Potata's turned side panel: MFG read as "MEG", a year cut at the crop
    # edge, and a stray "Imported by)" heading from the importer list.
    found = window("EXP: OF AUG 2027 MRP RS: 30.00.", "LOT: UD 2068 D IMP BY: PRAN BEVERAGES",
                   "EXP: 07 AUG 2027 MRP RS: 30.00.", "MEG-08 AUG 2026 EXP: 07 AUG 20", "RS. 9.40 PER LOT: UD 2068 D",
                   "Imported by)", "MEG:08 AUG 2026 EXP:07 AUG 20")
    assert found["date"] == "08 AUG 2026"
    assert found["expiry"] == "07 AUG 2027"
    assert found["manufacturer"] == "PRAN BEVERAGES"
    assert found["mrp"] == "RS 30.00"


def test_coding_window_needs_headings_and_ignores_prose_dates():
    # No MRP heading: a lone price is not called the MRP. A packaging-film licence date is not a manufacture date.
    found = window("Rs. 99.00", "MFD: see coding", "Pkg. Material Mfd. By: Uflex Ltd. Jammu digital licence dt.11-02-2019",
                   "DECLARATION 2011")
    assert "mrp" not in found and "date" not in found
    # Two different non-unit prices are ambiguous.
    assert "mrp" not in window("MRP Rs. (incl. of all taxes)", "Rs. 300.00", "Rs. 250.00")


def test_sideways_coding_print_is_read_turned(monkeypatch, tmp_path):
    from app.services import analysis as pipeline
    from app.schemas.analysis import AnalysisRequest
    # Potata side panel (live): the upright read saw only "Net Quantity: 75g"; the coding print runs sideways.
    monkeypatch.setattr(settings, "XIAOMI_OCR_ENABLED", True)
    monkeypatch.setattr(pipeline, "recognize", lambda raw: [
        OCRResult(provider="xiaomi", model="t", status="ok", lines=[OCRLine(text="Net Quantity: 75g"), OCRLine(text="Story of Spicy Potatoes")]),
        OCRResult(provider="tesseract", model="t", status="ok")])
    monkeypatch.setattr(pipeline, "orientation", lambda raw: 270)
    turns = []
    def turned(raw, degrees):
        turns.extend(degrees)
        yield OCRResult(provider="xiaomi_rot270", model="t", status="ok", lines=[
            OCRLine(text="MFG:08 AUG 2026 EXP:07 AUG 2027 MRP RS:30.00; Rs:0.40 Per g LOT:UD 2068 D"),
            OCRLine(text="IMP BY:PRAN BEVERAGES (INDIA) PVT. LTD.")])
    monkeypatch.setattr(pipeline, "rotated_reads", turned)
    image = tmp_path / "side.png"
    image.write_bytes(photo())
    analysis = pipeline.analyze_record({"product_category": "food_grocery", "images": {"side": {"filepath": str(image)}}},
                                       AnalysisRequest(as_of=date(2026, 11, 18)))
    fields = {f.field: f for f in analysis.fields}
    assert turns == [270]
    assert "30.00" in fields["mrp"].value
    assert fields["date"].value.upper() == "08 AUG 2026"
    assert analysis.profile.inputs.origin == "imported"


def test_turned_coding_print_missing_its_date_is_scanned_in_sections(monkeypatch, tmp_path):
    from app.services import analysis as pipeline
    from app.schemas.analysis import AnalysisRequest
    monkeypatch.setattr(settings, "XIAOMI_OCR_ENABLED", True)
    monkeypatch.setattr(pipeline, "recognize", lambda raw: [
        OCRResult(provider="xiaomi", model="t", status="ok", lines=[OCRLine(text="Net Quantity: 75g")]),
        OCRResult(provider="tesseract", model="t", status="ok")])
    monkeypatch.setattr(pipeline, "orientation", lambda raw: 270)
    # Potata side (live): the whole turned read kept EXP and MRP but lost "MFG:08 AUG 2026".
    monkeypatch.setattr(pipeline, "rotated_reads", lambda raw, degrees: iter([OCRResult(
        provider="xiaomi_rot270", model="t", status="ok", lines=[OCRLine(text="EXP: OF AUG 2027 MRP RS: 30.00.")])]))
    monkeypatch.setattr(pipeline, "turned", lambda raw, turn: raw)
    def sections(raw, **kwargs):
        yield OCRResult(provider="xiaomi_detail_0", model="t", status="ok", lines=[OCRLine(text="MFG:08 AUG 2026 EXP:07 AUG 2027")])
        pytest.fail("scanning must stop once the date is read")
    monkeypatch.setattr(pipeline, "detail_regions", sections)
    image = tmp_path / "side.png"
    image.write_bytes(photo())
    analysis = pipeline.analyze_record({"product_category": "food_grocery", "images": {"side": {"filepath": str(image)}}},
                                       AnalysisRequest(as_of=date(2026, 11, 18)))
    fields = {f.field: f for f in analysis.fields}
    assert fields["date"].value == "08 AUG 2026" and fields["date"].evidence[0].provider == "xiaomi_rot270_detail_0"
    assert fields["expiry"].status == "observed" and fields["mrp"].value == "RS 30.00"


def pick(options: list[str], text: str, confidence: float) -> DecisionAnswer:
    choice = f"span_{options.index(text)}"
    return DecisionAnswer(type="choice", choice=choice, confidence=confidence, probabilities={choice: confidence})


@pytest.mark.parametrize(("lines", "origin"), [
    (["Country of origin: India"], "domestic"),
    (["Country of origin: Thailand"], "imported"),
    (["Made in U.S.A."], "imported"),
    (["Country of origin: BHARAT"], "domestic"),
    (["Imported by: Acme Foods, Mumbai 400001"], "imported"),
    (["Manufactured by: Parle Products Pvt. Ltd., Mumbai, India"], "domestic"),
    # Live Xiaomi read of evaluation/fixtures/parle-g-rear.jpg: the PIN sits below the extracted line.
    (["8 901719 255144", "MANUFACTURED BY:", "(MF) FOODS PVT LTD. A.S. SANKALPURI INDUL AREA", "BALLARI ROAD, MARIGONJ, KA - 583231"], "domestic"),
    (["8 901719 255144", "MANUFACTURED BY:", "(MF) FOODS PVT LTD"], "unknown"),
    (["Net quantity: 70 g"], "unknown"),
    # Tedhe Medhe retake (live): no manufacturer printed, only the brand owner's Bengaluru address.
    (["NURSE CARE OFFICE, ITC LIMITED,", "INDIA, BENGALURU- 560005."], "domestic"),
    # Potata side panel: the importer's Indian address must not make it domestic.
    (["MFG:08 AUG 2026 EXP:07 AUG 2027 MRP RS:30.00", "IMP BY:PRAN BEVERAGES (INDIA) PVT. LTD.", "Kolkata-700156"], "imported"),
])
def test_label_origin_needs_a_declaration(lines, origin):
    assert label_origin(analysis_of(*lines).fields, list(lines))[0] == origin


@pytest.fixture
def client(tmp_path, monkeypatch):
    from app.services import ocr
    monkeypatch.setattr(store, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(store, "FALLBACK_FILE", str(tmp_path / "inspections.json"))
    monkeypatch.setattr(store, "_MEMORY_INSPECTIONS", {})
    monkeypatch.setattr(store, "is_database_available", lambda: False)
    monkeypatch.setattr(settings, "XIAOMI_OCR_ENABLED", False)
    monkeypatch.setattr(settings, "TYPESAFE_API_KEY", None)
    monkeypatch.setattr(ocr, "xiaomi_ocr", lambda _: OCRResult(provider="xiaomi", model="test", status="ok", lines=[
        OCRLine(text="Parle-G Gluco BISCUITS"), OCRLine(text="Net quantity: 70 g"), OCRLine(text="Country of origin: India")]))
    return TestClient(app)


def photo() -> bytes:
    image = np.full((400, 800, 3), 255, np.uint8)
    cv2.putText(image, "Parle-G", (40, 200), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 0), 3)
    return cv2.imencode(".png", image)[1].tobytes()


def test_photo_alone_names_the_package_and_selects_the_profile(client):
    created = client.post("/inspections/", json={})
    assert created.status_code == 201
    inspection_id = created.json()["id"]
    assert created.json()["product_name"] == ""
    assert client.post(f"/inspections/{inspection_id}/images", data={"view_type": "front"},
                       files={"file": ("front.png", photo())}).status_code == 200
    analyzed = client.post(f"/inspections/{inspection_id}/analyze", json={})
    assert analyzed.status_code == 200, analyzed.text
    record = analyzed.json()
    assert record["product_name"] == "Parle-G Gluco BISCUITS · 70 g"
    profile = record["analysis"]["profile"]
    assert profile["inputs"]["origin"] == "domestic" and profile["status"] == "selected"
    assert profile["inputs"]["as_of"] == date.today().isoformat()
    assert profile["reason"].startswith("Origin read from the label")


def test_typed_name_and_explicit_origin_win_over_the_label(client):
    inspection_id = client.post("/inspections/", json={"product_name": "Shelf sample 2"}).json()["id"]
    client.post(f"/inspections/{inspection_id}/images", data={"view_type": "front"}, files={"file": ("front.png", photo())})
    record = client.post(f"/inspections/{inspection_id}/analyze", json={"origin": "unknown"}).json()
    assert record["product_name"] == "Shelf sample 2"
    assert record["analysis"]["profile"]["inputs"]["origin"] == "unknown"
    assert record["analysis"]["profile"]["status"] == "review_required"

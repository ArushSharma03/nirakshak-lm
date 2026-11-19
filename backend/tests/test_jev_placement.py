"""Jev places verbatim OCR lines into fields no pattern found; it never writes a value."""

from datetime import date

import httpx
import pytest
from pydantic import SecretStr

from app.core.config import settings
from app.schemas.analysis import AnalysisRequest, OCRLine, OCRResult, ViewAnalysis
from app.services import analysis as pipeline
from app.services.decision import judge_fields, placements, transcript_lines
from app.services.extraction import extract, fuse

# Live Xiaomi lines from evaluation/fixtures/parle-g-rear.jpg: no "MRP"/"Mfd by" anchors for these values.
LINES = ["Parle-G Gluco BISCUITS", "8 901719 255144", "(P) PARLE PRODUCTS PVT LTD",
         "NORTHELL CROSSING, VILE PARLE EAST, MUMBAI, MH - 400057", "PRICE Rs. 10.00 PER PACK", "NET WEIGHT: 70g"]


def views():
    ocr = OCRResult(provider="xiaomi", model="test", status="ok", lines=[OCRLine(text=t) for t in LINES])
    return {"rear": ViewAnalysis(file_hash="x", ocr=[ocr])}


def jev(choices: dict[str, tuple[str, float]], calls: list):
    def respond(*args, **kwargs):
        calls.append(kwargs["json"])
        answers = {}
        for key, question in kwargs["json"]["questions"].items():
            choice, confidence = choices.get(key, ("none", 0.9))
            rest = (1 - confidence) / (len(question["criteria"]) - 1)
            answers[key] = {"type": "choice", "choice": choice, "confidence": confidence,
                            "probabilities": {o: confidence if o == choice else rest for o in question["criteria"]}}
        return httpx.Response(200, request=httpx.Request("POST", "https://api.typesafe.ai/v1/systemone"),
                              json={"model": settings.TYPESAFE_MODEL, "answers": answers, "usage": {"input_tokens": 1}})
    return respond


def test_placement_copies_the_chosen_line_and_ignores_weak_or_invalid_picks(monkeypatch):
    monkeypatch.setattr(settings, "TYPESAFE_API_KEY", SecretStr("test-key"))
    lines = transcript_lines(views())
    fields = fuse([c for run in views()["rear"].ocr for c in extract(run, "rear")])
    calls = []
    monkeypatch.setattr(httpx, "post", jev({"place_manufacturer": ("line_2", 0.9), "place_mrp": ("line_4", 0.8),
                                            "place_date": ("line_1", 0.9), "place_generic_name": ("line_0", 0.4)}, calls))
    decision = judge_fields(fields, lines)
    assert decision.status == "ok" and len(calls) == 1
    assert "place_net_quantity" not in calls[0]["questions"]  # the pattern already found it
    placed = {c.field: c for c in placements(decision, lines)}
    assert placed["manufacturer"].value == "(P) PARLE PRODUCTS PVT LTD" and placed["manufacturer"].provider == "jev"
    assert placed["mrp"].value == "Rs. 10.00" and placed["mrp"].source_text == LINES[4]
    assert "date" not in placed  # a barcode line has no date to copy
    assert "generic_name" not in placed  # below the confidence floor


def test_a_line_read_as_one_declaration_is_not_placed_as_another():
    from app.schemas.analysis import Candidate, DecisionAnswer, DecisionResult
    # Tedhe Medhe (live): Jev placed the consumer-care office line as the manufacturer.
    office = "NURSE CARE OFFICE, ITC LIMITED,"
    lines = [("rear", office), ("rear", "ITC LIMITED, Virginia House, Kolkata 700071")]
    care = Candidate(field="consumer_care", value="...", view="rear", provider="xiaomi", source_text=f"PACK/COMPLAINT CONTACT:\n{office}\n1800 425 444 444")
    def answer(choice):
        return DecisionAnswer(type="choice", choice=choice, confidence=.9, probabilities={choice: .9})
    decision = DecisionResult(status="ok", model="t", message="", answers={"place_manufacturer": answer("line_0")})
    assert placements(decision, lines, [care]) == []
    decision.answers["place_manufacturer"] = answer("line_1")
    assert placements(decision, lines, [care])[0].value.startswith("ITC LIMITED")


def test_placed_country_is_the_country_named_in_the_line():
    from app.services.decision import _placed_value
    # Amul report in this session: Jev placed the manufacturer line as country of origin.
    line = "Manufactured by: Kaira District Co-operative Milk Producer Union Ltd., Anand 388 001, India. Lic. No. 10012021000243"
    assert _placed_value("country_of_origin", line) == "India"
    assert _placed_value("country_of_origin", "Made in Thailand, imported by Acme, Mumbai, India") is None  # two countries
    assert _placed_value("country_of_origin", "Keep under refrigeration") is None


def test_consumer_care_readings_with_the_same_number_agree():
    from app.schemas.analysis import Candidate
    # Amul report in this session: three reads of one block were marked "Conflicting readings".
    def care(value, provider):
        return Candidate(field="consumer_care", value=value, view="rear", provider=provider, source_text=value)
    full = "We appreciate your feedback. Contact our Customer Care Executive at:\n1800 258 3333 (Toll free) [6 AM - 9 PM]"
    short = "Contact our Customer Care Executive at:\n1800 258 3333 (Toll free) [6 AM - 9 PM]"
    field = next(f for f in fuse([care(full, "xiaomi"), care(short, "xiaomi_detail_0"), care(short, "xiaomi_detail_2")]) if f.field == "consumer_care")
    assert field.status == "observed" and len(field.evidence) == 3
    other = next(f for f in fuse([care(full, "xiaomi"), care("Call 1800 999 0000", "xiaomi_detail_0")]) if f.field == "consumer_care")
    assert other.status == "conflict"


def test_same_company_with_and_without_its_address_agrees():
    from app.schemas.analysis import Candidate
    def maker(value, provider):
        return Candidate(field="manufacturer", value=value, view="rear", provider=provider, source_text=value)
    # SuperYou rear (live): three reads of one manufacturer were a conflict.
    field = next(f for f in fuse([
        maker("P. PRAYAGH CONSUMER CARE PRIVATE LIMITED", "xiaomi"),
        maker("P. PRAYAGH CONSUMER CARE PVT LTD UNIT I, SURVEY NO. 527 528, TELANGANA - 509216", "xiaomi_detail_1")]) if f.field == "manufacturer")
    assert field.status == "observed" and field.value.startswith("P. PRAYAGH CONSUMER CARE PVT LTD UNIT I")
    other = next(f for f in fuse([maker("Agro Tech Foods Ltd., Kashipur", "xiaomi"), maker("Rukkveer Food Products Pvt. Ltd.", "xiaomi_detail_0")])
                 if f.field == "manufacturer")
    assert other.status == "conflict"


def test_name_questions_send_spans_as_option_objects_with_front_context(monkeypatch):
    # Live regression: bare-string options read as conditions and Jev answered "none" for every package.
    monkeypatch.setattr(settings, "TYPESAFE_API_KEY", SecretStr("test-key"))
    calls = []
    monkeypatch.setattr(httpx, "post", jev({}, calls))
    judge_fields(fuse([]), [], ["Amul", "BUTTER"], ["Amul PASTEURISED BUTTER"])
    question = calls[0]["questions"]["name_brand"]
    assert question["criteria"]["span_0"] == {"text": "Amul"}
    assert calls[0]["state"]["front_text"] == ["Amul PASTEURISED BUTTER"]


def test_photo_flow_uses_jev_when_configured_and_placements_reach_checks(monkeypatch):
    monkeypatch.setattr(settings, "TYPESAFE_API_KEY", SecretStr("test-key"))
    monkeypatch.setattr(pipeline, "recognize", lambda raw: [views()["rear"].ocr[0].model_copy(deep=True)])
    calls = []
    monkeypatch.setattr(httpx, "post", jev({"place_manufacturer": ("line_2", 0.9)}, calls))
    record = {"product_category": "food_grocery", "images": {}}
    analysis = pipeline.analyze_record(record, AnalysisRequest(as_of=date(2026, 11, 6)))
    assert analysis.decision.status == "not_needed" and calls == []  # no photos, nothing to place

    image = pytest.importorskip("pathlib").Path(__file__).resolve().parents[2] / "evaluation/fixtures/parle-g-rear.jpg"
    record["images"] = {"rear": {"filepath": str(image)}}
    analysis = pipeline.analyze_record(record, AnalysisRequest(as_of=date(2026, 11, 6), origin="domestic"))
    maker = next(f for f in analysis.fields if f.field == "manufacturer")
    assert maker.status == "observed" and maker.evidence[0].provider == "jev"
    assert any(c.field == "manufacturer" and c.evidence and c.evidence[0].provider == "jev" for c in analysis.checks.results)

    record["analysis"] = analysis.model_dump(mode="json")
    again = pipeline.analyze_record(record, AnalysisRequest(as_of=date(2026, 11, 6), origin="domestic"))
    assert len(calls) == 1, "identical OCR must reuse the saved Jev answer"
    assert next(f for f in again.fields if f.field == "manufacturer").value == "(P) PARLE PRODUCTS PVT LTD"

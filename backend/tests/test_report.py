"""Printable inspector report: compact, honest about unread declarations, safe to open offline."""

import hashlib
import re
from datetime import date

import pytest

from app.schemas.analysis import (Analysis, Candidate, CheckReport, DecisionResult, DeclarationCheck, FusedField,
                                  OCRLine, OCRResult, Profile, ProfileRequest, Rule, ScreeningClassification,
                                  ViewAnalysis)
from app.services.report import render_report

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
URL = "https://consumeraffairs.gov.in/pages/legal-metrology-act"
UNREAD = "No anchored reading. Missing OCR is not proof that the declaration is absent."


def rule(field: str, citation: str) -> Rule:
    return Rule(id=field, version="1", citation=citation, field=field, requirement=f"{field} requirement",
                effective_from=date(2011, 1, 1), origins=["domestic"], source_url=URL)


def check(field: str, kind: str, status: str, reason: str) -> DeclarationCheck:
    return DeclarationCheck(rule_id=field, field=field, kind=kind, status=status, reason=reason,
                            citation="LMPC", source_url=URL)


def candidate(field: str, value: str, source_text: str, provider: str = "xiaomi") -> Candidate:
    return Candidate(field=field, value=value, view="rear", provider=provider, source_text=source_text)


@pytest.fixture
def case(tmp_path):
    photo = tmp_path / "rear.png"
    photo.write_bytes(PNG)
    digest = hashlib.sha256(PNG).hexdigest()
    fields = [
        FusedField(field="net_quantity", status="observed", value="250g", reason="Unverified OCR",
                   evidence=[candidate("net_quantity", "250g", "NET WEIGHT: 250g")]),
        FusedField(field="mrp", status="missing", reason=UNREAD),
        FusedField(field="manufacturer", status="missing", reason=UNREAD),
        FusedField(field="date", status="conflict", reason="OCR providers disagree.",
                   evidence=[candidate("date", "03/2026", "PKD 03/2026"), candidate("date", "08/2026", "PKD 08/2026", "tesseract")]),
    ]
    checks = [check(f, k, "insufficient_evidence", UNREAD) for f in ("mrp", "manufacturer")
              for k in ("presence", "completeness", "placement", "readability", "character_height")]
    checks += [check("net_quantity", "presence", "pass", "An anchored reading exists."),
               check("net_quantity", "units", "pass", "Supported unit."),
               check("net_quantity", "placement", "insufficient_evidence", "No verified placement constraint."),
               check("date", "consistency", "fail", "Source readings disagree."),
               check("net_quantity", "readability", "fail", "A supporting capture needs retaking.")]
    analysis = Analysis(
        version="1.2.0",
        views={"rear": ViewAnalysis(file_hash=digest, ocr=[OCRResult(
            provider="xiaomi", model="m", status="ok", raw_text="NET WEIGHT: 250g\nM.R.P. ₹40 <script>x</script>",
            lines=[OCRLine(text="NET WEIGHT: 250g")])])},
        fields=fields,
        profile=Profile(status="selected", id="lmpc-food", version="0.1", reason="Selected.",
                        inputs=ProfileRequest(category="food_grocery", origin="domestic", as_of=date(2026, 11, 18)),
                        rules=[rule("net_quantity", "Rule 6(1)(c)"), rule("mrp", "Rule 6(1)(e)"),
                               rule("manufacturer", "Rule 6(1)(a)"), rule("date", "Rule 6(1)(d)")]),
        warnings=["front: no captured evidence."],
        decision=DecisionResult(status="unavailable", model="jev", message="Jev disabled."),
        checks=CheckReport(results=checks),
        classification=ScreeningClassification(reason="One or more checks need review."),
    )
    record = {"id": "INS-TEST", "product_name": "Biscuits <b>", "product_category": "food_grocery",
              "timestamp": "2026-11-18T11:36:13+00:00", "final_outcome": "Manual Review Required",
              "images": {"rear": {"filepath": str(photo), "original_filename": "rear.png",
                                  "quality_assessment": {"composite_score": 79.0, "overall_status": "Warning"}}}}
    return record, analysis


def printed(html: str) -> str:
    """Text a default print shows: drop the collapsed appendix and markup."""
    html = re.sub(r"<details>.*?</details>", "", html, flags=re.S)
    html = re.sub(r"<style>.*?</style>", "", html, flags=re.S)
    return re.sub(r"<[^>]+>", " ", html)


def test_report_is_a4_compact_and_drops_repeated_boilerplate(case):
    html = render_report(*case)
    text = printed(html)
    assert "size: A4" in html
    assert "insufficient" not in text.lower() and "not enough data" not in text.lower()
    assert UNREAD not in text
    # Unread declarations collapse into one locate task that never claims absence.
    assert text.count("Locate and record on the package") == 1
    assert "Retail sale price (MRP) and Manufacturer / packer" in text
    assert "does not show the declaration is absent" in text
    assert "₹40" not in text.split("Locate and record")[0]  # OCR hints never become a reading


def test_report_shows_readings_conflicts_and_verified_checks(case):
    text = printed(render_report(*case))
    assert "250g" in text and "NET WEIGHT: 250g" in text
    assert "03/2026" in text and "08/2026" in text and "OCR readings disagree" in text
    assert "presence, units" in text  # passed screening checks stay visible
    assert "A supporting capture needs retaking." in text
    # The conflict's consistency failure is covered by the resolve task, not repeated.
    assert "Source readings disagree." not in text
    assert "Not a legal compliance finding" in text
    assert "Manual Review Required" in text


def test_report_keeps_evidence_escaped_embedded_and_linked(case):
    record, analysis = case
    html = render_report(record, analysis)
    assert "Biscuits &lt;b&gt;" in html and "Biscuits <b>" not in html
    assert "data:image/png;base64," in html
    assert analysis.views["rear"].file_hash in html
    assert f'href="{URL}"' in html
    # Raw OCR stays available in a collapsed appendix, escaped.
    appendix = re.search(r"<details>.*?</details>", html, flags=re.S).group(0)
    assert "&lt;script&gt;" in appendix and "<script>" not in html
    assert "M.R.P." in appendix


def test_report_rejects_changed_photo(case):
    record, analysis = case
    analysis.views["rear"].file_hash = "0" * 64
    with pytest.raises(ValueError, match="photo changed"):
        render_report(record, analysis)


def test_historical_report_without_checks_still_renders(case):
    record, analysis = case
    analysis.checks = None
    analysis.classification = None
    analysis.version = "1.0.0"
    text = printed(render_report(record, analysis))
    assert "Run declaration checks in the app" in text
    assert "Verify on the package: Net quantity" in text


def test_non_http_sources_are_not_linked(case):
    record, analysis = case
    analysis.profile.rules[0].source_url = "javascript:alert(1)"
    html = render_report(record, analysis)
    assert "javascript:" not in html

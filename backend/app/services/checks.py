"""Deterministic evidence checks, independent of OCR and model recommendations."""

import re
from datetime import date, datetime
from decimal import Decimal
from app.schemas.analysis import CheckReport, CheckKind, DeclarationCheck, FusedField, Profile, ViewAnalysis
from app.services.calibration import physical_height
from app.services.extraction import normalize

KINDS: tuple[CheckKind, ...] = ("presence", "completeness", "units", "consistency", "placement", "readability", "character_height")
_QUANTITY = re.compile(r"([0-9]+(?:\.[0-9]+)?)\s*(kg|mg|g|ml|cl|l|litres?|liters?|ग्राम|किग्रा|मिलीलीटर|लीटर|nos?\.?|pcs?\.?|units?)", re.I)
_UNITS = {"kg": ("mass", "1000"), "g": ("mass", "1"), "mg": ("mass", ".001"),
          "किग्रा": ("mass", "1000"), "ग्राम": ("mass", "1"), "l": ("volume", "1000"),
          "ml": ("volume", "1"), "cl": ("volume", "10"), "लीटर": ("volume", "1000"), "मिलीलीटर": ("volume", "1")}


def quantity(value: str):
    match = _QUANTITY.fullmatch(normalize(value))
    if not match or Decimal(match[1]) <= 0:
        return None
    unit = match[2].rstrip(".")
    if unit.startswith("lit"):
        unit = "l"
    dimension, factor = _UNITS.get(unit, ("count", "1"))
    amount = Decimal(match[1]) * Decimal(factor)
    if dimension == "count" and amount != amount.to_integral_value():
        return None
    return dimension, amount


def price(value: str):
    value = re.sub(r"^(?:₹|rs\.?|inr)\s*", "", normalize(value))
    if not re.fullmatch(r"[0-9]+(?:\.[0-9]{1,2})?", value):
        return None
    return Decimal(value)


def valid_date(value: str, as_of: date) -> bool | None:
    """Validate supported date formats; ambiguous two-digit years stay unresolved."""
    value = normalize(value)
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%Y", "%m-%Y", "%b %Y", "%B %Y", "%b%Y", "%B%Y"):
        try:
            parsed = datetime.strptime(value, fmt).date()
        except ValueError:
            continue
        return parsed <= as_of if "%d" in fmt else (parsed.year, parsed.month) <= (as_of.year, as_of.month)
    return False if re.fullmatch(r"(?:\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{4}|\d{1,2}[-/]\d{4})", value) else None


def check_declarations(profile: Profile, fields: list[FusedField], views: dict[str, ViewAnalysis], images: dict) -> CheckReport:
    by_field = {f.field: f for f in fields}
    results = []
    # A non-selected profile has no reliable applicability. Keep every field visible.
    rules = profile.rules
    if profile.status != "selected":
        for field in fields:
            for kind in KINDS:
                results.append(DeclarationCheck(rule_id="unselected-profile", field=field.field, kind=kind,
                    status="insufficient_evidence", reason=profile.reason, citation="Profile not selected", source_url="", evidence=field.evidence))
        return CheckReport(results=results)

    for rule in rules:
        field = by_field.get(rule.field)
        evidence = [c for c in field.evidence if c.value.strip() and c.source_text.strip() and c.view in views] if field else []
        for kind in KINDS:
            status = "insufficient_evidence"
            reason = "No anchored reading. Missing OCR is not proof that the declaration is absent."
            measured = None
            required = rule.minimum_glyph_height_mm if kind == "character_height" else None
            if evidence:
                if kind == "presence":
                    status, reason = "pass", "An anchored reading exists; the package declaration still needs visual verification."
                elif kind == "consistency":
                    parser = quantity if rule.field == "net_quantity" else price if rule.field == "mrp" else normalize
                    values = [parser(c.value) for c in evidence]
                    if any(value is None for value in values):
                        reason = "Some readings cannot be normalized reliably."
                    else:
                        status = "pass" if len(set(values)) == 1 else "fail"
                        reason = "Normalized readings agree; repeated crops are not independent confirmation." if status == "pass" else "Source readings disagree. Review every cited photo."
                elif kind == "units":
                    if rule.field != "net_quantity":
                        status, reason = "not_applicable", "Unit validation applies to net quantity."
                    else:
                        status = "pass" if all(quantity(c.value) is not None for c in evidence) else "fail"
                        reason = "Quantity has a positive amount and supported mass, volume or count unit." if status == "pass" else "A reading lacks a supported unit or valid positive amount. This is an OCR-value failure, not a legal finding."
                elif kind == "completeness":
                    if field is None or field.status == "conflict":
                        reason = "Resolve conflicting readings before assessing completeness."
                    elif rule.field in ("net_quantity", "mrp"):
                        parser = quantity if rule.field == "net_quantity" else price
                        status = "pass" if all(parser(c.value) is not None for c in evidence) else "fail"
                        reason = "The extracted value has the supported numeric structure. Tax wording and package applicability still require review."
                    elif rule.field == "date":
                        dates = [valid_date(c.value, profile.inputs.as_of) for c in evidence]
                        if any(v is None for v in dates):
                            reason = "Date format is invalid, unsupported or has an ambiguous year."
                        else:
                            status = "pass" if all(dates) else "fail"
                            reason = "Recognized calendar date is not after the inspection date." if status == "pass" else "The manufacture/packing date is invalid or after the inspection date. Verify the source."
                    elif rule.field in ("generic_name", "country_of_origin"):
                        reason = "OCR text alone cannot establish the correct commodity identity or country."
                    else:
                        reason = "A name/contact fragment does not establish complete address or complaint particulars; inspect the full declaration."
                elif kind == "placement":
                    if not rule.constraints_verified or rule.required_view is None:
                        reason = "No verified placement constraint for this package/profile; front/rear/side names do not identify the principal display panel."
                    elif rule.required_view not in views:
                        reason = "The required panel was not captured."
                    elif any(c.view == rule.required_view and c.box is not None for c in evidence):
                        status, reason = "pass", "Positioned evidence exists in the profile's required view. Panel identification needs inspector confirmation."
                    else:
                        reason = "No located evidence on the required view; unlocated OCR cannot establish a placement failure."
                elif kind == "readability":
                    qualities = [images.get(c.view, {}).get("quality_assessment", {}).get("overall_status") for c in evidence]
                    if "Retake Recommended" in qualities:
                        status, reason = "fail", "A supporting capture needs retaking. This does not establish that the printed label is illegible."
                    elif qualities and all(q == "Pass" for q in qualities):
                        status, reason = "pass", "Supporting photos passed the optical capture check; human-readable print still requires review."
                    else:
                        reason = "Capture optics are missing or warn about readability; no legal readability conclusion."
                elif kind == "character_height":
                    heights = []
                    measured_views = set()
                    for c in evidence:
                        view = views.get(c.view)
                        if c.glyph_box is not None and view and view.calibration.status == "available":
                            height = physical_height(c.glyph_box, view.calibration)
                            if height is not None:
                                heights.append(height)
                                measured_views.add(c.view)
                    if heights:
                        measured = min(heights)
                    if not rule.constraints_verified or required is None:
                        reason = "No verified applicable glyph-height threshold. Package area, printing method and exceptions must be resolved."
                    else:
                        if field is not None and field.status == "conflict":
                            reason = "Resolve conflicting declaration readings before treating a glyph measurement as representative."
                        elif heights and measured_views == {c.view for c in evidence}:
                            measured = min(heights)
                            status = "pass" if measured >= required else "fail"
                            reason = "Minimum calibrated glyph-box height compared with the profile threshold."
                        else:
                            reason = "Confirmed glyph boxes and coplanar calibration are required. OCR line-box height is not glyph height."
            if kind == "units" and rule.field != "net_quantity":
                status, reason = "not_applicable", "Unit validation applies to net quantity."
            results.append(DeclarationCheck(rule_id=rule.id, field=rule.field, kind=kind, status=status,
                reason=reason, citation=rule.citation, source_url=rule.source_url, evidence=evidence,
                measured_mm=measured, required_mm=required))
    return CheckReport(results=results)

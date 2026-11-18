"""Setup facts read from label evidence, so a photo is the only input an inspection needs."""

import re
from collections.abc import Mapping
from typing import Literal

from app.schemas.analysis import Analysis, Candidate, DecisionResult, FusedField, View, ViewAnalysis
from app.services.extraction import ANCHORS, _CONTACT, _SECTION

# Same bar as Jev's field placement: this becomes declaration evidence, not just a display name.
PLACEMENT_CONFIDENCE = 0.6

_MAX_NAME_OPTIONS = 60
# Names only label the record (not evidence), so a lower bar than field placement.
NAME_CONFIDENCE = 0.5

# Lines that open many panels but never name the product.
_NOT_A_TITLE = re.compile(
    r"let'?s\s+talk|trade\s*mark|nutrition|ingredients?|facts|serving|calories|energy|protein|fat\b|"
    r"carbohydrate|sugar|sodium|fssai|veg(?:etarian)?\b|batch|best\s+before|www\.|@", re.I)
_TITLE_VIEWS: tuple[View, ...] = ("front", "rear", "side")
# "Imported by", "IMP BY:", "(Imported by)", "Importer:".
_IMPORTER = re.compile(r"\bimported\s+by\b|\bimp\.?\s*by\b|\bimporter\b", re.I)
# "India", or a PIN written as an address ("MH - 400057", "PIN: 400057"); bare digit runs are barcodes.
_INDIAN_ADDRESS = re.compile(r"\bindia\b|[-–]\s*[1-9]\d{5}\b|\bpin(?:\s*code)?\s*[:.-]?\s*[1-9]\d{5}\b", re.I)


def label_origin(fields: list[FusedField], transcript: list[str]) -> tuple[Literal["domestic", "imported", "unknown"], str]:
    """Infer origin from declarations; anything short of a clear reading stays unknown.

    `transcript` is the primary OCR text: extraction keeps only the first lines of a
    manufacturer block, while the address with its PIN code often follows.
    """
    by_field = {field.field: field for field in fields}
    country = by_field["country_of_origin"]
    if country.status == "observed" and country.value:
        if re.search(r"\bindia\b|भारत", country.value, re.I):
            return "domestic", f"Origin read from the label: country of origin “{country.value}”."
        return "imported", f"Origin read from the label: country of origin “{country.value}”."
    text = "\n".join([*transcript, *(candidate.source_text for candidate in by_field["manufacturer"].evidence)])
    if _IMPORTER.search(text):
        return "imported", "Origin read from the label: an importer is declared."
    if any(_INDIAN_ADDRESS.search(line) for line in text.splitlines()):
        return "domestic", "Origin read from the label: an Indian address is printed and no importer is declared."
    return "unknown", "Origin was not found on the label."


def _title(lines: list[str]) -> str | None:
    for line in lines[:8]:
        text = _clean(line)
        compact = text.replace(" ", "")
        if not 3 <= len(text) <= 64 or re.search(r"\d", text):
            continue
        if sum(char.isalpha() for char in compact) < .7 * len(compact):
            continue
        if _NOT_A_TITLE.search(text) or _SECTION.search(text) or _CONTACT.search(text):
            continue
        if any(re.search(anchor, text, re.I) for anchor in ANCHORS.values()):
            continue
        return text
    return None


def _clean(text: str) -> str:
    """Drop OCR replacement glyphs and edge punctuation."""
    return re.sub(r"\s+", " ", re.sub(r"[�\u0000-\u001f]", " ", text)).strip(" *•:-|,.")


def title_lines(views: Mapping[View, ViewAnalysis]) -> list[str]:
    """Primary transcript of the panel most likely to carry the brand: front, else the first captured."""
    for view in _TITLE_VIEWS:
        if view in views:
            return [line.text for result in views[view].ocr
                    if result.provider == "xiaomi" and result.status in ("ok", "partial") for line in result.lines]
    return []


def name_options(views: Mapping[View, ViewAnalysis]) -> list[str]:
    """Verbatim word spans Jev may pick as the brand or product name.

    Logos are often read as one run ("Amul PASTEURISED BUTTER utterly butterly delicious"),
    so whole lines cannot separate brand, product and tagline; short spans can.
    """
    options: dict[str, str] = {}
    lines = [_clean(line) for line in title_lines(views)[:15]]
    for index, line in enumerate(lines):
        words = line.split()
        spans = [" ".join(words[start:start + size]) for size in range(1, 5) for start in range(len(words) - size + 1)]
        # Products split across lines ("MAKHANA" / "POPPED FOX NUTS") need adjacent short lines joined.
        if index + 1 < len(lines) and len(words) <= 3 and len(lines[index + 1].split()) <= 3:
            spans.append(f"{line} {lines[index + 1]}")
        for span in spans:
            if re.search(r"[A-Za-z]{2,}", span) and not re.search(r"\d", span) and len(span) <= 48:
                options.setdefault(span.casefold(), span)
    return list(options.values())[:_MAX_NAME_OPTIONS]


def _picked(decision: DecisionResult, key: str, options: list[str], floor: float) -> tuple[str, float] | None:
    """Jev's span and its support: the probability of every option overlapping it.

    Overlapping spans ("TEDHE MEDHE", "TEDHE", "MEDHE") name the same thing and split
    Jev's probability, so the chosen option's own share understates agreement.
    """
    answer = decision.answers.get(key)
    if answer is None or not answer.choice.startswith("span_"):
        return None
    index = int(answer.choice.removeprefix("span_"))
    if index >= len(options):
        return None
    chosen = options[index].casefold()
    support = sum(p for option, p in answer.probabilities.items() if option.startswith("span_")
                  and int(option[5:]) < len(options)
                  and ((other := options[int(option[5:])].casefold()) in chosen or chosen in other))
    return (options[index], support) if support >= floor else None


def product_type_evidence(decision: DecisionResult, views: Mapping[View, ViewAnalysis]) -> Candidate | None:
    """Jev's product-type pick ("BUTTER", "POPPED FOX NUTS") as generic-name evidence, quoted from the front panel."""
    picked = _picked(decision, "name_type", name_options(views), PLACEMENT_CONFIDENCE)
    if picked is None:
        return None
    span, support = picked
    view = next(v for v in _TITLE_VIEWS if v in views)
    source = next((line for line in title_lines(views) if span.casefold() in _clean(line).casefold()), span)
    return Candidate(field="generic_name", value=span, view=view, provider="jev", source_text=source, confidence=min(1.0, support))


def label_brand(analysis: Analysis) -> str | None:
    """The brand as printed on the front, when Jev picked one."""
    picked = _picked(analysis.decision, "name_brand", name_options(analysis.views), NAME_CONFIDENCE)
    return picked[0] if picked else None


def label_name(analysis: Analysis) -> str | None:
    """A display name for catalog grouping, plus net quantity.

    Jev's brand and product picks first; without them, the first title-like line,
    else the generic name, else the manufacturer.
    """
    fields = {field.field: field for field in analysis.fields}
    observed = {name: field.value for name, field in fields.items() if field.status == "observed" and field.value}
    options = name_options(analysis.views)
    brand, product = (picked[0] if (picked := _picked(analysis.decision, key, options, NAME_CONFIDENCE)) else None
                      for key in ("name_brand", "name_product"))
    if brand and product and product.casefold().startswith(brand.casefold()):
        brand = None
    title = " ".join(part for part in (brand, product) if part) or _title(title_lines(analysis.views))
    if title is None and "generic_name" in observed:
        title = observed["generic_name"].splitlines()[0]
    if title is None and "manufacturer" in observed:
        first = observed["manufacturer"].splitlines()[0]
        # The company, not its address: "P. PRAYAGH CONSUMER CARE PVT LTD" from "... PVT LTD UNIT I, SURVEY NO. ...".
        company = re.match(r"^(.*?\b(?:private\s+limited|pvt\.?\s*ltd\.?|limited|ltd\.?|llp))(?!\w)", first, re.I)
        title = (company[1] if company else first).strip(" ,")
    quantity = observed.get("net_quantity")
    if title and quantity and quantity.casefold() not in title.casefold():
        return f"{title} · {quantity}"[:80]
    name = title or quantity
    return name[:80] if name else None

"""Conservative anchored extraction; values retain their source view and text."""

import re
import unicodedata
from decimal import Decimal
from app.schemas.analysis import Box, Calibration, Candidate, FieldName, FusedField, OCRLine, OCRResult, View
from app.services.calibration import physical_height

FIELDS: tuple[FieldName, ...] = ("generic_name", "net_quantity", "mrp", "manufacturer", "date", "consumer_care", "country_of_origin")
ANCHORS: dict[FieldName, str] = {
    "generic_name": r"(?:generic\s+name|product\s+name|commodity|proprietary\s+food\s*[-:]|उत्पाद\s*नाम)",
    "net_quantity": r"(?:net\s*(?:wt\.?|weight|qty\.?|quantity|content[s]?)|शुद्ध\s*(?:मात्रा|वजन))",
    "mrp": r"(?:m\.?\s*r\.?\s*p\.?|maximum\s+retail\s+price|अधिकतम\s*खुदरा\s*मूल्य)",
    "manufacturer": r"(?:manufactured\s+(?:in\s+[^:;,\n]{1,40}?\s+)?by|packed\s+by|imported\s+by|mf[gd]\.?\s*(?:&\s*mkt\.?\s*)?by|निर्माता|निर्मित)",
    "date": r"(?:mf[gd](?!\.?\s*(?:&\s*mkt\.?\s*)?by\b)\.?\s*(?:date)?|packed\s+on|date\s+of\s+(?:manufacture|packing)|निर्माण\s*तिथि)",
    "consumer_care": r"(?:(?:consumer|customer)\s*(?:care|services?)(?:\s+manager)?|helpline|उपभोक्ता\s*सेवा)",
    "country_of_origin": r"(?:country\s+of\s+origin|made\s+in|उद्गम\s*देश)",
}
ANCHORS = {field: rf"(?<!\w){pattern}(?!\w)" for field, pattern in ANCHORS.items()}
_QUANTITY = re.compile(r"(\d+(?:\.\d+)?)\s*(kg|mg|g|ml|cl|l|litres?|liters?|nos?\.?|pcs?\.?|units?|ग्राम|किग्रा|मिलीलीटर|लीटर)\b", re.I)
_UNITS = {"kg": ("mass", "1000"), "g": ("mass", "1"), "mg": ("mass", ".001"),
          "किग्रा": ("mass", "1000"), "ग्राम": ("mass", "1"), "l": ("volume", "1000"),
          "ml": ("volume", "1"), "cl": ("volume", "10"), "लीटर": ("volume", "1000"), "मिलीलीटर": ("volume", "1")}
_PRICE = re.compile(r"(?:₹|rs\.?|inr)?\s*(?:\d{1,3}(?:,\d{2})*,\d{3}|\d{1,3}(?:,\d{3})+|\d+)(?:\.\d{1,2})?(?![\d.,%])", re.I)
_DATE = re.compile(
    r"\b(?:\d{4}[-/.](?:0?[1-9]|1[0-2])[-/.](?:0?[1-9]|[12]\d|3[01])"
    r"|(?:0?[1-9]|[12]\d|3[01])[-/.](?:0?[1-9]|1[0-2])[-/.]\d{2,4}"
    r"|(?:0?[1-9]|1[0-2])[-/.]\d{2,4}"
    r"|(?:\d{1,2}[-\s]?)?(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*[-\s]?\d{2,4})\b", re.I,
)
_SECTION = re.compile(r"^(?:nutrition|ingredients?|serving|storage|allergen|contains|lot\b|batch\b|see\s|best\s+before|use\s+by|expiry|lic\.?\s*no|good\s+to\s+know|step\s+\d|scan\s|based\s+on)", re.I)
_REFERENCE = re.compile(r"^\W*(?:refer\b|see\s+(?:below|above|side|panel|pack|batch|address|label|details)\b|not\s+(?:shown|available|printed)\b)|\b(?:see\s+(?:below|above|side\s+panel)|letter\s+after\s+use\s+by)\b", re.I)
_CONTACT = re.compile(r"[\w.+-]+@[\w.-]+\.[a-z]{2,}|\bwww\.|\+?\d[\d ()-]{6,}\d|\b\d{6}\b", re.I)


def normalize(value: str, *, preserve_commas: bool = False) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    value = "".join(str(unicodedata.digit(c)) if c.isdigit() else c for c in value)
    return re.sub(r"[\s:;]+" if preserve_commas else r"[\s:;,]+", " ", value).strip(" .")


def price(value: str) -> Decimal | None:
    value = normalize(value, preserve_commas=True)
    if not _PRICE.fullmatch(value):
        return None
    return Decimal(re.sub(r"₹|rs\.?|inr|\s|,", "", value))


def quantity(value: str) -> tuple[str, Decimal] | None:
    match = _QUANTITY.fullmatch(normalize(value, preserve_commas=True))
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


def _next_line(current: OCRLine, lines: list[OCRLine], used: list[OCRLine]) -> OCRLine | None:
    """Follow the nearest aligned text, regardless of provider serialization order."""
    if current.box is None:
        index = next(i for i, line in enumerate(lines) if line is current)
        neighbor = lines[index + 1] if index + 1 < len(lines) else None
        return neighbor if neighbor is not None and neighbor.box is None and all(neighbor is not x for x in used) else None
    a = current.box
    height = a.y1 - a.y0
    nearby = []
    for line in lines:
        if any(line is x for x in used) or line.box is None:
            continue
        b = line.box
        overlap = min(a.y1, b.y1) - max(a.y0, b.y0)
        if overlap >= .5 * min(height, b.y1 - b.y0) and 0 <= b.x0 - a.x1 <= 3 * height:
            nearby.append(((b.x0 - a.x1) / height, line))
        elif b.y0 > a.y0 + .5 * height and -.4 * height <= b.y0 - a.y1 <= 2 * height and abs(b.x0 - a.x0) <= 2 * height:
            nearby.append((3 + (b.y0 - a.y1) / height + abs(b.x0 - a.x0) / height, line))
    nearby.sort(key=lambda pair: pair[0])
    if not nearby:
        return None
    # Equal-distance alternatives are ambiguous, not a reason to pick OCR order.
    if len(nearby) > 1 and abs(nearby[0][0] - nearby[1][0]) < .15 and normalize(nearby[0][1].text) != normalize(nearby[1][1].text):
        return None
    return nearby[0][1]


def _value(field: FieldName, text: str) -> str:
    numeric = field in ("net_quantity", "mrp", "date")
    text = text.strip(" :।,.;" if numeric else " :-।,.;")
    if _REFERENCE.search(text):
        return ""
    if numeric:
        normalized = normalize(text, preserve_commas=True)
        # Numeric declarations must start with their value, not a later lot number.
        pattern = {"net_quantity": _QUANTITY, "mrp": _PRICE, "date": _DATE}[field]
        parsed = pattern.match(normalized)
        if parsed and field == "mrp" and normalized[parsed.end():].lstrip().startswith("%"):
            return ""
        return parsed.group(0).strip() if parsed else ""
    return text


def extract(ocr: OCRResult, view: View, calibration: Calibration | None = None) -> list[Candidate]:
    candidates: list[Candidate] = []
    if ocr.status not in ("ok", "partial"):
        return candidates
    lines = []
    seen_regions = set()
    for line in ocr.lines:
        if line.box is not None:
            key = (normalize(line.text), *line.box.model_dump().values())
            if key in seen_regions:
                continue
            seen_regions.add(key)
        lines.append(line)
    for line in lines:
        for field, anchor in ANCHORS.items():
            match = re.search(anchor, line.text, re.I)
            if not match:
                continue
            source = line
            source_text = line.text
            tail = line.text[match.end():]
            boundaries = [m.start() for pattern in ANCHORS.values() if (m := re.search(pattern, tail, re.I))]
            segment = tail[:min(boundaries)] if boundaries else tail
            value = _value(field, segment)
            if _REFERENCE.search(segment):
                continue
            used = [line]
            parts = [value] if value else []
            # Without geometry, continue only explicit text blocks, never numbers.
            limit = 6 if field == "consumer_care" else 1 if not value and field in ("manufacturer", "country_of_origin", "generic_name") else 0
            if not value and line.box is not None:
                limit = max(limit, 1)
            if boundaries:
                limit = 0
            if field in ("net_quantity", "mrp", "date") and not value and tail.strip(" :-।,.;"):
                limit = 0
            for _ in range(limit):
                neighbor = _next_line(used[-1], lines, used)
                if neighbor is None or _SECTION.search(neighbor.text.strip(" *•")) or any(re.search(pattern, neighbor.text, re.I) for pattern in ANCHORS.values()):
                    break
                used.append(neighbor)
                part = _value(field, neighbor.text)
                if not part:
                    break
                parts.append(part)
            value = "\n".join(parts)
            if field == "consumer_care" and not _CONTACT.search(value):
                continue
            if len(used) > 1:
                value_lines = used if parts and parts[0] == _value(field, tail) else used[1:]
                boxes = [item.box for item in value_lines if item.box is not None]
                source_text = "\n".join(item.text for item in used)
                source = OCRLine(text="\n".join(item.text for item in value_lines),
                    box=Box(x0=min(b.x0 for b in boxes), y0=min(b.y0 for b in boxes),
                            x1=max(b.x1 for b in boxes), y1=max(b.y1 for b in boxes)) if boxes else None,
                    words=[word for item in value_lines for word in item.words])
            if not value:
                continue
            value_box = source.box
            height_box = source.box
            confidence = source.confidence
            # Word boxes isolate declaration values from taller anchors and other text.
            value_start = normalize(source.text).find(normalize(value))
            if source.words and value_start >= 0:
                offset = 0
                selected = []
                for word in source.words:
                    word_length = len(normalize(word.text))
                    if offset < value_start + len(normalize(value)) and offset + word_length > value_start:
                        selected.append(word)
                    offset += word_length + 1
                if selected:
                    value_box = Box(x0=min(w.box.x0 for w in selected), y0=min(w.box.y0 for w in selected),
                                    x1=max(w.box.x1 for w in selected), y1=max(w.box.y1 for w in selected))
                    confidence = sum(w.confidence for w in selected) / len(selected)
                    numerals = [w for w in selected if re.search(r"\d", w.text)]
                    height_box = numerals[0].box if field in ("net_quantity", "mrp") and numerals else value_box
            candidates.append(Candidate(field=field, value=value, view=view, provider=ocr.provider,
                source_text=source_text, box=value_box, confidence=confidence,
                height_mm=physical_height(height_box, calibration) if calibration else None))
    return candidates


def canonical(field: FieldName, value: str) -> str:
    if field == "mrp":
        amount = price(value)
        return format(amount.normalize(), "f") if amount is not None else normalize(value)
    if field == "net_quantity":
        parsed = quantity(value)
        if parsed is not None:
            dimension, amount = parsed
            return f"{dimension}:{format(amount.normalize(), 'f')}"
    value = normalize(value)
    if field == "consumer_care":
        value = re.sub(r"(?<=\d)[\s()-]+(?=\d)", "", value)
    if field == "net_quantity":
        return re.sub(r"\s", "", value).replace("ग्राम", "g").replace("मिलीलीटर", "ml")
    return value


def fuse(candidates: list[Candidate]) -> list[FusedField]:
    fused = []
    for field in FIELDS:
        evidence = [c for c in candidates if c.field == field]
        # Rank supporting evidence; never let confidence erase a conflicting value.
        evidence.sort(key=lambda c: c.confidence if c.confidence is not None else -1, reverse=True)
        values = {canonical(field, c.value) for c in evidence}
        if not evidence:
            fused.append(FusedField(field=field, status="missing", reason="No anchored declaration extracted. Missing OCR is not proof of absence."))
        elif len(values) > 1:
            fused.append(FusedField(field=field, status="conflict", evidence=evidence,
                reason="OCR providers or views disagree. Inspector review required."))
        else:
            fused.append(FusedField(field=field, status="observed", value=evidence[0].value, evidence=evidence,
                reason="Unverified OCR transcription; inspector review required. Readings from the same photo or its crops are not independent confirmation."))
    return fused

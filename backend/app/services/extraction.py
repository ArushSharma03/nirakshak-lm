"""Conservative anchored extraction; values retain their source view and text."""

import re
import unicodedata
from app.schemas.analysis import Box, Calibration, Candidate, FieldName, FusedField, OCRResult, View
from app.services.calibration import physical_height

FIELDS: tuple[FieldName, ...] = ("generic_name", "net_quantity", "mrp", "manufacturer", "date", "consumer_care", "country_of_origin")
ANCHORS: dict[FieldName, str] = {
    "generic_name": r"(?:generic\s+name|product\s+name|commodity|उत्पाद\s*नाम)",
    "net_quantity": r"(?:net\s*(?:wt\.?|weight|qty\.?|quantity|content[s]?)|शुद्ध\s*(?:मात्रा|वजन))",
    "mrp": r"(?:m\.?\s*r\.?\s*p\.?|maximum\s+retail\s+price|अधिकतम\s*खुदरा\s*मूल्य)",
    "manufacturer": r"(?:manufactured\s+by|packed\s+by|imported\s+by|mfd\.?\s*by|निर्माता|निर्मित)",
    "date": r"(?:mfg\.?\s*(?:date)?|mfd\.?\s*(?:date)?|packed\s+on|date\s+of\s+(?:manufacture|packing)|निर्माण\s*तिथि)",
    "consumer_care": r"(?:consumer\s*care|customer\s*care|helpline|उपभोक्ता\s*सेवा)",
    "country_of_origin": r"(?:country\s+of\s+origin|made\s+in|उद्गम\s*देश)",
}
_QUANTITY = re.compile(r"\d+(?:[.,]\d+)?\s*(?:kg|mg|g|ml|cl|l|litres?|liters?|ग्राम|किग्रा|मिलीलीटर|लीटर)\b", re.I)
_PRICE = re.compile(r"(?:₹|rs\.?|inr)?\s*\d+(?:[.,]\d{1,2})?", re.I)


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    value = "".join(str(unicodedata.digit(c)) if c.isdigit() else c for c in value)
    return re.sub(r"[\s:;,]+", " ", value).strip(" .")


def extract(ocr: OCRResult, view: View, calibration: Calibration) -> list[Candidate]:
    candidates: list[Candidate] = []
    if ocr.status != "ok":
        return candidates
    for index, line in enumerate(ocr.lines):
        for field, anchor in ANCHORS.items():
            match = re.search(anchor, line.text, re.I)
            if not match:
                continue
            source = line
            value = line.text[match.end():].strip(" :-।")
            # Adjacent values must be below the anchor and aligned in this image.
            if not value and index + 1 < len(ocr.lines):
                neighbor = ocr.lines[index + 1]
                a, b = line.box, neighbor.box
                if a and b and 0 <= b.y0 - a.y1 <= 2 * (a.y1 - a.y0) and abs(b.x0 - a.x0) <= 2 * (a.y1 - a.y0):
                    if not any(re.search(pattern, neighbor.text, re.I) for pattern in ANCHORS.values()):
                        source, value = neighbor, neighbor.text
                elif a is None and b is None and field == "manufacturer":
                    # VLM line order supports immediate label continuation, not geometry.
                    if not any(re.search(pattern, neighbor.text, re.I) for pattern in ANCHORS.values()):
                        source, value = neighbor, neighbor.text
            if field == "net_quantity":
                parsed = _QUANTITY.search(normalize(value))
                value = parsed.group(0) if parsed else ""
            elif field == "mrp":
                parsed = _PRICE.search(normalize(value))
                value = parsed.group(0).strip() if parsed else ""
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
                source_text=source.text if source is line else f"{line.text}\n{source.text}", box=value_box, confidence=confidence,
                height_mm=physical_height(height_box, calibration)))
    return candidates


def canonical(field: FieldName, value: str) -> str:
    value = normalize(value)
    if field == "mrp":
        value = re.sub(r"₹|rs\.?|inr|\s", "", value)
        try:
            return str(float(value.replace(",", ".")))
        except ValueError:
            return value
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
                reason="Matching source readings; OCR confidence ranks evidence without asserting legal validity."))
    return fused

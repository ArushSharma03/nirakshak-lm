"""Conservative anchored extraction; values retain their source view and text."""

import re
import unicodedata
from datetime import date
from decimal import Decimal
from difflib import SequenceMatcher
from app.schemas.analysis import Box, Calibration, Candidate, FieldName, FusedField, OCRLine, OCRResult, View
from app.services.calibration import physical_height
from app.services.countries import country_of

FIELDS: tuple[FieldName, ...] = ("generic_name", "net_quantity", "mrp", "manufacturer", "date", "expiry", "consumer_care", "country_of_origin")
ANCHORS: dict[FieldName, str] = {
    "generic_name": r"(?:generic\s+name|product\s+name|commodity|proprietary\s+food\s*[-:]|उत्पाद\s*नाम)",
    "net_quantity": r"(?:net\s*(?:wt\.?|weight|qty\.?|quantity|content[s]?)|शुद्ध\s*(?:मात्रा|वजन))",
    "mrp": r"(?:m\.?\s*r\.?\s*p\.?|maximum\s+retail\s+price|अधिकतम\s*खुदरा\s*मूल्य)",
    # "PRAN ... Pvt. Ltd. (Imported by)" names the role after the company; in parentheses (even when OCR
    # splits it to "Imported by)") it is not a heading.
    "manufacturer": r"(?<!\()(?:manufactured\s+(?:in\s+[^:;,\n]{1,40}?\s+)?by|packed\s+by|imported\s+by|imp\.?\s*by|mf[gd]\.?\s*(?:&\s*mkt\.?\s*)?by|निर्माता|निर्मित)(?!\s*\))",
    # "MEG-08 AUG 2026": OCR reads the F of a dot-matrix MFG as E; only before a number.
    "date": r"(?:mf[gd](?!\.?\s*(?:&\s*mkt\.?\s*)?by\b)\.?\s*(?:date)?|me[gd](?=\s*[:\-]\s*\d)|packed\s+on|date\s+of\s+(?:manufacture|packing)|निर्माण\s*तिथि)",
    "expiry": r"(?:best\s+before|use\s+by(?:\s+date)?|exp(?:iry)?\.?(?:\s*date)?|ubd)",
    # Not inside a company name: "P. PRAYAGH CONSUMER CARE PRIVATE LIMITED" is a manufacturer.
    "consumer_care": r"(?:(?:consumer|customer)\s*(?:care|services?|complaints?|feedback)(?:\s+manager)?(?!\s+(?:private|pvt|ltd|limited|products|foods)\b)"
                     r"|for\s+feedback|(?:feedback\s*/\s*)?complaints?\s+contact|feedback\s*/\s*complaints?|helpline|उपभोक्ता\s*सेवा)",
    "country_of_origin": r"(?:country\s+of\s+origin|made\s+in|product\s+of|उद्गम\s*देश)",
}
# Never inside a word, email or URL: "CUSTOMERCARE@HALDIRAM.COM" is not a consumer-care heading.
ANCHORS = {field: rf"(?<![\w@.]){pattern}(?![\w@])" for field, pattern in ANCHORS.items()}
# The generic name before its class: "READY-TO-EAT SAVOURIES (PROPRIETARY FOOD)",
# "(15.1) MICROWAVE POPCORN - READY TO COOK CORN PRODUCT A PROPRIETARY FOOD".
_NAME_BEFORE_CLASS = re.compile(r"^\W*(?:\(\s*[\d.]+\s*\)\s*)?(?P<name>[A-Za-z][^()]{2,80}?)\s*(?:[-–]\s*)?(?:\(\s*|\ba\s+)proprietary\s+food\b", re.I)
_QUANTITY = re.compile(r"(\d+(?:\.\d+)?)\s*(kg|mg|g|ml|cl|l|litres?|liters?|nos?\.?|pcs?\.?|units?|ग्राम|किग्रा|मिलीलीटर|लीटर)\b", re.I)
_UNITS = {"kg": ("mass", "1000"), "g": ("mass", "1"), "mg": ("mass", ".001"),
          "किग्रा": ("mass", "1000"), "ग्राम": ("mass", "1"), "l": ("volume", "1000"),
          "ml": ("volume", "1"), "cl": ("volume", "10"), "लीटर": ("volume", "1000"), "मिलीलीटर": ("volume", "1")}
_PRICE = re.compile(r"(?:₹|rs\.?|inr)?\s*(?:\d{1,3}(?:,\d{2})*,\d{3}|\d{1,3}(?:,\d{3})+|\d+)(?:\.\d{1,2})?(?![\d.,%])", re.I)
_DATE = re.compile(
    r"\b(?:\d{4}[-/.](?:0?[1-9]|1[0-2])[-/.](?:0?[1-9]|[12]\d|3[01])"
    r"|(?:0?[1-9]|[12]\d|3[01])[-/.](?:0?[1-9]|1[0-2])[-/.]\d{2,4}"
    r"|(?:0?[1-9]|1[0-2])[-/.]\d{2,4}"
    r"|(?:\d{1,2}[-\s]?)?(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?[-\s]?\d{2,4})\b", re.I,
)
_MONTHS = ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec")
# Whole month tokens only, so "DECLARATION 2011" is not December 2011. [0o]ct: OCR reads the O of OCT as zero.
_MONTH = r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sep(?:t(?:ember)?)?|[0o]ct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
# "13/08/2026", "06/09/26", "24 AUG. 26", "09APR2025", "230CT26".
_DATE_TOKEN = re.compile(
    r"(?<![\d/.])(?P<d>\d{1,2})\s?[/.-]\s?(?P<m>\d{1,2})\s?[/.-]\s?(?P<y>\d{4}|\d{2})(?![\d/])"
    rf"|(?<!\d)(?P<d2>\d{{1,2}})?[\s.:-]*(?<![a-z])(?P<mon>{_MONTH})(?![a-z])\.?[\s-]*(?P<y2>\d{{4}}|\d{{2}})(?!\d)",
    re.I)


def parse_date(match: re.Match[str]) -> date | None:
    """A date token as a date; month-only tokens ("AUG 2027") become the 1st."""
    try:
        if match["d"]:
            day, month, year = int(match["d"]), int(match["m"]), int(match["y"])
        else:
            mon = match["mon"].casefold().replace("0", "o")
            day, month, year = int(match["d2"] or 1), _MONTHS.index(mon[:3]) + 1, int(match["y2"])
        return date(year + 2000 if year < 100 else year, month, day)
    except ValueError:
        return None


def _date_parts(value: str) -> tuple[int, int, int | None] | None:
    """(year, month, day or None) of the single date a reading states."""
    matches = [m for m in _DATE_TOKEN.finditer(value) if parse_date(m)]
    if len(matches) != 1:
        return None
    parsed = parse_date(matches[0])
    has_day = bool(matches[0]["d"] or matches[0]["d2"])
    return parsed.year, parsed.month, parsed.day if has_day else None


def _agreeing_dates(evidence: list[Candidate]) -> Candidate | None:
    """The most precise reading when all name one month and no two name different days
    ("AUG 2027" from a garbled day and "07 AUG 2027" agree)."""
    # A crop edge can cut a reading short ("07 AUG 20" beside "07 AUG 2027"); it repeats, not contradicts.
    texts = [normalize(c.value) for c in evidence]
    whole = [c for c, t in zip(evidence, texts) if not any(o != t and o.startswith(t) for o in texts)]
    parts = [_date_parts(c.value) for c in whole]
    if None in parts or len({(y, m) for y, m, _ in parts}) != 1 or len({d for *_, d in parts if d is not None}) > 1:
        return None
    return next((c for c, p in zip(whole, parts) if p[2] is not None), whole[0])


# Best before / use by: a date, or a shelf life ("TWELVE MONTHS FROM PACKAGING").
_EXPIRY = re.compile(
    _DATE.pattern + r"|\b(?:\d{1,2}|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|eighteen|twenty[-\s]four)"
    r"\s+months?\b(?:\s+from\s+(?:the\s+date\s+of\s+)?(?:manufacture|manufacturing|packaging|packing|mfg|mfd|pkd))?", re.I)
_SECTION = re.compile(r"^(?:nutrition|ingredients?|serving|storage|allergen|contains|lot\b|batch\b|see\s|best\s+before|use\s+by|expiry|lic\.?\s*no|good\s+to\s+know|step\s+\d|scan\s|based\s+on)", re.I)
_REFERENCE = re.compile(r"^\W*(?:refer\b|see\s+(?:below|above|side|panel|pack|batch|address|label|details)\b|not\s+(?:shown|available|printed)\b)|\b(?:see\s+(?:below|above|side\s+panel)|letter\s+after\s+use\s+by)\b", re.I)
_TAX_INCLUSIVE_PRICE = re.compile(
    r"(?P<price>(?:₹|rs\.?|inr)\s*\d[\d,]*(?:\.\d{1,2})?)\s*(?:/-\s*)?\(?\s*incl(?:usive|uding|\.)?\s*(?:of\s+)?all\s+taxes", re.I)
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
    numeric = field in ("net_quantity", "mrp", "date", "expiry")
    text = text.strip(" :।,.;" if numeric else " :-।,.;")
    if field in ("date", "expiry"):
        text = text.lstrip("-– ")  # a separator, never a sign: "MEG-08 AUG 2026"
    if _REFERENCE.search(text):
        return ""
    if numeric:
        normalized = normalize(text, preserve_commas=True)
        pattern = {"net_quantity": _QUANTITY, "mrp": _PRICE, "date": _DATE, "expiry": _EXPIRY}[field]
        # Numeric declarations must start with their value, not a later lot number. An expiry may follow
        # an OCR-garbled day ("EXP: OF AUG 2027"), so it is searched; its segment already ends at the next heading.
        find = pattern.search if field == "expiry" else pattern.match
        parsed = find(normalized)
        if not parsed or field == "mrp" and normalized[parsed.end():].lstrip().startswith("%"):
            return ""
        # Report the value as printed ("Rs. 30.00", "09APR2025"), not casefolded; digits stay ASCII.
        ascii_digits = "".join(str(unicodedata.digit(c)) if c.isdigit() else c for c in unicodedata.normalize("NFKC", text))
        printed = find(re.sub(r"[\s:;]+", " ", ascii_digits).strip())
        return (printed or parsed).group(0).strip()
    # A heading followed only by punctuation ("Imported by)") states nothing.
    return text if re.search(r"\w", text) else ""


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
        if named := _NAME_BEFORE_CLASS.search(line.text):
            candidates.append(Candidate(field="generic_name", value=named["name"].strip(" -–,"), view=view, provider=ocr.provider,
                source_text=line.text, box=line.box, confidence=line.confidence))
        # Retail price printed without "MRP": "₹20.00 incl. of all taxes" is the statutory wording.
        if not re.search(ANCHORS["mrp"], line.text, re.I) and (taxed := _TAX_INCLUSIVE_PRICE.search(line.text)):
            candidates.append(Candidate(field="mrp", value=taxed["price"].strip(), view=view, provider=ocr.provider,
                source_text=line.text, box=line.box, confidence=line.confidence))
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
            # A cross-reference can straddle the next heading ("Refer letter after | Use by and see below");
            # one that starts after the cut belongs to the next heading ("MRP: see side panel").
            if _REFERENCE.search(segment) or any(m.start() < len(segment) for m in _REFERENCE.finditer(tail[:len(segment) + 24])):
                continue
            used = [line]
            parts = [value] if value else []
            first_part_line = 0 if parts else 1  # index into `used` of parts[0]
            # Without geometry, continue only explicit text blocks, never numbers.
            limit = 6 if field == "consumer_care" else 1 if not value and field in ("manufacturer", "country_of_origin", "generic_name") else 0
            if not value and line.box is not None:
                limit = max(limit, 1)
            if boundaries:
                limit = 0
            if field in ("net_quantity", "mrp", "date", "expiry") and not value and tail.strip(" :-।,.;"):
                limit = 0
            for _ in range(limit):
                neighbor = _next_line(used[-1], lines, used)
                # "customercare@amul.coop" continues a contact block; it does not start a new declaration.
                own_contact = field == "consumer_care" and _CONTACT.search(neighbor.text) if neighbor else False
                if neighbor is None or _SECTION.search(neighbor.text.strip(" *•")) or any(
                        re.search(pattern, neighbor.text, re.I) for name, pattern in ANCHORS.items() if not (own_contact and name == field)):
                    break
                used.append(neighbor)
                part = _value(field, neighbor.text)
                if not part:
                    break
                parts.append(part)
            if field == "consumer_care":
                # A contact block ends at its last address, phone, email or website line, not at
                # the next slogan ("QUALITY GUARANTEED") that happens to sit below it.
                last = max((i for i, part in enumerate(parts) if _CONTACT.search(part)), default=-1)
                parts, used = parts[:last + 1], used[:max(1, last + 1 + first_part_line)]
                # It starts at the first company, address or contact line, not at lead-in text
                # ("Executive at", "/ FEEDBACK", "POST CRO AT CORPORATE OFFICE").
                while parts and not re.search(r"\d|@|www\.|\b(?:ltd|limited|pvt|private|llp|inc|co-?op)", parts[0], re.I):
                    parts.pop(0)
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
            if field == "country_of_origin":
                value = country_of(value) or ""  # "Made in India." -> "India"; no single country, no reading
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


def country_from_maker(fields: list[FusedField]) -> Candidate | None:
    """Country named in the manufacturer's address, when nothing else declares one.

    Imports are excluded: their Indian importer address says nothing about where the goods were made.
    """
    by_field = {field.field: field for field in fields}
    maker = by_field["manufacturer"]
    if by_field["country_of_origin"].status != "missing" or not maker.evidence:
        return None
    sources = [c for c in maker.evidence if c.provider != "tesseract"] or maker.evidence
    text = "\n".join(c.source_text for c in sources)
    if re.search(r"\bimport|\bimp\.?\s*by\b", text, re.I) or (country := country_of(text)) is None:
        return None
    source = next(c for c in sources if country_of(c.source_text) == country)
    return Candidate(field="country_of_origin", value=country, view=source.view, provider=source.provider,
                     source_text=source.source_text, box=source.box)


def _company(value: str) -> str | None:
    """The company name up to its legal suffix, spelled one way: 'p prayagh consumer care pvt ltd'."""
    match = re.search(r"^(.*?\b(?:private\s+limited|pvt\.?\s*ltd|limited|ltd|llp))\b", value, re.I | re.S)
    if match is None:
        return None
    name = normalize(match[1]).replace("private limited", "pvt ltd").replace("limited", "ltd")
    return re.sub(r"[^\w ]+", "", re.sub(r"pvt\.?\s*ltd", "pvt ltd", name)).strip()


def _agreeing_company(evidence: list[Candidate]) -> Candidate | None:
    """The fullest reading when every reading names the same company, allowing a one-letter OCR slip
    ("P. PRAYASH" / "P. PRAYAGH") but not a different name ("Agro Tech" / "Rukkveer")."""
    names = [_company(c.value) for c in evidence]
    if None in names:
        return None
    first = names[0]
    if all(SequenceMatcher(None, first, name).ratio() >= 0.92 for name in names):
        return max(evidence, key=lambda c: len(c.value))
    return None


def _contacts(value: str) -> frozenset[str]:
    """Phone numbers (digits only), emails and websites in a consumer-care reading."""
    phones = {re.sub(r"\D", "", m) for m in re.findall(r"\+?\d[\d ()-]{6,}\d", value)}
    links = {m.casefold().rstrip(".") for m in re.findall(r"[\w.+-]+@[\w.-]+\.[a-z]{2,}|\bwww\.[\w.-]+", value, re.I)}
    return frozenset({p for p in phones if len(p) >= 8} | links)


def _agreeing_contacts(evidence: list[Candidate]) -> Candidate | None:
    """The reading whose contacts include every other reading's, if all readings have contacts."""
    sets = [_contacts(c.value) for c in evidence]
    if not all(sets):
        return None
    richest = max(range(len(evidence)), key=lambda i: len(sets[i]))
    return evidence[richest] if all(s <= sets[richest] for s in sets) else None


def _agreeing_prefix(evidence: list[Candidate]) -> Candidate | None:
    """The longest reading when every other is a crop-cut copy of it ("TWELVE MONTHS" of "... FROM PACKAGING")."""
    longest = max(evidence, key=lambda c: len(normalize(c.value)))
    return longest if all(normalize(longest.value).startswith(normalize(c.value)) for c in evidence) else None


# Readings that differ in wording but state one declaration. Prices and quantities have no such rule:
# "Rs. 3" is not a cut-off "Rs. 30".
_AGREEMENT = {
    "date": _agreeing_dates, "expiry": _agreeing_dates,
    "manufacturer": _agreeing_company,  # one company with and without its address, or a one-letter OCR slip
    "consumer_care": _agreeing_contacts,  # same phone/email/website under different lead-in text
}


def _agreeing(field: FieldName, evidence: list[Candidate]) -> Candidate | None:
    if field not in ("mrp", "net_quantity") and (whole := _agreeing_prefix(evidence)) is not None:
        return whole
    rule = _AGREEMENT.get(field)
    return rule(evidence) if rule else None


def _as_date(value: str) -> date | None:
    parts = _date_parts(value)
    return date(parts[0], parts[1], parts[2] or 1) if parts else None


def fuse(candidates: list[Candidate]) -> list[FusedField]:
    fused = []
    made: date | None = None
    for field in FIELDS:
        evidence = [c for c in candidates if c.field == field]
        if field == "expiry" and made is not None:
            # A pack cannot expire on or before it was made; such a reading took the wrong column
            # ("USE BY : 06/09/26" where 06/09/26 is the MFG date).
            evidence = [c for c in evidence if (d := _as_date(c.value)) is None or d > made]
        # Rank supporting evidence; never let confidence erase a conflicting value.
        evidence.sort(key=lambda c: c.confidence if c.confidence is not None else -1, reverse=True)
        values = {canonical(field, c.value) for c in evidence}
        if len(values) > 1 and (richest := _agreeing(field, evidence)) is not None:
            evidence.remove(richest)
            evidence.insert(0, richest)
            values = {canonical(field, richest.value)}
        if field == "date" and len(values) == 1 and evidence:
            made = _as_date(evidence[0].value)
        if not evidence:
            fused.append(FusedField(field=field, status="missing", reason="No anchored declaration extracted. Missing OCR is not proof of absence."))
        elif len(values) > 1:
            fused.append(FusedField(field=field, status="conflict", evidence=evidence,
                reason="OCR providers or views disagree. Inspector review required."))
        elif all(c.provider == "jev" for c in evidence):
            fused.append(FusedField(field=field, status="observed", value=evidence[0].value, evidence=evidence,
                reason="No text pattern matched; Jev placed this OCR line here. Unverified; inspector review required."))
        else:
            fused.append(FusedField(field=field, status="observed", value=evidence[0].value, evidence=evidence,
                reason="Unverified OCR transcription; inspector review required. Readings from the same photo or its crops are not independent confirmation."))
    return fused

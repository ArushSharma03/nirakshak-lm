"""Read printed coding windows: MRP, manufacture and expiry dates, and net quantity printed apart from their headings.

Packs print headings ("MRP Rs. (incl. of all taxes)", "Mfg. Date ; Exp. Date", "NET WT.:") in one
place and stamp the values elsewhere, and OCR returns them in no reliable order. The values identify
themselves instead: the MRP is the one rupee amount that is not a per-gram unit price, the
manufacture date is the earlier of the stamped dates, and the net quantity is a lone weight. A
value is used only for a field whose heading appears on the same panel and that nothing else found.
"""

import re
from datetime import date
from decimal import Decimal

from app.schemas.analysis import Candidate, FieldName, View
from app.services.extraction import _DATE_TOKEN, _MONTH, ANCHORS, _QUANTITY, parse_date

_PRICE_TOKEN = re.compile(r"(?:₹|\brs\b\.?|\binr\b)\s*[:.]?\s*(?P<amount>\d[\d,]*(?:\s?\.\s?\d{1,2})?)", re.I)
# What follows a unit sale price: "/g", OCR's "/9", "Per g", "per 100 g".
_UNIT_PRICE = re.compile(r"^\s*(?:/\s*-?\s*(?:\d{0,3}\s*)?(?:g|9|gm|kg|ml|l)\b|per\b)", re.I)
_MFD_HEADING = re.compile(r"\bmf[gd]\b|\bme[gd](?=\s*[:\-]\s*\d)|\bmfg\.?\s*date|\bpkd\b|packed\s+on|date\s+of\s+(?:manufacture|packing)", re.I)
_EXPIRY_HEADING = re.compile(r"use\s+by|best\s+before|\bexp(?:iry)?\b|\bubd\b", re.I)
_MRP_HEADING = re.compile(ANCHORS["mrp"] + r"|incl(?:usive|\.)?\s*(?:of\s+)?all\s+taxes", re.I)
# Words a stamped coding line may contain; anything wordier is prose (e.g. a packaging-film licence date).
_CODE_WORDS = re.compile(rf"^(?:mf[gd]|date|exp|expiry|use|best|before|batch|lot|pkd|packed|mrp|ubd|incl|taxes|per|{_MONTH})$", re.I)


def _is_coding_line(text: str) -> bool:
    words = [w for w in re.findall(r"[A-Za-z]{4,}", text) if not _CODE_WORDS.match(w)]
    return len(words) <= 2


def coding_window(lines: list[tuple[str, str]], view: View, found: set[FieldName]) -> list[Candidate]:
    """Candidates for MRP, date and net quantity from one panel's (provider, text) lines."""
    panel = "\n".join(text for _, text in lines)
    candidates: list[Candidate] = []

    def add(field: FieldName, value: str, provider: str, source: str) -> None:
        candidates.append(Candidate(field=field, value=value.strip(" .,;:"), view=view, provider=provider, source_text=source))

    if "mrp" not in found and _MRP_HEADING.search(panel):
        prices: dict[Decimal, tuple[str, str, str]] = {}
        for provider, text in lines:
            for match in _PRICE_TOKEN.finditer(text):
                amount = Decimal(re.sub(r"[\s,]", "", match["amount"]))
                if amount > 0 and not _UNIT_PRICE.match(text[match.end():]):
                    prices.setdefault(amount, (match.group(0), provider, text))
        if len(prices) == 1:
            value, provider, source = next(iter(prices.values()))
            add("mrp", value, provider, source)

    tokens = [(match, provider, text) for provider, text in lines if _is_coding_line(text) for match in _DATE_TOKEN.finditer(text)]
    spelled = {re.sub(r"\s+", " ", m.group(0)).casefold() for m, _, _ in tokens}
    dates: dict[date, tuple[str, str, str]] = {}
    for match, provider, text in tokens:
        token = re.sub(r"\s+", " ", match.group(0)).casefold()
        # A crop edge cuts "07 AUG 2027" to "07 AUG 20", which would parse as 2020.
        if any(other != token and other.startswith(token) for other in spelled):
            continue
        if (parsed := parse_date(match)) is not None:
            dates.setdefault(parsed, (match.group(0), provider, text))
    mfd_heading, expiry_heading = _MFD_HEADING.search(panel), _EXPIRY_HEADING.search(panel)
    # A pack is made before it expires: the earliest stamped date is the manufacture date, the latest the expiry.
    if "date" not in found and mfd_heading and (len(dates) >= 2 or len(dates) == 1 and not expiry_heading):
        value, provider, source = dates[min(dates)]
        add("date", value, provider, source)
    if "expiry" not in found and expiry_heading and (len(dates) >= 2 or len(dates) == 1 and not mfd_heading):
        value, provider, source = dates[max(dates)]
        add("expiry", value, provider, source)

    if "net_quantity" not in found and re.search(ANCHORS["net_quantity"], panel, re.I):
        alone = {}
        for provider, text in lines:
            stripped = text.strip(" .:;|")
            if (match := _QUANTITY.fullmatch(stripped)) and Decimal(match[1]) == Decimal(match[1]).to_integral_value():
                alone.setdefault(stripped.casefold().replace(" ", ""), (stripped, provider, text))
        if len(alone) == 1:
            value, provider, source = next(iter(alone.values()))
            add("net_quantity", value, provider, source)
    return candidates

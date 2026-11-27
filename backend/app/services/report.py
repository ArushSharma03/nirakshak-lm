"""Build a printable, offline A4 inspector report from saved analysis and original evidence.

The report is advisory screening output. It never fills in values OCR did not read, never treats an
unread declaration as absent, and never presents a passed screening check as legal compliance.
"""

import base64
import hashlib
import re
from html import escape
from pathlib import Path
from urllib.parse import urlsplit

from app.schemas.analysis import Analysis, DeclarationCheck, FusedField, OCRResult

FIELD_NAMES = {
    "generic_name": "Generic name",
    "net_quantity": "Net quantity",
    "mrp": "Retail sale price (MRP)",
    "manufacturer": "Manufacturer / packer",
    "date": "Date of manufacture / packing",
    "expiry": "Best before / use by",
    "consumer_care": "Consumer care contact",
    "country_of_origin": "Country of origin",
}
FIELD_ORDER = list(FIELD_NAMES)

# What the inspector does on the physical package when a check could not be settled from photos.
KIND_ACTIONS = {
    "presence": "Confirm the declaration is printed on the package",
    "completeness": "Read the complete declaration on the package",
    "units": "Confirm the declared unit on the package",
    "consistency": "Compare the OCR readings with the printed declaration",
    "placement": "Confirm the declaration sits on the required display panel",
    "readability": "Confirm the print is legible on the physical package",
    "character_height": "Measure character height against the applicable minimum",
}
KIND_NAMES = {
    "presence": "presence", "completeness": "completeness", "units": "units", "consistency": "consistency",
    "placement": "placement", "readability": "readability", "character_height": "character height",
}

# OCR lines worth pointing an inspector at when a declaration was not extracted. These are search
# aids only; the matched text is quoted, never parsed or promoted to a declared value.
HINTS = {
    "generic_name": None,
    "net_quantity": r"\bnet\s*(?:wt|weight|quantity|qty|content)",
    "mrp": r"\bm\.?\s?r\.?\s?p\b|retail\s+(?:sale\s+)?price",
    "manufacturer": r"\b(?:manufactured|mfd\.?|mkt\.?|marketed|packed|imported)\s*(?:by|for)\b|\bmanufacturer\b|\bpvt\.?\s*ltd\b|\blimited\b",
    "date": r"\b(?:mfd|mfg|pkd|packed\s+on|date\s+of)\b",
    "expiry": r"\b(?:best\s+before|use\s+by|ubd|expiry|exp\.?)\b",
    "consumer_care": r"consumer\s+care|customer\s+care|toll[-\s]?free|e-?mail|phone|\btel\b",
    "country_of_origin": r"country\s+of\s+origin|made\s+in|product\s+of",
}

STYLE = """
:root { --ink:#0f172a; --ink2:#475569; --ink3:#64748b; --rule:#cbd5e1; --rule2:#e2e8f0;
  --accent:#365c70; --wash:#f1f5f7; --warn:#92400e; --danger:#be123c; --ok:#047857; }
* { box-sizing: border-box; }
html { background: #f8fafc; }
body { max-width: 190mm; margin: 8mm auto; padding: 10mm 12mm; background: #fff; color: var(--ink);
  font: 13px/1.45 ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, "Noto Sans", sans-serif;
  overflow-wrap: anywhere; }
h1, h2, h3, p, ul, ol, figure, blockquote { margin: 0; }
h1 { font-size: 19px; font-weight: 600; line-height: 1.25; }
h2 { font-size: 11px; font-weight: 600; letter-spacing: .06em; text-transform: uppercase; color: var(--ink2);
  border-bottom: 1px solid var(--rule); padding-bottom: 3px; margin: 14px 0 6px; break-after: avoid; }
a { color: var(--accent); }
code, .mono { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: .92em; }
.muted { color: var(--ink3); } .small { font-size: .88em; }
.masthead { display: flex; justify-content: space-between; align-items: baseline; gap: 12px;
  font-size: 11px; color: var(--ink2); border-bottom: 2px solid var(--ink); padding-bottom: 4px; margin-bottom: 8px; }
.masthead strong { color: var(--ink); letter-spacing: .04em; }
.meta { display: flex; flex-wrap: wrap; gap: 2px 14px; margin-top: 3px; font-size: 11.5px; color: var(--ink2); }
.meta b { font-weight: 600; color: var(--ink); }
.outcome { display: grid; grid-template-columns: auto 1fr; gap: 3px 14px; align-items: baseline; margin-top: 9px;
  padding: 7px 10px; border: 1px solid var(--rule); border-left: 4px solid var(--warn); background: #fffbeb; }
.outcome.risk { border-left-color: var(--danger); background: #fff1f2; }
.outcome.clear { border-left-color: var(--ok); background: #ecfdf5; }
.outcome .verdict { font-size: 15px; font-weight: 600; }
.outcome .counts { font-size: 12px; }
.outcome .advisory { grid-column: 1 / -1; font-size: 11px; color: var(--ink2); }
.evidence { display: grid; grid-template-columns: 70mm 1fr; gap: 0 12px; margin-top: 10px; align-items: start; }
.photos { display: grid; gap: 6px; }
.photos figure { border: 1px solid var(--rule2); padding: 3px; break-inside: avoid; }
.photos img { display: block; width: 100%; height: auto; max-height: 92mm; object-fit: contain; }
.photos.n2 img { max-height: 58mm; } .photos.n3 img { max-height: 40mm; }
.photos figcaption { font-size: 10.5px; color: var(--ink2); padding: 2px 1px 0; }
table { width: 100%; border-collapse: collapse; font-size: 12px; }
th { text-align: left; font-weight: 600; font-size: 10.5px; color: var(--ink2); border-bottom: 1px solid var(--rule); padding: 3px 6px 3px 0; }
td { border-bottom: 1px solid var(--rule2); padding: 4px 6px 4px 0; vertical-align: top; }
tr { break-inside: avoid; }
.readings td:first-child { width: 33%; font-weight: 500; }
.value { white-space: pre-line; font-weight: 600; }
.value.long { font-weight: 500; font-size: 11px; }
.tag { display: inline-block; font-size: 10px; font-weight: 600; letter-spacing: .03em; text-transform: uppercase; }
.tag.conflict { color: var(--danger); } .tag.unread { color: var(--warn); } .tag.read { color: var(--ok); }
.src { display: block; font-size: 10.5px; color: var(--ink3); }
.alts { margin: 1px 0 0; padding-left: 14px; }
.tasks { list-style: none; padding: 0; }
.tasks > li { position: relative; padding: 4px 0 4px 20px; border-bottom: 1px solid var(--rule2); break-inside: avoid; }
.tasks > li::before { content: ""; position: absolute; left: 0; top: 6px; width: 10px; height: 10px; border: 1.2px solid var(--ink); }
.tasks .what { font-weight: 600; }
.tasks .why { display: block; font-size: 11px; color: var(--ink2); }
.tasks ul { padding-left: 14px; font-size: 11.5px; margin-top: 2px; }
.signoff { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin-top: 12px; font-size: 11px; color: var(--ink2); break-inside: avoid; }
.signoff div { border-top: 1px solid var(--ink3); padding-top: 3px; min-height: 22px; }
.signoff b { color: var(--ink); font-weight: 600; }
th { white-space: nowrap; } .checks td:nth-child(4) { text-align: right; padding-right: 0; } .checks th:nth-child(4) { text-align: right; padding-right: 0; }
.checks td:first-child { width: 42%; } .checks .ok { color: var(--ok); } .checks .bad { color: var(--danger); }
td.cite { white-space: nowrap; }
.checks .req { display: block; font-size: 10.5px; color: var(--ink2); }
blockquote { white-space: pre-line; border-left: 2px solid var(--rule); padding: 1px 0 1px 7px; margin: 2px 0 5px; font-size: 11.5px; }
.detail h3 { font-size: 12px; font-weight: 600; margin-top: 6px; break-after: avoid; }
.notes { padding-left: 16px; font-size: 11.5px; }
details { margin-top: 14px; border-top: 1px solid var(--rule); padding-top: 6px; font-size: 11.5px; }
summary { cursor: pointer; font-weight: 600; color: var(--ink2); }
details h3 { font-size: 11.5px; font-weight: 600; margin-top: 8px; }
pre { white-space: pre-wrap; font: 10.5px/1.4 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  background: var(--wash); padding: 6px 8px; margin: 3px 0 0; }
.page2 { break-before: page; }
.integrity td:nth-child(1) { width: 12mm; } .integrity td:nth-child(2) { width: 38mm; } .integrity td:nth-child(3) { width: 42mm; }
@page { size: A4; margin: 13mm 14mm 15mm;
  @bottom-left { content: "Nirikshak-LM · %(id)s · Advisory screening"; font: 8pt system-ui, sans-serif; color: #64748b; }
  @bottom-right { content: "Page " counter(page) " of " counter(pages); font: 8pt system-ui, sans-serif; color: #64748b; } }
@media print {
  html { background: #fff; }
  body { max-width: none; margin: 0; padding: 0; font-size: 9.2pt; }
  a { color: inherit; text-decoration: none; }
  details:not([open]) { display: none; }
  .outcome, .outcome.risk, .outcome.clear, pre { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
}
"""


def label(value: str) -> str:
    return escape(value.replace("_", " ").capitalize())


def field_name(field: str) -> str:
    return escape(FIELD_NAMES.get(field, field.replace("_", " ").capitalize()))


def source(url: str, citation: str) -> str:
    if urlsplit(url).scheme in ("http", "https"):
        return f'<a href="{escape(url)}">{escape(citation)}</a>'
    return escape(citation)


def provider_name(provider: str) -> str:
    base, _, crop = provider.partition("_detail_")
    return f"{base.capitalize()} detail crop {int(crop) + 1}" if crop.isdigit() else provider.capitalize()


def join_names(names: list[str]) -> str:
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def plural(count: int, word: str, many: str | None = None) -> str:
    return f"{count} {word if count == 1 else (many or word + 's')}"


def ocr_lines(result: OCRResult) -> list[str]:
    text = result.raw_text or "\n".join(line.text for line in result.lines)
    return [line.strip() for line in text.splitlines() if line.strip()]


def hint_lines(field: str, runs: list[OCRResult], quoted: set[str]) -> list[str]:
    """Return up to two OCR lines that mention the field's usual wording, as a search aid."""
    pattern = HINTS.get(field)
    if not pattern:
        return []
    found, seen = [], set(quoted)
    for run in runs:
        for line in ocr_lines(run):
            key = re.sub(r"\W+", "", line.lower())
            if key and key not in seen and re.search(pattern, line, re.IGNORECASE):
                seen.add(key)
                found.append(line if len(line) <= 90 else line[:87] + "…")
                if len(found) == 2:
                    return found
    return found


def verified_photos(record: dict, analysis: Analysis):
    for view, result in analysis.views.items():
        photo = record.get("images", {}).get(view)
        if not photo:
            raise ValueError(f"{view.capitalize()} photo is missing. Analyze the current photos again.")
        raw = Path(photo["filepath"]).read_bytes()
        if hashlib.sha256(raw).hexdigest() != result.file_hash:
            raise ValueError(f"{view.capitalize()} photo changed. Analyze the current photos again.")
        yield view, photo, raw, result.file_hash


def photo_figures(record: dict, analysis: Analysis) -> tuple[list[str], list[str]]:
    figures, integrity = [], []
    for view, photo, raw, file_hash in verified_photos(record, analysis):
        media = "image/png" if raw.startswith(b"\x89PNG") else "image/jpeg"
        data = base64.b64encode(raw).decode("ascii")
        quality = photo.get("quality_assessment") or {}
        score = quality.get("composite_score")
        status = quality.get("overall_status")
        optics = f"capture quality {score:g}/100" if isinstance(score, (int, float)) else ""
        if optics and status:
            optics += f" ({status.lower()})"
        caption = " · ".join(part for part in (view.capitalize() + " view", optics) if part)
        figures.append(f'<figure><img src="data:{media};base64,{data}" alt="{escape(view.capitalize())} package photo">'
                       f"<figcaption>{escape(caption)}</figcaption></figure>")
        original = photo.get("original_filename") or photo.get("filename") or ""
        integrity.append(f"<tr><td>{escape(view.capitalize())}</td><td>{escape(original)}</td>"
                         f"<td>{escape(optics or '—')}</td><td><code>{escape(file_hash)}</code></td></tr>")
    return figures, integrity


def render_report(record: dict, analysis: Analysis) -> str:
    figures, integrity = photo_figures(record, analysis)
    identity = escape(record["id"])
    profile = analysis.profile
    rules = {rule.field: rule for rule in profile.rules}
    checks: list[DeclarationCheck] = analysis.checks.results if analysis.checks else []
    fields = sorted(analysis.fields, key=lambda f: FIELD_ORDER.index(f.field) if f.field in FIELD_ORDER else 99)
    by_field = {f.field: f for f in fields}
    in_scope = (lambda field: field in rules) if rules else (lambda field: True)
    runs = [run for view in analysis.views.values() for run in view.ocr if run.status in ("ok", "partial")]
    reading_runs = [run for run in runs if run.provider != "tesseract"] or runs

    # A "reading" with no letters or digits (e.g. a lone comma) is an OCR fragment, not a declaration.
    fragments = [f for f in fields if f.status == "observed" and not re.search(r"\w", f.value or "")]
    observed = [f for f in fields if f.status == "observed" and f not in fragments]
    conflicts = [f for f in fields if f.status == "conflict"]
    unread = [f for f in fields if (f.status == "missing" or f in fragments) and in_scope(f.field)]
    passes = [c for c in checks if c.status == "pass"]
    fails = [c for c in checks if c.status == "fail"]

    # ---- Review tasks: concrete actions, each reason stated once. ----
    tasks: list[str] = []
    if profile.status != "selected":
        tasks.append(f'<li><span class="what">Confirm the applicable rule profile.</span>'
                     f'<span class="why">{escape(profile.reason)}</span></li>')
    for field in conflicts:
        values: dict[str, list[str]] = {}
        for item in field.evidence:
            values.setdefault(item.value, []).append(f"{item.view} · {provider_name(item.provider)}")
        alts = "".join(f"<li>“{escape(v)}” <span class='muted'>({escape(', '.join(dict.fromkeys(s)))})</span></li>"
                       for v, s in values.items())
        tasks.append(f'<li><span class="what">Resolve {field_name(field.field).lower()}: OCR readings disagree.</span>'
                     f'<span class="why">Read the printed declaration and record the correct value.</span>'
                     f'<ul>{alts}</ul></li>')
    grouped_fails: dict[str, list[DeclarationCheck]] = {}
    conflict_fields = {f.field for f in conflicts}
    for check in fails:
        if check.kind == "consistency" and check.field in conflict_fields:
            continue  # already a "resolve conflicting readings" task
        grouped_fails.setdefault(check.reason, []).append(check)
    for reason, group in grouped_fails.items():
        items = join_names(list(dict.fromkeys(f"{FIELD_NAMES.get(c.field, c.field)} ({KIND_NAMES.get(c.kind, c.kind)})" for c in group)))
        measured = "".join(f" Measured {c.measured_mm:g} mm against {c.required_mm:g} mm."
                           for c in group if c.measured_mm is not None and c.required_mm is not None)
        tasks.append(f'<li><span class="what">Review flagged check: {escape(items)}.</span>'
                     f'<span class="why">{escape(reason)}{escape(measured)}</span></li>')
    if unread:
        quoted = {re.sub(r"\W+", "", line.lower()) for f in fields for item in f.evidence
                  for line in item.source_text.splitlines()}
        hints = []
        for field in unread:
            lines = hint_lines(field.field, reading_runs, quoted)
            if lines:
                hints.append(f"<li>{field_name(field.field)}: look near " +
                             " / ".join(f"“{escape(line)}”" for line in lines) + "</li>")
        names = join_names([FIELD_NAMES.get(f.field, f.field) for f in unread])
        tasks.append(f'<li><span class="what">Locate and record on the package: {escape(names)}.</span>'
                     f'<span class="why">Not extracted from the photos. This does not show the declaration is absent.</span>'
                     + (f"<ul>{''.join(hints)}</ul>" if hints else "") + "</li>")
    # Open checks on fields that were read: one task per set of fields sharing the same open checks.
    open_by_field: dict[str, dict[tuple[str, str], None]] = {}
    for check in checks:
        status = by_field[check.field].status if check.field in by_field else "missing"
        if check.status == "insufficient_evidence" and status == "observed" and by_field[check.field] not in fragments:
            open_by_field.setdefault(check.field, {})[(check.kind, check.reason)] = None
    open_groups: dict[tuple, list[str]] = {}
    for field, items in open_by_field.items():
        open_groups.setdefault(tuple(items), []).append(FIELD_NAMES.get(field, field))
    for items, names in open_groups.items():
        steps = "".join(f"<li>{escape(KIND_ACTIONS.get(kind, 'Review ' + kind.replace('_', ' ')))}."
                        f" <span class='muted'>{escape(reason)}</span></li>" for kind, reason in items)
        tasks.append(f'<li><span class="what">Verify on the package: {escape(join_names(names))}.</span>'
                     f'<span class="why">Read from the photos, but not settled by screening:</span><ul>{steps}</ul></li>')
    if not analysis.checks and observed:
        tasks.append(f'<li><span class="what">Verify on the package: {escape(join_names([FIELD_NAMES.get(f.field, f.field) for f in observed]))}.</span>'
                     '<span class="why">Confirm each OCR reading against the printed declaration.</span></li>')
    if not analysis.checks and profile.status == "selected":
        tasks.append('<li><span class="what">Run declaration checks in the app.</span>'
                     '<span class="why">This saved analysis predates automated declaration checks.</span></li>')
    task_html = (f'<ol class="tasks">{"".join(tasks)}</ol>' if tasks
                 else '<p>No open review tasks within the implemented checks. Confirm the readings against the physical package.</p>')

    # ---- Label readings. ----
    rows = []
    for field in fields:
        if field in fragments:
            cell = (f'<span class="tag unread">Not read</span><span class="src">OCR returned only “{escape(field.value or "")}”</span>')
        elif field.status == "observed":
            sources = ", ".join(dict.fromkeys(f"{i.view} · {provider_name(i.provider)}" for i in field.evidence))
            value = field.value or ""
            css = "value long" if len(value) > 40 or "\n" in value else "value"
            cell = f'<span class="{css}">{escape(value)}</span><span class="src">{escape(sources)}</span>'
        elif field.status == "conflict":
            cell = '<span class="tag conflict">Conflicting readings</span><span class="src">See review tasks</span>'
        elif in_scope(field.field):
            cell = '<span class="tag unread">Not read</span>'
        else:
            cell = '<span class="muted small">Not required by the selected profile</span>'
        rows.append(f"<tr><td>{field_name(field.field)}</td><td>{cell}</td></tr>")
    readings = f'<table class="readings"><thead><tr><th>Declaration</th><th>OCR reading (unverified)</th></tr></thead><tbody>{"".join(rows)}</tbody></table>'

    # ---- Summary line. ----
    scope_total = sum(1 for f in fields if in_scope(f.field))
    scope_read = sum(1 for f in observed if in_scope(f.field))
    counts = [f"{scope_read} of {scope_total} declarations read"]
    if conflicts:
        counts.append(plural(len(conflicts), "conflict"))
    if analysis.checks:
        counts.append(f"{plural(len(passes), 'check')} passed")
        counts.append(plural(len(fails), "flagged check"))
    counts.append(plural(len(tasks), "review task"))
    outcome = record.get("final_outcome") or (analysis.classification.outcome if analysis.classification else "Manual Review Required")
    tone = {"Potential Non-Compliance": " risk", "Compliant within Implemented Checks": " clear"}.get(outcome, "")
    outcome_reason = ""
    if analysis.classification and outcome != "Manual Review Required":
        outcome_reason = f'<div class="advisory">{escape(analysis.classification.reason)}</div>'
    profile_ref = escape(" ".join(p for p in (profile.id or "", profile.version or "") if p) or "no selected profile")

    # ---- Header metadata, only what was recorded. ----
    meta = [("Captured", record.get("timestamp", "")[:16].replace("T", " ")),
            ("Category", (record.get("product_category") or profile.inputs.category).replace("_", " ")),
            ("Origin", profile.inputs.origin), ("Rules as of", str(profile.inputs.as_of)),
            ("Brand", record.get("brand")), ("Declared qty", record.get("declared_net_qty")),
            ("Declared MRP", record.get("declared_mrp")), ("Location", record.get("location")),
            ("Inspector", record.get("inspector_name"))]
    meta_html = "".join(f"<span>{escape(k)} <b>{escape(str(v))}</b></span>" for k, v in meta if v not in (None, ""))
    captured = [v for v in ("front", "rear", "side") if v in analysis.views]

    # ---- Page 2: check matrix, evidence, profile, integrity, notes. ----
    matrix, dash = [], '<span class="muted">—</span>'
    for field in fields:
        mine = [c for c in checks if c.field == field.field and c.status != "not_applicable"]
        if not mine and not (field.field in rules):
            continue
        ok = ", ".join(KIND_NAMES.get(c.kind, c.kind) for c in mine if c.status == "pass")
        bad = ", ".join(KIND_NAMES.get(c.kind, c.kind) for c in mine if c.status == "fail")
        pending = sum(1 for c in mine if c.status == "insufficient_evidence")
        rule = rules.get(field.field)
        req = (f'<span class="req">{source(rule.source_url, rule.citation)} · {escape(rule.requirement)}</span>'
               if rule else "")
        matrix.append(f"<tr><td>{field_name(field.field)}{req}</td>"
                      f"<td class='ok'>{escape(ok) or dash}</td><td class='bad'>{escape(bad) or dash}</td>"
                      f"<td>{pending or dash}</td></tr>")
    if analysis.checks:
        check_html = ('<table class="checks"><thead><tr><th>Declaration</th><th>Passed screening</th><th>Flagged</th>'
                      f'<th>Open</th></tr></thead><tbody>{"".join(matrix)}</tbody></table>'
                      f'<p class="small muted" style="margin-top:4px">{escape(analysis.checks.scope)} '
                      "Open checks are covered by the review tasks on page 1.</p>")
    else:
        check_html = f"<p>Declaration checks were not saved with this analysis (version {escape(analysis.version)}).</p>"

    detail = []
    for field in observed + conflicts:
        quotes = "".join(
            f"<blockquote>{escape(item.source_text)}<span class='src'>{escape(item.view.capitalize())} · "
            f"{escape(provider_name(item.provider))}"
            + (f" · box {item.box.x0:g},{item.box.y0:g} – {item.box.x1:g},{item.box.y1:g} px" if item.box else "")
            + "</span></blockquote>" for item in field.evidence)
        detail.append(f"<h3>{field_name(field.field)}</h3>{quotes}")
    detail_html = "".join(detail) or "<p>No declaration text was extracted.</p>"

    rule_rows = "".join(f"<tr><td class='cite'>{source(r.source_url, r.citation)}</td><td>{field_name(r.field)}</td>"
                        f"<td>{escape(r.requirement)}</td></tr>" for r in profile.rules)
    if not profile.rules:
        rule_html = f"<p class='small'>{escape(profile.reason)}</p>"
    elif analysis.checks:
        rule_html = ""  # citations and requirements are listed with the check results
    else:
        rule_html = (f'<table><thead><tr><th>Citation</th><th>Declaration</th><th>Requirement</th></tr></thead>'
                     f'<tbody>{rule_rows}</tbody></table>')

    notes = [w for w in analysis.warnings
             if not re.search(r"marker|calibration|no captured evidence", w, re.IGNORECASE)]
    if analysis.decision.status in ("ok", "failed"):
        notes.append(f"Language-model assist: {analysis.decision.status}. {analysis.decision.message}")
    if record.get("notes"):
        notes.insert(0, f"Inspection notes: {record['notes']}")
    notes_html = f'<h2>Processing notes</h2><ul class="notes">{"".join(f"<li>{escape(n)}</li>" for n in notes)}</ul>' if notes else ""

    transcripts = []
    for view, result in analysis.views.items():
        for run in result.ocr:
            text = "\n".join(ocr_lines(run))
            heading = f"{view.capitalize()} · {provider_name(run.provider)} · {run.status}"
            transcripts.append(f"<h3>{escape(heading)} <span class='muted'>{escape(run.model)}</span></h3>"
                               + (f"<p class='small muted'>{escape(run.message)}</p>" if run.message else "")
                               + (f"<pre>{escape(text)}</pre>" if text else "<p class='small muted'>No text returned.</p>"))
    footer_id = re.sub(r"[^A-Za-z0-9-]", "", record["id"])

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Inspection report {identity}</title><style>{STYLE.replace("%(id)s", footer_id)}</style></head><body>
<div class="masthead"><strong>NIRIKSHAK-LM · LABEL SCREENING REPORT</strong><span class="mono">{identity}</span></div>
<header><h1>{escape(record["product_name"] or "Untitled package")}</h1><div class="meta">{meta_html}</div></header>
<section class="outcome{tone}"><div class="verdict">{escape(outcome)}</div><div class="counts">{escape(" · ".join(counts))}</div>
{outcome_reason}<div class="advisory">Advisory screening of {escape(join_names(captured) if captured else "no")} photo{"s" if len(captured) != 1 else ""} against {profile_ref}.
Not a legal compliance finding — confirm on the physical package before any enforcement action.</div></section>
<section class="evidence"><div class="photos n{min(len(figures), 3)}">{"".join(figures)}</div><div>{readings}</div></section>
<h2>Review tasks</h2>{task_html}
<div class="signoff"><div><b>Inspector</b><br>{escape(record.get("inspector_name") or "")}</div><div><b>Date of physical check</b></div><div><b>Outcome after review</b></div></div>
<section class="page2">
<h2>Check results</h2>{check_html}
<h2>Source text for readings</h2><div class="detail">{detail_html}</div>
<h2>Rule profile</h2><p class="small" style="margin-bottom:4px">{profile_ref} · {label(profile.status)} · analysis {escape(analysis.version)}. {escape(profile.advisory)}</p>{rule_html}
<h2>Photo integrity</h2><table class="integrity"><thead><tr><th>View</th><th>Uploaded file</th><th>Capture</th><th>SHA-256</th></tr></thead><tbody>{"".join(integrity)}</tbody></table>
{notes_html}
<p class="small muted" style="margin-top:10px">Raw OCR transcripts ({plural(len(transcripts), "run")}) are kept in the HTML report appendix.</p>
</section>
<details><summary>Appendix · Raw OCR transcripts ({plural(len(transcripts), "run")}) — expand to view; expanded transcripts are included when printed</summary>{"".join(transcripts)}</details>
</body></html>"""

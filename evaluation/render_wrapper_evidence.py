"""Build a local evidence gallery from actual wrapper results and report screenshots."""
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    report = json.loads((ROOT / "evaluation/multi-wrapper-results.json").read_text())
    rows, cards = [], []
    for case in report["results"]:
        name = html.escape(case["name"])
        score = case["quality"]["composite_score"]
        quantity = next(f for f in case["analysis"]["fields"] if f["field"] == "net_quantity")
        actual = html.escape(quantity["value"] or "Unverified")
        expected = html.escape(case["expected_quantity"] or "Blank quantity space")
        screenshot = ROOT / "docs/evidence/wrappers" / (case["id"] + "-report.png")
        if not screenshot.is_file():
            raise FileNotFoundError(screenshot)
        source = ROOT / "evaluation/fixtures/wrappers" / case["file"]
        status = "Target check passed" if case["quantity_check"] else "Target check failed"
        rows.append(f'<div class="row"><span>{name}</span><div class="track"><div class="bar" style="width:{score}%"></div></div><strong>{score:g}/100</strong></div>')
        expanded = "open" if case["id"] == "maggi" else ""
        cards.append(f'''<article><h2>{name}</h2><p><strong>{status}</strong>. Visible quantity: {expected}. Extracted: {actual}.</p>
        <p class="muted">{html.escape(case['visual_note'])}</p>
        <details><summary>Source wrapper</summary><img class="source" src="{source}" alt="{name} original internet source"/></details>
        <details {expanded}><summary>Actual app report · {html.escape(case['inspection_id'])}</summary><img src="{screenshot}" alt="Saved application report for {name}"/></details>
        <a href="{html.escape(case['url'], quote=True)}" target="_blank" rel="noreferrer">Original image source</a></article>''')
    page = '''<!doctype html><html><head><meta charset="utf-8"><style>
    *{box-sizing:border-box}body{margin:0;color:var(--foreground);font:14px/1.5 var(--font-sans)}
    p{margin:0 0 12px}h2{font-size:17px;margin:0 0 8px}.muted{color:var(--muted-foreground)}
    .chart,article{background:var(--card);border:1px solid var(--border);border-radius:var(--radius);padding:16px;margin:0 0 16px}.chart{height:260px}
    .row{display:grid;grid-template-columns:minmax(90px,180px) 1fr 75px;gap:12px;align-items:center;margin:16px 0}
    .track{background:var(--secondary);height:12px;border-radius:3px;overflow:hidden}.bar{background:var(--chart-1);height:12px}
    strong{font-weight:600}details{margin:12px 0}summary{cursor:pointer;font-weight:600;margin-bottom:10px}
    img{display:block;max-width:100%;height:auto;border:1px solid var(--border)}.source{max-height:320px;object-fit:contain;width:100%;background:var(--secondary)}
    a{color:var(--primary)}@media(max-width:480px){.row{grid-template-columns:100px 1fr 65px;gap:6px;font-size:12px}}
    </style></head><body>'''
    desktop = ROOT / "docs/evidence/wrappers/dashboard-desktop.png"
    mobile = ROOT / "docs/evidence/wrappers/dashboard-mobile.png"
    page += f'<article><h2>Original console, polished</h2><p>Dark sidebar and original navigation restored. Counts come from stored records. Screenshots are from the final production build.</p><details open><summary>Desktop dashboard</summary><img src="{desktop}" alt="Polished original console dashboard"/></details><details><summary>Phone dashboard</summary><img style="max-width:390px" src="{mobile}" alt="Polished console on a phone"/></details></article>'
    page += '<p>Three catalogue-wrapper tests. These are optical scores, not OCR accuracy or legal compliance scores.</p><section class="chart" aria-label="Optical scores by wrapper">'
    page += "".join(rows) + '</section><p class="muted">White studio backgrounds trigger exposure/glare checks. Passing the targeted quantity check does not verify the other declarations. No physical marker was supplied; Jev was disabled.</p>'
    page += "".join(cards) + '</body></html>'
    output = ROOT / "docs/evidence/wrappers/results.html"
    output.write_text(page)
    print(output)


if __name__ == "__main__":
    main()

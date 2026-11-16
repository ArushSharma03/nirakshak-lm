"""Render the measured Jev text/image comparison without rerunning inference."""
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    results = json.loads((ROOT / "evaluation/jev-mode-results.json").read_text())["results"]
    attempts = len(json.loads((ROOT / "evaluation/jev-wrapper-budget.json").read_text())["attempts"])
    usage = {key: sum(row["response"]["usage"][key] for row in results) for key in ("input_tokens", "output_tokens")}
    names = {"maggi": "Maggi", "good-day": "Good Day", "lays": "Lay's"}
    chart, detail = [], []
    for case, name in names.items():
        pair = {row["mode"]: row for row in results if row["case"] == case}
        chart.append({"name": name, **{mode: {field: row["response"]["answers"][field]["probabilities"] for field in ("net_quantity_presence", "mrp_presence")} for mode, row in pair.items()}})
        entries = []
        for mode, row in pair.items():
            answers = []
            for field, answer in row["response"]["answers"].items():
                criterion = row["questions"][field]["criteria"][answer["choice"]]
                value = criterion if isinstance(criterion, str) else criterion["value"]
                if answer["choice"] == "none":
                    value = "Rejected supplied candidates"
                answers.append(f'<tr><td>{html.escape(field.replace("_", " "))}</td><td>{html.escape(value)}</td><td>{answer["confidence"]:.0%}</td></tr>')
            entries.append(f'<details><summary>{"Text only" if mode == "text" else "Text + image"} · {row["response"]["usage"]["input_tokens"]:,} input tokens</summary><table><thead><tr><th>Question</th><th>Choice</th><th>Confidence</th></tr></thead><tbody>{"".join(answers)}</tbody></table></details>')
        detail.append(f'<section class="card"><h2>{name}</h2>{"".join(entries)}</section>')
    page = '''<!doctype html><html><head><meta charset="utf-8"><style>
    *{box-sizing:border-box}body{margin:0;font:14px/1.5 var(--font-sans);color:var(--foreground)}p{margin:0 0 12px}h2{font-size:16px;margin:0 0 10px}.muted{color:var(--muted-foreground)}
    .card{background:var(--card);border:1px solid var(--border);border-radius:var(--radius);padding:16px;margin:0 0 16px}.failure{border-left:3px solid var(--warning)}
    label{display:flex;flex-wrap:wrap;gap:8px;align-items:center}select{color:var(--foreground);background:var(--card);border:1px solid var(--border);padding:6px;border-radius:4px;font:inherit}
    #chart{height:260px;display:grid;align-content:space-around}.group{display:grid;grid-template-columns:80px 1fr;gap:10px}.bars{display:grid;gap:6px}.barrow{display:grid;grid-template-columns:1fr 42px;gap:8px;align-items:center}.track{height:12px;background:var(--secondary);overflow:hidden;border-radius:2px}.bar{height:12px;background:var(--chart-1)}.bar.image{background:var(--chart-2)}.value{font-family:var(--font-mono);font-size:12px}
    .legend{display:flex;gap:18px;font-size:12px}.legend span:before{content:"";display:inline-block;width:12px;height:8px;background:var(--chart-1);margin-right:5px}.legend .image:before{background:var(--chart-2)}
    details{margin:10px 0}summary{cursor:pointer;font-weight:600}table{width:100%;border-collapse:collapse;font-size:12px;margin-top:8px}th,td{text-align:left;border-bottom:1px solid var(--border);padding:8px 4px;vertical-align:top}th:last-child,td:last-child{text-align:right}th{color:var(--muted-foreground)}
    </style></head><body>'''
    page += f'<p><strong>{attempts} of 20 requests used</strong> · jev-1.14.0 · {usage["input_tokens"]:,} input tokens, {usage["output_tokens"]:,} output tokens. No automatic retries.</p>'
    page += '<p>Both modes received the same OCR transcripts, candidate values and questions. Image mode additionally received the original wrapper pixels, resized within the documented image limit.</p>'
    page += '<section class="card failure"><h2>Image verification still made a wrong choice</h2><p>Good Day says <strong>Made in Oman</strong>. Text-only Jev rejected the bad OCR country candidates. Image-backed Jev selected <strong>ORAN</strong> with 79% model confidence. That result remains unverified; confidence is not accuracy.</p></section>'
    page += '<section class="card"><label for="metric">Compare model probabilities <select id="metric"><option value="mrp_presence">MRP blank or not shown</option><option value="net_quantity_presence">Numeric net quantity readable</option></select></label><div id="chart" role="img" aria-label="Model probability comparison by wrapper"></div><div class="legend"><span>Text only</span><span class="image">Text + image</span></div><p class="muted" style="margin-top:12px">These are the model\'s probabilities, not measured OCR accuracy or package compliance scores. Maggi and Good Day show numeric quantity; Lay\'s quantity space is blank. None shows a numeric MRP.</p></section>'
    page += '<p>Both modes supported Maggi 70 g and Good Day 120 g, and left Lay\'s blank quantity unfilled. Both selected the printed base company names for Maggi and Lay\'s; complete addresses and all other fields were not established.</p>'
    page += "".join(detail)
    page += '<p class="muted">Three catalogue images are diagnostic cases, not a general accuracy benchmark. TypeSafe documents image/Box support as experimental. Raw evidence and conflicts remain unchanged.</p>'
    page += '<script>const data=' + json.dumps(chart) + ''';function render(){const metric=document.getElementById('metric').value;const choice=metric==='mrp_presence'?'blank_or_not_shown':'readable';document.getElementById('chart').innerHTML=data.map(row=>'<div class="group"><strong>'+row.name+'</strong><div class="bars">'+['text','image'].map(mode=>{const p=Math.round(row[mode][metric][choice]*100);return '<div class="barrow"><div class="track"><div class="bar '+mode+'" style="width:'+p+'%"></div></div><span class="value">'+p+'%</span></div>'}).join('')+'</div></div>').join('')}document.getElementById('metric').addEventListener('change',render);render();</script></body></html>'''
    output = ROOT / "docs/evidence/jev-text-image-comparison.html"
    output.write_text(page)
    print(output)


if __name__ == "__main__":
    main()

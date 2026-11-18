"""Parse spotting tokens and reuse production extraction without invoking any OCR.

Run with PYTHONPATH=backend backend/.venv/bin/python evaluation/review_paddle_spotting.py.
Coordinates follow PaddleX's post_process_for_spotting: normalized 0..1000.
"""

import html
import json
import re
from collections import Counter
from pathlib import Path

from app.schemas.analysis import Box, Calibration, OCRLine, OCRResult
from app.services.extraction import canonical, extract, fuse

ROOT = Path(__file__).resolve().parent


def main():
    report = json.loads((ROOT / "paddle-spotting-results.json").read_text())
    baseline = json.loads((ROOT / "multi-wrapper-results.json").read_text())
    cards = []
    for case in report["results"]:
        w, h = case["original_dimensions"]
        pairs = re.findall(
            r"<\|TEXT_START\|>(.*?)<\|TEXT_END\|>\s*<\|LOC_BEGIN\|>(.*?)<\|LOC_END\|>",
            case["raw_output"], re.S,
        )
        # PaddleX also supports plain text followed by eight location tokens.
        if not pairs:
            pairs = re.findall(r"(.*?)((?:<\|LOC_\d+\|>){8})", case["raw_output"], re.S)
        lines, polys, rejected = [], [], 0
        for text, block in pairs:
            nums = [int(n) for n in re.findall(r"<\|LOC_(\d+)\|>", block)]
            if len(nums) != 8 or not all(0 <= n <= 1000 for n in nums):
                rejected += 1
                continue
            points = [(nums[i] * w / 1000, nums[i + 1] * h / 1000) for i in range(0, 8, 2)]
            xs, ys = zip(*points)
            if min(xs) == max(xs) or min(ys) == max(ys):
                rejected += 1
                continue
            lines.append(OCRLine(text=text.strip(), box=Box(x0=min(xs), y0=min(ys), x1=max(xs), y1=max(ys))))
            polys.append({"text": text.strip(), "points": points})
        ocr = OCRResult(provider="paddle_spotting", model=report["model"], status="ok" if lines else "failed", lines=lines)
        fields = fuse(extract(ocr, "rear", Calibration(status="unavailable", reason="Catalogue image has no marker")))
        quantity = next(f for f in fields if f.field == "net_quantity")
        expected = case["expected_quantity"]
        matches = canonical("net_quantity", quantity.value or "") == canonical("net_quantity", expected or "")
        passed = case["completed_eos"] and matches
        region_counts = Counter((p["text"], tuple(tuple(xy) for xy in p["points"])) for p in polys)
        old = next(c for c in baseline["results"] if c["id"] == case["id"])
        case.update({"parsed_lines": len(lines), "rejected_boxes": rejected,
                     "polygons": polys, "fields": [f.model_dump() for f in fields],
                     "quantity_match": matches, "quantity_check": passed,
                     "max_identical_region_repeats": max(region_counts.values(), default=0),
                     "baseline_fields": old["analysis"]["fields"]})
        overlays = "".join(f'<polygon points="{" ".join(f"{x},{y}" for x,y in p["points"])}"><title>{html.escape(p["text"])}</title></polygon>' for p in polys)
        cards.append(f'''<article><h2>{html.escape(case['id'])}</h2>
<p>{case['elapsed_seconds']} seconds; {len(lines)} text regions; finished: {case['completed_eos']}; quantity: {html.escape(quantity.value or 'missing')} (expected {html.escape(expected or 'missing')}).</p>
<svg viewBox="0 0 {w} {h}" role="img" aria-label="Predicted text polygons"><image href="fixtures/wrappers/{case['file']}" width="{w}" height="{h}"/>{overlays}</svg>
<details><summary>Extracted fields</summary><pre>{html.escape(json.dumps(case['fields'], ensure_ascii=False, indent=2))}</pre></details>
<details><summary>Raw model output</summary><pre>{html.escape(case['raw_output'])}</pre></details></article>''')
    (ROOT / "paddle-spotting-review.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    (ROOT / "paddle-spotting-review.html").write_text('''<!doctype html><html lang="en"><meta charset="utf-8"><title>Paddle spotting diagnostic</title><style>
body{max-width:1100px;margin:32px auto;padding:0 20px;font:15px/1.5 system-ui;color:#17212b}article{border-top:1px solid #ccc;margin-top:28px}svg{width:100%;height:auto}polygon{fill:transparent;stroke:#1567e6;stroke-width:2}polygon:hover{fill:#1567e633}pre{white-space:pre-wrap;overflow-wrap:anywhere}summary{cursor:pointer}
</style><h1>Single-model spotting: wrapper diagnostic</h1><p>Original catalogue photos with predicted polygons. Hover a box to read its text. Three cases cannot establish general accuracy. Timed-out output is incomplete. No marker or physical size validation.</p>''' + "".join(cards) + '</html>')
    for c in report["results"]:
        print(c["id"], c["elapsed_seconds"], c["completed_eos"], c["parsed_lines"], "quantity_check", c["quantity_check"])


if __name__ == "__main__":
    main()

"""Replay frozen real OCR through current analysis, geometry matching and checks.

Only inference adapters are replaced with saved transcripts. Photo decoding,
marker detection, extraction, fusion, profiles and declaration checks run normally.
Run: PYTHONPATH=backend backend/.venv/bin/python evaluation/replay_pipeline.py
"""

import json
import html
from pathlib import Path
from unittest.mock import patch

from app.schemas.analysis import AnalysisRequest, OCRResult
from app.services.analysis import analyze_record

ROOT = Path(__file__).resolve().parent


def main():
    baseline = json.loads((ROOT / "multi-wrapper-results.json").read_text())
    report = {"scope": "Frozen real Xiaomi/Tesseract transcripts, replayed through the current pipeline. No new OCR; historical completion statuses preserved. No user records modified.", "results": []}
    for case in baseline["results"]:
        old = case["analysis"]
        saved = [OCRResult.model_validate(r) for r in old["views"]["rear"]["ocr"]]
        whole = [r for r in saved if not r.provider.startswith("xiaomi_detail")]
        detail = [r for r in saved if r.provider.startswith("xiaomi_detail")]
        record = {"product_category": "food_grocery", "images": {"rear": {
            "filepath": str(ROOT / "fixtures/wrappers" / case["file"]), "quality_assessment": case["quality"],
        }}}
        with patch("app.services.analysis.recognize", return_value=whole), patch("app.services.analysis.detail_regions", return_value=iter(detail)):
            analysis = analyze_record(record, AnalysisRequest(origin="imported", as_of="2026-11-17"))
        fields = {f.field: f for f in analysis.fields}
        actual = (fields["net_quantity"].value or "").replace(" ", "").lower() or None
        assert actual == case["expected_quantity"], (case["id"], actual)
        assert fields["mrp"].status == fields["date"].status == "missing"
        assert analysis.views["rear"].file_hash == case["sha256"]
        assert analysis.decision.usage == {}
        if case["id"] in ("maggi", "lays"):
            assert fields["consumer_care"].status == "observed"
            assert fields["manufacturer"].status == "observed"
            assert "@" in fields["consumer_care"].value
        else:
            assert fields["country_of_origin"].status == "conflict"
        comparisons = [{"field": f.field, "before": next(o for o in old["fields"] if o["field"] == f.field),
                        "after": f.model_dump(mode="json")} for f in analysis.fields]
        report["results"].append({"id": case["id"], "inspection_source": case["inspection_id"],
            "field_comparison": comparisons, "analysis": analysis.model_dump(mode="json")})
        print(case["id"], [(f.field, f.status) for f in analysis.fields], flush=True)
    (ROOT / "extraction-replay-results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    rows = []
    for case in report["results"]:
        counts = {side: sum(f[side]["status"] == "observed" for f in case["field_comparison"]) for side in ("before", "after")}
        bars = "".join(f'<div class="row"><span>{label}</span><div class="track"><div class="bar {side}" style="width:{counts[side] / 7 * 100}%"></div></div><b>{counts[side]}/7</b></div>'
            for side, label in (("before", "Stored baseline"), ("after", "Fixed extraction")))
        changed = [f for f in case["field_comparison"] if f["before"]["status"] != f["after"]["status"]]
        details = "; ".join(f'{f["field"].replace("_", " ")}: {f["before"]["status"]} → {f["after"]["status"]}' for f in changed) or "No status change; country disagreement retained."
        rows.append(f'<section><strong>{html.escape(case["id"].title())}</strong>{bars}<p class="note">{html.escape(details)}</p></section>')
    output = ROOT.parent / "docs/evidence/pipeline-repair/replay.html"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text('''<!doctype html><html lang="en"><meta charset="utf-8"><title>Frozen OCR replay</title><style>
body{margin:0;color:var(--foreground);font:14px/1.5 var(--font-sans)}p{margin:0 0 14px}section{padding:16px;margin:0 0 12px;background:var(--card);border:1px solid var(--border);border-radius:var(--radius)}.row{display:grid;grid-template-columns:135px 1fr 35px;gap:10px;align-items:center;margin:8px 0}.track{height:12px;background:var(--secondary);border-radius:3px;overflow:hidden}.bar{height:12px}.before{background:var(--muted-foreground)}.after{background:var(--chart-1)}b{font-variant-numeric:tabular-nums}.note{font-size:12px;color:var(--muted-foreground);margin:10px 0 0}@media(max-width:420px){.row{grid-template-columns:110px 1fr 30px;gap:6px;font-size:12px}}
</style><p><strong>Anchored fields recovered from the same saved OCR</strong><br>Seven fields per photo. These counts measure extraction coverage, not correctness or compliance. No new model inference in this replay.</p>''' + "".join(rows) + '</html>')


if __name__ == "__main__":
    main()

"""Exercise a running API with Google-discovered packaging, without paid calls.

Run from the repository root after starting the backend. Fixtures and their
source manifest are checked in so changes in search results cannot change inputs.
"""

import argparse
import hashlib
import json
import time
from pathlib import Path

import httpx


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--output", default="evaluation/public-image-result.json")
    parser.add_argument("--keep-analysis", action="store_true", help="Retain the analyzed record for browser review; skip retake checks")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    sources = json.loads((root / "public-image-sources.json").read_text())
    checks = []
    start = time.monotonic()
    with httpx.Client(base_url=args.base_url, timeout=900) as client:
        def request(method, path, **kwargs):
            response = client.request(method, path, **kwargs)
            response.raise_for_status()
            return response.json()

        record = request("POST", "/inspections/", json={
            "product_name": "Parle-G 70 g public-image evaluation", "product_category": "food_grocery",
            "notes": "Google-discovered catalog rear and nutrition-detail images; not independent physical captures.",
        })
        base = f"/inspections/{record['id']}"
        for source in sources["images"]:
            raw = (root / source["file"]).read_bytes()
            assert hashlib.sha256(raw).hexdigest() == source["sha256"]
            record = request("POST", base + "/images", data={"view_type": source["view"]},
                files={"file": (Path(source["file"]).name, raw, "image/jpeg")})
            assert record["images"][source["view"]]["file_hash"] == source["sha256"]
        checks.append("Both JPEG uploads preserved source SHA-256 hashes")
        record = request("POST", base + "/analyze", json={
            "as_of": "2026-11-06", "origin": "domestic", "coplanar_views": [], "use_jev": False,
        })
        analysis = record["analysis"]
        quantity = next(field for field in analysis["fields"] if field["field"] == "net_quantity")
        assert quantity["status"] == "observed" and quantity["value"].replace(" ", "") == "70g", quantity
        checks.append("Recovered visible NET WEIGHT: 70g without confusing nutrition per-100g values")
        assert analysis["decision"]["answers"] == {} and analysis["decision"]["usage"] == {}
        assert analysis["decision"]["status"] == "unavailable"
        checks.append("Jev disabled with no usage or recommendations")
        for view in analysis["views"].values():
            assert view["calibration"]["status"] == "unavailable"
            assert all(item["status"] == "ok" for item in view["ocr"])
        assert all(c["height_mm"] is None for f in analysis["fields"] for c in f["evidence"])
        checks.append("Real Xiaomi and Tesseract completed for both images; no invented physical scale")
        assert analysis["profile"]["status"] == "selected"
        assert record["final_outcome"] == "Manual Review Required"
        assert request("GET", base)["analysis"] == analysis
        checks.append("Dated domestic draft profile selected; manual-review outcome and GET reload preserved")
        if not args.keep_analysis:
            # Replacing even the same bytes must invalidate published analysis.
            source = sources["images"][1]
            raw = (root / source["file"]).read_bytes()
            replaced = request("POST", base + "/images", data={"view_type": source["view"]},
                files={"file": ("retake.jpg", raw, "image/jpeg")})
            assert replaced["analysis"] is None
            removed = request("DELETE", base + "/images/" + source["view"])
            assert not removed["views_captured"][source["view"]]
            assert removed["analysis"] is None
            checks.append("Replacement and removal invalidate analysis")
    result = {"inspection_id": record["id"], "elapsed_seconds": round(time.monotonic() - start, 2),
        "checks": checks, "analysis": analysis}
    Path(args.output).write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key != "analysis"}, indent=2))


if __name__ == "__main__":
    main()

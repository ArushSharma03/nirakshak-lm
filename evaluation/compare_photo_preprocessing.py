"""Compare the primary reader on an unchanged-size enhanced rear fixture.

Run public_image_flow.py with --output evaluation/public-image-primary-result.json
first. This creates a separate experimental inspection; it never overwrites raw
evidence or enables Jev. Enhancement is not enabled in production OCR by this test.
"""

import hashlib
import json
from pathlib import Path
import sys
import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.services.preprocessor import preprocess_package_image
from app.services.extraction import fuse
from app.schemas.analysis import Analysis


def main():
    baseline = Analysis.model_validate(json.loads((ROOT / "evaluation/public-image-primary-result.json").read_text())["analysis"])
    raw = (ROOT / "evaluation/fixtures/parle-g-rear.jpg").read_bytes()
    processed = preprocess_package_image(raw, enable_perspective_correction=False)
    assert processed["success"]
    assert processed["original_dimensions"] == processed["processed_dimensions"]
    assert processed["raw_file_hash"] == hashlib.sha256(raw).hexdigest()
    with httpx.Client(base_url="http://127.0.0.1:8000", timeout=900) as client:
        def request(method, path, **kwargs):
            response = client.request(method, path, **kwargs)
            response.raise_for_status()
            return response.json()
        record = request("POST", "/inspections/", json={
            "product_name": "Experimental CLAHE copy of public rear wrapper",
            "product_category": "food_grocery",
            "notes": "Derived evaluation copy, not an independent capture or original evidence.",
        })
        path = f"/inspections/{record['id']}"
        request("POST", path + "/images", data={"view_type": "rear"}, files={
            "file": ("rear-enhanced.jpg", processed["processed_bytes"], "image/jpeg"),
        })
        result = request("POST", path + "/analyze", json={
            "as_of": "2026-11-12", "origin": "domestic", "coplanar_views": [], "use_jev": False,
        })
    analysis = result["analysis"]
    assert not analysis["decision"]["usage"]
    report = {
        "inspection_id": record["id"],
        "scope": "Two OCR inputs from the same rear-wrapper pixels, not an accuracy benchmark. Baseline is filtered to rear-view evidence for comparison.",
        "preprocessing": {k: v for k, v in processed.items() if k != "processed_bytes"},
        "original_fields": [f.model_dump(mode="json") for f in fuse([
            candidate for field in baseline.fields for candidate in field.evidence if candidate.view == "rear"
        ])],
        "enhanced_analysis": analysis,
    }
    output = ROOT / "evaluation/photo-preprocessing-comparison.json"
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(output)


if __name__ == "__main__":
    main()

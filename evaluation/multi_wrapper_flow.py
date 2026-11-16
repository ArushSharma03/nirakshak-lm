"""Run real local OCR on three internet wrappers, retaining failures and sources."""
import hashlib
import json
import time
from pathlib import Path
import httpx
from PIL import Image

ROOT = Path(__file__).resolve().parent
CASES = [
    {"id": "maggi", "name": "Maggi rear wrapper", "file": "maggi-single.jpg", "url": "https://m.media-amazon.com/images/I/81lk1JbWLTL.jpg", "query": "maggi noodles back packet net weight MRP", "expected_quantity": "70g", "visual_note": "NET QUANTITY: 70 g. Numeric MRP, lot and date are on another panel and not shown. Manufacturer Nestle India Limited is printed."},
    {"id": "good-day", "name": "Good Day Choco Almond rear wrapper", "file": "good-day.jpg", "url": "https://britannia-international.com/wp-content/uploads/2023/12/Good-Day-Choco-Almond-back.jpg", "query": "britannia good day back wrapper net weight", "expected_quantity": "120g", "visual_note": "NET WT: 120g; MADE IN OMAN. Manufacturer Al Sallan Food Industries Co SAOC. Blank PKD/EXP patch. Export pack, not proof of Indian retail applicability."},
    {"id": "lays", "name": "Lays rear wrapper", "file": "lays.jpg", "url": "https://m.media-amazon.com/images/I/71dteupEcXL.jpg", "query": "lays classic salted back packet net quantity", "expected_quantity": None, "visual_note": "NET QTY, MRP and MFD/USE BY spaces are blank. 20 g serving and per-100 g nutrition values are not net quantity. PepsiCo India Holdings Pvt Ltd is printed."},
]


def main():
    output = ROOT / "multi-wrapper-results.json"
    report = {"retrieved_on": "2026-11-12", "scope": "Three public catalogue rear images; no front/side captures, no physical marker, no accuracy benchmark or legal verdict. Rights remain with image owners. Expected quantity and notes were transcribed visually before OCR; catalogue titles were not fed to extraction.", "results": []}
    with httpx.Client(base_url="http://127.0.0.1:8000", timeout=900) as client:
        def request(method, path, **kwargs):
            response = client.request(method, path, **kwargs)
            response.raise_for_status()
            return response.json()
        for case in CASES:
            started = time.monotonic()
            file = ROOT / "fixtures/wrappers" / case["file"]
            raw = file.read_bytes()
            record = request("POST", "/inspections/", json={"product_name": case["name"], "product_category": "food_grocery", "notes": "Public catalogue-image evaluation; rear only; origin unknown."})
            base = f"/inspections/{record['id']}"
            record = request("POST", base + "/images", data={"view_type": "rear"}, files={"file": (file.name, raw, "image/jpeg")})
            quality = record["images"]["rear"]["quality_assessment"]
            record = request("POST", base + "/analyze", json={"origin": "unknown", "as_of": "2026-11-12", "coplanar_views": [], "use_jev": False})
            analysis = record["analysis"]
            quantity = next(f for f in analysis["fields"] if f["field"] == "net_quantity")
            actual = (quantity["value"] or "").replace(" ", "").lower() or None
            result = {**case, "sha256": hashlib.sha256(raw).hexdigest(), "dimensions": list(Image.open(file).size), "inspection_id": record["id"], "elapsed_seconds": round(time.monotonic()-started, 2), "quality": quality, "quantity_check": actual == case["expected_quantity"] and quantity["status"] != "conflict", "analysis": analysis}
            assert analysis["decision"]["usage"] == {}
            assert analysis["views"]["rear"]["file_hash"] == result["sha256"]
            assert request("GET", base)["analysis"] == analysis
            report["results"].append(result)
            output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n")
            print(json.dumps({"case": case["id"], "inspection": record["id"], "quantity": actual, "quantity_check": result["quantity_check"], "optical_score": quality["composite_score"]}), flush=True)


if __name__ == "__main__":
    main()

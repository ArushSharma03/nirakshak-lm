"""One generated label through the real HTTP app, local OCR, and optional Jev.

Run from the repository root with PYTHONPATH=backend. Jev is off unless --jev
is supplied. Its single batched request is not retried. No credentials are saved.
"""

import argparse
import json
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np
from fastapi.testclient import TestClient

from app.main import app
from app.services import inspection_store as store
from app.services.marker_detector import generate_reference_marker_image


def make_label():
    """Generate a reproducible English label and a coplanar synthetic reference."""
    image = np.full((720, 1500, 3), 255, np.uint8)
    for row, text in enumerate([
        "Product name: Butter Cookies", "Net quantity: 100 g", "MRP: Rs. 50.00",
        "Manufactured by: Sample Foods, Jammu", "Mfg date: 10/2026",
        "Consumer care: care@example.test", "Made in India",
    ]):
        cv2.putText(image, text, (40, 70 + row * 80), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (0, 0, 0), 2)
    marker = cv2.imdecode(np.frombuffer(generate_reference_marker_image(size_px=250, margin_px=45), np.uint8), cv2.IMREAD_COLOR)
    h, w = marker.shape[:2]
    image[60:60 + h, 1120:1120 + w] = marker
    return image


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--jev", action="store_true", help="One paid batched request; requires TYPESAFE_API_KEY")
    parser.add_argument("--output", default="evaluation/live-result.json")
    args = parser.parse_args()
    image = make_label()
    _, png = cv2.imencode(".png", image)
    start = time.monotonic()
    with tempfile.TemporaryDirectory() as directory:
        with patch.object(store, "DATA_DIR", directory), patch.object(store, "FALLBACK_FILE", str(Path(directory) / "records.json")), patch.object(store, "_MEMORY_INSPECTIONS", {}), patch.object(store, "is_database_available", return_value=False):
            with TestClient(app) as client:
                record = client.post("/inspections/", json={"product_name": "Synthetic OCR validation label"}).json()
                base = f"/inspections/{record['id']}"
                response = client.post(base + "/images", data={"view_type": "front"}, files={"file": ("label.png", png.tobytes(), "image/png")})
                response.raise_for_status()
                response = client.post(base + "/analyze", json={"as_of": "2026-11-06", "origin": "domestic", "coplanar_views": ["front"], "use_jev": args.jev})
                response.raise_for_status()
                analysis = response.json()["analysis"]
                assert all(ocr["status"] == "ok" for ocr in analysis["views"]["front"]["ocr"]), analysis
                assert analysis["profile"]["status"] == "selected"
                assert analysis["views"]["front"]["calibration"]["status"] == "available"
                qty = next(field for field in analysis["fields"] if field["field"] == "net_quantity")
                assert qty["value"] == "100 g" and qty["status"] == "observed", qty
                assert any(item["height_mm"] is not None for item in qty["evidence"])
                if args.jev:
                    assert analysis["decision"]["status"] == "ok", analysis["decision"]
                store._MEMORY_INSPECTIONS.clear()
                store._load_persisted_fallback()
                assert client.get(base).json()["analysis"] == analysis
    report = {"sample": "Generated English label, not a real packaging benchmark", "elapsed_seconds": round(time.monotonic() - start, 2), "analysis": analysis}
    Path(args.output).write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"output": args.output, "elapsed_seconds": report["elapsed_seconds"], "jev": analysis["decision"]}, indent=2))


if __name__ == "__main__":
    main()

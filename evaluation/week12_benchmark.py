"""Replay held-out packaging photographs through the inspection API in an isolated store."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import platform
import re
from statistics import median
import sys
from tempfile import TemporaryDirectory
from time import perf_counter
from urllib.request import urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from fastapi.testclient import TestClient
from app.core.config import settings
from app.main import app
from app.services import inspection_store as store


def checked(response):
    response.raise_for_status()
    return response


def normalized(value):
    return re.sub(r"[^\w.]", "", (value or "").casefold().replace("₹", "").replace("rs.", ""))


def evaluate(client, sample):
    inspection = checked(client.post("/inspections/", json={})).json()
    url = f"/inspections/{inspection['id']}"
    upload_seconds = 0
    for view, image in sample["views"].items():
        with urlopen(image["url"], timeout=30) as response:
            data = response.read(20 * 1024 * 1024 + 1)
        if hashlib.sha256(data).hexdigest() != image["sha256"]:
            raise ValueError(f"Source image changed for {sample['name']} ({view})")
        started = perf_counter()
        uploaded = checked(client.post(f"{url}/images", data={"view_type": view},
                                       files={"file": (f"{view}.jpg", data, "image/jpeg")})).json()
        upload_seconds += perf_counter() - started
        assert uploaded["images"][view]["file_hash"] == image["sha256"]

    started = perf_counter()
    checked(client.post(f"{url}/analyze", json={"use_jev": False, "as_of": "2026-11-27"}))
    analysis_seconds = perf_counter() - started
    record = checked(client.get(url)).json()
    analysis = record["analysis"]
    fields = {field["field"]: field for field in analysis["fields"]}
    scores = {}
    for name, expected in sample["expected"].items():
        field = fields.get(name, {})
        actual = field.get("value")
        status = field.get("status")
        result = "unread"
        if status == "conflict":
            result = "conflict"
        elif status == "observed":
            result = "match" if normalized(actual) in map(normalized, expected) else "incorrect"
        scores[name] = {"expected": expected, "actual": actual, "result": result}
    exports = {}
    for format in ["html", "pdf", "docx"]:
        started = perf_counter()
        report = checked(client.get(f"{url}/report", params={"format": format}))
        exports[format] = {"seconds": round(perf_counter() - started, 3), "bytes": len(report.content)}
    runs = Counter(f'{run["provider"]}:{run["status"]}'
                   for view in analysis["views"].values() for run in view["ocr"])
    return {
        "name": sample["name"], "fields": scores, "outcome": record["final_outcome"], "ocr_runs": dict(runs),
        "upload_seconds": round(upload_seconds, 3), "analysis_seconds": round(analysis_seconds, 3),
        "exports": exports,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    root = Path(__file__).parent
    parser.add_argument("--manifest", type=Path, default=root / "week12-packages.json")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    samples = json.loads(args.manifest.read_text(encoding="utf-8"))
    with TemporaryDirectory(prefix="nirik-week12-") as directory:
        store.DATA_DIR = directory
        store.FALLBACK_FILE = str(Path(directory) / "inspections.json")
        store._MEMORY_INSPECTIONS = {}
        store.is_database_available = lambda: False
        client = TestClient(app)  # Skip sample-data seeding for the isolated benchmark.
        results = []
        for sample in samples:
            result = evaluate(client, sample)
            results.append(result)
            print(f"{result['name']}: {result['analysis_seconds']} s", flush=True)
    scores = Counter(field["result"] for row in results for field in row["fields"].values())
    report = {
        "runtime": {"platform": platform.platform(), "cpu": platform.processor(), "python": platform.python_version(),
                    "ocr_device": settings.OCR_DEVICE, "xiaomi_enabled": settings.XIAOMI_OCR_ENABLED,
                    "tesseract_languages": settings.TESSERACT_LANGUAGES},
        "counts": dict(scores), "median_analysis_seconds": median(row["analysis_seconds"] for row in results),
        "cases": results,
    }
    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

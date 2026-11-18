"""Run the pinned single-checkpoint spotting model on unchanged wrapper fixtures.

Run with backend/.venv/bin/python evaluation/paddle_spotting_benchmark.py.
This diagnostic saves raw output; it does not modify inspections or production OCR.
"""

import hashlib
import json
import platform
import time
from pathlib import Path

import torch
import transformers
from PIL import Image
from transformers import AutoModelForImageTextToText, AutoProcessor

ROOT = Path(__file__).resolve().parent
MODEL = "PaddlePaddle/PaddleOCR-VL-1.6"
REVISION = "132c45f52c0a26ed5a6b2f6bd8e3985794cc27dd"
DEST = ROOT / "paddle-spotting-results.json"


def main():
    torch.set_num_threads(4)
    torch.set_num_interop_threads(2)
    baseline = json.loads((ROOT / "multi-wrapper-results.json").read_text())
    report = {
        "model": MODEL, "revision": REVISION, "prompt": "Spotting:",
        "device": "cpu", "dtype": "float32", "threads": 4,
        "torch": torch.__version__, "transformers": transformers.__version__,
        "platform": platform.platform(), "max_new_tokens": 4096,
        "max_time_seconds": 300, "min_pixels": 112896, "max_pixels": 2048 * 28 * 28,
        "scope": "Three catalogue images, no crops or second OCR model. Raw spotting quality and CPU feasibility diagnostic; not full accuracy or physical camera validation.",
        "results": [],
    }
    start = time.perf_counter()
    print("Loading pinned model (first run downloads weights)", flush=True)
    model = AutoModelForImageTextToText.from_pretrained(
        MODEL, revision=REVISION, dtype=torch.float32,
    ).eval()
    processor = AutoProcessor.from_pretrained(MODEL, revision=REVISION)
    report["load_seconds"] = round(time.perf_counter() - start, 2)
    print("Loaded", report["load_seconds"], flush=True)
    for case in baseline["results"]:
        path = ROOT / "fixtures" / "wrappers" / case["file"]
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != case["sha256"]:
            raise ValueError(f"Fixture changed: {case['id']}")
        image = Image.open(path).convert("RGB")
        original = image.size
        if image.width < 1500 and image.height < 1500:
            image = image.resize((image.width * 2, image.height * 2), Image.Resampling.LANCZOS)
        messages = [{"role": "user", "content": [
            {"type": "image", "image": image}, {"type": "text", "text": "Spotting:"},
        ]}]
        start = time.perf_counter()
        inputs = processor.apply_chat_template(
            messages, add_generation_prompt=True, tokenize=True,
            return_dict=True, return_tensors="pt",
            processor_kwargs={"images_kwargs": {"size": {"shortest_edge": 112896,
                                                        "longest_edge": 2048 * 28 * 28}}},
        )
        print("Generating", case["id"], flush=True)
        with torch.inference_mode():
            output = model.generate(**inputs, max_new_tokens=4096, max_time=300,
                                    do_sample=False, use_cache=True)
        tokens = output[0][inputs["input_ids"].shape[-1]:]
        eos = model.generation_config.eos_token_id
        eos_ids = eos if isinstance(eos, list) else [eos]
        result = {
            "id": case["id"], "file": case["file"], "sha256": digest,
            "original_dimensions": original, "processed_dimensions": image.size,
            "elapsed_seconds": round(time.perf_counter() - start, 2),
            "generated_tokens": len(tokens), "completed_eos": int(tokens[-1]) in eos_ids,
            "raw_output": processor.decode(tokens, skip_special_tokens=False),
            "expected_quantity": case["expected_quantity"],
            "visual_note": case["visual_note"],
            "baseline_pipeline_seconds": case["elapsed_seconds"],
        }
        report["results"].append(result)
        DEST.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps({k: v for k, v in result.items() if k not in {"raw_output", "visual_note"}}), flush=True)


if __name__ == "__main__":
    main()

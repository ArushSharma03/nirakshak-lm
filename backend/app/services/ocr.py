"""Local OCR adapters. Unavailable models never produce simulated evidence."""

import csv
import io
import subprocess
from functools import lru_cache
from threading import Lock
import cv2
import numpy as np

from app.core.config import settings
from app.schemas.analysis import Box, OCRLine, OCRResult, OCRWord

XIAOMI_MODEL = "xiaomi-research/Xiaomi-OCR-0"
XIAOMI_REVISION = "bbd8cf8d21f256b3644b44cb860f3a7cecb93c30"
_INFERENCE_LOCK = Lock()


@lru_cache(maxsize=1)
def _xiaomi():
    import torch
    from transformers import AutoModelForImageTextToText, AutoProcessor
    processor = AutoProcessor.from_pretrained(XIAOMI_MODEL, revision=XIAOMI_REVISION)
    model = AutoModelForImageTextToText.from_pretrained(
        XIAOMI_MODEL, revision=XIAOMI_REVISION,
        dtype=torch.float32 if settings.OCR_DEVICE == "cpu" else torch.float16,
    ).to(settings.OCR_DEVICE).eval()
    return processor, model


def xiaomi_ocr(image_bytes: bytes) -> OCRResult:
    result = OCRResult(provider="xiaomi", model=f"{XIAOMI_MODEL}@{XIAOMI_REVISION}", status="unavailable")
    if not settings.XIAOMI_OCR_ENABLED:
        result.message = "Xiaomi OCR disabled by configuration."
        return result
    try:
        import torch
        from PIL import Image
        with _INFERENCE_LOCK:
            processor, model = _xiaomi()
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            messages = [{"role": "user", "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": "Extract the text in the image."},
            ]}]
            inputs = processor.apply_chat_template(
                messages, tokenize=True, add_generation_prompt=True,
                return_dict=True, return_tensors="pt",
            ).to(model.device)
            with torch.inference_mode():
                output = model.generate(**inputs, do_sample=False,
                                        max_new_tokens=settings.OCR_MAX_TOKENS, max_time=120)
            text = processor.batch_decode(output[:, inputs["input_ids"].shape[1]:], skip_special_tokens=True)[0]
        result.status = "ok"
        result.lines = [OCRLine(text=line.strip()) for line in text.splitlines() if line.strip()]
        result.message = "Generative transcription. No calibrated confidence or text boxes supplied."
    except (ImportError, OSError):
        result.message = "Xiaomi weights or runtime unavailable. Install requirements-ocr.txt and download the pinned checkpoint."
    except Exception:
        result.status = "failed"
        result.message = "Xiaomi inference failed. Check local model/runtime compatibility."
    return result


def tesseract_ocr(image_bytes: bytes) -> OCRResult:
    result = OCRResult(provider="tesseract", model=f"tesseract/{settings.TESSERACT_LANGUAGES}", status="unavailable")
    try:
        process = subprocess.run(
            ["tesseract", "stdin", "stdout", "-l", settings.TESSERACT_LANGUAGES, "--psm", "11", "tsv"],
            input=image_bytes, capture_output=True, timeout=40, check=True,
        )
        groups: dict[tuple[str, str, str, str], list[dict[str, str]]] = {}
        # OCR quotes are literal text; CSV quoting can swallow subsequent TSV rows.
        for row in csv.DictReader(io.StringIO(process.stdout.decode()), delimiter="\t", quoting=csv.QUOTE_NONE):
            if row.get("level") == "5" and row.get("text", "").strip():
                key = tuple(row[k] for k in ("page_num", "block_num", "par_num", "line_num"))
                groups.setdefault(key, []).append(row)
        for words in groups.values():
            x0 = min(int(w["left"]) for w in words)
            y0 = min(int(w["top"]) for w in words)
            x1 = max(int(w["left"]) + int(w["width"]) for w in words)
            y1 = max(int(w["top"]) + int(w["height"]) for w in words)
            if x1 <= x0 or y1 <= y0:
                continue
            result.lines.append(OCRLine(
                text=" ".join(w["text"] for w in words),
                box=Box(x0=x0, y0=y0, x1=x1, y1=y1),
                confidence=max(0, min(1, sum(float(w["conf"]) for w in words) / (100 * len(words)))),
                words=[OCRWord(text=w["text"], box=Box(x0=int(w["left"]), y0=int(w["top"]),
                       x1=int(w["left"]) + int(w["width"]), y1=int(w["top"]) + int(w["height"])),
                       confidence=max(0, min(1, float(w["conf"]) / 100)))
                       for w in words if int(w["width"]) > 0 and int(w["height"]) > 0],
            ))
        result.status = "ok"
        result.message = "Original-image line boxes; confidence is an OCR heuristic, not legal certainty."
    except (FileNotFoundError, subprocess.CalledProcessError):
        result.message = "Install Tesseract and the configured language data."
    except subprocess.TimeoutExpired:
        result.status = "failed"
        result.message = "Tesseract exceeded 40 seconds."
    return result


def recognize(image_bytes: bytes) -> list[OCRResult]:
    return [xiaomi_ocr(image_bytes), tesseract_ocr(image_bytes)]


def detail_regions(image_bytes: bytes):
    """Yield overlapping original-image quadrants for a bounded local rescan."""
    image = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        return
    height, width = image.shape[:2]
    for index, (left, top, right, bottom) in enumerate(((0, 0, .6, .6), (.4, 0, 1, .6), (0, .4, .6, 1), (.4, .4, 1, 1))):
        x0, y0, x1, y1 = int(left * width), int(top * height), int(right * width), int(bottom * height)
        _, encoded = cv2.imencode(".png", image[y0:y1, x0:x1])
        result = xiaomi_ocr(encoded.tobytes())
        result.provider = f"xiaomi_detail_{index}"
        result.message = f"Detail scan of original-image region [{x0}, {y0}, {x1}, {y1}]. " + result.message
        yield result

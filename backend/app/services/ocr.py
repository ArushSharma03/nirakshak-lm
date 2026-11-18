"""Local OCR adapters. Unavailable models never produce simulated evidence."""

import csv
import io
import subprocess
import math
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
    if settings.OCR_DEVICE == "cpu":
        torch.set_num_threads(settings.OCR_CPU_THREADS)
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
        from PIL import Image, ImageOps
        with _INFERENCE_LOCK:
            processor, model = _xiaomi()
            # Match OpenCV and browser display orientation while preserving source bytes.
            image = ImageOps.exif_transpose(Image.open(io.BytesIO(image_bytes))).convert("RGB")
            messages = [{"role": "user", "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": "Extract the text in the image."},
            ]}]
            inputs = processor.apply_chat_template(
                messages, tokenize=True, add_generation_prompt=True,
                return_dict=True, return_tensors="pt",
                processor_kwargs={"images_kwargs": {"size": {"shortest_edge": 65536,
                                                             "longest_edge": settings.OCR_MAX_PIXELS}}},
            ).to(model.device)
            with torch.inference_mode():
                output = model.generate(**inputs, do_sample=False,
                                        max_new_tokens=settings.OCR_MAX_TOKENS, max_time=120)
            generated = output[0, inputs["input_ids"].shape[1]:]
            eos = model.generation_config.eos_token_id
            eos_ids = eos if isinstance(eos, list) else [eos]
            complete = len(generated) > 0 and int(generated[-1]) in eos_ids
            text = processor.batch_decode(generated.unsqueeze(0), skip_special_tokens=True)[0]
        result.status = "ok" if complete else "partial"
        result.raw_text = text
        # A cutoff can leave an unfinished value on the last line. Keep it out of extraction.
        lines = text.splitlines() if complete or text.endswith("\n") else text.splitlines()[:-1]
        result.lines = [OCRLine(text=line.strip()) for line in lines if line.strip()]
        result.message = "Generative transcription. No calibrated confidence or text boxes supplied."
        if not complete:
            result.message = "Incomplete transcription: generation reached its token/time limit. Only complete lines retained; missing text needs a detail scan or retake. " + result.message
        if not result.lines and complete:
            result.status = "failed"
            result.message = "No complete text lines returned. Retake the photo or check the model runtime."
    except (ImportError, OSError):
        result.message = "Xiaomi weights or runtime unavailable. Install requirements-ocr.txt and download the pinned checkpoint."
    except Exception:
        result.status = "failed"
        result.message = "Xiaomi inference failed. Check local model/runtime compatibility."
    return result


def tesseract_ocr(image_bytes: bytes) -> OCRResult:
    result = OCRResult(provider="tesseract", model=f"tesseract/{settings.TESSERACT_LANGUAGES}", status="unavailable")
    try:
        # Strip EXIF after applying its orientation so every adapter uses displayed pixels.
        image = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            result.status, result.message = "failed", "Cannot decode the source photo."
            return result
        _, encoded = cv2.imencode(".png", image)
        process = subprocess.run(
            ["tesseract", "stdin", "stdout", "-l", settings.TESSERACT_LANGUAGES, "--psm", "11", "tsv"],
            input=encoded.tobytes(), capture_output=True, timeout=40, check=True,
        )
        groups: dict[tuple[str, str, str, str], list[OCRWord]] = {}
        rejected = 0
        # OCR quotes are literal text; CSV quoting can swallow subsequent TSV rows.
        for row in csv.DictReader(io.StringIO(process.stdout.decode()), delimiter="\t", quoting=csv.QUOTE_NONE):
            if row.get("level") != "5" or not (row.get("text") or "").strip():
                continue
            try:
                key = tuple(row[k] for k in ("page_num", "block_num", "par_num", "line_num"))
                left, top, width, height = (int(row[k]) for k in ("left", "top", "width", "height"))
                confidence = float(row["conf"]) / 100
                if not math.isfinite(confidence) or not all(key):
                    raise ValueError("Invalid OCR row")
                word = OCRWord(text=row["text"], box=Box(x0=left, y0=top, x1=left + width, y1=top + height),
                               confidence=max(0, min(1, confidence)))
            except (KeyError, TypeError, ValueError):
                rejected += 1
                continue
            groups.setdefault(key, []).append(word)
        for words in groups.values():
            result.lines.append(OCRLine(
                text=" ".join(w.text for w in words),
                box=Box(x0=min(w.box.x0 for w in words), y0=min(w.box.y0 for w in words),
                        x1=max(w.box.x1 for w in words), y1=max(w.box.y1 for w in words)),
                confidence=sum(w.confidence for w in words) / len(words), words=words,
            ))
        result.status = "partial" if rejected else "ok"
        result.message = "Original-image line boxes; confidence is an OCR heuristic, not legal certainty."
        if rejected:
            result.message += f" Skipped {rejected} malformed word rows."
    except (FileNotFoundError, subprocess.CalledProcessError):
        result.message = "Install Tesseract and the configured language data."
    except subprocess.TimeoutExpired:
        result.status = "failed"
        result.message = "Tesseract exceeded 40 seconds."
    return result


def recognize(image_bytes: bytes) -> list[OCRResult]:
    return [xiaomi_ocr(image_bytes), tesseract_ocr(image_bytes)]


def detail_regions(image_bytes: bytes, *, boxes: list[Box] | None = None, include_quadrants: bool = False):
    """Read at most four label crops, using geometry only to choose where to look."""
    image = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        return
    height, width = image.shape[:2]
    regions = []
    for box in boxes or []:
        line_height = box.y1 - box.y0
        dx, dy = max(2 * line_height, .03 * width), max(3 * line_height, .04 * height)
        region = (max(0, int(box.x0 - dx)), max(0, int(box.y0 - dy)),
                  min(width, int(box.x1 + max(4 * line_height, .2 * width))), min(height, int(box.y1 + dy)))
        if region not in regions and region[2] > region[0] and region[3] > region[1]:
            regions.append(region)
    # A located declaration gets a focused read, not guesses from unrelated panels.
    if not regions or include_quadrants:
        # Truncated whole-page reads usually leave the lower panels unvisited.
        for left, top, right, bottom in ((.4, .4, 1, 1), (0, .4, .6, 1), (.4, 0, 1, .6), (0, 0, .6, .6)):
            region = (int(left * width), int(top * height), int(right * width), int(bottom * height))
            if region not in regions:
                regions.append(region)
    for index, (x0, y0, x1, y1) in enumerate(regions[:4]):
        _, encoded = cv2.imencode(".png", image[y0:y1, x0:x1])
        result = xiaomi_ocr(encoded.tobytes())
        result.provider = f"xiaomi_detail_{index}"
        result.message = f"Detail scan of original-image region [{x0}, {y0}, {x1}, {y1}]. " + result.message
        yield result

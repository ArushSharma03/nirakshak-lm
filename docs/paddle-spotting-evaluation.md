# PaddleOCR-VL-1.6 wrapper test — 17 November 2026

Direct single-checkpoint `Spotting:` inference ran locally on the same three unchanged catalogue photos as the saved Xiaomi evaluation. One of three transcripts finished within the five-minute generation budget. This native Transformers CPU configuration is not ready to replace the current pipeline.

| Photo | Inference + preprocessing | Tokens | Complete transcript | Returned regions | Observed result |
| --- | ---: | ---: | --- | ---: | --- |
| Maggi | 299.67 s | 2,083 | No; time limit | 114 | Manufacturer `Nestlé India Limited` read correctly. Transcript stops before the visible `NET QUANTITY: 70 g` line. Small promotional text contains recognition errors. |
| Good Day | 300.22 s | 1,631 | No; time limit | 60 | `120g` read correctly. Country line becomes `MADE IN OMAN / MOUA`. Repeated regions consume the generation budget; the exact same text and polygon occurs up to six times. |
| Lay’s | 247.59 s | 1,515 | Yes | 86 | Blank quantity, price and date remain unfilled. Small manufacturer line becomes `PEPISCO INDIA HOLDINGS PVT. LTD`, rather than `PEPSICO`. |

All 260 parsed quadrilaterals were within the original image bounds and nondegenerate. Original-photo overlays were inspected for all three cases. Returned boxes generally follow printed lines, but this is a visual check, not an annotated box accuracy score. These are line regions, not single-glyph measurements.

## Comparison with saved Xiaomi results

The saved Xiaomi pipeline recovered Maggi’s 70g and Good Day’s 120g, and left the blank Lay’s quantity unfilled. Paddle’s partial Maggi output cannot establish a recognition failure for the quantity: generation stopped before reaching it. Good Day’s correct quantity does not make its unfinished, repetitive transcript successful.

Paddle resolved Maggi’s manufacturer into one correct candidate where the old fused report had a conflict. On Good Day it read the country name OMAN, but added garbage; the old Xiaomi report had conflicting country readings. On Lay’s, Xiaomi’s saved manufacturer value had the correct PEPSICO spelling and Paddle’s did not.

Saved Xiaomi pipeline durations were 315.46, 94.18 and 259.83 seconds respectively. Those historical runs include different pipeline work, including crop retries, and are not a controlled speed comparison with this direct-model run. No new Xiaomi, Tesseract or Jev inference was made for this test.

Reusing the existing field extractor also exposed independent gaps: Maggi’s column-interleaved line order separates a consumer-care heading from its contact details; Lay’s uses “CONSUMER SERVICES MANAGER”, outside the current consumer-care anchor patterns. Merely swapping OCR models does not repair those extraction paths.

## Reproduce

```sh
OMP_NUM_THREADS=4 HF_HUB_DISABLE_XET=1 backend/.venv/bin/python evaluation/paddle_spotting_benchmark.py
PYTHONPATH=backend backend/.venv/bin/python evaluation/review_paddle_spotting.py
```

The first command reruns inference and overwrites the raw benchmark JSON. The second regenerates the extraction comparison and HTML overlays without model inference. Model downloads remain in the normal Hugging Face cache. Use `HF_HUB_OFFLINE=1` after the checkpoint is cached.

- Model: [PaddlePaddle/PaddleOCR-VL-1.6](https://huggingface.co/PaddlePaddle/PaddleOCR-VL-1.6), pinned revision `132c45f52c0a26ed5a6b2f6bd8e3985794cc27dd`.
- AMD Ryzen 5 5600H, CPU only, four PyTorch compute threads, two interop threads, float32. No quantization or second model.
- PyTorch 2.14.0+cpu; Transformers 5.17.0. Cached model load: 2.46 seconds, excluded from per-photo timings. The successful initial download/load took 436.42 seconds before the model-card preprocessing example hit a version mismatch; it produced no inference output.
- Greedy decoding, cache enabled, maximum 4,096 new tokens and 300 seconds per image. The time check occurs between decoding steps and is not a hard process deadline.
- Model-card spotting resize: double both dimensions when both are below 1,500; processor pixel limits 112,896–1,605,632. JSON `processed_dimensions` records the PIL size before the processor’s final resize, not the final tensor grid.
- Spotting token parsing follows [PaddleX post-processing](https://github.com/PaddlePaddle/PaddleX/blob/develop/paddlex/inference/pipelines/paddleocr_vl/uilts.py): location coordinates are normalized to 0–1000 and mapped to original pixels. Partial outputs are inspected diagnostically; they are never submitted to production records as complete OCR.
- No calibrated confidence is invented. The isolated field extractor receives line text and boxes; production OCR and stored inspections are unchanged.

## Evidence and limits

- [Raw outputs and timings](../evaluation/paddle-spotting-results.json)
- [Parsed polygons and comparison fields](../evaluation/paddle-spotting-review.json)
- [Interactive original-photo overlays and transcripts](../evaluation/paddle-spotting-review.html)
- [Rerunnable inference script](../evaluation/paddle_spotting_benchmark.py)
- [Existing baseline](../evaluation/multi-wrapper-results.json), including image source URLs and visually transcribed target notes. Fixture hashes were checked before inference.

This is a three-image diagnostic, not a full accuracy benchmark. Hindi, broader Indian scripts, GPU inference, quantized deployment, camera photos, curved-label correction and physical character height were not tested. No legal compliance score or general OCR accuracy percentage can be inferred from these results.

Recommendation: retain the current app pipeline while testing a smaller spotting model or a GPU deployment on an annotated set. A single checkpoint can supply text and coordinates, but this particular CPU setup has not demonstrated an acceptable replacement.

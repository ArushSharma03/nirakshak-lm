# OCR and decision models

Model cards and TypeSafe documentation were checked on 2026-11-06.

| Model | Fit | Verification |
|---|---|---|
| [Xiaomi-OCR-0](https://huggingface.co/xiaomi-research/Xiaomi-OCR-0) | Requested Xiaomi model; approximately 0.8B, Apache 2.0, local transcription | Installed and run on a generated English label; no boxes or calibrated confidence |
| Tesseract | Lightweight geometry provider with local language packs | Real word boxes, confidence and HTTP pipeline tested in English |
| [Bodhan Indic OCR](https://huggingface.co/bodhan-ai/indic-ocr) | Candidate for English plus 22 Indian languages, recognition and layout | Model card reviewed only; gated access and Indic Open Model License need review |
| [PaddleOCR-VL-1.6](https://huggingface.co/PaddlePaddle/PaddleOCR-VL-1.6) | Compact multilingual alternative under Apache 2.0 | Model card reviewed only; not installed or benchmarked |

Xiaomi is pinned to `bbd8cf8d21f256b3644b44cb860f3a7cecb93c30` for reproducibility.
Keep it as the requested primary transcriber. Evaluate Bodhan against labeled
packaging in the actual target languages before adding a provider. Its coverage
is a model-card claim, not accuracy measured here. Include bilingual labels, small
print, glare and curved packaging. Measure exact declaration values and boxes.

TypeSafe `jev-1.14.0` performs closed candidate selection after OCR and extraction.
Calibration, profile selection and legal rules stay in code. The contract follows
the [System One API](https://docs.typesafe.ai/api/system-one) and
[pre-parsed extraction cookbook](https://docs.typesafe.ai/cookbooks/pre_parsed_value_extraction_cookbook).

One live batch used 3,144 input and 297 output tokens. At the checked rate of
$0.042 per million input tokens and free output, estimated cost was $0.000132048.
The later user-authorized public-image batch used 783 input and 68 output tokens,
estimated $0.000032886. Combined estimated validation cost is $0.000164934.
These estimates use published pricing and returned usage; the account balance
was not measured. See [the real-image findings](public-image-evaluation.md),
including the imperfect manufacturer suggestion despite high model confidence.

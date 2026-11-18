# Jev text-only and image-backed wrapper checks

Run on 12 November 2026 with `jev-1.14.0`. Six real API requests completed successfully: one text-only and one image-backed request for each of three wrappers. The user authorized at most 20 requests; 14 remain unused. The persistent counter in `evaluation/jev-wrapper-budget.json` reserves attempts before networking, counts failures conservatively and prevents duplicate automatic requests. No retries were made.

Both modes received the same saved OCR transcripts, extracted candidate values and questions. Image mode additionally received a separate JPEG derived from the original wrapper within the documented 1568-pixel image limit. Original image bytes and hashes were preserved. Human-transcribed expected values, catalogue titles and ground-truth notes were not sent in either mode.

| Check | Text-only Jev | Image-backed Jev | Visual reference |
| --- | --- | --- | --- |
| Maggi quantity | Selected 70 g, confidence 96% | Selected 70 g, confidence 100% | NET QUANTITY: 70 g |
| Good Day quantity | Selected 120g, confidence 92% | Selected 120g, confidence 98% | NET WT: 120g |
| Lay's quantity | Blank/not shown, confidence 85% | Blank/not shown, confidence 98% | Blank NET QTY area; nutrition/serving values do not count |
| Maggi numeric MRP | Unreadable, confidence 37% | Blank/not shown, confidence 82% | Numeric MRP is on a different panel, not shown |
| Good Day numeric MRP | Blank/not shown, confidence 98% | Blank/not shown, confidence 77% | No numeric MRP in supplied photo |
| Lay's numeric MRP | Blank/not shown, confidence 85% | Blank/not shown, confidence 98% | Blank MRP area |
| Good Day country | Rejected supplied candidates, confidence 49% | Incorrectly selected ORAN, confidence 79% | Printed MADE IN OMAN |

Both modes selected the printed base company names for Maggi and Lay's. Confidence was distributed between similar company/address candidates; this is not proof that complete addresses were transcribed correctly. Neither mode can generate a correct missing value in this Choice-based workflow. The correct Oman value was absent from the supplied OCR candidates; the supported safe response was to reject those candidates. The image-backed request failed that check.

Confidence is the model's distribution summary, not measured accuracy. In the country failure, the selected wrong option had probability 86% and confidence 79%. Those are different values. The interactive chart displays option probabilities; the table above displays model confidence.

Text mode used 10,127 input and 487 output tokens. Image mode used 21,516 input and 491 output tokens. Combined usage was 31,643 input and 978 output tokens. These are provider-reported token counts, not a measured account charge. No monetary estimate is inferred.

Raw requests' text state, questions, sanitized answers, usage, image transforms and source hashes are retained in `evaluation/jev-mode-results.json`. Image base64 and credentials are not written to that artifact. The visual report is `docs/evidence/jev-text-image-comparison.html`, generated without more inference by `evaluation/render_jev_comparison.py`.

TypeSafe's [image documentation](https://docs.typesafe.ai/images.md) describes image/Box support as experimental and requires an explicit image header. The [OCR verification cookbook](https://docs.typesafe.ai/cookbooks/ocr_confidence_bounding_boxes.md) demonstrates separate page and crop checks; this experiment tested whole-photo candidate selection, not that complete multi-stage workflow. The [HTTP API](https://docs.typesafe.ai/api.md) and current image limits were checked through the T3 browser before the requests.

These three catalogue cases establish specific successes and a specific failure. They do not establish general field accuracy, physical capture behavior, Indic-language accuracy or legal compliance. Jev suggestions remain separate from the saved local OCR analysis; the incorrect country result was not applied to the reports.

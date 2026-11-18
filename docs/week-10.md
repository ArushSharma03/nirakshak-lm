# Week 10 screening and reports

Upload at least one package photo, choose the origin and inspection date, and
run analysis. All views use the same process. No reference target or scale
confirmation is needed. New optical checks report image quality and OCR
positions remain in pixels. Physical character height needs direct verification
on the package. Historical calibrated measurements remain readable.

## Screening outcomes

| Outcome | Trigger |
| --- | --- |
| Potential Non-Compliance | A supported quantity, price or date check has a structured failure from an unconflicted reading on a view with a complete primary OCR run. The report gives the check reason for inspector review. |
| Compliant within Implemented Checks | Every applicable implemented check passes and all captured views have complete primary OCR. The draft profile has checks that require more evidence, so the ordinary photo workflow often cannot reach this outcome. |
| Manual Review Required | Missing, conflicting or incomplete evidence, a capture quality issue without a structured declaration failure, or a profile that needs review. |

These are advisory outcomes. They use saved deterministic evidence checks.
Jev suggestions do not affect classification. Rerunning checks computes and
saves the outcome with the rule profile and reason. Removing or replacing a
photo invalidates the evidence, classification and report.

## Reports

Open Reports and select an analyzed inspection. **Printable report** opens the
photo, extracted readings and review tasks first. Use the browser's print dialog
to print or save a PDF. The print layout groups unresolved checks by what to
verify on the package. **Download report** saves the same report as a standalone
HTML file. Expand the appendix there to inspect raw OCR. The API verifies the
embedded original photos against their saved hashes. Older analyses remain
viewable and can be rechecked using their saved text.

## Live wrapper verification

Expected values below were read from the photos. These are catalogue images
rather than physical samples. Each was uploaded unchanged through FastAPI,
processed with local Xiaomi OCR and Tesseract, checked again from saved OCR,
reloaded and exported. Rechecking preserved the OCR. Exported photo bytes
matched the originals. Each generated 42 checks and required manual review.

| Photo | Inspection | Printed | Extracted | Upload through recheck |
| --- | --- | --- | --- | --- |
| [Parle-G, GoToChef rear](https://cdn.justgotochef.com/uploads/1523530788-Parle-Parle%20G%20Original%20Gluco%20Biscuits-Back.jpg) | INS-2026-9CF9DE55 | 250 g | 250 g | 29.89 s |
| [Parle Marie, BigBasket 500 px](https://www.bbassets.com/media/uploads/p/l/216875-3_8-parle-marie-biscuits.jpg) | INS-2026-0E75CE5E | 250 g | 25 g | 38.49 s |
| [Parle Marie, BigBasket 900 px](https://www.bbassets.com/media/uploads/p/xxl/216875-3_8-parle-marie-biscuits.jpg) | INS-2026-0A24DF15 | 250 g | 250 g | 87.65 s |

The 900 px Marie image recovered the dropped zero. The consumer-care
transcript still contained spelling and contact errors. Catalogue listings
can differ from the photographed pack. Check the photo before using its values.

## Verification by entry point

| Surface | Verification |
| --- | --- |
| Capture, uploads and OCR | Real Chromium inspection creation and rear photo upload, real OCR, navigation to Reports and 250 g displayed. No scale fields in the analysis request. |
| Saved checks and report | Chromium recheck, HTML download and printable view. Three saved wrapper reports printed on two A4 pages each, with the photo, readings and review tasks on page one. Raw OCR remains in the HTML appendix. |
| Retake/remove | Chromium removed the test inspection's photo. The export endpoint then returned 409. |
| Legacy data and API | Backend suite covers saved records, report escaping and attachment behavior, photo invalidation, all three OCR completion scenarios used by the classification regression, and measurement behavior for historical data. |
| Windows | PowerShell parser, backend runtime imports and Tesseract, and launch/health logic exercised on Linux. Native Windows provisioning and shutdown are unverified. See [Windows setup](windows-dev.md). |
| Other modes | Physical camera capture, CUDA and paid Jev were outside these live runs. |

# Photo and regulation follow-up

Base: latest fetched `origin/main`, `c4968dc`, including merged PR 1. Changes are uncommitted.

## Constraints

Preserve original photo bytes and unrelated work. Do not manufacture a perfect score, a declaration, a physical measurement, or a legal verdict. No commit or push was requested. Keep paid Jev calls disabled during verification.

## Photo processing

Xiaomi is the primary declaration reader. Tesseract readings can supply geometry only when the same field and normalized value were read by Xiaomi in that view. Unmatched Tesseract readings remain in the transcript but cannot create or override extracted declarations. When Xiaomi is unavailable, declarations stay unverified instead of falling back silently to Tesseract.

The existing OpenCV pipeline already preserves the source and creates a separate bilateral/CLAHE preview. A local experiment on the 596 x 514 rear wrapper produced 86 Tesseract lines from the original versus 49 from the enhanced copy; neither recovered the quantity anchor. A 3x cubic upscale also failed to recover the anchor. These experiments do not justify enabling enhanced Tesseract OCR. No TypeScript image library was added, and the extra enhanced Tesseract pass was removed after the user's correction.

Optical scoring keeps the original weighted formula but caps a retake at 59 and a warning at 79. These are product score ceilings, not calibrated probabilities or statutory thresholds. Individual metric statuses determine the overall status; the score does not select it. Scores use the original photo; they do not establish text readability. All-pass guidance now asks the inspector to check small declarations and calibration instead of describing the image as optimal. The UI explicitly explains the limit, including at 100/100.

## Applicable paths

| Path | Applies | Evidence |
| --- | --- | --- |
| Camera/upload, front/rear/side | Yes | Shared stored-image quality service; HTTP image processing tests |
| Standalone quality API | Yes | Same quality service; HTTP quality test |
| Stored processed preview | Yes | Original bytes preserved; preprocessing unchanged |
| Analysis and rerun | Yes | Primary-reader filtering before fusion and Jev selection |
| Xiaomi detail crops | Yes | Primary readings accepted before geometry matching |
| Tesseract unavailable or disagreement | Yes | Transcript retained; cannot create primary field values |
| Replacement/removal | Yes | Existing analysis invalidation retained and tested |
| Saved reports | Yes | Same analysis contract; provenance/transcripts remain visible |
| Jev | Yes | Receives filtered fields; disabled for live verification |
| Regulation lookup | Yes | `/profiles/regulations?q=...`, `/rules` search, checked-in source index |
| Other jurisdictions/categories | No | Research covers Indian LMPC and FSSAI food labelling only |
| Mobile native/offline clients | No | No separate clients in this repository |

## Verification

All 35 backend tests passed, including HTTP capture/preview/quality tests against the running server. Frontend lint, TypeScript and production build passed. The production `/rules` page returned all 41 documents and narrowed to two for `2026` in the T3 browser with no displayed errors. Source currency warnings remained visible. The browser tab was closed after checking.

The first real HTTP photo rerun failed to recover `70g`: the pinned Xiaomi checkpoint was missing on this machine. Tesseract alone did not recover it. After restoring the pinned checkpoint, the focused real HTTP rerun passed in 241.33 seconds. It recovered `70g`, preserved both original hashes, retained uncalibrated status and null physical heights, kept Jev disabled and reloaded the saved analysis. See `evaluation/public-image-primary-result.json`. Manufacturer remains an imperfect generated transcription, and MRP remains missing. The separate unchanged-size CLAHE comparison completed with both OCR providers and detail crops. It retained `70g` but lost the manufacturer reading. This does not justify replacing the original OCR input with the enhanced image. See `evaluation/photo-preprocessing-comparison.json` and `evaluation/compare_photo_preprocessing.py` for reproduction. The initial failure is not an accuracy pass.

Still not established: perfect small-print transcription, camera/device capture under physical conditions, Indic-language accuracy, calibrated glyph heights, and current-law reconciliation of every amendment. A low-resolution catalogue photo cannot supply unreadable price digits through contrast enhancement.

Observed field descriptions now explicitly call the result an unverified transcription. Agreement between crops or providers using the same photo is not independent confirmation. The recorded evaluation JSON predates this wording-only update.

## Final UI and wider validation

The user rejected the replacement evidence-bag design. A second Opus medium task restored and polished the original slate/teal console layout, with real-data dashboard, history, product grouping, analytics and system pages. Fake data fallbacks and government impersonation were not restored. Parent review added full-size photo links and clearer conflict wording. All 48 backend tests, frontend lint, TypeScript and final production build passed. The full browser create/upload/analyze/report/remove path passed; desktop and phone screenshots are in `docs/evidence/wrappers/`. See `docs/multi-wrapper-evaluation.md` for the test IDs and limits. No live camera capture was tested.

Separate Jev text-only and image-backed comparisons used 6 of the authorized maximum of 20 requests. See `docs/jev-text-image-comparison.md` for measured results and the image-backed country error. No Jev suggestion was applied as verified evidence. Changes remain uncommitted and unpushed.

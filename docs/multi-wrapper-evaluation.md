# Three additional wrapper checks

Sources were discovered in the T3 browser using Google Images on 12 November 2026. Exact image URLs, query terms, dimensions, original SHA-256 hashes, expected visible quantities, timings, full OCR transcripts and stored inspection IDs are in `evaluation/multi-wrapper-results.json`. Images are catalogue references, not physical camera captures; rights remain with their respective owners.

| Image | Visible quantity before OCR | Visible limitations |
| --- | --- | --- |
| Maggi rear wrapper | NET QUANTITY: 70 g | Numeric MRP, lot and date are on a different panel. Manufacturer Nestle India Limited is printed. |
| Good Day Choco Almond rear wrapper | NET WT: 120g | Made in Oman. Small multilingual print; blank date patch. Export packaging does not establish Indian retail applicability. |
| Lay's rear wrapper | Blank NET QTY space | Price and date spaces are also blank. Serving size 20 g and per-100 g nutrition must not become net quantity. |

## First run

The real HTTP pipeline passed all three targeted quantity checks: `70g`, `120g`, and missing respectively. This is not 100% field accuracy or a perfect compliance score. The first run is preserved separately in `evaluation/multi-wrapper-initial-results.json`.

Review of the other fields found that `Mfg. By` and `Mfg. & Mkt. by` were incorrectly interpreted as date anchors. `MFD & USE BY` label text became a date candidate even without a printed date, and a comma following `CONSUMER CARE` became a value. Extraction now recognizes the manufacturer abbreviations, requires a date-shaped value after a date anchor and discards punctuation-only values. Regression cases use the exact failed lines, including a manufacturer street number that must not become a date.

Good Day produced conflicting country transcriptions. That conflict remains visible for review; the model's reading is not silently replaced with manually transcribed ground truth.

The original optical scores were 59, 59 and 77.9. Large white studio backgrounds trigger exposure/glare checks. The current global optical heuristic cannot reliably separate white background from reflections on the wrapper. This limitation is stated rather than changing thresholds to force a perfect score. Optical quality and successful declaration extraction are different measurements.

## Reproduce

Start the backend with the pinned Xiaomi checkpoint available and the optional OCR runtime installed, then run:

```bash
backend/.venv/bin/python -u evaluation/multi_wrapper_flow.py
```

The script creates separate inspections, uploads each rear image unchanged, requests local analysis with unknown origin and Jev explicitly disabled, verifies file hashes and saved-analysis reload, and retains every result including failed quantity checks. No catalogue title or expected quantity is passed to OCR.

The complete HTTP rerun after the extraction fix passed all three targeted quantity checks. Maggi and Lay's no longer have false dates; punctuation-only consumer care was removed. Lay's manufacturer is read as PEPSICO INDIA HOLDINGS PVT. LTD. Maggi manufacturer and Good Day country retain conflicts. The final saved reports are INS-2026-E8C4ADA9, INS-2026-820EB3AF and INS-2026-6C5806D7 respectively.

The backend no longer fills new blank setup fields with fictitious quantities, prices or inspector identities, and zero prices survive reload. For the three task-owned final reports, only the unsupplied setup placeholders were cleared, preserving original photos, hashes, scores and OCR analysis. `evaluation/wrapper-setup-cleanup.json` records exactly which values were removed and why. Other existing records were left unchanged.

Separate authorized Jev tests made six requests over the saved evidence, comparing text-only and image-backed judgments. See `docs/jev-text-image-comparison.md`; those suggestions were not applied to the local OCR reports. The final original-console polish was rebuilt and launched on port 3000. Desktop and phone checks passed without page-wide horizontal scrolling. Final screenshots are in `docs/evidence/wrappers/`, with an interactive gallery at `docs/evidence/wrappers/results.html`.

## Final browser flow

The production UI created inspection INS-2026-149355B1 with blank optional fields, uploaded the Good Day rear image through its real file control, enabled analysis with one photo, kept Jev off, completed local OCR and navigated to the saved report showing `120g`. Removing that photo through the UI cleared the captured-view flag and invalidated its analysis. The three benchmark records and images were not changed by that reverse-action test. The separate API assertions confirmed null setup MRP and blank inspector/quantity.

Final checks: 48 backend tests, frontend lint, TypeScript and production build passed. No live camera or physical marker capture was tested. The app still requires human review of OCR conflicts and unreadable declarations.

# Photo-to-report pipeline repair

## Constraints and scope

Preserve original evidence and existing unrelated work. Do not infer missing values
from setup notes, turn capture quality into OCR accuracy, erase disagreements or
invent confidence/geometry. No paid Jev calls, credential changes, commits or pushes
were made. The earlier Paddle benchmark remains separate from production OCR.

The shipped reader remains Xiaomi-OCR-0. Tesseract can locate headings for a new
model read and contribute geometry only when its extracted value matches the primary
reading. It cannot silently replace an unavailable model.

## Repairs

- Find the nearest aligned label continuation across shuffled/interleaved columns,
  including values to the right. Reject ambiguous neighbors, distant columns,
  nutrition sections and other declarations.
- Recognize consumer services/manager headings and bounded multiline contact blocks;
  recognize manufacture-in-country-by headings and proprietary-food declarations.
- Stop values at another same-line declaration. Do not extract lot/address numbers
  as prices/dates or referral instructions as company names. Preserve malformed or
  ambiguous OCR in the transcript rather than manufacturing a clean value.
- Deduplicate identical positioned OCR regions before extracting evidence.
- Parse grouped prices with decimal arithmetic. Reject invalid grouping, negative
  numeric prefixes and percentages. Checks and fusion share price/quantity parsers,
  so equivalent quantities such as 0.1kg and 100g agree without merging mass/volume.
- Report truncated model output as `partial`. Preserve full raw output, extract only
  complete lines, and permit crop recovery even when no first line finished.
- Bound model images to a configurable pixel budget rather than the checkpoint's
  16-megapixel maximum. Target missing printed headings first; recover unvisited
  manufacturer panels after cutoffs within the same four-crop limit.
- Apply EXIF orientation consistently across OpenCV, Xiaomi and Tesseract input;
  convert the Tesseract working copy to PNG without altering stored originals.
- Skip malformed external TSV rows with an explicit partial result instead of
  crashing analysis or accepting nonfinite confidence/bad geometry.
- Rebuild existing analyses from saved transcripts on explicit request, checking
  source hashes before reuse and again before publication. Clear stale manual
  glyph selections. Fresh inference remains the default.
- Extend API/frontend validation, report warnings/transcripts, multiline evidence,
  analytics counts and capture controls for these states. Preserve saved profile
  inputs when reopening an analysis. Correct stale report copy about glyph checks.

## Surface ledger

| Surface | Applies | Source/change | Verification |
| --- | --- | --- | --- |
| Fresh analysis | Yes | `services/analysis.py`, `services/ocr.py` | Real three-wrapper API batch; additional Lay’s recovery run |
| Frozen OCR replay | Yes | `evaluation/replay_pipeline.py` | Identical saved Xiaomi/Tesseract inputs, current extraction/fusion/profile/checks |
| Primary unavailable/failed/partial | Yes | OCR result contract, detail scan gate | Adapter/state regression cases; real partial transcripts persisted |
| Geometry provider | Yes | TSV validation, orientation, exact-value gate | Negative provider tests, rotated JPEG cases, original coordinate assertions |
| Detail crops | Yes | Targeted headings and partial manufacturer recovery | Crop bounds/deduplication/four-call cap tests; real wrapper output |
| Extraction/fusion | Yes | `services/extraction.py` | Mixed columns, right-hand values, instruction text, price groups, duplicate regions and retained conflicts |
| Declaration checks | Yes | Shared price parsing; recomputed fields | Existing week-9 suite plus rebuilt real reports |
| API persistence/reload | Yes | `/analyze`, `/checks`, stored `raw_text`/`partial` | HTTP persistence/reload tests and live saved-text rebuild |
| Retake/removal/stale evidence | Yes | Existing invalidation, reuse hash gate | Replacement/removal tests; corrupted source refused for reuse |
| Browser client/data contract | Yes | Zod schema, report/analytics/capture controls | Actual real-run JSON parsed by frontend schema; lint/types/production build |
| Browser clicks/camera/physical marker | Not verified in this repair | No browser/device automation was requested for this turn | Hardware and visual acceptance are separate from API/build evidence |
| CUDA, remote deployment, distributed workers | No | Local CPU path; no distributed-state changes | Not tested; keep the documented single-worker restriction |
| PostgreSQL-native analysis | No | Analysis still lives in the existing local repository even when metadata is mirrored | No database migration or PostgreSQL validation claimed |

## Evidence

- [Frozen-input replay](../evaluation/extraction-replay-results.json): Maggi gains the
  contact block and loses a referral-text manufacturer conflict. Lay’s gains contact
  and generic-name candidates. Good Day's country disagreement remains unresolved.
- [First fresh failure](../evaluation/live-pipeline-initial-results.json): timeout
  returned only `LET`; no complete first line, and crop recovery was skipped. Retained
  as evidence of the failed attempt, not replaced with a successful score.
- [Fresh real-model API batch](../evaluation/live-pipeline-results.json): 70g, 120g and
  blank quantity respectively. This run exposed the misspelled referral instruction
  and incomplete lower-panel recovery that received further fixes.
- [Live saved-text rebuild](../evaluation/live-saved-text-rebuild.json): Maggi updated
  in about 0.5 seconds; source OCR JSON unchanged, manufacturer/contact/70g recovered.
- [Final running-code checks](../evaluation/live-pipeline-final-checks.json): all
  three current reports rebuilt and rechecked over HTTP, original-photo downloads
  matched their hashes, raw OCR stayed unchanged and persisted reloads matched.
- [Lay’s recovery rerun](../evaluation/live-lays-recovery-results.json): subsequent
  real-model verification after adding lower-panel recovery. It read PEPSICO INDIA
  HOLDINGS PVT. LTD correctly and left the blank quantity/price/date unfilled;
  224.88 seconds including the model load, upload and processing.
- [Regression cases](../backend/tests/test_extraction_layout.py), existing pipeline,
  photo-source, image-processing, marker and declaration-check suites.
- [Frozen-replay chart](evidence/pipeline-repair/replay.html): extraction coverage
  on identical old transcripts, not a field-accuracy score.

Final checks: 109 backend tests pass with no skips; frontend ESLint, TypeScript and
production build pass. The real frontend API functions rebuilt and rechecked Maggi
over HTTP in 653 ms, preserving raw stored OCR exactly. Nine production frontend
routes returned HTTP 200. This is client/transport evidence, not a browser-click
or visual acceptance test.

The older image-processing integration tests wrote synthetic records to the live
backend. They now use isolated temporary storage and real in-process handlers.
The five synthetic records created by those old tests during this repair were
removed only after their IDs, metadata and original image hashes matched the exact
generated fixture. Other records and the real-wrapper evaluation records remain.

Run the frozen replay without changing user records:

```sh
PYTHONPATH=backend backend/.venv/bin/python evaluation/replay_pipeline.py
```

Run fresh local inference through the live API, writing a new result file:

```sh
backend/.venv/bin/python evaluation/multi_wrapper_flow.py --output /tmp/new-wrapper-results.json
```

## Remaining recognition limits

These repairs do not establish perfect OCR. Good Day's tiny manufacturer/country
print produces unreliable model readings; conflict or missing evidence remains
appropriate. Read contact/address transcription against the photo: a recovered block
can still contain spelling mistakes. The optical scores are unchanged and some
photos still need retaking. No full field-accuracy percentage is claimed.

No GPU, live camera, Indian-script benchmark or printed-marker measurement was
performed. Analyzed records remain **Manual Review Required**. Existing raw OCR
mistakes are preserved, not silently rewritten by extraction.

The [community reading-order discussion](https://dev.to/kolmopdf/why-naive-text-extraction-destroys-rag-on-multi-column-pdfs-and-how-to-fix-reading-order-404a)
and its comments describe column interleaving and ambiguous layouts; the changes
here were verified against this repository’s transcripts and regression cases.

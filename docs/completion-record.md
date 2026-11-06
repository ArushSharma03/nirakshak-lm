# Work through week 8

Base: `origin/main` at `c6d88c7`. Branch: `feat/week-8-evidence-pipeline`.
The checkout was clean. The user subsequently authorized a commit and push to
open a PR against the original GitHub repository.

Board read on 2026-11-06. Week 5 has no card; OCR is a dependency of week 6.
Week 9 checks, week 10 classification, and week 11 report generation are outside this milestone.

| Result | Source | Check | State |
|---|---|---|---|
| Week 4 planar calibration and physical height estimates | calibration service, capture/upload API | synthetic known dimensions, numeric-word heights and API tests | implemented; physical validation pending |
| OCR with Xiaomi and an explicit geometry provider | OCR service | real local inference, no fabricated boxes/confidence | implemented; generated English label only |
| Week 6 anchored, spatial declaration extraction | extraction service | positive, missing, Hindi anchors, distant-value rejection | implemented; real-label benchmark pending |
| Week 7 confidence-aware fusion with provenance | fusion service | agreement, disagreement, missing confidence, retained conflicts | implemented; no cross-view registration |
| Week 8 versioned rule/profile selection | rules data, profile engine | dates, origins, version overlap, unsupported | implemented; initial legal data is draft |
| Capture, reprocess, reload and report evidence | frontend and API | typecheck, lint, build, real API boundary | implemented; full browser flow unverified |

## Hard constraints

Preserve unrelated work. Use apply_patch for manual edits. Do not store credentials.
Do not commit or push without instruction. Read installed Next.js documentation before editing frontend.
Do not treat a build as runtime evidence. Do not invent OCR confidence or physical calibration.

## Surface ledger

| Surface | Applies | Change and check |
|---|---|---|
| New inspection and direct capture | yes | stored images enter one analysis pipeline |
| Backend and frontend contracts | yes | typed analysis, calibration and profile inputs |
| OCR providers | yes | Xiaomi transcription, Tesseract spatial baseline, explicit failures |
| Retake, replacement, reprocess | yes | invalidate old analysis, recompute from stored source |
| JSON persistence and reload | yes | store analysis alongside existing inspection evidence |
| PostgreSQL | yes | existing records are mirrored locally; analysis uses that existing repository, no claim of DB-native analysis storage |
| Offline browser | yes | processing fails visibly; no fabricated extraction |
| Rules and reports | yes | show profile and actual evidence, remove hardcoded verification claims |
| Mobile/native apps | no | repository has only a web client |
| Relay / multi-device | no | no such transport exists in the repository |
| Legal determinations | no | weeks 9–10, keep advisory manual-review outcome |

## Validation evidence

Final backend run: `PYTHONPATH=backend backend/.venv/bin/pytest backend/tests -q`,
29 passed. One upstream Starlette/AnyIO deprecation warning remains.
Tests cover geometry, Hindi anchors, confidence/conflicts, dated rules, valid and
invalid mocked Jev responses, opt-out/reuse without provider calls, HTTP upload,
analysis, persistence reload, retake invalidation and stale-analysis rejection.

Frontend `npm run lint`, `npx tsc --noEmit` and `npm run build` passed.
All routes compiled; these checks do not prove browser behavior.

[Local-only result](../evaluation/local-result.json) records the final real
TestClient upload → Xiaomi/Tesseract → calibration → extraction → fusion → profile
→ save/reload run in 36.18 seconds. No model-provider network call was made in
that run; weights were cached and Hugging Face offline mode was enabled.

[Earlier Jev result](../evaluation/live-result.json) records the one paid batch
with `jev-1.14.0`: 3,144 input and 297 output tokens, estimated $0.000132048.
All seven Choice responses validated. A subsequent user-authorized real-image
batch used 783 input and 68 output tokens, estimated $0.000032886. Combined estimated
paid validation cost is $0.000164934. No request was retried.
Jev is opt-in and off by default. The server used for testing has no API key.

## Remaining verification and scope

- No real package-photo benchmark, physical print calibration, camera capture,
  Indic OCR benchmark or PostgreSQL-native analysis persistence proof.
- Public Google-discovered JPEGs were uploaded and processed through the real HTTP
  server. The initial failure and repaired quantity extraction are recorded in
  [public-image evaluation](public-image-evaluation.md), with sources, raw results
  and browser capture evidence. Physical camera capture remains untested.
- The final production browser report loaded the requested record, displayed `70g`
  with detail-region provenance and an unverified MRP, and retained manual review.
- Spatial continuation checks alignment within a view. Fusion compares declaration
  values across views and retains conflicts; it does not register views geometrically.
- The official Legal Metrology source register was reachable. PDF text, amendment
  dates and category exceptions were not fully verified. Rules stay `0.1.0-draft`.
- Bodhan Indic OCR and PaddleOCR-VL-1.6 were researched from model cards, not run.
- Plane milestone requirements were read. No issue status or comment was changed.
- PR branch: `feat/week-8-evidence-pipeline`. The original repository grants read
  access; the authorized PR is submitted from the `jR4dh3y/nirakshak-lm` fork.

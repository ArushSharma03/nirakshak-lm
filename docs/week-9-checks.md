# Week 9: deterministic declaration checks

> Historical milestone. See [Week 10](week-10.md) for current classification, reports, and capture behavior.


The engine evaluates saved OCR evidence. It never converts an OCR omission into
proof of absence or changes the inspection's overall manual-review outcome.

Every selected profile rule gets seven results: presence, completeness, units,
consistency, placement, readability and character height. Each result contains
its rule ID, citation, source URL, source candidates and a reason. States are
pass, fail, insufficient_evidence and not_applicable. A pass describes the
specific evidence test, not a statutory finding.

## Behavior

- Presence needs an anchored reading linked to a captured view.
- Completeness validates supported numeric quantity/price structures and full-year
  calendar dates. Invalid/future dates fail; ambiguous years stay unresolved.
  Name/contact fragments do not establish complete legal particulars.
- Units normalize mass, volume and whole-item counts using exact decimal values.
  Equivalent units agree; invalid amounts and unsupported units fail the OCR test.
- Consistency retains source conflicts. Repeated crops do not become independent
  confirmations. Unknown country names are not silently corrected.
- Placement requires a verified per-rule view constraint, captured panel and
  located evidence. There is no assumed mapping from front/rear to principal
  display panel. Missing geometry does not prove incorrect placement.
- Readability checks capture optics using the quality assessor's overall_status.
  A retake failure describes the photo, not the printed label's legal legibility.
- Character height maps an inspector-selected single-glyph box through the
  confirmed coplanar marker homography. Text-line height is never substituted.
  A comparison needs a verified applicable threshold; no universal threshold is
  invented. The draft food/grocery rules currently supply none.

The official FSSAI compilation's regulation 6 includes package-area and printing
conditions and refers several declaration sizes to Legal Metrology provisions.
This is why the implementation does not use one minimum for every declaration.
Sources: https://www.fssai.gov.in/docs/food-law/regulations/Comp_Labelling%20Display_Version%20VIII_09_09_2025.pdf
and https://consumeraffairs.gov.in/pages/legal-metrology-act . Current amendments,
exceptions and applicability remain the explicit limits of the draft profile.

## API and website

New analysis includes checks automatically. Existing records remain readable.
POST /inspections/{id}/checks runs checks using saved OCR, without OCR or Jev
calls. Optional origin and as_of inputs select the current dated profile.
Optional glyph_measurements entries contain field, view and an original-image
box. The API rejects an annotation without coplanar calibration or outside the
located declaration box. Annotation coordinates are retained in source evidence.
Annotations can be cleared on a subsequent check run. Duplicate annotations for
the same declaration and view are rejected instead of silently overwriting one.

Reports have a Declaration checks section with origin/date controls, status
filter, source evidence and an optional Inspector glyph measurement form.
Retaking/replacing/removing a photo invalidates the entire analysis and checks.
Saving checks revalidates original hashes and view membership; stale evidence is
rejected. Concurrent OCR and check runs use the same lock.

## Surface ledger

| Surface | Coverage |
| --- | --- |
| New analysis | Checks run after extraction/profile selection |
| Existing saved analysis | Recheck endpoint and backward-readable optional checks |
| Backend/frontend contract | Pydantic results and Zod parsing |
| Report UI | Filterable results, evidence and explicit measurement constraints |
| Persistence/reload | Results saved alongside immutable-source hashes |
| Retake/remove/replacement | Existing invalidation removes checks with analysis |
| Unsupported category/unknown origin | Insufficient evidence, no guessed applicability |
| Missing geometry/marker/threshold | Explicit insufficient evidence |
| Jev | Never called by check endpoint; model answers excluded from checks |
| Overall classification | Remains Manual Review Required; Week 10 scope |
| Native/mobile clients | No native client exists; web layout remains responsive |
| Physical marker/camera accuracy | Requires real-device validation; not proved by synthetic tests |

## Validation

27 focused tests cover missing evidence, invalid units/amounts, unit equivalence,
conflicts, calendar validity, unknown profiles, real quality-assessor output,
placement, glyph threshold boundaries, annotation validation, HTTP persistence,
reload, stale hashes and removal invalidation. Full backend suite: 75 tests.

A follow-up review reproduced and fixed two glyph-height edge cases. Geometry
retains full precision for threshold comparisons; rounding is presentation-only.
A 1.9996 mm estimate cannot pass a 2 mm fixture threshold. Measurement coverage
is per original photo rather than per duplicated OCR provider; an unlocated
Xiaomi reading does not block the matching located reading's measurement from
that same photo. A second unmeasured view or conflicting readings still require
review. These tests use synthetic thresholds, not new legal defaults.

The real Good Day record INS-2026-820EB3AF was rechecked through the report UI
using imported origin as a screening input. The original transcript still reads
120g. Results: 5 pass, 3 fail, 35 insufficient evidence, 6 not applicable. Failures
include conflicting country readings and capture-readability failures. These
counts are check results, not a compliance score. Filtered failures display in
the browser and saved results survive retrieval. No paid Jev request was made.
The final browser also rejected an uncalibrated annotation with a specific
message and preserved all previously saved results. Positive calibrated glyph
measurements, threshold boundaries and clearing were exercised using synthetic
geometry through the HTTP/storage tests. Physical accuracy remains untested.

## Plane updates verified on 17 November 2026

| Card | Milestone | Final state |
| --- | --- | --- |
| COM71127-5 | Week 3 preprocessing | In Progress: curved-label/orientation/coverage gaps documented |
| COM71127-6 | Week 4 calibration | Done: implementation and synthetic validation; physical validation pending |
| COM71127-7 | Week 6 extraction | Done: MVP implemented; accuracy limits documented |
| COM71127-8 | Week 7 fusion | In Progress: spatial consistency and broader multiview validation pending |
| COM71127-9 | Week 8 profiles | Done: engine and initial draft inventory; legal review pending |
| COM71127-10 | Week 9 checks | Done: implementation with explicit insufficient-evidence states |

Each card has an implementation/evidence comment. Done describes the delivered
MVP implementation, not legally verified outcomes. Weeks 10–12 remain pending.

The baseline work was committed as 3f96f10 before Week 9 implementation. The
Week 9 implementation, regression fixes and live-browser verification are included
in the follow-up commit on feat/week-8-evidence-pipeline.

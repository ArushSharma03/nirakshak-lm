# Live browser verification, 17 November 2026

Production Next.js app on localhost:3000 and the real backend on localhost:8000.
Both services were down at the start and were restarted. This run used browser
clicks, native form inputs, file upload and page reloads. No unit-test runner,
mocked OCR response or API-only script substituted for the user flow.

New inspection: INS-2026-29853F17, named Live browser inspection 17 Nov.
Source: evaluation/fixtures/wrappers/good-day.jpg, a public rear-label image.
Optional setup values were left blank. Imported origin was supplied as a
screening input; Jev remained unchecked. One real OCR analysis was requested.

| Browser action | Observed result |
| --- | --- |
| Start an inspection; enter name and source; submit | New record opened in guided capture |
| Select Rear; upload fixture | Stored photo, optical score 59, retake warning, no marker |
| Open Analyze | One photo accepted; unavailable marker options disabled |
| Analyze 1 photo | Processing state disabled capture steps; report opened after roughly 3.5 minutes on CPU |
| Read report | Net quantity 120g and source text displayed; optional setup notes stayed blank |
| Check results | 49 results: 5 pass, 3 fail, 35 insufficient evidence, 6 not applicable |
| Select Fail filter | Country consistency and capture-readability failures displayed |
| Run declaration checks | Completed without another OCR run; controls re-enabled |
| Enter glyph bounds without calibration | Specific calibration error displayed; prior results retained |
| Uncheck annotation and rerun | Recovered without error |
| Reload report | 120g and 49 checks remained present |
| Photos and re-run; Rear; Remove and retake | Returned to upload; Open report disappeared immediately |
| Reopen report after removal | No rear photo, Not analyzed yet, no checks or extracted results |
| History search for new name | Exactly one matching record, No photos yet |
| Search a nonexistent name | Nothing matches |
| Quick look, then Escape | Correct record opened; panel closed |
| Resize to 390px; open mobile menu; Escape | Menu opened and closed; no document horizontal overflow |

The final empty inspection is retained as evidence of removal/invalidation.
Existing records were not removed or replaced. Browser snapshots produced frames
and accessibility trees during this run. No unexpected console errors were seen;
the annotation rejection was deliberate. The physical camera, real printed
marker accuracy and print dialog were not tested.

## Findings

- Cold CPU OCR latency is visibly slow, about 3.5 minutes for one rear image in
  this run. A completed request does not establish acceptable performance.
- The optional setup legend occupied one form-grid column beside the brand
  field. Both legends now span both desktop columns; this is a presentation fix.
  The rebuilt production page was checked again: both headings are above their
  first input, with 903px-wide legends on desktop and no mobile overflow.
- Current draft-rule and extraction limitations remain explicit. These results
  are not a compliance certification or an OCR accuracy score.

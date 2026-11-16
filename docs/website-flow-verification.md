# Website behavior follow-up

The top bar now wraps its title and actions according to the actual available
space beside the sidebar. API status does not shrink. Action groups can wrap
without forcing the header to scroll horizontally.

Photo removal now consumes the updated inspection returned by DELETE. Previously
the backend invalidated analysis but the capture page retained the old analysis
in memory, leaving stale report links and the already-analyzed message visible.
The delete function now lives beside the record mapper in the API client, and
the unused version that discarded the response has been removed.

Verification record: INS-2026-DAAB1F3A, created through the website with the
Good Day rear fixture. Jev remains disabled. Final behavior results follow below.

## Observed results

- Browser form creation succeeded; rear upload succeeded; Analyze 1 photo was
  enabled with Jev unchecked. Real local OCR completed and opened the report.
- Saved quantity was 120g and the report displayed the source photo.
- Photos and re-run returned to capture. Remove and retake returned to upload,
  immediately removed Open report, and produced no alert. A separate API read
  confirmed both images and analysis were cleared. The named test record remains
  as an empty inspection so the reverse-action result can be inspected.
- History search returned the single named record; an unmatched search showed
  Nothing matches.
- Dashboard toolbar child bounds fit at actual 390px and 1920px browser widths;
  additional responsive measurements were recorded in the working session.
- 48 backend tests, frontend lint, production build/TypeScript and diff check pass.
- Screenshot frames were unavailable. DOM layout and real browser interactions
  were verified; live camera hardware, print dialog and paid Jev were not tested.

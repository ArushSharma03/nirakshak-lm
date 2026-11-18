# Product

<!-- impeccable:product-schema 1 -->

> Written from the implementation brief without a live interview. Updated 2026-11-12 after the user rejected the evidence-bag redesign and asked to keep the original console UI, polished. Items marked *assumption* should be confirmed.

## Platform

web

## Users

- **Primary:** a Legal Metrology inspector or student evaluator screening a packaged commodity (biscuits, soap, beverages) photographed at a shop shelf or desk, on a phone or a laptop with a webcam. *Assumption:* one inspector per session, no sign-in.
- **Secondary:** a project reviewer reading a saved inspection report to judge what the system extracted and how it got there.

## Product Purpose

Nirikshak-LM screens package photos for the declarations required under the Legal Metrology (Packaged Commodities) Rules, 2011. The inspector captures or uploads front, rear and side panels; the backend scores photo optics, looks for a 50 mm ArUco reference marker, transcribes the label, extracts declarations with traceable evidence, and selects a versioned rule profile. Success is an inspector who can see quickly what was read, from which photo and OCR provider, and what still needs a human decision.

## Positioning

Every reading is traceable to a view, an OCR provider and the original-image text. The product never issues a statutory verdict: every record ends in manual review.

## Operating Context

- Capture: browser camera or file upload per view; a printed 50 mm ArUco 4x4_50 ID 0 marker placed flat beside the label when physical scale is wanted.
- OCR: Xiaomi-OCR is the primary transcription. Tesseract supplies line geometry only where it matches the primary reading. Jev decision support is optional and off by default because it consumes paid credits.
- Storage: FastAPI backend on port 8000 persisting to PostgreSQL when available, otherwise to a JSON file store on the API server. Both are real storage.
- Rules: `/profiles/select` returns a versioned profile; `/profiles/regulations` searches an index of official LMPC and FSSAI source links.

## Capabilities and Constraints

- The optical score (0–100) measures sharpness, exposure, contrast, glare and resolution of the original photo. It is not OCR accuracy and not legal compliance.
- Extraction statuses: observed, conflict, missing. Missing OCR is not proof of absence.
- Physical text-height estimates exist only when a marker is detected and the inspector confirms it is coplanar. Legal thresholds are not implemented.
- New records keep blank setup fields blank (MRP null; a typed zero price is valid). Legacy records may still hold server placeholders (for example `Unspecified Manufacturer`, `100 g`, ₹50). The UI labels all setup metadata as inspector-entered and unverified.
- No product catalog, analytics or settings backend exists. The Product catalog, Analytics and System pages are computed in the browser from real API records and health only; they hold no sample data and save nothing.

## Evidence on Hand

- Real records from the running API, e.g. `INS-2026-704984E8` (Parle-G 70 g public catalog images, analyzed, manual review).
- `rules/regulation-index.json`: official source links.
- No customer data, testimonials or compliance statistics exist; never fabricate counts, rates or trends.

## Product Principles

1. Evidence before conclusion: show the photo, the transcript and the provider before any summary.
2. Never imply legal compliance. Outcomes say what needs review, not what is lawful.
3. Honest states: offline, empty, failed and partial are shown as such, never papered over with sample data.
4. One task at a time: capture flows forward view by view; the report is for reading.

## Accessibility & Inclusion

WCAG 2.2 AA contrast and keyboard access; usable one-handed on a phone at a shop counter.

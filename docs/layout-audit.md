# Page layout audit

The shell owns the 80rem maximum width and responsive gutters: 16px on phones,
24px from 640px, 32px from 768px. Top bar, content and footer use the same
container. Pages use a 24px section gap. No page adds a narrower outer container.
Card headers and bodies use 20px horizontal padding. Compact table cells, image
captions and evidence slips retain their smaller internal padding.

| Page | Finding | Change |
| --- | --- | --- |
| Dashboard | Custom header differed from other pages | Shared page header; common section spacing |
| New inspection | Centered 48rem container inside shell; desktop fieldsets added extra padding | Remove nested width; use 20px form padding at every size |
| History | Shared shell width; quick look is an intentional overlay | Common page stack; overlay stays independent |
| Capture picker | Existing full width | Common page stack |
| Capture with record | Equal photo columns and analysis sidebar contain long transcripts and names | Shrink grid children safely; wrap long text |
| Reports | Second 16rem sidebar reduced report width; 32px gaps; padding changed by breakpoint | Full-width report selector above body; 24px gaps; consistent 20px padding |
| Rules | 48px page gaps versus 24px elsewhere | Common page stack |
| Products | Responsive card grid could inherit long names' minimum widths | Shrink grid children safely; wrap text |
| Analytics | Responsive cards and fixed inner columns | Common page stack; shrink grid children safely |
| System | Full-width sections already matched shell | Common page stack; preserve functional inner columns |
| Dashboard redirect | No rendered layout | Continues to redirect to dashboard |

Shared card minimum widths and nested grid children now permit shrinking. Long
names, source text and identifiers wrap. Photo aspect ratios remain unchanged.
Data contracts, providers, persistence and reverse actions are unaffected by this
layout pass. Desktop and phone geometry checks are recorded after verification.

## Verification

Production lint, TypeScript build and whitespace checks passed. Browser DOM
measurements covered all ten rows above except the redirect, with both capture
picker and selected-record capture counted separately, at 1280×850 and 390×850.
Every page measured 945px content width at desktop and 343px at phone width,
including the browser's 15px scrollbar reservation. No measured descendants
escaped the page container; horizontal table scroll regions were excluded.
The loaded Maggi report at phone width had document width 390px and no nested
grid scroll overflow. Screenshot capture failed because the desktop browser was
not producing frames, so visual appearance is not established by these checks.

Scrollbar gutters are reserved on short and long pages and in the top bar, so
adding enough content to scroll no longer changes the horizontal alignment.

## Single top bar

Page titles, descriptions and page actions now render into the shell top bar.
The old in-content page header has been removed from every route. The shell
supplies the route title while data loads or when a page has no custom toolbar.
Portals keep action handlers owned by their page and remove them on navigation.
Capture's record title and Open report action use this same slot. Reports keep
their document details in a section; Photos and re-run and Print are in the top
bar. System's Check again action has moved out of the Backend card.
The top bar wraps actions beneath the title on smaller screens.

Single-top-bar verification: browser DOM checks across all ten page variants at
1280px and 390px found exactly one header and one visible h1, with zero h1s in
page content. Route-specific action labels matched each page. A client-side
sidebar transition from history to System replaced New inspection with Check
again, and the relocated Check again button was exercised. A transient history
width reading during loading was rechecked after loading: document width 1280px,
no elements beyond the viewport. No new OCR, capture or print-dialog run was
performed for this toolbar change.

---
name: Nirikshak-LM
description: Inspector console for packaged-commodity label screening. Slate console with restrained status text and muted blue actions.
colors:
  ground: "#f8fafc"
  sheet: "#ffffff"
  ink: "#0f172a"
  ink-2: "#475569"
  ink-3: "#64748b"
  rule: "#e2e8f0"
  rule-strong: "#cbd5e1"
  rail: "#0f172a"
  rail-2: "#1e293b"
  accent: "#365c70"
  accent-deep: "#284654"
  accent-wash: "#f1f5f7"
  accent-soft: "#cad8df"
  warn: "#92400e"
  warn-wash: "#fffbeb"
  danger: "#be123c"
  danger-wash: "#fff1f2"
  ok: "#047857"
  ok-wash: "#ecfdf5"
typography:
  page-title:
    fontFamily: "ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Noto Sans, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 600
    lineHeight: 1.25
    letterSpacing: "normal"
  card-title:
    fontFamily: "ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 600
  body:
    fontFamily: "ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.55
  serial:
    fontFamily: "ui-monospace, SFMono-Regular, JetBrains Mono, Menlo, Consolas, monospace"
    fontSize: "0.8rem"
rounded:
  badge: "0px"
  control: "8px"
  card: "6px"
  banner: "16px"
spacing:
  gutter-phone: "16px"
  gutter-desktop: "32px"
  section: "24px"
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.sheet}"
    rounded: "{rounded.control}"
    height: "40px"
  button-secondary:
    backgroundColor: "{colors.sheet}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    height: "40px"
  card:
    backgroundColor: "{colors.sheet}"
    rounded: "{rounded.card}"
---

# Design System: Nirikshak-LM

## Overview

The original Nirikshak-LM console, kept and polished: a dark slate navigation rail, a white top bar, a slate-50 workspace, white cards, and one teal accent. It is an Operate surface for an inspector at a shop counter or lab desk. The 2026-11-12 evidence-bag redesign (custody blue, tilted stamps, tear lines) was rejected by the user and removed; do not reintroduce it.

## Shell

- **Sidebar** (`rail` #0f172a, 16rem, collapsible to 4.25rem on desktop, slide-in drawer on phones with Esc and backdrop close). Two groups: Screening (Dashboard, New inspection, Guided capture, Inspection history, Reports) and Reference (Compliance rules, Product catalog, Analytics, System). Active item: `rail-2` fill, white text, `accent-soft` icon.
- **Top bar**: 64px white, section / page title, API status pill (links to System), and a New inspection action except on setup and capture.
- **Footer** line under every page: screening support only, not a statutory finding.

## Colors

- Teal `accent` is the only brand colour: primary buttons, links, active states, meters, captured-view marks.
- Amber, rose and emerald report state only: optical status, analysis outcome, errors, API status. Never decoration.
- Categories use one neutral tag style; no per-category rainbow.

## Components

- **Badge**: rounded-full pill with a state dot, soft wash and matching 200-level border. Never rotated or animated.
- **Card**: white, 1px `rule` border, 12px radius, a 1px soft shadow; optional header row with a 14px semibold title.
- **Stat tile**: label, real count, one-line meaning; links to the matching filter. Only counts derivable from API records. No trends, rates or invented figures.
- **Inspection table**: Inspection (mono ID + date), Package, Category (lg+), Scale (xl+), Photos (F/R/S marks), Status, actions (Quick look, next step). Collapses to stacked rows under md.
- **Quick look**: right-side panel from history with photos, optical scores, declarations read and unverified setup notes.
- **Meter**: single-hue 6px bar with its value printed beside it.

## Typography

System sans throughout; mono only for IDs, hashes, OCR transcripts and pixel values. Tabular numerals for counts.

## Do

- Show the photo, transcript and provider beside every reading.
- Label setup metadata as typed at setup and unverified.
- Show offline, empty and failed states plainly with a recovery action.
- Keep the optical-score caveat wherever the score appears.

## Don't

- No sample, cached or invented data; no compliance rates or trends.
- No fictitious inspector identity in the chrome.
- No gradient banners, glass, rotated stamps, dashed "tear" lines or evidence-bag theatrics.
- No government letterheads or seals.


## November 16 refinement

Status labels and API status use text without pills, borders or dots. Loading
spinners and chart keys retain their functional shapes. The dashboard uses an
ordinary heading instead of a dark banner. Page headings are 20px semibold,
section headings 16px semibold. Shared cards have light borders without shadows.
Actions and links use muted blue.

Applies to desktop and mobile shell, dashboard, history, capture, reports,
products, analytics, rules and system through shared components. Offline and
error labels retain explicit wording. Data contracts, OCR providers, persistence
and reverse actions do not change in this presentation pass.


## Shared page geometry

The shell alone owns an 80rem container with 16/24/32px responsive gutters.
Top bar, footer and page content align. A stable scrollbar gutter prevents
short and long pages from shifting. Pages use a shared 24px stack. Forms and
reports occupy the same outer width as lists; report selection sits above the
report. Grid children shrink and long identifiers wrap within their columns.
See docs/layout-audit.md for the per-page findings and verification limits.

## Single page header

The website top bar is the only page header. TopBarContent supplies each page's
title, description and actions via a React portal. There is no second heading
block at the start of page content. Card headings and report document details
remain within the content because they label specific sections.

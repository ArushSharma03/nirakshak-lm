# Week 12 validation

Week 11 added PDF and Word exports and counts for screening outcomes and rule checks. Each export reads the saved inspection and checks the SHA-256 hash of every analyzed image. Download HTML for original image bytes and the full OCR appendix. PDF and Word contain the key readings, review actions, source citations, and resized photo copies. PDF uses a Latin font. Use Word or HTML to preserve other scripts.

## Held-out packaging benchmark

The [manifest](../evaluation/week12-packages.json) pins four catalogue images by SHA-256 and records values transcribed from the printed label. These photos were not used to tune extraction in this milestone. One catalogue SKU disagrees with the weight printed on its image, so the printed label is the benchmark reference. Blank batch and price stamps in catalogue artwork are excluded from accuracy scoring.

Run from the repository root with the backend OCR dependencies and Xiaomi weights installed.

```sh
backend/.venv/bin/python evaluation/week12_benchmark.py --out /tmp/nirik-week12.json
```

The runner uses a temporary store and the normal creation, photo upload, analysis, readback and export endpoints. It disables Jev and times local API processing separately from image download. It records conflicts, incorrect readings and unread fields separately. A correct result requires an observed value matching one of the frozen reference spellings after normalizing punctuation, spacing and case.

## Physical capture acceptance

The repository contains seven previously photographed packages. Those records check saved-evidence compatibility and report layout. Run the following acceptance test on a physical Android phone with the backend reachable before using the app for an inspection.

1. Scan a flat carton, a reflective wrapper, and a curved bottle. Write down the printed quantity, price and any readable date before scanning.
2. Hold the same panel in view after the first capture. Confirm the app requests the next panel and keeps the old one.
3. Move out of frame, closer to the packet, and into a glare spot. Check that the prompts respond, then hold a clean view until it captures automatically. Skip the optional side on one package.
4. Deny and regrant camera access. Background and reopen the app during capture. Disconnect the network during submission, reconnect, and retry.
5. Compare view labels, photos and extracted values against the package. Export each report format and verify hashes, review actions and the recorded screening outcome.
6. Record phone model, Android version, package type, lighting, time per capture, retries, mislabelled panels, end-to-end duration, and the count of matching fields.

No physical phone or new physical package photographs were available for this milestone. Catalogue images and the Android emulator exercise separate parts of the workflow. Their results do not measure field capture accuracy or compliance.

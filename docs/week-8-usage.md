# Run the evidence pipeline

Use Python 3.13 and Node.js 20.9+. Install Tesseract and English language data
with your package manager; add Hindi data for `TESSERACT_LANGUAGES=eng+hin`.

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
# Install CPU/CUDA torch wheels appropriate to your machine first.
pip install -r requirements-ocr.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The first Xiaomi run downloads the pinned public Hugging Face checkpoint.
Set `XIAOMI_OCR_ENABLED=false` for Tesseract alone. Provider failures are explicit.
API docs are at `http://localhost:8000/docs`. Start the frontend with `npm ci`
and `npm run dev` in `frontend`, then open `http://localhost:3000`.

Create an inspection, upload views, select the inspection date and origin, then
process evidence. A 50 mm ArUco 4x4_50 marker, ID 0, enables height estimates only
when the inspector confirms that marker and declaration are coplanar. Curved
packaging cannot be calibrated by that assumption. Retakes invalidate analysis.

Configuration comes from the backend environment or working directory's `.env`.
See [.env.example](../.env.example). Supply `TYPESAFE_API_KEY` with a server-side
secret manager. Never expose it through `NEXT_PUBLIC_*` variables.

## Optional paid decisions

Jev is unchecked by default and requires explicit opt-in per run. It receives
extracted text, not images. One batch selects existing candidates or `none`, with
no retries. Successful suggestions are reused for identical fields and model.
Each request is capped at 24,000 context characters and six candidates per field.
This is a per-request limit, not an account spending cap. Leave Jev off to avoid
paid requests. Suggestions cannot clear conflicts or produce legal outcomes.

## API

- `POST /inspections/` creates an inspection.
- `POST /inspections/{id}/images` accepts JPEG/PNG and a `view_type` form field.
- `DELETE /inspections/{id}/images/{view}` removes active evidence.
- `POST /inspections/{id}/analyze` accepts the following body.
- `GET /inspections/{id}` includes persisted analysis.
- `GET /profiles/` lists rules; `POST /profiles/select` accepts `category`, `origin`, `as_of`.

```json
{"as_of":"2026-11-06","origin":"domestic","coplanar_views":[],"use_jev":false}
```

Analysis requires captured evidence. Unknown origin requests review. Unsupported
categories and dates return explicit profile results. Boxes refer to original
images; preprocessing copies are separate. No cross-view image registration is
claimed. Spatial association is within each view; cross-view fusion matches values.

When whole-image OCR misses quantity on a declaration panel, the pipeline scans
up to four overlapping quadrants with Xiaomi and stops on an anchored quantity.
Each detail transcript records the original-image crop coordinates. These are
region coordinates, not word boxes; no confidence or physical height is invented.
This local fallback can add several minutes on CPU and makes no paid request.

## Validation

```bash
PYTHONPATH=backend backend/.venv/bin/pytest backend/tests -q
PYTHONPATH=backend OMP_NUM_THREADS=4 backend/.venv/bin/python evaluation/live_pipeline.py --output /tmp/local-ocr-result.json
cd frontend
npm run lint
npx tsc --noEmit
npm run build
```

Older HTTP integration tests expect a backend on port 8000. The evaluation script
uses temporary storage and real local OCR. It makes no paid call unless `--jev`
is added explicitly. Checked-in results contain generated evidence only.

## Limits

Use one backend worker. Analysis and images use the existing local JSON repository,
including when inspection metadata is mirrored from PostgreSQL. Locks are in-process,
not distributed. Database-native analysis persistence was not implemented.

The food/grocery inventory links to the official source register but requires
amendment, date and exception review. Physical text heights are estimates, not
certified font measurements. Xiaomi supplies no coordinates or calibrated confidence;
Tesseract confidence is heuristic. Bare commodity names without explicit anchors
may be missed. Very long labels may exceed OCR generation limits.

Generated English-label checks do not establish accuracy on real packaging,
small print, glare or Indian-language labels. Hindi anchors exist; an Indic OCR
benchmark, physical camera capture and printed-marker accuracy remain untested.

The Google-discovered packaging flow is documented separately in
[public-image evaluation](public-image-evaluation.md), including initial failures.

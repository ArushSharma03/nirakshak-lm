# Nirikshak-LM

**An Evidence-Calibrated Multiview System for Explainable Packaged-Commodity Compliance Screening**

> B.Tech CSE Minor Project (COM-711) — Group 27

---

## Purpose

Nirikshak-LM is a preliminary compliance-screening and inspection-support system for packaged commodities under the Legal Metrology (Packaged Commodities) Rules, 2011 and applicable amendments.

It is **not** an autonomous legal authority. All outcomes are advisory and must be verified by a qualified inspector.

## Technology Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js (React) + TypeScript |
| Backend | Python FastAPI |
| Computer Vision | OpenCV planar calibration and preprocessing |
| OCR | Xiaomi-OCR-0 transcription + Tesseract geometry |
| Decisions | Optional TypeSafe Jev candidate selection |
| Information Extraction | Regex, keyword matching, spatial analysis |
| Compliance Engine | Versioned rule-as-data (Python) |
| Database | PostgreSQL / SQLite (future) |
| Reports | ReportLab / python-docx (future) |

## Current Implementation Status

Implemented through week 8: capture, image quality, planar calibration, OCR,
anchored English/Hindi extraction, spatial continuation, multi-view fusion and
versioned category/origin/date profile selection. Retakes invalidate analysis.
The UI shows actual source evidence and optional Jev suggestions.

The initial food/grocery rules are drafts requiring legal review. Other categories
return unsupported. Weeks 9–11 legal checks, classification and report export are
outside this milestone. See [setup and limitations](docs/week-8-usage.md),
[model selection](docs/model-selection.md) and [validation](docs/completion-record.md).

---

## Getting Started

### Prerequisites

- Python 3.13, Node.js 20.9+ and npm
- Tesseract with English language data; Hindi data for `eng+hin`

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Optional Xiaomi runtime; install CPU/CUDA torch wheels for your machine first
pip install -r requirements-ocr.txt

# Run the server
uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`.
Health check: `GET http://localhost:8000/health`
API docs: `http://localhost:8000/docs`

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run the dev server
npm run dev
```

The frontend will be available at `http://localhost:3000`.

---

## Project Structure

```
nirakshak lm/
├── backend/          # FastAPI modular monolith
│   ├── app/
│   │   ├── api/      # Route handlers
│   │   ├── core/     # Configuration
│   │   ├── models/   # DB models
│   │   ├── schemas/  # Pydantic evidence contracts
│   │   ├── services/ # CV, OCR, extraction and fusion
│   │   ├── engine/   # Versioned profile selection
│   │   └── main.py   # FastAPI entry point
│   └── requirements.txt
├── frontend/         # Next.js application
├── docs/             # Architecture & documentation
├── evaluation/       # Evaluation notebooks & scripts
├── dataset/          # Dataset management
├── rules/            # Legal Metrology rule definitions
├── tests/            # Integration & E2E tests
├── .env.example      # Environment variable template
└── README.md
```

## License

This project is developed for academic purposes.

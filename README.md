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
| Computer Vision | OpenCV photo quality and preprocessing |
| OCR | Xiaomi-OCR-0 transcription + Tesseract geometry |
| Decisions | Optional TypeSafe Jev candidate selection |
| Information Extraction | Regex, keyword matching, spatial analysis |
| Compliance Engine | Versioned rule-as-data (Python) |
| Database | PostgreSQL / SQLite (future) |
| Reports | Printable, self-contained HTML |

## Current Implementation Status

Implemented through Week 10: package photo capture, OCR, declaration extraction,
multi-view fusion, versioned rule profiles, declaration checks, and advisory screening
classification. Capture and analysis use package photos alone. Verify physical text height
on the package if needed. Replacing or removing a photo invalidates analysis.

The food/grocery profile is a draft. Other categories need manual review. The reports page
offers a printable view and a downloadable HTML file with the original photos and saved
evidence. See [Week 10 behavior and verification](docs/week-10.md) and
[setup and OCR limitations](docs/week-8-usage.md).

---

## Getting Started

### Windows

See [Windows setup and launch](docs/windows-dev.md).

### Manual setup prerequisites

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

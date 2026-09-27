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
| Computer Vision | OpenCV (future) |
| OCR | PaddleOCR (future) |
| Information Extraction | Regex, keyword matching, spatial analysis |
| Compliance Engine | Versioned rule-as-data (Python) |
| Database | PostgreSQL / SQLite (future) |
| Reports | ReportLab / python-docx (future) |

## Current Implementation Status

- [x] **Step 1** — Project setup & environment configuration
- [ ] Step 2 — Backend/database foundation
- [ ] Step 3 — Frontend foundation (extended)
- [ ] Step 4 — Inspection creation & multi-view image upload
- [ ] Steps 5–21 — See development plan

---

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+ and npm

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

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
│   │   ├── models/   # DB models (future)
│   │   ├── schemas/  # Pydantic schemas (future)
│   │   ├── services/ # CV, OCR, IE, Fusion (future)
│   │   ├── engine/   # Rule engine (future)
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

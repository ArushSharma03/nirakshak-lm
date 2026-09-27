"""
Nirikshak-LM — FastAPI Application Entry Point.

This is the main application factory. All routers are registered here.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.core.config import settings


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    application = FastAPI(
        title=settings.APP_NAME,
        description=(
            "An Evidence-Calibrated Multiview System for "
            "Explainable Packaged-Commodity Compliance Screening"
        ),
        version="0.1.0",
    )

    # --- CORS middleware (allow frontend dev server) ---
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Register routers ---
    application.include_router(health_router)

    return application


app = create_app()

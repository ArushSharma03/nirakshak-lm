"""
Health-check endpoint.

Provides a simple liveness probe for the backend service.
"""

from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    """Return the current health status of the Nirikshak-LM backend."""
    return {
        "status": "healthy",
        "service": "nirikshak-lm-backend",
        "version": "0.1.0",
    }

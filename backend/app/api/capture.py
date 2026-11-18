"""
Capture-related API endpoints.

"""

from fastapi import APIRouter, File, UploadFile, HTTPException, status
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from app.services.quality_assessor import assess_image_quality

router = APIRouter(prefix="/capture", tags=["Capture"])


class QualityAssessmentResponse(BaseModel):
    """Response schema for image quality assessment."""

    overall_status: str  # "Pass" | "Warning" | "Retake Recommended"
    is_acceptable: bool
    composite_score: float
    metrics: Dict[str, Any]
    recommendations: List[str]
    thresholds_used: Optional[Dict[str, float]] = None
    disclaimer: str


@router.post(
    "/assess-quality",
    response_model=QualityAssessmentResponse,
    summary="Assess capture quality (sharpness, lighting, contrast, resolution, glare)",
)
async def assess_quality_endpoint(
    file: UploadFile = File(..., description="Package image file to assess"),
):
    """
    Evaluate optical quality of uploaded package photograph.
    Checks sharpness, exposure, contrast, resolution, and glare hotspots.
    """
    image_bytes = await file.read()
    if len(image_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )
    return assess_image_quality(image_bytes)

"""
Capture-related API endpoints.

POST /capture/detect-marker — Accept an image and return marker detection result.
"""

from fastapi import APIRouter, File, UploadFile, HTTPException, status
from pydantic import BaseModel
from typing import Optional

from app.services.marker_detector import detect_marker

router = APIRouter(prefix="/capture", tags=["Capture"])


class MarkerDetectionResponse(BaseModel):
    """Response schema for marker detection."""

    detected: bool
    bounding_box: Optional[list[float]] = None
    pixel_width: Optional[float] = None
    pixel_height: Optional[float] = None
    score: Optional[float] = None
    message: str


@router.post(
    "/detect-marker",
    response_model=MarkerDetectionResponse,
    summary="Detect reference marker in an image",
)
async def detect_marker_endpoint(
    file: UploadFile = File(..., description="Package image (JPEG/PNG)"),
):
    """
    Accept an uploaded image and attempt to detect an ArUco reference marker.

    Returns detection status, bounding box, pixel dimensions, and a quality score.
    Pixel-to-physical-scale calibration is not performed here (Week 4 milestone).
    """
    # Validate content type
    if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type: {file.content_type}. Upload JPEG or PNG.",
        )

    image_bytes = await file.read()

    if len(image_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    result = detect_marker(image_bytes)

    return MarkerDetectionResponse(
        detected=result.detected,
        bounding_box=result.bounding_box,
        pixel_width=result.pixel_width,
        pixel_height=result.pixel_height,
        score=result.score,
        message=result.message,
    )

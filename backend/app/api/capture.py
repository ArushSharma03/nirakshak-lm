"""
Capture-related API endpoints.

POST /capture/detect-marker — Accept an image and return marker detection result.
GET /capture/reference-marker — Return official printable reference marker image.
GET /capture/reference-marker/info — Return marker specifications and calibration guidelines.
"""

from fastapi import APIRouter, File, UploadFile, HTTPException, Response, status
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from app.services.marker_detector import detect_marker, generate_reference_marker_image
from app.services.quality_assessor import assess_image_quality

router = APIRouter(prefix="/capture", tags=["Capture"])


class MarkerDetectionResponse(BaseModel):
    """Response schema for marker detection."""

    detected: bool
    marker_id: Optional[int] = None
    dictionary: Optional[str] = None
    bounding_box: Optional[list[float]] = None
    pixel_width: Optional[float] = None
    pixel_height: Optional[float] = None
    score: Optional[float] = None
    estimated_ppm: Optional[float] = None
    message: str


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

    Returns detection status, bounding box, pixel dimensions, quality score,
    and preliminary planar scale estimation.
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
        marker_id=result.marker_id,
        dictionary=result.dictionary,
        bounding_box=result.bounding_box,
        pixel_width=result.pixel_width,
        pixel_height=result.pixel_height,
        score=result.score,
        estimated_ppm=result.estimated_ppm,
        message=result.message,
    )


@router.get(
    "/reference-marker",
    summary="Download printable ArUco reference marker image",
)
def get_reference_marker(marker_id: int = 0):
    """
    Generate and return the official PNG image of the reference marker (ArUco 4x4_50 ID 0).
    Includes the required white quiet zone border and calibration ruler markings.
    """
    png_bytes = generate_reference_marker_image(marker_id=marker_id)
    return Response(content=png_bytes, media_type="image/png")


@router.get(
    "/reference-marker/info",
    summary="Reference marker specifications and calibration requirements",
)
def get_reference_marker_info():
    """Return physical dimensions, dictionary specifications, and placement guidelines."""
    return {
        "standard_dictionary": "ArUco 4x4_50",
        "standard_marker_id": 0,
        "physical_dimension_mm": 50.0,
        "quiet_zone_requirement": "Surrounding white border must remain intact (minimum 15% width).",
        "placement_instructions": [
            "Place marker on the same flat depth plane as the packaging face.",
            "Do not cut along the black edge — preserve the outer white paper border.",
            "Avoid direct specular reflections from room lighting or flash.",
            "Keep distance between 20 cm and 50 cm so marker is at least 80 pixels across.",
        ],
    }

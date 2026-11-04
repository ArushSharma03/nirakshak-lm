"""
Inspection API endpoints.

POST /inspections/                     — Create a new inspection.
GET  /inspections/                     — List all inspections.
GET  /inspections/{inspection_id}      — Retrieve an inspection with its images and metadata.
POST /inspections/{inspection_id}/images — Attach a captured view image (front, rear, side) and run marker detection.
GET  /inspections/{inspection_id}/images/{view_type} — Serve the stored view image file.
"""

import os
from typing import List, Optional
from fastapi import APIRouter, File, Form, UploadFile, HTTPException, Response, status
from fastapi.responses import FileResponse

from app.schemas.inspection import InspectionCreate, InspectionRecordResponse
from app.services.inspection_store import (
    create_inspection_record,
    get_inspection_record,
    list_inspection_records,
    attach_inspection_image,
)
from app.services.marker_detector import detect_marker

router = APIRouter(prefix="/inspections", tags=["Inspections"])


@router.post(
    "/",
    response_model=InspectionRecordResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new inspection record",
)
def create_inspection(payload: InspectionCreate):
    """
    Create a new compliance-screening inspection record.
    Saves to PostgreSQL when available, or to safe persistent local repository in demo/offline mode.
    """
    record = create_inspection_record(payload.model_dump(exclude_unset=True))
    return record


@router.get(
    "/",
    response_model=List[InspectionRecordResponse],
    summary="List all inspections",
)
def list_inspections():
    """Retrieve all inspection records, ordered by date descending."""
    return list_inspection_records()


@router.get(
    "/{inspection_id}",
    response_model=InspectionRecordResponse,
    summary="Retrieve an inspection by ID",
)
def get_inspection(inspection_id: str):
    """Retrieve an inspection by ID, including its captured views, marker calibration, and metadata."""
    inspection = get_inspection_record(inspection_id)
    if inspection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inspection '{inspection_id}' not found.",
        )
    return inspection


@router.post(
    "/{inspection_id}/images",
    response_model=InspectionRecordResponse,
    summary="Attach captured package view image to inspection",
)
async def upload_inspection_view(
    inspection_id: str,
    view_type: str = Form(..., description="Package view orientation: front, rear, or side"),
    file: UploadFile = File(..., description="Captured image file (JPEG/PNG)"),
):
    """
    Attach an optical evidence plate to the specified inspection record.
    Automatically executes ArUco reference marker detection on the uploaded image
    and stores pixel scaling and quality scores.
    """
    normalized_view = view_type.lower().strip()
    if normalized_view not in ("front", "rear", "side"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid view_type '{view_type}'. Expected 'front', 'rear', or 'side'.",
        )

    image_bytes = await file.read()
    if len(image_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded image file is empty.",
        )

    # Automatically analyze marker detection on the captured image
    detection_res = detect_marker(image_bytes)
    marker_dict = {
        "detected": detection_res.detected,
        "score": detection_res.score,
        "pixel_width": detection_res.pixel_width,
        "pixel_height": detection_res.pixel_height,
        "estimated_ppm": detection_res.estimated_ppm,
        "marker_id": detection_res.marker_id,
        "dictionary": detection_res.dictionary,
        "message": detection_res.message,
    }

    updated_record = attach_inspection_image(
        inspection_id=inspection_id,
        view_type=normalized_view,
        image_bytes=image_bytes,
        original_filename=file.filename or f"{normalized_view}.jpg",
        marker_result=marker_dict,
    )

    return updated_record


@router.get(
    "/{inspection_id}/images/{view_type}",
    summary="Download or view captured package image",
)
def get_inspection_view_image(inspection_id: str, view_type: str):
    """Return the raw image file for a captured package view."""
    record = get_inspection_record(inspection_id)
    if not record:
        raise HTTPException(status_code=404, detail="Inspection not found.")

    images = record.get("images", {})
    image_meta = images.get(view_type.lower())
    if not image_meta or not os.path.exists(image_meta.get("filepath", "")):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image for view '{view_type}' not found on inspection '{inspection_id}'.",
        )

    return FileResponse(image_meta["filepath"], media_type="image/jpeg")


@router.get(
    "/{inspection_id}/images/{view_type}/processed",
    summary="Download or view enhanced preprocessed package image",
)
def get_inspection_processed_image(inspection_id: str, view_type: str):
    """Return the separate preprocessed, contrast-enhanced copy of a captured package view."""
    record = get_inspection_record(inspection_id)
    if not record:
        raise HTTPException(status_code=404, detail="Inspection not found.")

    images = record.get("images", {})
    image_meta = images.get(view_type.lower())
    if not image_meta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"View '{view_type}' not found on inspection '{inspection_id}'.",
        )

    preproc = image_meta.get("preprocessing")
    proc_path = (preproc.get("processed_filepath") or preproc.get("filepath", "")) if preproc else ""
    if not preproc or not proc_path or not os.path.exists(proc_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Preprocessed image for view '{view_type}' not found.",
        )

    return FileResponse(proc_path, media_type="image/jpeg")


@router.get(
    "/{inspection_id}/images/{view_type}/quality",
    summary="Get detailed image quality assessment for a view",
)
def get_inspection_image_quality(inspection_id: str, view_type: str):
    """Retrieve sharpness, exposure, contrast, resolution, and glare assessment for a captured view."""
    record = get_inspection_record(inspection_id)
    if not record:
        raise HTTPException(status_code=404, detail="Inspection not found.")

    images = record.get("images", {})
    image_meta = images.get(view_type.lower())
    if not image_meta or "quality_assessment" not in image_meta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quality assessment for view '{view_type}' not available.",
        )

    return image_meta["quality_assessment"]

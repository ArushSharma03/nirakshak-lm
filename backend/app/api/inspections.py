"""
Inspection API endpoints.

POST /inspections      — Create a new inspection.
GET  /inspections/{id} — Retrieve an inspection with its images.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Inspection, Product, InspectionStatus
from app.schemas import InspectionCreate, InspectionOut

router = APIRouter(prefix="/inspections", tags=["Inspections"])


@router.post(
    "/",
    response_model=InspectionOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new inspection",
)
def create_inspection(
    payload: InspectionCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new compliance-screening inspection.

    If product_name and product_category are provided, a Product record
    is created (or could be looked up) and linked to the inspection.
    """
    # Validate that the referenced user exists (lightweight check)
    from app.models import User

    user = db.get(User, payload.user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {payload.user_id} not found.",
        )

    # Optionally create a product record
    product_id = None
    if payload.product_name and payload.product_category:
        product = Product(
            name=payload.product_name,
            category=payload.product_category,
        )
        db.add(product)
        db.flush()  # populate product.id before we reference it
        product_id = product.id

    inspection = Inspection(
        user_id=payload.user_id,
        product_id=product_id,
        status=InspectionStatus.CREATED,
        notes=payload.notes,
    )
    db.add(inspection)
    db.commit()
    db.refresh(inspection)

    return inspection


@router.get(
    "/{inspection_id}",
    response_model=InspectionOut,
    summary="Retrieve an inspection",
)
def get_inspection(
    inspection_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """Retrieve an inspection by ID, including its images and product info."""
    inspection = db.get(Inspection, inspection_id)
    if inspection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inspection {inspection_id} not found.",
        )
    return inspection

"""
Pydantic schemas for the Inspection resource.

Uses Pydantic v2 conventions (model_config, ConfigDict).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.inspection import InspectionStatus, ComplianceOutcome
from app.models.package_image import ViewType, QualityStatus
from app.models.product import ProductCategory


# ---------------------------------------------------------------------------
# PackageImage schemas
# ---------------------------------------------------------------------------
class PackageImageOut(BaseModel):
    """Read-only representation of a package image."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    view_type: ViewType
    filepath: str
    original_filename: str
    file_hash: Optional[str] = None
    quality_status: QualityStatus
    scale_ppm: Optional[float] = None
    created_at: datetime


# ---------------------------------------------------------------------------
# Product schemas
# ---------------------------------------------------------------------------
class ProductBrief(BaseModel):
    """Minimal product info embedded inside an inspection response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    category: ProductCategory


# ---------------------------------------------------------------------------
# Inspection schemas
# ---------------------------------------------------------------------------
class InspectionCreate(BaseModel):
    """Payload for creating a new inspection."""

    user_id: uuid.UUID = Field(
        ..., description="ID of the inspector creating this inspection."
    )
    product_name: Optional[str] = Field(
        None, description="Generic product name (can be set later)."
    )
    product_category: Optional[ProductCategory] = Field(
        None, description="Product category."
    )
    notes: Optional[str] = None


class InspectionOut(BaseModel):
    """Full inspection response returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    product_id: Optional[uuid.UUID] = None
    status: InspectionStatus
    final_outcome: Optional[ComplianceOutcome] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    # Nested relations
    product: Optional[ProductBrief] = None
    images: list[PackageImageOut] = []


class InspectionSummary(BaseModel):
    """Lightweight listing representation (no nested images)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: InspectionStatus
    final_outcome: Optional[ComplianceOutcome] = None
    created_at: datetime

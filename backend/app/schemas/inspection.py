"""
Pydantic schemas for the Inspection resource.

Uses Pydantic v2 conventions (model_config, ConfigDict).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional, Any, Dict

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

    user_id: Optional[uuid.UUID] = Field(
        None, description="Optional ID of the inspector creating this inspection."
    )
    product_name: Optional[str] = Field(
        None, description="Generic product name."
    )
    product_category: Optional[str] = Field(
        None, description="Product category (food_grocery, beverage, personal_care, household)."
    )
    brand: Optional[str] = Field(
        None, description="Manufacturer or brand name."
    )
    declared_net_qty: Optional[str] = Field(
        None, description="Declared net quantity (e.g. 100 g, 500 ml)."
    )
    declared_mrp: Optional[float] = Field(
        None, description="Declared retail price (₹)."
    )
    location: Optional[str] = Field(
        None, description="Inspection location / retail bay."
    )
    inspector_name: Optional[str] = Field(
        None, description="Inspector full name."
    )
    views_captured: Optional[dict[str, bool]] = Field(
        default_factory=lambda: {"front": False, "rear": False, "side": False}
    )
    marker_detected: Optional[bool] = False
    scale_ppm: Optional[float] = None
    notes: Optional[str] = None


class InspectionRecordResponse(BaseModel):
    """Full comprehensive inspection record schema."""

    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: str
    product_name: str
    product_category: str
    brand: str
    declared_net_qty: str
    declared_mrp: float
    location: Optional[str] = None
    inspector_name: str
    status: str
    final_outcome: str
    notes: Optional[str] = None
    timestamp: str
    views_captured: dict[str, bool]
    marker_detected: bool
    scale_ppm: Optional[float] = None
    images: Optional[dict[str, Any]] = None
    database_saved: bool = False
    mode: str = "Demo / Offline Fallback"


class InspectionOut(BaseModel):
    """Full inspection response returned by the API."""

    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: Any
    user_id: Optional[Any] = None
    product_id: Optional[Any] = None
    status: Any
    final_outcome: Optional[Any] = None
    notes: Optional[str] = None
    created_at: Optional[Any] = None
    updated_at: Optional[Any] = None

    # Nested relations
    product: Optional[ProductBrief] = None
    images: list[PackageImageOut] = []


class InspectionSummary(BaseModel):
    """Lightweight listing representation (no nested images)."""

    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: Any
    status: Any
    final_outcome: Optional[Any] = None
    created_at: Optional[Any] = None

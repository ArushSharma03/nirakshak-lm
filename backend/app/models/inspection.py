"""
Inspection model.

Represents a single compliance-screening session.
An inspection is created by a user, optionally linked to a product,
and contains multiple PackageImage records (front, rear, side).

The final_outcome uses the three-level classification from the approved synopsis:
  - Compliant within Implemented Checks
  - Potential Non-Compliance
  - Manual Review Required
"""

import uuid
from datetime import datetime, timezone
import enum

from sqlalchemy import String, Text, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class InspectionStatus(str, enum.Enum):
    """Lifecycle status of an inspection."""

    CREATED = "created"
    IMAGES_UPLOADED = "images_uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ComplianceOutcome(str, enum.Enum):
    """Three-level compliance outcome per approved project synopsis."""

    COMPLIANT = "compliant_within_implemented_checks"
    POTENTIAL_NON_COMPLIANCE = "potential_non_compliance"
    MANUAL_REVIEW_REQUIRED = "manual_review_required"


class Inspection(Base):
    __tablename__ = "inspections"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )

    # --- Foreign keys ---
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), index=True
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("products.id"), nullable=True
    )

    # --- Status & outcome ---
    status: Mapped[InspectionStatus] = mapped_column(
        SAEnum(
            InspectionStatus,
            name="inspection_status",
            create_constraint=True,
        ),
        default=InspectionStatus.CREATED,
    )
    final_outcome: Mapped[ComplianceOutcome | None] = mapped_column(
        SAEnum(
            ComplianceOutcome,
            name="compliance_outcome",
            create_constraint=True,
        ),
        nullable=True,
    )

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # --- Relationships ---
    inspector: Mapped["User"] = relationship(
        back_populates="inspections", lazy="selectin"
    )
    product: Mapped["Product | None"] = relationship(
        back_populates="inspections", lazy="selectin"
    )
    images: Mapped[list["PackageImage"]] = relationship(
        back_populates="inspection", lazy="selectin",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Inspection {self.id} [{self.status.value}]>"


from app.models.user import User  # noqa: E402, F401
from app.models.product import Product  # noqa: E402, F401
from app.models.package_image import PackageImage  # noqa: E402, F401

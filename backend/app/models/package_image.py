"""
PackageImage model.

Represents a single captured/uploaded image of a package view.
Supports front, rear, and side views per the approved methodology.
"""

import uuid
from datetime import datetime, timezone
import enum

from sqlalchemy import String, Float, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ViewType(str, enum.Enum):
    """Package view orientation."""

    FRONT = "front"
    REAR = "rear"
    SIDE = "side"


class QualityStatus(str, enum.Enum):
    """Result of the image quality assessment."""

    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"


class PackageImage(Base):
    __tablename__ = "package_images"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )

    inspection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("inspections.id", ondelete="CASCADE"), index=True
    )

    view_type: Mapped[ViewType] = mapped_column(
        SAEnum(ViewType, name="view_type", create_constraint=True),
    )
    filepath: Mapped[str] = mapped_column(String(512))
    original_filename: Mapped[str] = mapped_column(String(255))

    # SHA-256 hash of the original file for evidence integrity
    file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    quality_status: Mapped[QualityStatus] = mapped_column(
        SAEnum(
            QualityStatus,
            name="quality_status",
            create_constraint=True,
        ),
        default=QualityStatus.PENDING,
    )

    # Pixels-per-mm scale from reference-marker calibration (set later)
    scale_ppm: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    # --- Relationships ---
    inspection: Mapped["Inspection"] = relationship(
        back_populates="images", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<PackageImage {self.view_type.value} for inspection {self.inspection_id}>"


from app.models.inspection import Inspection  # noqa: E402, F401

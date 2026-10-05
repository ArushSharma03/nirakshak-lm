"""
Product model.

Represents a packaged commodity being inspected.
Categories are aligned with the approved project synopsis.
"""

import uuid
from datetime import datetime, timezone
import enum

from sqlalchemy import String, Text, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ProductCategory(str, enum.Enum):
    """Supported product categories per approved synopsis."""

    FOOD_GROCERY = "food_grocery"
    BEVERAGE = "beverage"
    PERSONAL_CARE = "personal_care"
    HOUSEHOLD = "household"


class Product(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255))
    category: Mapped[ProductCategory] = mapped_column(
        SAEnum(
            ProductCategory,
            name="product_category",
            create_constraint=True,
        ),
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

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
    inspections: Mapped[list["Inspection"]] = relationship(
        back_populates="product", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Product {self.name} ({self.category.value})>"


from app.models.inspection import Inspection  # noqa: E402, F401

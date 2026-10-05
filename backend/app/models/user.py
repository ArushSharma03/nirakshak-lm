"""
User model.

Represents inspectors and administrators who use the system.
Authentication/password-hashing logic will be added in a later step.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Boolean, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.db.base import Base


class UserRole(str, enum.Enum):
    """Allowed user roles for RBAC."""

    INSPECTOR = "inspector"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="user_role", create_constraint=True),
        default=UserRole.INSPECTOR,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

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
        back_populates="inspector", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<User {self.email} ({self.role.value})>"


# Avoid circular import — Inspection is resolved by SQLAlchemy at runtime.
from app.models.inspection import Inspection  # noqa: E402, F401

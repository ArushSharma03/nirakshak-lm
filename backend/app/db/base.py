"""
SQLAlchemy declarative base.

All ORM models inherit from this Base class.
Alembic also imports it to discover models for auto-generation.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Application-wide declarative base for SQLAlchemy models."""

    pass

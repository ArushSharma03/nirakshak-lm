import pytest

from app.core.config import settings


@pytest.fixture(autouse=True)
def no_paid_jev_calls(monkeypatch):
    """A developer's backend/.env key must never reach tests; tests that need Jev set a fake key."""
    monkeypatch.setattr(settings, "TYPESAFE_API_KEY", None)

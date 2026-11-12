"""
Application settings loaded from environment variables.

Uses pydantic-settings to provide typed, validated configuration.
"""

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Application ---
    APP_NAME: str = "Nirikshak-LM"
    APP_ENV: str = "development"
    DEBUG: bool = True
    XIAOMI_OCR_ENABLED: bool = True
    OCR_DEVICE: str = "cpu"
    OCR_MAX_TOKENS: int = 1024
    TESSERACT_LANGUAGES: str = "eng"
    TYPESAFE_API_KEY: SecretStr | None = None
    TYPESAFE_MODEL: str = "jev-1.14.0"

    # --- Server ---
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000

    # --- Database ---
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/nirikshak_lm"

    # --- CORS ---
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",  # Next.js dev server
    ]


settings = Settings()

"""
Application settings loaded from environment variables.

Uses pydantic-settings to provide typed, validated configuration.
"""

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

    # --- Server ---
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000

    # --- CORS ---
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",  # Next.js dev server
    ]


settings = Settings()

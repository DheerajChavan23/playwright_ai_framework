"""Centralized settings and environment variables management."""

import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment or .env file."""

    gemini_api_key: str = "[ENCRYPTION_KEY]"
    gemini_model: str = "gemini-2.5-flash"
    default_headless: bool = True

    max_healing_attempts: int = 3
    page_timeout: int = 30000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

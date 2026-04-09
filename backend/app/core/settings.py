"""Runtime settings."""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    """Application settings sourced from environment variables."""

    app_env: str
    app_name: str
    host: str
    port: int
    database_url: str
    anthropic_api_key: str
    upload_dir: Path
    max_upload_bytes: int


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Load application settings."""
    return Settings(
        app_env=os.getenv("APP_ENV", "development"),
        app_name=os.getenv("APP_NAME", "invoice-journal-entry"),
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
        database_url=os.getenv(
            "DATABASE_URL", "postgresql://app:app@localhost:5432/app"
        ),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        upload_dir=Path(os.getenv("UPLOAD_DIR", "backend/data/uploads")),
        max_upload_bytes=int(os.getenv("MAX_UPLOAD_BYTES", str(10 * 1024 * 1024))),
    )

"""FastAPI dependency providers."""
from __future__ import annotations

from fastapi import Request

from backend.app.core.repository import AppRepository
from backend.app.core.settings import Settings


def get_repository(request: Request) -> AppRepository:
    """Return application repository from app state."""
    repository = request.app.state.repository
    if not isinstance(repository, AppRepository):
        raise RuntimeError("Repository is not configured")
    return repository


def get_settings(request: Request) -> Settings:
    """Return settings from app state."""
    settings = request.app.state.settings
    if not isinstance(settings, Settings):
        raise RuntimeError("Settings are not configured")
    return settings

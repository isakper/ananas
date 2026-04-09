"""FastAPI dependency providers."""

from __future__ import annotations

from fastapi import Request

from backend.app.core.repository import AppRepository
from backend.app.core.settings import Settings
from backend.app.workflows.journal_generation import JournalGenerationWorkflow


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


def get_journal_generation_workflow(request: Request) -> JournalGenerationWorkflow:
    """Return journal generation workflow from app state."""
    workflow = request.app.state.journal_generation_workflow
    if not isinstance(workflow, JournalGenerationWorkflow):
        raise RuntimeError("Journal generation workflow is not configured")
    return workflow

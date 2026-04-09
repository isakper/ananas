"""FastAPI application entrypoint."""
from __future__ import annotations

from fastapi import FastAPI

from backend.app.api.routes.accounts import router as accounts_router
from backend.app.api.routes.invoices import router as invoices_router
from backend.app.api.routes.journal_entries import router as journal_entries_router
from backend.app.api.schemas import HealthResponse
from backend.app.core.db import Database
from backend.app.core.repository import AppRepository
from backend.app.core.settings import get_settings

settings = get_settings()
database = Database(settings.database_url)
repository = AppRepository(database)

app = FastAPI(title=settings.app_name)
app.state.settings = settings
app.state.repository = repository

app.include_router(accounts_router)
app.include_router(invoices_router)
app.include_router(journal_entries_router)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Basic liveness endpoint."""
    return HealthResponse(status="ok")

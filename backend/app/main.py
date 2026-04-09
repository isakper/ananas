"""FastAPI application entrypoint."""

from __future__ import annotations

from fastapi import FastAPI

from backend.app.accounting.journal_generation_service import JournalGenerationService
from backend.app.accounting.journal_suggester import LlmJournalSuggester
from backend.app.api.routes.accounts import router as accounts_router
from backend.app.api.routes.invoices import router as invoices_router
from backend.app.api.routes.journal_entries import router as journal_entries_router
from backend.app.api.schemas import HealthResponse
from backend.app.core.db import Database
from backend.app.core.repository import AppRepository
from backend.app.core.settings import get_settings
from backend.app.documents.markdown_extractor import MarkdownExtractor
from backend.app.documents.service import DocumentExtractionService
from backend.app.integrations.llm.client import AnthropicLlmGateway, StubLlmGateway
from backend.app.workflows.journal_generation import JournalGenerationWorkflow

settings = get_settings()
database = Database(settings.database_url)
repository = AppRepository(database)
if settings.anthropic_api_key.strip() == "":
    llm_gateway = StubLlmGateway()
else:
    llm_gateway = AnthropicLlmGateway(
        api_key=settings.anthropic_api_key,
        model=settings.llm_model,
    )
document_extraction_service = DocumentExtractionService(
    markdown_extractor=MarkdownExtractor(llm_gateway=llm_gateway),
)
journal_generation_service = JournalGenerationService(
    suggester=LlmJournalSuggester(llm_gateway=llm_gateway)
)
journal_generation_workflow = JournalGenerationWorkflow(
    repository=repository,
    extraction_service=document_extraction_service,
    journal_generation_service=journal_generation_service,
)

app = FastAPI(title=settings.app_name)
app.state.settings = settings
app.state.repository = repository
app.state.journal_generation_workflow = journal_generation_workflow

app.include_router(accounts_router)
app.include_router(invoices_router)
app.include_router(journal_entries_router)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Basic liveness endpoint."""
    return HealthResponse(status="ok")

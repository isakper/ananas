"""Workflow for generating suggested journal entries."""
from __future__ import annotations

from pathlib import Path
from uuid import UUID

from backend.app.accounting.journal_generation_service import JournalGenerationService
from backend.app.core.records import InvoiceBundleRecord
from backend.app.core.repository import AppRepository
from backend.app.documents.service import DocumentExtractionService


class InvoiceNotFoundError(Exception):
    """Raised when a workflow references a missing invoice."""


class JournalGenerationWorkflow:
    """Orchestrates extraction and journal suggestion generation."""

    def __init__(
        self,
        repository: AppRepository,
        extraction_service: DocumentExtractionService,
        journal_generation_service: JournalGenerationService,
    ) -> None:
        self._repository = repository
        self._extraction_service = extraction_service
        self._journal_generation_service = journal_generation_service

    def run(self, invoice_id: UUID) -> InvoiceBundleRecord:
        """Generate a journal entry suggestion for an uploaded invoice."""
        invoice = self._repository.get_invoice(invoice_id)
        if invoice is None:
            raise InvoiceNotFoundError("Invoice not found")

        markdown = self._extraction_service.extract_markdown(
            pdf_path=Path(invoice.file_path)
        )
        self._repository.save_invoice_markdown(invoice_id=invoice.id, markdown=markdown)

        accounts = [account for account in self._repository.list_accounts() if account.is_active]
        postings = self._journal_generation_service.generate_postings(
            markdown=markdown,
            accounts=accounts,
        )
        self._repository.replace_suggested_journal_entry(
            invoice_id=invoice.id,
            postings=postings,
        )

        bundle = self._repository.get_invoice_bundle(invoice.id)
        if bundle is None:
            raise ValueError("Failed to load generated invoice")
        return bundle

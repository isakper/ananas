"""Workflow for generating suggested journal entries."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol
from uuid import UUID

from backend.app.accounting.types import SuggestedPosting
from backend.app.core.records import AccountRecord, InvoiceBundleRecord, InvoiceRecord


class Repository(Protocol):
    def get_invoice(self, invoice_id: UUID) -> InvoiceRecord | None: ...
    def mark_invoice_generation_started(self, invoice_id: UUID) -> bool: ...
    def save_invoice_markdown(
        self, invoice_id: UUID, markdown: str
    ) -> InvoiceRecord | None: ...
    def list_accounts(self) -> list[AccountRecord]: ...
    def replace_suggested_journal_entry(
        self, invoice_id: UUID, postings: list[SuggestedPosting]
    ) -> object: ...
    def mark_invoice_generation_ready(self, invoice_id: UUID) -> bool: ...
    def mark_invoice_generation_failed(self, invoice_id: UUID, error: str) -> bool: ...
    def get_invoice_bundle(self, invoice_id: UUID) -> InvoiceBundleRecord | None: ...


class ExtractionService(Protocol):
    def extract_markdown(self, pdf_path: Path) -> str: ...


class PostingGenerationService(Protocol):
    def generate_postings(
        self, markdown: str, accounts: list[AccountRecord]
    ) -> list[SuggestedPosting]: ...


class InvoiceNotFoundError(Exception):
    """Raised when a workflow references a missing invoice."""


class JournalGenerationWorkflow:
    """Orchestrates extraction and journal suggestion generation."""

    def __init__(
        self,
        repository: Repository,
        extraction_service: ExtractionService,
        journal_generation_service: PostingGenerationService,
    ) -> None:
        self._repository = repository
        self._extraction_service = extraction_service
        self._journal_generation_service = journal_generation_service

    def run(self, invoice_id: UUID) -> InvoiceBundleRecord:
        """Generate a journal entry suggestion for an uploaded invoice."""
        invoice = self._repository.get_invoice(invoice_id)
        if invoice is None:
            raise InvoiceNotFoundError("Invoice not found")

        marked_generating = self._repository.mark_invoice_generation_started(invoice.id)
        if not marked_generating:
            raise InvoiceNotFoundError("Invoice not found")

        try:
            markdown = self._extraction_service.extract_markdown(
                pdf_path=Path(invoice.file_path)
            )
            self._repository.save_invoice_markdown(
                invoice_id=invoice.id,
                markdown=markdown,
            )

            accounts = [
                account
                for account in self._repository.list_accounts()
                if account.is_active
            ]
            postings = self._journal_generation_service.generate_postings(
                markdown=markdown,
                accounts=accounts,
            )
            self._repository.replace_suggested_journal_entry(
                invoice_id=invoice.id,
                postings=postings,
            )
            self._repository.mark_invoice_generation_ready(invoice.id)
        except Exception as exc:
            self._repository.mark_invoice_generation_failed(
                invoice.id,
                str(exc),
            )
            raise

        bundle = self._repository.get_invoice_bundle(invoice.id)
        if bundle is None:
            raise ValueError("Failed to load generated invoice")
        return bundle

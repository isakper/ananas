"""Tests for generation workflow status transitions."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from backend.app.accounting.types import SuggestedPosting
from backend.app.core.records import (
    AccountRecord,
    InvoiceBundleRecord,
    InvoiceRecord,
    JournalEntryRecord,
    JournalPostingRecord,
)
from backend.app.workflows.journal_generation import (
    InvoiceNotFoundError,
    JournalGenerationWorkflow,
)


class _RepoStub:
    """Small in-memory repository stub for workflow tests."""

    def __init__(self, invoice: InvoiceRecord | None) -> None:
        self.invoice = invoice
        self.started = False
        self.ready = False
        self.failed_error: str | None = None

    def get_invoice(self, invoice_id: UUID) -> InvoiceRecord | None:
        if self.invoice is None:
            return None
        if self.invoice.id != invoice_id:
            return None
        return self.invoice

    def mark_invoice_generation_started(self, invoice_id: UUID) -> bool:
        if self.invoice is None or self.invoice.id != invoice_id:
            return False
        self.started = True
        return True

    def save_invoice_markdown(self, invoice_id: UUID, markdown: str) -> InvoiceRecord | None:
        if self.invoice is None or self.invoice.id != invoice_id:
            return None
        self.invoice = InvoiceRecord(
            id=self.invoice.id,
            original_filename=self.invoice.original_filename,
            mime_type=self.invoice.mime_type,
            file_path=self.invoice.file_path,
            extracted_text=markdown,
            generation_status=self.invoice.generation_status,
            generation_error=self.invoice.generation_error,
            generated_at=self.invoice.generated_at,
            created_at=self.invoice.created_at,
            updated_at=self.invoice.updated_at,
        )
        return self.invoice

    def list_accounts(self) -> list[AccountRecord]:
        now = datetime.now(tz=UTC)
        return [
            AccountRecord(
                id=uuid4(),
                code=6530,
                name="IT",
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            AccountRecord(
                id=uuid4(),
                code=2440,
                name="AP",
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
        ]

    def replace_suggested_journal_entry(
        self, invoice_id: UUID, postings: list[SuggestedPosting]
    ) -> JournalEntryRecord:
        _ = invoice_id
        now = datetime.now(tz=UTC)
        mapped_postings = [
            JournalPostingRecord(
                id=uuid4(),
                journal_entry_id=uuid4(),
                line_no=index + 1,
                account_id=posting.account_id,
                account_code_snapshot=posting.account_code,
                account_name_snapshot=posting.account_name,
                description=posting.description,
                debit_amount=posting.debit_amount,
                credit_amount=posting.credit_amount,
                created_at=now,
            )
            for index, posting in enumerate(postings)
        ]
        return JournalEntryRecord(
            id=uuid4(),
            invoice_id=self.invoice.id if self.invoice is not None else uuid4(),
            status="pending",
            currency="SEK",
            total_debit=Decimal("1000.00"),
            total_credit=Decimal("1000.00"),
            decided_at=None,
            decision_reason=None,
            created_at=now,
            updated_at=now,
            postings=mapped_postings,
        )

    def mark_invoice_generation_ready(self, invoice_id: UUID) -> bool:
        if self.invoice is None or self.invoice.id != invoice_id:
            return False
        self.ready = True
        return True

    def mark_invoice_generation_failed(self, invoice_id: UUID, error: str) -> bool:
        if self.invoice is None or self.invoice.id != invoice_id:
            return False
        self.failed_error = error
        return True

    def get_invoice_bundle(self, invoice_id: UUID) -> InvoiceBundleRecord | None:
        if self.invoice is None or self.invoice.id != invoice_id:
            return None
        now = datetime.now(tz=UTC)
        entry = JournalEntryRecord(
            id=uuid4(),
            invoice_id=invoice_id,
            status="pending",
            currency="SEK",
            total_debit=Decimal("1000.00"),
            total_credit=Decimal("1000.00"),
            decided_at=None,
            decision_reason=None,
            created_at=now,
            updated_at=now,
            postings=[],
        )
        return InvoiceBundleRecord(invoice=self.invoice, journal_entry=entry)


class _ExtractionServiceStub:
    def __init__(self, markdown: str = "# Invoice", raises: Exception | None = None) -> None:
        self.markdown = markdown
        self.raises = raises

    def extract_markdown(self, pdf_path: Path) -> str:
        _ = pdf_path
        if self.raises is not None:
            raise self.raises
        return self.markdown


class _GenerationServiceStub:
    def generate_postings(
        self, markdown: str, accounts: list[AccountRecord]
    ) -> list[SuggestedPosting]:
        _ = markdown
        return [
            SuggestedPosting(
                account_id=accounts[0].id,
                account_code=accounts[0].code,
                account_name=accounts[0].name,
                description="Debit",
                debit_amount=Decimal("1000.00"),
                credit_amount=Decimal("0.00"),
            ),
            SuggestedPosting(
                account_id=accounts[1].id,
                account_code=accounts[1].code,
                account_name=accounts[1].name,
                description="Credit",
                debit_amount=Decimal("0.00"),
                credit_amount=Decimal("1000.00"),
            ),
        ]


def _invoice() -> InvoiceRecord:
    now = datetime.now(tz=UTC)
    return InvoiceRecord(
        id=uuid4(),
        original_filename="invoice.pdf",
        mime_type="application/pdf",
        file_path="/tmp/invoice.pdf",
        extracted_text=None,
        generation_status="uploaded",
        generation_error=None,
        generated_at=None,
        created_at=now,
        updated_at=now,
    )


def test_workflow_marks_ready_on_success() -> None:
    invoice = _invoice()
    repo = _RepoStub(invoice=invoice)
    workflow = JournalGenerationWorkflow(
        repository=repo,
        extraction_service=_ExtractionServiceStub(),
        journal_generation_service=_GenerationServiceStub(),
    )

    bundle = workflow.run(invoice.id)

    assert bundle.invoice.id == invoice.id
    assert repo.started is True
    assert repo.ready is True
    assert repo.failed_error is None


def test_workflow_marks_failed_on_exception() -> None:
    invoice = _invoice()
    repo = _RepoStub(invoice=invoice)
    workflow = JournalGenerationWorkflow(
        repository=repo,
        extraction_service=_ExtractionServiceStub(raises=ValueError("parse failed")),
        journal_generation_service=_GenerationServiceStub(),
    )

    with pytest.raises(ValueError, match="parse failed"):
        workflow.run(invoice.id)

    assert repo.started is True
    assert repo.ready is False
    assert repo.failed_error is not None
    assert "parse failed" in repo.failed_error


def test_workflow_raises_for_missing_invoice() -> None:
    workflow = JournalGenerationWorkflow(
        repository=_RepoStub(invoice=None),
        extraction_service=_ExtractionServiceStub(),
        journal_generation_service=_GenerationServiceStub(),
    )

    with pytest.raises(InvoiceNotFoundError):
        workflow.run(uuid4())

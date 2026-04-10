"""Pydantic API schemas."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal, cast
from uuid import UUID

from pydantic import BaseModel

from backend.app.core.records import (
    AccountRecord,
    InvoiceBundleRecord,
    InvoiceRecord,
    JournalEntryRecord,
    JournalPostingRecord,
)


class AccountResponse(BaseModel):
    """Account output for API responses."""

    id: UUID
    code: int
    name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_record(cls, record: AccountRecord) -> "AccountResponse":
        return cls(**record.__dict__)


class AccountCreateRequest(BaseModel):
    """Payload for creating an account."""

    code: int
    name: str


class AccountUpdateRequest(BaseModel):
    """Payload for updating an account."""

    code: int | None = None
    name: str | None = None
    is_active: bool | None = None


class AccountSnapshotItemRequest(BaseModel):
    """One account item in a bulk snapshot save payload."""

    code: int
    name: str


class AccountBulkSaveRequest(BaseModel):
    """Payload for atomically saving the active chart of accounts."""

    accounts: list[AccountSnapshotItemRequest]


class JournalPostingResponse(BaseModel):
    """Journal posting output model."""

    id: UUID
    journal_entry_id: UUID
    line_no: int
    account_id: UUID
    account_code_snapshot: int
    account_name_snapshot: str
    description: str | None
    debit_amount: Decimal
    credit_amount: Decimal
    created_at: datetime

    @classmethod
    def from_record(cls, record: JournalPostingRecord) -> "JournalPostingResponse":
        return cls(**record.__dict__)


class JournalEntryResponse(BaseModel):
    """Journal entry output model."""

    id: UUID
    invoice_id: UUID
    status: Literal["pending", "approved", "declined"]
    currency: str
    total_debit: Decimal
    total_credit: Decimal
    decided_at: datetime | None
    decision_reason: str | None
    created_at: datetime
    updated_at: datetime
    postings: list[JournalPostingResponse]

    @classmethod
    def from_record(cls, record: JournalEntryRecord) -> "JournalEntryResponse":
        return cls(
            id=record.id,
            invoice_id=record.invoice_id,
            status=cast(Literal["pending", "approved", "declined"], record.status),
            currency=record.currency,
            total_debit=record.total_debit,
            total_credit=record.total_credit,
            decided_at=record.decided_at,
            decision_reason=record.decision_reason,
            created_at=record.created_at,
            updated_at=record.updated_at,
            postings=[
                JournalPostingResponse.from_record(posting)
                for posting in record.postings
            ],
        )


class InvoiceResponse(BaseModel):
    """Invoice output model."""

    id: UUID
    original_filename: str
    mime_type: str
    file_path: str
    content_hash: str | None
    duplicate_of_invoice_id: UUID | None
    extracted_text: str | None
    generation_status: Literal["uploaded", "generating", "ready", "failed"]
    generation_error: str | None
    generated_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_record(cls, record: InvoiceRecord) -> "InvoiceResponse":
        return cls(**record.__dict__)


class InvoiceBundleResponse(BaseModel):
    """Invoice + journal entry output model."""

    invoice: InvoiceResponse
    journal_entry: JournalEntryResponse | None

    @classmethod
    def from_record(cls, record: InvoiceBundleRecord) -> "InvoiceBundleResponse":
        journal_entry: JournalEntryResponse | None
        if record.journal_entry is None:
            journal_entry = None
        else:
            journal_entry = JournalEntryResponse.from_record(record.journal_entry)
        return cls(
            invoice=InvoiceResponse.from_record(record.invoice),
            journal_entry=journal_entry,
        )


class DeclineRequest(BaseModel):
    """Payload for declining a journal entry."""

    reason: str | None = None


class JournalPostingUpdateRequest(BaseModel):
    """Editable posting payload for journal entry updates."""

    account_id: UUID
    description: str | None = None
    debit_amount: Decimal
    credit_amount: Decimal


class JournalEntryUpdateRequest(BaseModel):
    """Payload for replacing posting lines on a pending journal entry."""

    postings: list[JournalPostingUpdateRequest]


class HealthResponse(BaseModel):
    """Simple health response."""

    status: str

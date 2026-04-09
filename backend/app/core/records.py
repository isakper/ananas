"""Typed records for API responses."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True)
class AccountRecord:
    """Chart of accounts row."""

    id: UUID
    code: int
    name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class InvoiceRecord:
    """Uploaded invoice row."""

    id: UUID
    original_filename: str
    mime_type: str
    file_path: str
    extracted_text: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class JournalPostingRecord:
    """Journal posting row."""

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


@dataclass(frozen=True)
class JournalEntryRecord:
    """Journal entry with postings."""

    id: UUID
    invoice_id: UUID
    status: str
    currency: str
    total_debit: Decimal
    total_credit: Decimal
    decided_at: datetime | None
    decision_reason: str | None
    created_at: datetime
    updated_at: datetime
    postings: list[JournalPostingRecord]


@dataclass(frozen=True)
class InvoiceBundleRecord:
    """Invoice and its related journal entry."""

    invoice: InvoiceRecord
    journal_entry: JournalEntryRecord

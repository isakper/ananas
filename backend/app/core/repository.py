"""Repository methods for invoice and journal-entry workflows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from psycopg.rows import dict_row

from backend.app.accounting.service import PostingAmounts, calculate_totals, is_balanced
from backend.app.accounting.types import SuggestedPosting
from backend.app.core.db import Database
from backend.app.core.records import (
    AccountRecord,
    InvoiceBundleRecord,
    InvoiceRecord,
    JournalEntryRecord,
    JournalPostingRecord,
)


@dataclass(frozen=True)
class PostingCreate:
    """Input structure for inserting posting lines."""

    line_no: int
    account_id: UUID
    account_code_snapshot: int
    account_name_snapshot: str
    description: str | None
    debit_amount: Decimal
    credit_amount: Decimal


class AppRepository:
    """PostgreSQL repository for core take-home workflows."""

    def __init__(self, database: Database) -> None:
        self._database = database

    def list_accounts(self) -> list[AccountRecord]:
        """List all chart-of-accounts rows."""
        with self._database.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT id, code, name, is_active, created_at, updated_at
                    FROM accounts
                    ORDER BY code
                    """
                )
                rows = cur.fetchall()
        return [_account_from_row(row) for row in rows]

    def create_invoice(
        self,
        original_filename: str,
        mime_type: str,
        file_path: str,
    ) -> InvoiceRecord:
        """Create and return an uploaded invoice row."""
        with self._database.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    INSERT INTO invoices (original_filename, mime_type, file_path, extracted_text)
                    VALUES (%s, %s, %s, NULL)
                    RETURNING id, original_filename, mime_type, file_path, extracted_text, created_at, updated_at
                    """,
                    (original_filename, mime_type, file_path),
                )
                invoice_row = cur.fetchone()
                if invoice_row is None:
                    raise ValueError("Failed to create invoice")
                return _invoice_from_row(invoice_row)

    def get_invoice(self, invoice_id: UUID) -> InvoiceRecord | None:
        """Return invoice row by id."""
        with self._database.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT id, original_filename, mime_type, file_path, extracted_text, created_at, updated_at
                    FROM invoices
                    WHERE id = %s
                    """,
                    (invoice_id,),
                )
                row = cur.fetchone()
        if row is None:
            return None
        return _invoice_from_row(row)

    def get_invoice_bundle(self, invoice_id: UUID) -> InvoiceBundleRecord | None:
        """Return invoice and journal entry details for the review screen."""
        with self._database.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT id, original_filename, mime_type, file_path, extracted_text, created_at, updated_at
                    FROM invoices
                    WHERE id = %s
                    """,
                    (invoice_id,),
                )
                invoice_row = cur.fetchone()
                if invoice_row is None:
                    return None
                invoice = _invoice_from_row(invoice_row)

                cur.execute(
                    """
                    SELECT id, invoice_id, status, currency, total_debit, total_credit, decided_at, decision_reason, created_at, updated_at
                    FROM journal_entries
                    WHERE invoice_id = %s
                    """,
                    (invoice.id,),
                )
                entry_row = cur.fetchone()
                if entry_row is None:
                    return InvoiceBundleRecord(invoice=invoice, journal_entry=None)
                postings = self._load_postings_for_entry(cur, _uuid(entry_row["id"]))
                entry = _journal_entry_from_row(entry_row, postings)

        return InvoiceBundleRecord(invoice=invoice, journal_entry=entry)

    def save_invoice_markdown(
        self, invoice_id: UUID, markdown: str
    ) -> InvoiceRecord | None:
        """Persist extracted markdown for an existing invoice."""
        with self._database.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    UPDATE invoices
                    SET extracted_text = %s
                    WHERE id = %s
                    RETURNING id, original_filename, mime_type, file_path, extracted_text, created_at, updated_at
                    """,
                    (markdown, invoice_id),
                )
                row = cur.fetchone()
        if row is None:
            return None
        return _invoice_from_row(row)

    def replace_suggested_journal_entry(
        self, invoice_id: UUID, postings: list[SuggestedPosting]
    ) -> JournalEntryRecord:
        """Create or replace pending journal suggestion for an invoice."""
        if len(postings) == 0:
            raise ValueError("Suggested journal entry requires at least one posting")

        amounts = [
            PostingAmounts(debit=posting.debit_amount, credit=posting.credit_amount)
            for posting in postings
        ]
        if not is_balanced(amounts):
            raise ValueError("Suggested journal entry is not balanced")
        total_debit, total_credit = calculate_totals(amounts)

        with self._database.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT id
                    FROM journal_entries
                    WHERE invoice_id = %s
                    """,
                    (invoice_id,),
                )
                existing_row = cur.fetchone()

                if existing_row is None:
                    cur.execute(
                        """
                        INSERT INTO journal_entries (
                            invoice_id,
                            status,
                            currency,
                            total_debit,
                            total_credit,
                            decided_at,
                            decision_reason
                        )
                        VALUES (%s, 'pending', 'SEK', %s, %s, NULL, NULL)
                        RETURNING id, invoice_id, status, currency, total_debit, total_credit, decided_at, decision_reason, created_at, updated_at
                        """,
                        (invoice_id, total_debit, total_credit),
                    )
                    entry_row = cur.fetchone()
                    if entry_row is None:
                        raise ValueError("Failed to create journal entry")
                    entry_id = _uuid(entry_row["id"])
                else:
                    entry_id = _uuid(existing_row["id"])
                    cur.execute(
                        """
                        DELETE FROM journal_postings
                        WHERE journal_entry_id = %s
                        """,
                        (entry_id,),
                    )
                    cur.execute(
                        """
                        UPDATE journal_entries
                        SET status = 'pending',
                            currency = 'SEK',
                            total_debit = %s,
                            total_credit = %s,
                            decided_at = NULL,
                            decision_reason = NULL
                        WHERE id = %s
                        RETURNING id, invoice_id, status, currency, total_debit, total_credit, decided_at, decision_reason, created_at, updated_at
                        """,
                        (total_debit, total_credit, entry_id),
                    )
                    entry_row = cur.fetchone()
                    if entry_row is None:
                        raise ValueError("Failed to update journal entry")

                posting_rows = [
                    PostingCreate(
                        line_no=index + 1,
                        account_id=posting.account_id,
                        account_code_snapshot=posting.account_code,
                        account_name_snapshot=posting.account_name,
                        description=posting.description,
                        debit_amount=posting.debit_amount,
                        credit_amount=posting.credit_amount,
                    )
                    for index, posting in enumerate(postings)
                ]
                self._insert_postings(cur, entry_id, posting_rows)
                loaded_postings = self._load_postings_for_entry(cur, entry_id)
                return _journal_entry_from_row(entry_row, loaded_postings)

    def decide_journal_entry(
        self, journal_entry_id: UUID, status: str, reason: str | None
    ) -> JournalEntryRecord | None:
        """Set journal entry status to approved or declined."""
        if status not in {"approved", "declined"}:
            raise ValueError("Unsupported status")

        with self._database.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT id, invoice_id, status, currency, total_debit, total_credit, decided_at, decision_reason, created_at, updated_at
                    FROM journal_entries
                    WHERE id = %s
                    """,
                    (journal_entry_id,),
                )
                current_entry_row = cur.fetchone()
                if current_entry_row is None:
                    return None

                postings = self._load_postings_for_entry(cur, journal_entry_id)
                if len(postings) == 0:
                    raise ValueError("Journal entry has no postings")

                if status == "approved":
                    self._validate_accounts_for_postings(cur, postings)
                    amounts = [
                        PostingAmounts(
                            debit=posting.debit_amount, credit=posting.credit_amount
                        )
                        for posting in postings
                    ]
                    if not is_balanced(amounts):
                        raise ValueError("Journal entry is not balanced")
                    total_debit, total_credit = calculate_totals(amounts)
                else:
                    total_debit = Decimal(current_entry_row["total_debit"])
                    total_credit = Decimal(current_entry_row["total_credit"])

                cur.execute(
                    """
                    UPDATE journal_entries
                    SET status = %s,
                        decision_reason = %s,
                        decided_at = NOW(),
                        total_debit = %s,
                        total_credit = %s
                    WHERE id = %s
                    RETURNING id, invoice_id, status, currency, total_debit, total_credit, decided_at, decision_reason, created_at, updated_at
                    """,
                    (
                        status,
                        reason,
                        total_debit,
                        total_credit,
                        journal_entry_id,
                    ),
                )
                updated_row = cur.fetchone()
                if updated_row is None:
                    return None
                updated_postings = self._load_postings_for_entry(cur, journal_entry_id)
                return _journal_entry_from_row(updated_row, updated_postings)

    def _insert_postings(
        self, cur: Any, journal_entry_id: UUID, postings: list[PostingCreate]
    ) -> None:
        for posting in postings:
            cur.execute(
                """
                INSERT INTO journal_postings (
                  journal_entry_id, line_no, account_id, account_code_snapshot, account_name_snapshot,
                  description, debit_amount, credit_amount
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    journal_entry_id,
                    posting.line_no,
                    posting.account_id,
                    posting.account_code_snapshot,
                    posting.account_name_snapshot,
                    posting.description,
                    posting.debit_amount,
                    posting.credit_amount,
                ),
            )

    def _load_postings_for_entry(
        self, cur: Any, journal_entry_id: UUID
    ) -> list[JournalPostingRecord]:
        cur.execute(
            """
            SELECT id, journal_entry_id, line_no, account_id, account_code_snapshot, account_name_snapshot,
                   description, debit_amount, credit_amount, created_at
            FROM journal_postings
            WHERE journal_entry_id = %s
            ORDER BY line_no
            """,
            (journal_entry_id,),
        )
        rows = cur.fetchall()
        return [_posting_from_row(row) for row in rows]

    def _validate_accounts_for_postings(
        self, cur: Any, postings: list[JournalPostingRecord]
    ) -> None:
        account_ids = [posting.account_id for posting in postings]
        cur.execute(
            """
            SELECT COUNT(*) AS valid_count
            FROM accounts
            WHERE id = ANY(%s::uuid[]) AND is_active = TRUE
            """,
            (account_ids,),
        )
        row = cur.fetchone()
        if row is None:
            raise ValueError("Could not validate account references")
        valid_count = _int(row["valid_count"])
        if valid_count != len(account_ids):
            raise ValueError("Journal entry references missing or inactive accounts")


def _account_from_row(row: dict[str, Any]) -> AccountRecord:
    return AccountRecord(
        id=_uuid(row["id"]),
        code=_int(row["code"]),
        name=_str(row["name"]),
        is_active=_bool(row["is_active"]),
        created_at=_datetime(row["created_at"]),
        updated_at=_datetime(row["updated_at"]),
    )


def _invoice_from_row(row: dict[str, Any]) -> InvoiceRecord:
    extracted: str | None
    extracted_raw = row["extracted_text"]
    if extracted_raw is None:
        extracted = None
    else:
        extracted = _str(extracted_raw)
    return InvoiceRecord(
        id=_uuid(row["id"]),
        original_filename=_str(row["original_filename"]),
        mime_type=_str(row["mime_type"]),
        file_path=_str(row["file_path"]),
        extracted_text=extracted,
        created_at=_datetime(row["created_at"]),
        updated_at=_datetime(row["updated_at"]),
    )


def _posting_from_row(row: dict[str, Any]) -> JournalPostingRecord:
    description: str | None
    description_raw = row["description"]
    if description_raw is None:
        description = None
    else:
        description = _str(description_raw)
    return JournalPostingRecord(
        id=_uuid(row["id"]),
        journal_entry_id=_uuid(row["journal_entry_id"]),
        line_no=_int(row["line_no"]),
        account_id=_uuid(row["account_id"]),
        account_code_snapshot=_int(row["account_code_snapshot"]),
        account_name_snapshot=_str(row["account_name_snapshot"]),
        description=description,
        debit_amount=_decimal(row["debit_amount"]),
        credit_amount=_decimal(row["credit_amount"]),
        created_at=_datetime(row["created_at"]),
    )


def _journal_entry_from_row(
    row: dict[str, Any], postings: list[JournalPostingRecord]
) -> JournalEntryRecord:
    decided_at_raw = row["decided_at"]
    decision_reason_raw = row["decision_reason"]
    decided_at = None if decided_at_raw is None else _datetime(decided_at_raw)
    decision_reason = None if decision_reason_raw is None else _str(decision_reason_raw)
    return JournalEntryRecord(
        id=_uuid(row["id"]),
        invoice_id=_uuid(row["invoice_id"]),
        status=_str(row["status"]),
        currency=_str(row["currency"]),
        total_debit=_decimal(row["total_debit"]),
        total_credit=_decimal(row["total_credit"]),
        decided_at=decided_at,
        decision_reason=decision_reason,
        created_at=_datetime(row["created_at"]),
        updated_at=_datetime(row["updated_at"]),
        postings=postings,
    )


def _uuid(value: Any) -> UUID:
    if isinstance(value, UUID):
        return value
    raise ValueError("Expected UUID value")


def _int(value: Any) -> int:
    if isinstance(value, int):
        return value
    raise ValueError("Expected integer value")


def _str(value: Any) -> str:
    if isinstance(value, str):
        return value
    raise ValueError("Expected string value")


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    raise ValueError("Expected boolean value")


def _decimal(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    raise ValueError("Expected decimal value")


def _datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    raise ValueError("Expected datetime value")

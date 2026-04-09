"""Repository methods for invoice and journal-entry workflows."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from psycopg.rows import dict_row

from backend.app.accounting.service import (
    AccountChoice,
    PostingAmounts,
    choose_default_accounts,
    calculate_totals,
    is_balanced,
)
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

    def create_invoice_with_stub_entry(
        self,
        original_filename: str,
        mime_type: str,
        file_path: str,
        extracted_text: str | None,
    ) -> InvoiceBundleRecord:
        """Create invoice plus pending stub journal entry."""
        with self._database.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    INSERT INTO invoices (original_filename, mime_type, file_path, extracted_text)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id, original_filename, mime_type, file_path, extracted_text, created_at, updated_at
                    """,
                    (original_filename, mime_type, file_path, extracted_text),
                )
                invoice_row = cur.fetchone()
                if invoice_row is None:
                    raise ValueError("Failed to create invoice")
                invoice = _invoice_from_row(invoice_row)

                accounts = self._load_active_account_choices(cur)
                debit_account, credit_account = choose_default_accounts(accounts)
                amount = Decimal("1000.00")

                cur.execute(
                    """
                    INSERT INTO journal_entries (invoice_id, status, currency, total_debit, total_credit)
                    VALUES (%s, 'pending', 'SEK', %s, %s)
                    RETURNING id, invoice_id, status, currency, total_debit, total_credit, decided_at, decision_reason, created_at, updated_at
                    """,
                    (invoice.id, amount, amount),
                )
                entry_row = cur.fetchone()
                if entry_row is None:
                    raise ValueError("Failed to create journal entry")
                entry_id = _uuid(entry_row["id"])

                posting_inputs = [
                    PostingCreate(
                        line_no=1,
                        account_id=debit_account.id,
                        account_code_snapshot=debit_account.code,
                        account_name_snapshot=debit_account.name,
                        description="Auto-generated debit line (stub)",
                        debit_amount=amount,
                        credit_amount=Decimal("0.00"),
                    ),
                    PostingCreate(
                        line_no=2,
                        account_id=credit_account.id,
                        account_code_snapshot=credit_account.code,
                        account_name_snapshot=credit_account.name,
                        description="Auto-generated credit line (stub)",
                        debit_amount=Decimal("0.00"),
                        credit_amount=amount,
                    ),
                ]
                self._insert_postings(cur, entry_id, posting_inputs)

        bundle = self.get_invoice_bundle(invoice.id)
        if bundle is None:
            raise ValueError("Failed to load created invoice bundle")
        return bundle

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
                    return None
                postings = self._load_postings_for_entry(cur, _uuid(entry_row["id"]))
                entry = _journal_entry_from_row(entry_row, postings)

        return InvoiceBundleRecord(invoice=invoice, journal_entry=entry)

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

    def _load_active_account_choices(
        self, cur: Any
    ) -> list[AccountChoice]:
        cur.execute(
            """
            SELECT id, code, name
            FROM accounts
            WHERE is_active = TRUE
            ORDER BY code
            """
        )
        rows = cur.fetchall()
        return [
            AccountChoice(
                id=_uuid(row["id"]),
                code=_int(row["code"]),
                name=_str(row["name"]),
            )
            for row in rows
        ]

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
    decision_reason = (
        None if decision_reason_raw is None else _str(decision_reason_raw)
    )
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

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
from backend.app.core.default_accounts import DEFAULT_ACCOUNTS
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


@dataclass(frozen=True)
class PostingUpdate:
    """Input structure for replacing posting lines on a pending entry."""

    account_id: UUID
    description: str | None
    debit_amount: Decimal
    credit_amount: Decimal


@dataclass(frozen=True)
class AccountSnapshotItem:
    """Desired active account state item for bulk save operations."""

    code: int
    name: str


class AccountConflictError(ValueError):
    """Raised when account uniqueness constraints are violated."""


class AccountInUseError(ValueError):
    """Raised when attempting to deactivate an account used by approved entries."""


ACCOUNT_CODE_CONSTRAINT_NAMES = {"accounts_code_key"}
ACCOUNT_NAME_CONSTRAINT_NAMES = {"accounts_active_name_unique_idx"}


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

    def ensure_default_accounts(self) -> None:
        """Ensure default accounts exist and are active on service startup."""
        with self._database.connection() as conn:
            with conn.cursor() as cur:
                for code, name in DEFAULT_ACCOUNTS:
                    cur.execute(
                        """
                        INSERT INTO accounts (code, name, is_active)
                        VALUES (%s, %s, TRUE)
                        ON CONFLICT (code) DO UPDATE
                        SET
                          name = EXCLUDED.name,
                          is_active = TRUE
                        """,
                        (code, name),
                    )

    def get_account(self, account_id: UUID) -> AccountRecord | None:
        """Return chart-of-accounts row by id."""
        with self._database.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT id, code, name, is_active, created_at, updated_at
                    FROM accounts
                    WHERE id = %s
                    """,
                    (account_id,),
                )
                row = cur.fetchone()
        if row is None:
            return None
        return _account_from_row(row)

    def create_account(self, code: int, name: str) -> AccountRecord:
        """Create a chart-of-accounts entry or reactivate a matching code."""
        try:
            with self._database.connection() as conn:
                with conn.cursor(row_factory=dict_row) as cur:
                    cur.execute(
                        """
                        SELECT id, code, name, is_active, created_at, updated_at
                        FROM accounts
                        WHERE code = %s
                        """,
                        (code,),
                    )
                    existing_row = cur.fetchone()
                    if existing_row is not None:
                        existing_id = _uuid(existing_row["id"])
                        existing_active = _bool(existing_row["is_active"])
                        if existing_active:
                            raise AccountConflictError("Account code already exists")
                        self._assert_active_account_name_available(
                            cur,
                            name=name,
                            exclude_account_id=existing_id,
                        )
                        cur.execute(
                            """
                            UPDATE accounts
                            SET name = %s,
                                is_active = TRUE
                            WHERE id = %s
                            RETURNING id, code, name, is_active, created_at, updated_at
                            """,
                            (name, existing_id),
                        )
                        row = cur.fetchone()
                        if row is None:
                            raise ValueError("Failed to reactivate account")
                        return _account_from_row(row)

                    self._assert_active_account_name_available(cur, name=name)
                    cur.execute(
                        """
                        INSERT INTO accounts (code, name, is_active)
                        VALUES (%s, %s, TRUE)
                        RETURNING id, code, name, is_active, created_at, updated_at
                        """,
                        (code, name),
                    )
                    row = cur.fetchone()
        except Exception as exc:
            conflict_error = _account_conflict_error_from_exception(exc)
            if conflict_error is not None:
                raise conflict_error from exc
            raise
        if row is None:
            raise ValueError("Failed to create account")
        return _account_from_row(row)

    def update_account(
        self,
        account_id: UUID,
        code: int | None,
        name: str | None,
        is_active: bool | None,
    ) -> AccountRecord | None:
        """Update account fields and enforce deactivation safeguards."""
        try:
            with self._database.connection() as conn:
                with conn.cursor(row_factory=dict_row) as cur:
                    current = self._load_account_row(cur, account_id)
                    if current is None:
                        return None

                    next_name = name if name is not None else _str(current["name"])
                    next_is_active = (
                        is_active
                        if is_active is not None
                        else _bool(current["is_active"])
                    )
                    if next_is_active:
                        self._assert_active_account_name_available(
                            cur,
                            name=next_name,
                            exclude_account_id=account_id,
                        )

                    if is_active is False:
                        current_is_active = _bool(current["is_active"])
                        if (
                            current_is_active
                            and self._account_used_in_approved_entries(cur, account_id)
                        ):
                            raise AccountInUseError(
                                "Account is used by an approved journal entry"
                            )

                    cur.execute(
                        """
                        UPDATE accounts
                        SET code = COALESCE(%s, code),
                            name = COALESCE(%s, name),
                            is_active = COALESCE(%s, is_active)
                        WHERE id = %s
                        RETURNING id, code, name, is_active, created_at, updated_at
                        """,
                        (code, name, is_active, account_id),
                    )
                    row = cur.fetchone()
        except Exception as exc:
            if isinstance(exc, AccountInUseError):
                raise
            conflict_error = _account_conflict_error_from_exception(exc)
            if conflict_error is not None:
                raise conflict_error from exc
            raise

        if row is None:
            return None
        return _account_from_row(row)

    def deactivate_account(self, account_id: UUID) -> AccountRecord | None:
        """Soft-delete account by deactivating it."""
        return self.update_account(
            account_id=account_id,
            code=None,
            name=None,
            is_active=False,
        )

    def save_accounts_snapshot(
        self, accounts: list[AccountSnapshotItem]
    ) -> list[AccountRecord]:
        """Atomically replace the active chart of accounts with the provided snapshot."""
        if len(accounts) == 0:
            raise ValueError("At least one account is required")

        seen_codes: set[int] = set()
        seen_names: set[str] = set()
        for account in accounts:
            if account.code in seen_codes:
                raise AccountConflictError(f"Duplicate account code: {account.code}")
            seen_codes.add(account.code)

            normalized_name = account.name.strip().lower()
            if normalized_name in seen_names:
                raise AccountConflictError(
                    f"Duplicate account name: {account.name.strip()}"
                )
            seen_names.add(normalized_name)

        desired_by_code = {account.code: account for account in accounts}
        desired_codes = set(desired_by_code.keys())

        try:
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
                    rows_by_code = {_int(row["code"]): row for row in rows}
                    active_rows = [row for row in rows if _bool(row["is_active"])]

                    for row in active_rows:
                        code = _int(row["code"])
                        if code in desired_codes:
                            continue
                        account_id = _uuid(row["id"])
                        if self._account_used_in_approved_entries(cur, account_id):
                            raise AccountInUseError(
                                f"Account {code} is used by an approved journal entry"
                            )

                    for row in active_rows:
                        code = _int(row["code"])
                        if code in desired_codes:
                            continue
                        cur.execute(
                            """
                            UPDATE accounts
                            SET is_active = FALSE
                            WHERE id = %s
                            """,
                            (_uuid(row["id"]),),
                        )

                    for item in accounts:
                        existing_row = rows_by_code.get(item.code)
                        if existing_row is None:
                            cur.execute(
                                """
                                INSERT INTO accounts (code, name, is_active)
                                VALUES (%s, %s, TRUE)
                                RETURNING id, code, name, is_active, created_at, updated_at
                                """,
                                (item.code, item.name),
                            )
                            inserted = cur.fetchone()
                            if inserted is None:
                                raise ValueError(
                                    "Failed to create account in bulk save"
                                )
                            rows_by_code[item.code] = inserted
                            continue

                        cur.execute(
                            """
                            UPDATE accounts
                            SET name = %s,
                                is_active = TRUE
                            WHERE id = %s
                            RETURNING id, code, name, is_active, created_at, updated_at
                            """,
                            (item.name, _uuid(existing_row["id"])),
                        )
                        updated = cur.fetchone()
                        if updated is None:
                            raise ValueError("Failed to update account in bulk save")
                        rows_by_code[item.code] = updated

                    cur.execute(
                        """
                        SELECT id, code, name, is_active, created_at, updated_at
                        FROM accounts
                        ORDER BY code
                        """
                    )
                    final_rows = cur.fetchall()
        except Exception as exc:
            if isinstance(exc, AccountConflictError | AccountInUseError):
                raise
            conflict_error = _account_conflict_error_from_exception(exc)
            if conflict_error is not None:
                raise conflict_error from exc
            raise

        return [_account_from_row(row) for row in final_rows]

    def create_invoice(
        self,
        original_filename: str,
        mime_type: str,
        file_path: str,
        content_hash: str | None,
    ) -> InvoiceRecord:
        """Create and return an uploaded invoice row."""
        with self._database.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                duplicate_of_invoice_id: UUID | None = None
                if content_hash is not None and content_hash != "":
                    # Serialize uploads for the same hash to avoid duplicate-detection races.
                    cur.execute(
                        """
                        SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))
                        """,
                        (content_hash,),
                    )
                    cur.execute(
                        """
                        SELECT id
                        FROM invoices
                        WHERE content_hash = %s
                        ORDER BY created_at ASC, id ASC
                        LIMIT 1
                        """,
                        (content_hash,),
                    )
                    duplicate_row = cur.fetchone()
                    if duplicate_row is not None:
                        duplicate_of_invoice_id = _uuid(duplicate_row["id"])

                cur.execute(
                    """
                    INSERT INTO invoices (
                        original_filename,
                        mime_type,
                        file_path,
                        content_hash,
                        duplicate_of_invoice_id,
                        extracted_text,
                        generation_status,
                        generation_error,
                        generated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, NULL, 'uploaded', NULL, NULL)
                    RETURNING id, original_filename, mime_type, file_path,
                              content_hash, duplicate_of_invoice_id, extracted_text,
                              generation_status, generation_error, generated_at, created_at, updated_at
                    """,
                    (
                        original_filename,
                        mime_type,
                        file_path,
                        content_hash,
                        duplicate_of_invoice_id,
                    ),
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
                    SELECT id, original_filename, mime_type, file_path,
                           content_hash, duplicate_of_invoice_id, extracted_text,
                           generation_status, generation_error, generated_at, created_at, updated_at
                    FROM invoices
                    WHERE id = %s
                    """,
                    (invoice_id,),
                )
                row = cur.fetchone()
        if row is None:
            return None
        return _invoice_from_row(row)

    def list_invoices(self) -> list[InvoiceRecord]:
        """List invoices ordered by most recently created first."""
        with self._database.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT id, original_filename, mime_type, file_path,
                           content_hash, duplicate_of_invoice_id, extracted_text,
                           generation_status, generation_error, generated_at, created_at, updated_at
                    FROM invoices
                    ORDER BY created_at DESC
                    """
                )
                rows = cur.fetchall()
        return [_invoice_from_row(row) for row in rows]

    def get_invoice_bundle(self, invoice_id: UUID) -> InvoiceBundleRecord | None:
        """Return invoice and journal entry details for the review screen."""
        with self._database.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT id, original_filename, mime_type, file_path,
                           content_hash, duplicate_of_invoice_id, extracted_text,
                           generation_status, generation_error, generated_at, created_at, updated_at
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
                    RETURNING id, original_filename, mime_type, file_path,
                              content_hash, duplicate_of_invoice_id, extracted_text,
                              generation_status, generation_error, generated_at, created_at, updated_at
                    """,
                    (markdown, invoice_id),
                )
                row = cur.fetchone()
        if row is None:
            return None
        return _invoice_from_row(row)

    def mark_invoice_generation_started(self, invoice_id: UUID) -> bool:
        """Set invoice generation status to generating."""
        with self._database.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE invoices
                    SET generation_status = 'generating',
                        generation_error = NULL,
                        generated_at = NULL
                    WHERE id = %s
                    """,
                    (invoice_id,),
                )
                return cur.rowcount > 0

    def mark_invoice_generation_ready(self, invoice_id: UUID) -> bool:
        """Set invoice generation status to ready."""
        with self._database.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE invoices
                    SET generation_status = 'ready',
                        generation_error = NULL,
                        generated_at = NOW()
                    WHERE id = %s
                    """,
                    (invoice_id,),
                )
                return cur.rowcount > 0

    def mark_invoice_generation_failed(self, invoice_id: UUID, error: str) -> bool:
        """Set invoice generation status to failed with error details."""
        with self._database.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE invoices
                    SET generation_status = 'failed',
                        generation_error = %s,
                        generated_at = NULL
                    WHERE id = %s
                    """,
                    (error[:1000], invoice_id),
                )
                return cur.rowcount > 0

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
                    self._assert_invoice_not_duplicate_for_approval(
                        cur,
                        invoice_id=_uuid(current_entry_row["invoice_id"]),
                    )
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

    def update_pending_journal_entry(
        self, journal_entry_id: UUID, postings: list[PostingUpdate]
    ) -> JournalEntryRecord | None:
        """Replace postings for a pending journal entry and recalculate totals."""
        if len(postings) == 0:
            raise ValueError("Journal entry requires at least one posting")

        amounts: list[PostingAmounts] = []
        for index, posting in enumerate(postings, start=1):
            debit = posting.debit_amount
            credit = posting.credit_amount
            if debit < 0 or credit < 0:
                raise ValueError(f"Line {index}: amounts must be non-negative")
            if (debit > 0 and credit > 0) or (debit == 0 and credit == 0):
                raise ValueError(
                    f"Line {index}: exactly one of debit or credit must be greater than zero"
                )
            amounts.append(PostingAmounts(debit=debit, credit=credit))

        if not is_balanced(amounts):
            raise ValueError("Journal entry is not balanced")
        total_debit, total_credit = calculate_totals(amounts)

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
                if _str(current_entry_row["status"]) != "pending":
                    raise ValueError("Only pending journal entries can be edited")

                account_ids = list({posting.account_id for posting in postings})
                cur.execute(
                    """
                    SELECT id, code, name
                    FROM accounts
                    WHERE id = ANY(%s::uuid[]) AND is_active = TRUE
                    """,
                    (account_ids,),
                )
                account_rows = cur.fetchall()
                account_map = {
                    _uuid(account_row["id"]): account_row
                    for account_row in account_rows
                }
                if len(account_map) != len(account_ids):
                    raise ValueError(
                        "Journal entry references missing or inactive accounts"
                    )

                cur.execute(
                    """
                    DELETE FROM journal_postings
                    WHERE journal_entry_id = %s
                    """,
                    (journal_entry_id,),
                )

                updated_rows: list[PostingCreate] = []
                for index, posting in enumerate(postings, start=1):
                    account_row = account_map.get(posting.account_id)
                    if account_row is None:
                        raise ValueError(
                            "Journal entry references missing or inactive accounts"
                        )
                    updated_rows.append(
                        PostingCreate(
                            line_no=index,
                            account_id=posting.account_id,
                            account_code_snapshot=_int(account_row["code"]),
                            account_name_snapshot=_str(account_row["name"]),
                            description=posting.description,
                            debit_amount=posting.debit_amount,
                            credit_amount=posting.credit_amount,
                        )
                    )
                self._insert_postings(cur, journal_entry_id, updated_rows)

                cur.execute(
                    """
                    UPDATE journal_entries
                    SET total_debit = %s,
                        total_credit = %s,
                        status = 'pending',
                        decision_reason = NULL,
                        decided_at = NULL
                    WHERE id = %s
                    RETURNING id, invoice_id, status, currency, total_debit, total_credit, decided_at, decision_reason, created_at, updated_at
                    """,
                    (
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
        account_ids = list({posting.account_id for posting in postings})
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

    def _assert_active_account_name_available(
        self,
        cur: Any,
        name: str,
        exclude_account_id: UUID | None = None,
    ) -> None:
        if exclude_account_id is None:
            cur.execute(
                """
                SELECT id
                FROM accounts
                WHERE LOWER(name) = LOWER(%s)
                  AND is_active = TRUE
                LIMIT 1
                """,
                (name,),
            )
        else:
            cur.execute(
                """
                SELECT id
                FROM accounts
                WHERE LOWER(name) = LOWER(%s)
                  AND is_active = TRUE
                  AND id <> %s
                LIMIT 1
                """,
                (name, exclude_account_id),
            )

        row = cur.fetchone()
        if row is not None:
            raise AccountConflictError("Account name already exists")

    def _assert_invoice_not_duplicate_for_approval(
        self, cur: Any, invoice_id: UUID
    ) -> None:
        cur.execute(
            """
            SELECT content_hash
            FROM invoices
            WHERE id = %s
            FOR UPDATE
            """,
            (invoice_id,),
        )
        row = cur.fetchone()
        if row is None:
            raise ValueError("Invoice not found for journal entry")

        content_hash_raw = row["content_hash"]
        if content_hash_raw is None:
            return
        content_hash = _str(content_hash_raw)
        if content_hash == "":
            return

        # Lock whole duplicate group so concurrent approvals cannot pass together.
        cur.execute(
            """
            SELECT id
            FROM invoices
            WHERE content_hash = %s
            FOR UPDATE
            """,
            (content_hash,),
        )

        cur.execute(
            """
            SELECT i.id AS approved_invoice_id
            FROM invoices i
            JOIN journal_entries je
              ON je.invoice_id = i.id
            WHERE i.content_hash = %s
              AND i.id <> %s
              AND je.status = 'approved'
            ORDER BY je.decided_at ASC NULLS LAST, je.updated_at ASC, je.id ASC
            LIMIT 1
            """,
            (content_hash, invoice_id),
        )
        approved_row = cur.fetchone()
        if approved_row is not None:
            approved_invoice_id = _uuid(approved_row["approved_invoice_id"])
            raise ValueError(
                "Approval blocked: duplicate invoice group already approved by "
                f"{approved_invoice_id}"
            )

    def _load_account_row(self, cur: Any, account_id: UUID) -> dict[str, Any] | None:
        cur.execute(
            """
            SELECT id, code, name, is_active, created_at, updated_at
            FROM accounts
            WHERE id = %s
            """,
            (account_id,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        if isinstance(row, dict):
            return row
        raise ValueError("Unexpected account row shape")

    def _account_used_in_approved_entries(self, cur: Any, account_id: UUID) -> bool:
        cur.execute(
            """
            SELECT EXISTS (
                SELECT 1
                FROM journal_postings jp
                JOIN journal_entries je
                  ON je.id = jp.journal_entry_id
                WHERE jp.account_id = %s
                  AND je.status = 'approved'
            ) AS in_use
            """,
            (account_id,),
        )
        row = cur.fetchone()
        if row is None:
            raise ValueError("Could not verify account usage")
        return _bool(row["in_use"])


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
    content_hash_raw = row["content_hash"]
    content_hash: str | None
    if content_hash_raw is None:
        content_hash = None
    else:
        content_hash = _str(content_hash_raw)

    duplicate_of_raw = row["duplicate_of_invoice_id"]
    duplicate_of_invoice_id: UUID | None
    if duplicate_of_raw is None:
        duplicate_of_invoice_id = None
    else:
        duplicate_of_invoice_id = _uuid(duplicate_of_raw)

    extracted: str | None
    extracted_raw = row["extracted_text"]
    if extracted_raw is None:
        extracted = None
    else:
        extracted = _str(extracted_raw)
    generation_error_raw = row["generation_error"]
    generation_error: str | None
    if generation_error_raw is None:
        generation_error = None
    else:
        generation_error = _str(generation_error_raw)
    generated_at_raw = row["generated_at"]
    generated_at = None if generated_at_raw is None else _datetime(generated_at_raw)
    return InvoiceRecord(
        id=_uuid(row["id"]),
        original_filename=_str(row["original_filename"]),
        mime_type=_str(row["mime_type"]),
        file_path=_str(row["file_path"]),
        content_hash=content_hash,
        duplicate_of_invoice_id=duplicate_of_invoice_id,
        extracted_text=extracted,
        generation_status=_str(row["generation_status"]),
        generation_error=generation_error,
        generated_at=generated_at,
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


def _is_unique_violation(exc: Exception) -> bool:
    if _unique_violation_constraint_name(exc) is not None:
        return True
    message = str(exc).lower()
    return "duplicate key value violates unique constraint" in message


def _unique_violation_constraint_name(exc: Exception) -> str | None:
    current: BaseException | None = exc
    while current is not None:
        sqlstate = getattr(current, "sqlstate", None)
        if sqlstate == "23505":
            diag = getattr(current, "diag", None)
            constraint_name = getattr(diag, "constraint_name", None)
            if isinstance(constraint_name, str) and constraint_name.strip() != "":
                return constraint_name.strip()
            return ""
        current = current.__cause__
    return None


def _account_conflict_error_from_exception(
    exc: Exception,
) -> AccountConflictError | None:
    constraint_name = _unique_violation_constraint_name(exc)
    if constraint_name is None:
        if _is_unique_violation(exc):
            return AccountConflictError("Account code or name already exists")
        return None

    if constraint_name in ACCOUNT_CODE_CONSTRAINT_NAMES:
        return AccountConflictError("Account code already exists")
    if constraint_name in ACCOUNT_NAME_CONSTRAINT_NAMES:
        return AccountConflictError("Account name already exists")
    return AccountConflictError("Account code or name already exists")

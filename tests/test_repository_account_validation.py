"""Repository validation regression tests."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from backend.app.core.records import JournalPostingRecord
from backend.app.core.repository import AppRepository, PostingUpdate


class _CursorStub:
    def __init__(self, valid_count: int) -> None:
        self.valid_count = valid_count
        self.last_params: tuple[object, ...] | None = None

    def execute(self, _query: str, params: tuple[object, ...]) -> None:
        self.last_params = params

    def fetchone(self) -> dict[str, int]:
        return {"valid_count": self.valid_count}


class _InvoiceDuplicateCursorStub:
    def __init__(
        self,
        *,
        has_row: bool = True,
        content_hash: object = "hash-1",
        approved_invoice_id: object | None = None,
    ) -> None:
        self.has_row = has_row
        self.content_hash = content_hash
        self.approved_invoice_id = approved_invoice_id
        self.last_params: tuple[object, ...] | None = None
        self._last_query: str = ""

    def execute(self, query: str, params: tuple[object, ...]) -> None:
        self.last_params = params
        self._last_query = query

    def fetchone(self) -> dict[str, object] | None:
        if "SELECT content_hash" in self._last_query:
            if not self.has_row:
                return None
            return {"content_hash": self.content_hash}

        if "approved_invoice_id" in self._last_query:
            if self.approved_invoice_id is None:
                return None
            return {"approved_invoice_id": self.approved_invoice_id}

        return None


def _posting(account_id: UUID, line_no: int) -> JournalPostingRecord:
    now = datetime.now(tz=UTC)
    return JournalPostingRecord(
        id=uuid4(),
        journal_entry_id=uuid4(),
        line_no=line_no,
        account_id=account_id,
        account_code_snapshot=3000,
        account_name_snapshot="Sales",
        description=None,
        debit_amount=Decimal("0.00"),
        credit_amount=Decimal("100.00"),
        created_at=now,
    )


def test_account_validation_accepts_duplicate_account_ids_in_postings() -> None:
    """Approve validation should handle multiple lines using one account."""
    account_id = uuid4()
    postings = [
        _posting(account_id=account_id, line_no=1),
        _posting(account_id=account_id, line_no=2),
    ]
    cursor = _CursorStub(valid_count=1)
    repository = AppRepository(database=None)  # type: ignore[arg-type]

    repository._validate_accounts_for_postings(cursor, postings)

    assert cursor.last_params is not None
    account_ids = cursor.last_params[0]
    assert isinstance(account_ids, list)
    assert len(account_ids) == 1


def test_update_pending_journal_entry_requires_postings() -> None:
    repository = AppRepository(database=None)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="requires at least one posting"):
        repository.update_pending_journal_entry(uuid4(), [])


def test_update_pending_journal_entry_rejects_negative_amount() -> None:
    repository = AppRepository(database=None)  # type: ignore[arg-type]
    postings = [
        PostingUpdate(
            account_id=uuid4(),
            description=None,
            debit_amount=Decimal("-1.00"),
            credit_amount=Decimal("0.00"),
        )
    ]

    with pytest.raises(ValueError, match="non-negative"):
        repository.update_pending_journal_entry(uuid4(), postings)


def test_update_pending_journal_entry_rejects_double_sided_line() -> None:
    repository = AppRepository(database=None)  # type: ignore[arg-type]
    postings = [
        PostingUpdate(
            account_id=uuid4(),
            description=None,
            debit_amount=Decimal("50.00"),
            credit_amount=Decimal("50.00"),
        )
    ]

    with pytest.raises(ValueError, match="exactly one of debit or credit"):
        repository.update_pending_journal_entry(uuid4(), postings)


def test_update_pending_journal_entry_rejects_unbalanced_totals() -> None:
    repository = AppRepository(database=None)  # type: ignore[arg-type]
    postings = [
        PostingUpdate(
            account_id=uuid4(),
            description=None,
            debit_amount=Decimal("100.00"),
            credit_amount=Decimal("0.00"),
        ),
        PostingUpdate(
            account_id=uuid4(),
            description=None,
            debit_amount=Decimal("0.00"),
            credit_amount=Decimal("20.00"),
        ),
    ]

    with pytest.raises(ValueError, match="not balanced"):
        repository.update_pending_journal_entry(uuid4(), postings)


def test_duplicate_approval_check_accepts_non_duplicate_invoice() -> None:
    repository = AppRepository(database=None)  # type: ignore[arg-type]
    cursor = _InvoiceDuplicateCursorStub(content_hash=None)

    repository._assert_invoice_not_duplicate_for_approval(cursor, invoice_id=uuid4())

    assert cursor.last_params is not None


def test_duplicate_approval_check_accepts_duplicate_without_approved_peer() -> None:
    repository = AppRepository(database=None)  # type: ignore[arg-type]
    cursor = _InvoiceDuplicateCursorStub(
        content_hash="same-hash",
        approved_invoice_id=None,
    )

    repository._assert_invoice_not_duplicate_for_approval(cursor, invoice_id=uuid4())


def test_duplicate_approval_check_rejects_when_group_already_approved() -> None:
    repository = AppRepository(database=None)  # type: ignore[arg-type]
    approved_invoice_id = uuid4()
    cursor = _InvoiceDuplicateCursorStub(
        content_hash="same-hash",
        approved_invoice_id=approved_invoice_id,
    )

    with pytest.raises(ValueError, match="already approved"):
        repository._assert_invoice_not_duplicate_for_approval(
            cursor, invoice_id=uuid4()
        )


def test_duplicate_approval_check_rejects_missing_invoice_row() -> None:
    repository = AppRepository(database=None)  # type: ignore[arg-type]
    cursor = _InvoiceDuplicateCursorStub(has_row=False)

    with pytest.raises(ValueError, match="Invoice not found"):
        repository._assert_invoice_not_duplicate_for_approval(
            cursor, invoice_id=uuid4()
        )

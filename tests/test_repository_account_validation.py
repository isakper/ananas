"""Repository validation regression tests."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

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
    def __init__(self, duplicate_of_invoice_id: object, has_row: bool = True) -> None:
        self.duplicate_of_invoice_id = duplicate_of_invoice_id
        self.has_row = has_row
        self.last_params: tuple[object, ...] | None = None

    def execute(self, _query: str, params: tuple[object, ...]) -> None:
        self.last_params = params

    def fetchone(self) -> dict[str, object] | None:
        if not self.has_row:
            return None
        return {"duplicate_of_invoice_id": self.duplicate_of_invoice_id}


def _posting(account_id, line_no: int) -> JournalPostingRecord:
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
    cursor = _InvoiceDuplicateCursorStub(duplicate_of_invoice_id=None)

    repository._assert_invoice_not_duplicate_for_approval(cursor, invoice_id=uuid4())

    assert cursor.last_params is not None


def test_duplicate_approval_check_rejects_duplicate_invoice() -> None:
    repository = AppRepository(database=None)  # type: ignore[arg-type]
    duplicate_of = uuid4()
    cursor = _InvoiceDuplicateCursorStub(duplicate_of_invoice_id=duplicate_of)

    with pytest.raises(ValueError, match="marked duplicate"):
        repository._assert_invoice_not_duplicate_for_approval(cursor, invoice_id=uuid4())


def test_duplicate_approval_check_rejects_missing_invoice_row() -> None:
    repository = AppRepository(database=None)  # type: ignore[arg-type]
    cursor = _InvoiceDuplicateCursorStub(duplicate_of_invoice_id=None, has_row=False)

    with pytest.raises(ValueError, match="Invoice not found"):
        repository._assert_invoice_not_duplicate_for_approval(cursor, invoice_id=uuid4())

"""API-route integration tests for accounts and duplicate approval safeguards."""

from __future__ import annotations

import os
from decimal import Decimal
from typing import Iterator
from uuid import uuid4

import psycopg
import pytest
from fastapi import HTTPException

from backend.app.accounting.types import SuggestedPosting
from backend.app.api.routes.accounts import (
    create_account,
    deactivate_account,
    update_account,
)
from backend.app.api.routes.journal_entries import approve_journal_entry
from backend.app.api.schemas import AccountCreateRequest, AccountUpdateRequest
from backend.app.core.db import Database
from backend.app.core.repository import AppRepository


def _unique_code() -> int:
    # Keep in chart-of-accounts style integer range while avoiding collisions.
    return 8000 + (uuid4().int % 1000)


def _unique_name(prefix: str) -> str:
    return f"{prefix}-{str(uuid4())[:8]}"


def _candidate_database_urls() -> list[str]:
    values = [
        os.getenv("TEST_DATABASE_URL", "").strip(),
        os.getenv("DATABASE_URL", "").strip(),
        "postgresql://app:app@localhost:5433/app",
        "postgresql://app:app@localhost:5432/app",
    ]
    return [value for value in values if value != ""]


@pytest.fixture(scope="session")  # type: ignore[misc]
def database_url() -> str:
    for candidate in _candidate_database_urls():
        try:
            with psycopg.connect(candidate):
                pass
            return candidate
        except Exception:
            continue
    pytest.skip(
        "PostgreSQL is not available. Set TEST_DATABASE_URL or start local Postgres."
    )
    raise RuntimeError("unreachable")


@pytest.fixture(scope="session")  # type: ignore[misc]
def repository(database_url: str) -> AppRepository:
    return AppRepository(Database(database_url))


@pytest.fixture(scope="session", autouse=True)  # type: ignore[misc]
def assert_required_tables(database_url: str) -> None:
    required_tables = {"accounts", "invoices", "journal_entries", "journal_postings"}
    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                """
            )
            rows = cur.fetchall()

    discovered = {row[0] for row in rows if isinstance(row, tuple) and len(row) > 0}
    missing = required_tables - discovered
    if missing:
        pytest.skip(
            "Missing required tables. Run migrations before integration tests: "
            f"{', '.join(sorted(missing))}"
        )


@pytest.fixture(autouse=True)  # type: ignore[misc]
def clean_database(database_url: str) -> Iterator[None]:
    _truncate_all(database_url)
    yield
    _truncate_all(database_url)


def _truncate_all(database_url: str) -> None:
    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                TRUNCATE TABLE journal_postings, journal_entries, invoices, accounts
                RESTART IDENTITY CASCADE
                """
            )
        conn.commit()


def test_account_create_update_remove_reactivate(repository: AppRepository) -> None:
    base_code = _unique_code()
    cash_name = _unique_name("Cash")
    operating_name = _unique_name("Operating cash")
    reactivated_name = _unique_name("Operating cash reactivated")
    created = create_account(
        AccountCreateRequest(code=base_code, name=cash_name),
        repository=repository,
    )
    account_id = created.id

    updated_code = base_code + 1
    updated = update_account(
        str(account_id),
        AccountUpdateRequest(code=updated_code, name=operating_name),
        repository=repository,
    )
    assert updated.code == updated_code
    assert updated.name == operating_name
    assert updated.is_active is True

    removed = deactivate_account(str(account_id), repository=repository)
    assert removed.is_active is False

    reactivated = create_account(
        AccountCreateRequest(code=updated_code, name=reactivated_name),
        repository=repository,
    )
    assert reactivated.id == account_id
    assert reactivated.is_active is True
    assert reactivated.name == reactivated_name


def test_account_conflict_messages_for_create(repository: AppRepository) -> None:
    first_code = _unique_code()
    second_code = first_code + 1
    travel_name = _unique_name("Travel")
    create_account(
        AccountCreateRequest(code=first_code, name=travel_name),
        repository=repository,
    )

    with pytest.raises(HTTPException) as code_exc:
        create_account(
            AccountCreateRequest(code=first_code, name="Supplies"),
            repository=repository,
        )
    assert code_exc.value.status_code == 409
    assert code_exc.value.detail == "Account code already exists"

    with pytest.raises(HTTPException) as name_exc:
        create_account(
            AccountCreateRequest(code=second_code, name=travel_name.upper()),
            repository=repository,
        )
    assert name_exc.value.status_code == 409
    assert name_exc.value.detail == "Account name already exists"


def test_account_conflict_messages_for_update(repository: AppRepository) -> None:
    first_code = _unique_code()
    second_code = first_code + 1
    sales_name = _unique_name("Sales")
    marketing_name = _unique_name("Marketing")
    first = create_account(
        AccountCreateRequest(code=first_code, name=sales_name),
        repository=repository,
    )
    second = create_account(
        AccountCreateRequest(code=second_code, name=marketing_name),
        repository=repository,
    )

    with pytest.raises(HTTPException) as code_exc:
        update_account(
            str(second.id),
            AccountUpdateRequest(code=first.code),
            repository=repository,
        )
    assert code_exc.value.status_code == 409
    assert code_exc.value.detail == "Account code already exists"

    with pytest.raises(HTTPException) as name_exc:
        update_account(
            str(second.id),
            AccountUpdateRequest(name=sales_name.upper()),
            repository=repository,
        )
    assert name_exc.value.status_code == 409
    assert name_exc.value.detail == "Account name already exists"


def test_duplicate_invoice_only_one_can_be_approved(repository: AppRepository) -> None:
    content_hash = f"hash-{uuid4()}"
    debit_code = _unique_code()
    credit_code = debit_code + 1
    debit = repository.create_account(
        code=debit_code,
        name=_unique_name("Office supplies"),
    )
    credit = repository.create_account(
        code=credit_code,
        name=_unique_name("Accounts payable"),
    )

    original = repository.create_invoice(
        original_filename="a.pdf",
        mime_type="application/pdf",
        file_path="/tmp/a.pdf",
        content_hash=content_hash,
    )
    duplicate = repository.create_invoice(
        original_filename="b.pdf",
        mime_type="application/pdf",
        file_path="/tmp/b.pdf",
        content_hash=content_hash,
    )

    assert duplicate.duplicate_of_invoice_id is not None

    duplicate_entry = repository.replace_suggested_journal_entry(
        invoice_id=duplicate.id,
        postings=[
            SuggestedPosting(
                account_id=debit.id,
                account_code=debit.code,
                account_name=debit.name,
                description="Expense",
                debit_amount=Decimal("125.00"),
                credit_amount=Decimal("0.00"),
            ),
            SuggestedPosting(
                account_id=credit.id,
                account_code=credit.code,
                account_name=credit.name,
                description="Liability",
                debit_amount=Decimal("0.00"),
                credit_amount=Decimal("125.00"),
            ),
        ],
    )

    original_entry = repository.replace_suggested_journal_entry(
        invoice_id=original.id,
        postings=[
            SuggestedPosting(
                account_id=debit.id,
                account_code=debit.code,
                account_name=debit.name,
                description="Expense",
                debit_amount=Decimal("125.00"),
                credit_amount=Decimal("0.00"),
            ),
            SuggestedPosting(
                account_id=credit.id,
                account_code=credit.code,
                account_name=credit.name,
                description="Liability",
                debit_amount=Decimal("0.00"),
                credit_amount=Decimal("125.00"),
            ),
        ],
    )

    # First approver in duplicate group should succeed.
    approved = approve_journal_entry(original_entry.id, repository=repository)
    assert approved.status == "approved"

    # After one approval, peer duplicates are blocked.
    with pytest.raises(HTTPException) as exc_info:
        approve_journal_entry(duplicate_entry.id, repository=repository)
    assert exc_info.value.status_code == 400
    assert "already approved" in str(exc_info.value.detail)

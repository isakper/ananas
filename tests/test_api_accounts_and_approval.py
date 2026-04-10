"""API-route integration tests for accounts and duplicate approval safeguards."""

from __future__ import annotations

import os
from decimal import Decimal
from typing import Iterator

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


def _candidate_database_urls() -> list[str]:
    values = [
        os.getenv("TEST_DATABASE_URL", "").strip(),
        os.getenv("DATABASE_URL", "").strip(),
        "postgresql://app:app@localhost:5433/app",
        "postgresql://app:app@localhost:5432/app",
    ]
    return [value for value in values if value != ""]


@pytest.fixture(scope="session")
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


@pytest.fixture(scope="session")
def repository(database_url: str) -> AppRepository:
    return AppRepository(Database(database_url))


@pytest.fixture(scope="session", autouse=True)
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

    discovered = {
        row[0] for row in rows if isinstance(row, tuple) and len(row) > 0
    }
    missing = required_tables - discovered
    if missing:
        pytest.skip(
            "Missing required tables. Run migrations before integration tests: "
            f"{', '.join(sorted(missing))}"
        )


@pytest.fixture(autouse=True)
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
    created = create_account(
        AccountCreateRequest(code=3000, name="Cash"),
        repository=repository,
    )
    account_id = created.id

    updated = update_account(
        str(account_id),
        AccountUpdateRequest(code=3010, name="Operating cash"),
        repository=repository,
    )
    assert updated.code == 3010
    assert updated.name == "Operating cash"
    assert updated.is_active is True

    removed = deactivate_account(str(account_id), repository=repository)
    assert removed.is_active is False

    reactivated = create_account(
        AccountCreateRequest(code=3010, name="Operating cash (reactivated)"),
        repository=repository,
    )
    assert reactivated.id == account_id
    assert reactivated.is_active is True
    assert reactivated.name == "Operating cash (reactivated)"


def test_account_conflict_messages_for_create(repository: AppRepository) -> None:
    create_account(
        AccountCreateRequest(code=4000, name="Travel"),
        repository=repository,
    )

    with pytest.raises(HTTPException) as code_exc:
        create_account(
            AccountCreateRequest(code=4000, name="Supplies"),
            repository=repository,
        )
    assert code_exc.value.status_code == 409
    assert code_exc.value.detail == "Account code already exists"

    with pytest.raises(HTTPException) as name_exc:
        create_account(
            AccountCreateRequest(code=4001, name="travel"),
            repository=repository,
        )
    assert name_exc.value.status_code == 409
    assert name_exc.value.detail == "Account name already exists"


def test_account_conflict_messages_for_update(repository: AppRepository) -> None:
    first = create_account(
        AccountCreateRequest(code=4100, name="Sales"),
        repository=repository,
    )
    second = create_account(
        AccountCreateRequest(code=4101, name="Marketing"),
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
            AccountUpdateRequest(name="sales"),
            repository=repository,
        )
    assert name_exc.value.status_code == 409
    assert name_exc.value.detail == "Account name already exists"


def test_duplicate_invoice_approval_is_blocked(repository: AppRepository) -> None:
    debit = repository.create_account(code=6530, name="Office supplies")
    credit = repository.create_account(code=2440, name="Accounts payable")

    original = repository.create_invoice(
        original_filename="a.pdf",
        mime_type="application/pdf",
        file_path="/tmp/a.pdf",
        content_hash="hash-1",
    )
    duplicate = repository.create_invoice(
        original_filename="b.pdf",
        mime_type="application/pdf",
        file_path="/tmp/b.pdf",
        content_hash="hash-1",
    )

    assert duplicate.duplicate_of_invoice_id == original.id

    entry = repository.replace_suggested_journal_entry(
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

    with pytest.raises(HTTPException) as exc_info:
        approve_journal_entry(entry.id, repository=repository)
    assert exc_info.value.status_code == 400
    assert "marked duplicate" in str(exc_info.value.detail)

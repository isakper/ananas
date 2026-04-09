"""Accounting domain rules used by APIs and repositories."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True)
class AccountChoice:
    """Minimal account data for posting selection."""

    id: UUID
    code: int
    name: str


@dataclass(frozen=True)
class PostingAmounts:
    """Amounts used for debit/credit validation."""

    debit: Decimal
    credit: Decimal


def calculate_totals(postings: list[PostingAmounts]) -> tuple[Decimal, Decimal]:
    """Calculate debit and credit totals for posting lines."""
    debit_total = sum((posting.debit for posting in postings), Decimal("0.00"))
    credit_total = sum((posting.credit for posting in postings), Decimal("0.00"))
    return (debit_total, credit_total)


def is_balanced(postings: list[PostingAmounts]) -> bool:
    """Return True when total debits match total credits."""
    debit_total, credit_total = calculate_totals(postings)
    return debit_total == credit_total


def choose_default_accounts(
    accounts: list[AccountChoice],
) -> tuple[AccountChoice, AccountChoice]:
    """Pick default debit and credit accounts for a stub suggestion."""
    if len(accounts) < 2:
        raise ValueError("At least two active accounts are required")

    debit_account = _find_by_code(accounts, 6530) or accounts[0]
    credit_account = _find_by_code(accounts, 2440)
    if credit_account is None:
        credit_account = _first_different(accounts, debit_account.id)
    if credit_account is None:
        raise ValueError("Could not find a valid credit account")
    if debit_account.id == credit_account.id:
        raise ValueError("Debit and credit accounts cannot be the same")
    return (debit_account, credit_account)


def _find_by_code(accounts: list[AccountChoice], code: int) -> AccountChoice | None:
    """Find the first account by account code."""
    for account in accounts:
        if account.code == code:
            return account
    return None


def _first_different(
    accounts: list[AccountChoice], account_id: UUID
) -> AccountChoice | None:
    """Return the first account whose id is not the provided id."""
    for account in accounts:
        if account.id != account_id:
            return account
    return None

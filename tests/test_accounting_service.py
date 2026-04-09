from decimal import Decimal
from uuid import uuid4

import pytest

from backend.app.accounting.service import (
    AccountChoice,
    PostingAmounts,
    calculate_totals,
    choose_default_accounts,
    is_balanced,
)


def test_calculate_totals_returns_expected_values() -> None:
    """Calculates debit and credit totals from posting lines."""
    postings = [
        PostingAmounts(debit=Decimal("10.00"), credit=Decimal("0.00")),
        PostingAmounts(debit=Decimal("0.00"), credit=Decimal("4.00")),
        PostingAmounts(debit=Decimal("0.00"), credit=Decimal("6.00")),
    ]
    debit_total, credit_total = calculate_totals(postings)
    assert debit_total == Decimal("10.00")
    assert credit_total == Decimal("10.00")


def test_is_balanced_detects_unbalanced_entries() -> None:
    """Returns False when debit and credit totals differ."""
    postings = [
        PostingAmounts(debit=Decimal("10.00"), credit=Decimal("0.00")),
        PostingAmounts(debit=Decimal("0.00"), credit=Decimal("5.00")),
    ]
    assert not is_balanced(postings)


def test_choose_default_accounts_prefers_expected_codes() -> None:
    """Prefers 6530 as debit and 2440 as credit when present."""
    accounts = [
        AccountChoice(id=uuid4(), code=2440, name="Leverantorsskulder"),
        AccountChoice(id=uuid4(), code=6530, name="IT-tjanster"),
        AccountChoice(id=uuid4(), code=5610, name="Kontorsmaterial"),
    ]
    debit, credit = choose_default_accounts(accounts)
    assert debit.code == 6530
    assert credit.code == 2440


def test_choose_default_accounts_requires_two_accounts() -> None:
    """Raises when there are not enough active accounts."""
    accounts = [AccountChoice(id=uuid4(), code=6530, name="IT-tjanster")]
    with pytest.raises(ValueError):
        choose_default_accounts(accounts)

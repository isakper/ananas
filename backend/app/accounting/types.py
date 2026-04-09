"""Types for journal-entry suggestion generation."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True)
class SuggestedPosting:
    """Single suggested posting line for a generated journal entry."""

    account_id: UUID
    account_code: int
    account_name: str
    description: str | None
    debit_amount: Decimal
    credit_amount: Decimal

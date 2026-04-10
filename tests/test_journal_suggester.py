"""Tests for LLM-based journal suggestion parsing and validation."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from backend.app.accounting.journal_suggester import LlmJournalSuggester
from backend.app.core.records import AccountRecord
from backend.app.integrations.llm.types import LlmRequest, LlmResponse


class _StaticGateway:
    """Minimal fake LLM gateway returning a preconfigured response."""

    def __init__(self, response: LlmResponse) -> None:
        self._response = response

    def call_llm(self, request: LlmRequest) -> LlmResponse:
        _ = request
        return self._response


def _account(code: int, name: str) -> AccountRecord:
    now = datetime.now(tz=UTC)
    return AccountRecord(
        id=uuid4(),
        code=code,
        name=name,
        is_active=True,
        created_at=now,
        updated_at=now,
    )


def test_suggest_returns_valid_postings() -> None:
    """Parses and returns postings when LLM JSON payload is valid."""
    gateway = _StaticGateway(
        LlmResponse(
            text="",
            json_payload={
                "postings": [
                    {
                        "account_code": 6530,
                        "description": "IT service",
                        "debit_amount": "1000.00",
                        "credit_amount": "0.00",
                    },
                    {
                        "account_code": 2440,
                        "description": "Accounts payable",
                        "debit_amount": "0.00",
                        "credit_amount": "1000.00",
                    },
                ]
            },
            raw=None,
        )
    )
    suggester = LlmJournalSuggester(llm_gateway=gateway)

    postings = suggester.suggest(
        markdown="# Invoice",
        accounts=[_account(6530, "IT"), _account(2440, "AP")],
    )

    assert len(postings) == 2
    assert postings[0].account_code == 6530
    assert postings[1].account_code == 2440


def test_suggest_raises_on_missing_json() -> None:
    """Raises when LLM does not return valid JSON payload."""
    gateway = _StaticGateway(
        LlmResponse(
            text="not-json",
            json_payload=None,
            raw=None,
        )
    )
    suggester = LlmJournalSuggester(llm_gateway=gateway)

    with pytest.raises(ValueError, match="valid JSON"):
        suggester.suggest(
            markdown="# Invoice",
            accounts=[_account(6530, "IT"), _account(2440, "AP")],
        )


def test_suggest_allows_unbalanced_postings() -> None:
    """Returns parsed postings even when debits/credits are unbalanced."""
    gateway = _StaticGateway(
        LlmResponse(
            text="",
            json_payload={
                "postings": [
                    {
                        "account_code": 6530,
                        "description": "IT service",
                        "debit_amount": "1000.00",
                        "credit_amount": "0.00",
                    },
                    {
                        "account_code": 2440,
                        "description": "Accounts payable",
                        "debit_amount": "0.00",
                        "credit_amount": "900.00",
                    },
                ]
            },
            raw=None,
        )
    )
    suggester = LlmJournalSuggester(llm_gateway=gateway)

    postings = suggester.suggest(
        markdown="# Invoice",
        accounts=[_account(6530, "IT"), _account(2440, "AP")],
    )

    assert len(postings) == 2
    assert str(postings[0].debit_amount) == "1000.00"
    assert str(postings[1].credit_amount) == "900.00"

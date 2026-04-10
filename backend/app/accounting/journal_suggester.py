"""Accounting-domain journal suggestion logic."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Protocol

from backend.app.accounting.types import SuggestedPosting
from backend.app.core.records import AccountRecord
from backend.app.integrations.llm.client import LlmGateway
from backend.app.integrations.llm.types import LlmRequest


class JournalSuggester(Protocol):
    """Contract for generating postings from invoice markdown."""

    def suggest(
        self, markdown: str, accounts: list[AccountRecord]
    ) -> list[SuggestedPosting]:
        """Generate suggested postings from markdown and accounts."""


class LlmJournalSuggester:
    """Use an LLM integration to suggest journal postings."""

    def __init__(self, llm_gateway: LlmGateway) -> None:
        self._llm_gateway = llm_gateway

    def suggest(
        self, markdown: str, accounts: list[AccountRecord]
    ) -> list[SuggestedPosting]:
        """Generate journal posting suggestions from markdown."""
        active_accounts = [account for account in accounts if account.is_active]
        if len(active_accounts) == 0:
            raise ValueError("No active accounts available")

        response = self._llm_gateway.call_llm(
            request=LlmRequest(
                system_prompt="You are a bookkeeping assistant that returns JSON.",
                user_prompt=_build_mapping_instruction(
                    markdown=markdown,
                    accounts=active_accounts,
                ),
                attachments=[],
                output_mode="json",
                output_schema=_journal_entry_output_schema(),
                model=None,
                temperature=0.0,
                max_tokens=3000,
            )
        )
        payload = response.json_payload
        if payload is None:
            raise ValueError("LLM did not return valid JSON output")
        postings = _postings_from_payload(payload=payload, accounts=active_accounts)
        if len(postings) == 0:
            raise ValueError("LLM output did not contain valid journal postings")
        return postings


def _build_mapping_instruction(markdown: str, accounts: list[AccountRecord]) -> str:
    account_lines = [f"{account.code} {account.name}" for account in accounts]
    return (
        "Map this invoice markdown to a balanced journal entry. "
        "Use only account_code values from the provided chart of accounts. "
        "Return JSON with a top-level 'postings' list. "
        "Each posting needs account_code, description, debit_amount, credit_amount.\n\n"
        f"Chart of accounts:\n{chr(10).join(account_lines)}\n\n"
        f"Invoice markdown:\n{markdown}"
    )


def _postings_from_payload(
    payload: dict[str, Any], accounts: list[AccountRecord]
) -> list[SuggestedPosting]:
    raw_postings = payload.get("postings")
    if not isinstance(raw_postings, list):
        return []

    account_by_code = {account.code: account for account in accounts}
    parsed: list[SuggestedPosting] = []
    for item in raw_postings:
        if not isinstance(item, dict):
            continue
        code_raw = item.get("account_code")
        if not isinstance(code_raw, int):
            continue
        account = account_by_code.get(code_raw)
        if account is None:
            continue
        debit = _to_decimal(item.get("debit_amount"))
        credit = _to_decimal(item.get("credit_amount"))
        if debit is None or credit is None:
            continue
        description_raw = item.get("description")
        description = description_raw if isinstance(description_raw, str) else None
        parsed.append(
            SuggestedPosting(
                account_id=account.id,
                account_code=account.code,
                account_name=account.name,
                description=description,
                debit_amount=debit,
                credit_amount=credit,
            )
        )
    return parsed


def _journal_entry_output_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "required": ["postings"],
        "additionalProperties": False,
        "properties": {
            "postings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": [
                        "account_code",
                        "description",
                        "debit_amount",
                        "credit_amount",
                    ],
                    "additionalProperties": False,
                    "properties": {
                        "account_code": {"type": "integer"},
                        "description": {"type": "string"},
                        "debit_amount": {"type": "string"},
                        "credit_amount": {"type": "string"},
                    },
                },
            }
        },
    }


def _to_decimal(value: Any) -> Decimal | None:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, str):
        try:
            return Decimal(value)
        except InvalidOperation:
            return None
    return None

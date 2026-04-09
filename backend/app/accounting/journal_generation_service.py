"""Service wrapper for journal suggestion generation."""
from __future__ import annotations

from backend.app.accounting.journal_suggester import JournalSuggester
from backend.app.accounting.types import SuggestedPosting
from backend.app.core.records import AccountRecord


class JournalGenerationService:
    """Generate suggested journal postings from extracted invoice markdown."""

    def __init__(self, suggester: JournalSuggester) -> None:
        self._suggester = suggester

    def generate_postings(
        self, markdown: str, accounts: list[AccountRecord]
    ) -> list[SuggestedPosting]:
        """Return suggested postings from provider output."""
        return self._suggester.suggest(markdown=markdown, accounts=accounts)

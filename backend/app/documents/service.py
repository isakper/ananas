"""Document extraction service orchestration."""
from __future__ import annotations

from pathlib import Path

from backend.app.documents.markdown_extractor import MarkdownExtractor


class DocumentExtractionService:
    """Extract markdown from a PDF invoice path."""

    def __init__(self, markdown_extractor: MarkdownExtractor) -> None:
        self._markdown_extractor = markdown_extractor

    def extract_markdown(self, pdf_path: Path) -> str:
        """Extract markdown directly from the source PDF."""
        return self._markdown_extractor.extract_markdown(pdf_path=pdf_path)

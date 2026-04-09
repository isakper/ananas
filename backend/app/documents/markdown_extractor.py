"""Document-domain markdown extraction logic."""
from __future__ import annotations

from pathlib import Path

from backend.app.integrations.llm.client import LlmGateway
from backend.app.integrations.llm.types import LlmAttachment, LlmRequest


class MarkdownExtractor:
    """Extract invoice markdown from a PDF using the shared LLM gateway."""

    def __init__(self, llm_gateway: LlmGateway) -> None:
        self._llm_gateway = llm_gateway

    def extract_markdown(self, pdf_path: Path) -> str:
        """Return markdown content for a source invoice PDF."""
        instruction = (
            "Extract the invoice faithfully into markdown. Preserve key fields, "
            "totals, VAT and line items."
        )
        response = self._llm_gateway.call_llm(
            request=LlmRequest(
                system_prompt="You extract invoice data to markdown.",
                user_prompt=instruction,
                attachments=[
                    LlmAttachment(
                        kind="pdf",
                        path=pdf_path,
                        media_type="application/pdf",
                    )
                ],
                output_mode="text",
                output_schema=None,
                model=None,
                temperature=0.0,
                max_tokens=3000,
            )
        )
        return response.text

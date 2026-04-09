"""Shared request and response types for LLM integrations."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal


@dataclass(frozen=True)
class LlmAttachment:
    """Optional file attachment sent with an LLM request."""

    kind: Literal["pdf"]
    path: Path
    media_type: str


@dataclass(frozen=True)
class LlmRequest:
    """Normalized request envelope for LLM calls."""

    system_prompt: str | None
    user_prompt: str
    attachments: list[LlmAttachment]
    output_mode: Literal["text", "json"]
    output_schema: dict[str, Any] | None
    model: str | None
    temperature: float | None
    max_tokens: int


@dataclass(frozen=True)
class LlmResponse:
    """Normalized response envelope for LLM calls."""

    text: str
    json_payload: dict[str, Any] | None
    raw: dict[str, Any] | None

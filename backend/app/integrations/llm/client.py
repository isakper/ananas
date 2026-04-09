"""Generic LLM integration client boundary."""

from __future__ import annotations

import base64
import json
import ssl
import urllib.error
import urllib.request
from typing import Protocol

from backend.app.integrations.llm.types import LlmRequest, LlmResponse


class LlmGateway(Protocol):
    """Contract for LLM calls used by domain services."""

    def call_llm(self, request: LlmRequest) -> LlmResponse:
        """Perform one model call and return normalized response output."""


class AnthropicLlmGateway:
    """Native Claude API implementation of the shared LLM gateway."""

    def __init__(self, api_key: str, model: str, verify_ssl: bool = True) -> None:
        key = api_key.strip()
        if key == "":
            raise ValueError("ANTHROPIC_API_KEY is required")
        self._api_key = key
        self._model = model
        if verify_ssl:
            self._ssl_context = ssl.create_default_context()
        else:
            self._ssl_context = ssl._create_unverified_context()

    def call_llm(self, request: LlmRequest) -> LlmResponse:
        """Call Claude Messages API and normalize text/JSON outputs."""
        content_blocks = []
        for attachment in request.attachments:
            encoded = base64.b64encode(attachment.path.read_bytes()).decode("utf-8")
            content_blocks.append(
                {
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": attachment.media_type,
                        "data": encoded,
                    },
                }
            )
        content_blocks.append({"type": "text", "text": request.user_prompt})

        payload: dict[str, object] = {
            "model": request.model or self._model,
            "max_tokens": request.max_tokens,
            "messages": [{"role": "user", "content": content_blocks}],
        }
        if request.system_prompt is not None:
            payload["system"] = request.system_prompt
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.output_mode == "json" and request.output_schema is not None:
            payload["output_config"] = {
                "format": {
                    "type": "json_schema",
                    "schema": request.output_schema,
                }
            }

        request_body = json.dumps(payload).encode("utf-8")
        http_request = urllib.request.Request(
            url="https://api.anthropic.com/v1/messages",
            data=request_body,
            method="POST",
            headers={
                "content-type": "application/json",
                "x-api-key": self._api_key,
                "anthropic-version": "2023-06-01",
            },
        )

        try:
            with urllib.request.urlopen(
                http_request,
                context=self._ssl_context,
                timeout=60,
            ) as response:
                raw_payload = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8")
            raise RuntimeError(
                f"LLM call failed with status {exc.code}: {detail}"
            ) from exc
        except urllib.error.URLError as exc:
            reason = str(exc.reason)
            if "CERTIFICATE_VERIFY_FAILED" in reason:
                raise RuntimeError(
                    "LLM TLS verification failed. Ensure your local trust store "
                    "includes your company proxy/root CA (for example Zscaler)."
                ) from exc
            raise RuntimeError(f"LLM call failed: {reason}") from exc

        parsed_payload = json.loads(raw_payload)
        text = _extract_text_from_response(parsed_payload)
        json_payload = _parse_json_payload(text=text, mode=request.output_mode)
        return LlmResponse(
            text=text,
            json_payload=json_payload,
            raw=parsed_payload if isinstance(parsed_payload, dict) else None,
        )


def _extract_text_from_response(response_payload: object) -> str:
    if not isinstance(response_payload, dict):
        return ""
    content = response_payload.get("content")
    if not isinstance(content, list):
        return ""
    text_chunks: list[str] = []
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") != "text":
            continue
        text = block.get("text")
        if isinstance(text, str):
            text_chunks.append(text)
    return "".join(text_chunks)


def _parse_json_payload(text: str, mode: str) -> dict[str, object] | None:
    if mode != "json":
        return None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None
    if isinstance(parsed, dict):
        return parsed
    return None

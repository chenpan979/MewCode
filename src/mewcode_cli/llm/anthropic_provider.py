"""Anthropic Messages protocol adapter."""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from typing import Any

from anthropic import AsyncAnthropic

from mewcode_cli.config import ProviderConfig
from mewcode_cli.llm import Message
from mewcode_cli.prompt import SYSTEM_PROMPT


class AnthropicProvider:
    def __init__(self, config: ProviderConfig, *, client: Any | None = None) -> None:
        self._config = config
        if client is None:
            options: dict[str, Any] = {
                "api_key": config.api_key,
                "max_retries": 0,
            }
            if config.base_url:
                options["base_url"] = config.base_url
            client = AsyncAnthropic(**options)
        self._client = client

    @property
    def name(self) -> str:
        return self._config.name

    @property
    def model(self) -> str:
        return self._config.model

    async def stream(self, messages: Sequence[Message]) -> AsyncIterator[str]:
        params: dict[str, Any] = {
            "model": self.model,
            "max_tokens": 4096,
            "system": SYSTEM_PROMPT,
            "messages": [
                {"role": message.role, "content": message.content} for message in messages
            ],
        }
        if self._config.thinking:
            params["thinking"] = {"type": "enabled", "budget_tokens": 2048}

        async with self._client.messages.stream(**params) as stream:
            async for event in stream:
                if getattr(event, "type", None) != "content_block_delta":
                    continue
                delta = getattr(event, "delta", None)
                if getattr(delta, "type", None) == "text_delta":
                    text = getattr(delta, "text", "")
                    if text:
                        yield text

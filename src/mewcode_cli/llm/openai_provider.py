"""OpenAI Chat Completions protocol adapter."""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from typing import Any

from openai import AsyncOpenAI

from mewcode_cli.config import ProviderConfig
from mewcode_cli.llm import Message
from mewcode_cli.prompt import SYSTEM_PROMPT


class OpenAIProvider:
    def __init__(self, config: ProviderConfig, *, client: Any | None = None) -> None:
        self._config = config
        if client is None:
            options: dict[str, Any] = {
                "api_key": config.api_key,
                "max_retries": 0,
            }
            if config.base_url:
                options["base_url"] = config.base_url
            client = AsyncOpenAI(**options)
        self._client = client

    @property
    def name(self) -> str:
        return self._config.name

    @property
    def model(self) -> str:
        return self._config.model

    async def stream(self, messages: Sequence[Message]) -> AsyncIterator[str]:
        request_messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *({"role": message.role, "content": message.content} for message in messages),
        ]
        stream = await self._client.chat.completions.create(
            model=self.model,
            messages=request_messages,
            stream=True,
        )
        async for chunk in stream:
            choices = getattr(chunk, "choices", None)
            if not choices:
                continue
            content = getattr(choices[0].delta, "content", None)
            if content:
                yield content

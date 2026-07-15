"""Protocol-independent LLM interfaces."""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from typing import Literal, Protocol

from mewcode_cli.config import ProviderConfig


@dataclass(frozen=True, slots=True)
class Message:
    role: Literal["user", "assistant"]
    content: str


class Provider(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def model(self) -> str: ...

    def stream(self, messages: Sequence[Message]) -> AsyncIterator[str]: ...


def new_provider(config: ProviderConfig) -> Provider:
    """Create the adapter selected by a validated provider config."""
    if config.protocol == "anthropic":
        from mewcode_cli.llm.anthropic_provider import AnthropicProvider

        return AnthropicProvider(config)
    if config.protocol == "openai":
        from mewcode_cli.llm.openai_provider import OpenAIProvider

        return OpenAIProvider(config)
    raise ValueError(f"不支持的 provider protocol: {config.protocol}")


def safe_error_text(error: BaseException, api_key: str = "") -> str:
    """Return a bounded, key-redacted error suitable for the conversation UI."""
    detail = str(error).strip() or error.__class__.__name__
    if api_key:
        detail = detail.replace(api_key, "***")
    if len(detail) > 800:
        detail = f"{detail[:797]}..."
    return f"{error.__class__.__name__}: {detail}"


__all__ = ["Message", "Provider", "new_provider", "safe_error_text"]

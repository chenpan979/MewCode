from __future__ import annotations

from collections.abc import AsyncIterator
from types import SimpleNamespace
from typing import Any, cast

import pytest

from mewcode_cli.config import ProviderConfig
from mewcode_cli.llm import Message, new_provider, safe_error_text
from mewcode_cli.llm.anthropic_provider import AnthropicProvider
from mewcode_cli.llm.openai_provider import OpenAIProvider
from mewcode_cli.prompt import SYSTEM_PROMPT


class AsyncEvents:
    def __init__(self, events: list[Any]) -> None:
        self.events = events

    def __aiter__(self) -> AsyncIterator[Any]:
        return self._iterate()

    async def _iterate(self) -> AsyncIterator[Any]:
        for event in self.events:
            yield event


class AsyncContext:
    def __init__(self, events: list[Any]) -> None:
        self.stream = AsyncEvents(events)

    async def __aenter__(self) -> AsyncEvents:
        return self.stream

    async def __aexit__(self, *_: object) -> None:
        return None


class FakeAnthropicMessages:
    def __init__(self, events: list[Any]) -> None:
        self.events = events
        self.params: dict[str, Any] = {}

    def stream(self, **params: Any) -> AsyncContext:
        self.params = params
        return AsyncContext(self.events)


class FakeAnthropicClient:
    def __init__(self, events: list[Any]) -> None:
        self.messages = FakeAnthropicMessages(events)


class FakeCompletions:
    def __init__(self, chunks: list[Any]) -> None:
        self.chunks = chunks
        self.params: dict[str, Any] = {}

    async def create(self, **params: Any) -> AsyncEvents:
        self.params = params
        return AsyncEvents(self.chunks)


class FakeOpenAIClient:
    def __init__(self, chunks: list[Any]) -> None:
        self.chat = SimpleNamespace(completions=FakeCompletions(chunks))


def config(protocol: str, *, thinking: bool = False) -> ProviderConfig:
    return ProviderConfig(
        name="test",
        protocol=cast(Any, protocol),
        api_key="top-secret",
        model="model-test",
        base_url="https://example.test/v1",
        thinking=thinking,
    )


@pytest.mark.asyncio
async def test_anthropic_stream_keeps_only_text_and_sends_thinking() -> None:
    events = [
        SimpleNamespace(type="message_start"),
        SimpleNamespace(
            type="content_block_delta",
            delta=SimpleNamespace(type="thinking_delta", thinking="hidden"),
        ),
        SimpleNamespace(
            type="content_block_delta",
            delta=SimpleNamespace(type="text_delta", text="hello"),
        ),
        SimpleNamespace(
            type="content_block_delta",
            delta=SimpleNamespace(type="text_delta", text=" world"),
        ),
    ]
    client = FakeAnthropicClient(events)
    provider = AnthropicProvider(config("anthropic", thinking=True), client=client)
    messages = (Message(role="user", content="hi"),)

    result = [part async for part in provider.stream(messages)]

    assert result == ["hello", " world"]
    assert client.messages.params["system"] == SYSTEM_PROMPT
    assert client.messages.params["messages"] == [{"role": "user", "content": "hi"}]
    assert client.messages.params["thinking"] == {
        "type": "enabled",
        "budget_tokens": 2048,
    }


@pytest.mark.asyncio
async def test_openai_stream_injects_system_and_skips_empty_chunks() -> None:
    chunks = [
        SimpleNamespace(choices=[]),
        SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=None))]),
        SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="answer"))]),
    ]
    client = FakeOpenAIClient(chunks)
    provider = OpenAIProvider(config("openai"), client=client)

    result = [part async for part in provider.stream((Message(role="user", content="question"),))]

    assert result == ["answer"]
    params = client.chat.completions.params
    assert params["stream"] is True
    assert params["messages"][0] == {"role": "system", "content": SYSTEM_PROMPT}
    assert params["messages"][1] == {"role": "user", "content": "question"}


def test_sdk_clients_disable_retries_and_apply_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    anthropic_options: dict[str, Any] = {}
    openai_options: dict[str, Any] = {}

    def fake_anthropic(**options: Any) -> object:
        anthropic_options.update(options)
        return object()

    def fake_openai(**options: Any) -> object:
        openai_options.update(options)
        return object()

    monkeypatch.setattr("mewcode_cli.llm.anthropic_provider.AsyncAnthropic", fake_anthropic)
    monkeypatch.setattr("mewcode_cli.llm.openai_provider.AsyncOpenAI", fake_openai)

    AnthropicProvider(config("anthropic"))
    OpenAIProvider(config("openai"))

    assert anthropic_options["max_retries"] == 0
    assert anthropic_options["base_url"] == "https://example.test/v1"
    assert openai_options["max_retries"] == 0
    assert openai_options["base_url"] == "https://example.test/v1"


def test_factory_and_error_redaction() -> None:
    assert isinstance(new_provider(config("anthropic")), AnthropicProvider)
    assert isinstance(new_provider(config("openai")), OpenAIProvider)

    with pytest.raises(ValueError, match="不支持"):
        new_provider(config("other"))

    error = RuntimeError("request contained top-secret and failed")
    rendered = safe_error_text(error, "top-secret")
    assert "top-secret" not in rendered
    assert "***" in rendered

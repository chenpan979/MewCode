from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Sequence

import pytest
from textual.pilot import Pilot
from textual.widgets import OptionList

from mewcode_cli.config import ProviderConfig
from mewcode_cli.llm import Message
from mewcode_cli.prompt import SYSTEM_PROMPT
from mewcode_cli.tui import MewCodeApp, SessionState
from mewcode_cli.tui.input import PromptTextArea


class FakeProvider:
    def __init__(
        self,
        config: ProviderConfig,
        *,
        parts: tuple[str, ...] = ("hello", " **world**"),
        error: Exception | None = None,
    ) -> None:
        self.name = config.name
        self.model = config.model
        self.parts = parts
        self.error = error
        self.received: list[tuple[Message, ...]] = []

    async def stream(self, messages: Sequence[Message]) -> AsyncIterator[str]:
        self.received.append(tuple(messages))
        await asyncio.sleep(0)
        if self.error is not None:
            raise self.error
        for part in self.parts:
            yield part
            await asyncio.sleep(0)


def provider_config(name: str = "Claude", model: str = "model-a") -> ProviderConfig:
    return ProviderConfig(
        name=name,
        protocol="anthropic",
        api_key="not-a-real-key",
        model=model,
    )


async def wait_for_idle(pilot: Pilot[None], app: MewCodeApp) -> None:
    for _ in range(100):
        await pilot.pause(0.01)
        if app.session_state is SessionState.IDLE:
            return
    raise AssertionError("app did not return to IDLE")


@pytest.mark.asyncio
async def test_single_provider_stream_commits_successful_turn() -> None:
    config = provider_config()
    fake = FakeProvider(config)
    app = MewCodeApp([config], provider_factory=lambda _: fake, cwd="C:/workspace")

    async with app.run_test(size=(100, 35)) as pilot:
        assert app.session_state is SessionState.IDLE
        prompt = app.query_one("#input", PromptTextArea)
        prompt.load_text("question")
        await pilot.press("enter")
        await wait_for_idle(pilot, app)

        assert app.conversation.messages() == (
            Message(role="user", content="question"),
            Message(role="assistant", content="hello **world**"),
        )
        assert fake.received == [(Message(role="user", content="question"),)]
        assert prompt.disabled is False
        assert prompt.text == ""


@pytest.mark.asyncio
async def test_failed_turn_restores_input_without_committing_history() -> None:
    config = provider_config()
    fake = FakeProvider(config, error=RuntimeError("bad not-a-real-key"))
    app = MewCodeApp([config], provider_factory=lambda _: fake)

    async with app.run_test(size=(100, 35)) as pilot:
        prompt = app.query_one("#input", PromptTextArea)
        prompt.load_text("will fail")
        await pilot.press("enter")
        await wait_for_idle(pilot, app)

        assert app.conversation.messages() == ()
        assert prompt.disabled is False


@pytest.mark.asyncio
async def test_multiple_providers_require_selection() -> None:
    first = provider_config("First", "model-1")
    second = provider_config("Second", "model-2")
    created: list[str] = []

    def factory(config: ProviderConfig) -> FakeProvider:
        created.append(config.name)
        return FakeProvider(config)

    app = MewCodeApp([first, second], provider_factory=factory)

    async with app.run_test(size=(100, 35)) as pilot:
        assert app.session_state is SessionState.SELECTING
        options = app.query_one("#provider-list", OptionList)
        options.highlighted = 1
        await pilot.press("enter")
        await pilot.pause()

        assert app.session_state is SessionState.IDLE
        assert app.provider_config == second
        assert created == ["Second"]


@pytest.mark.asyncio
async def test_alt_enter_inserts_newline() -> None:
    config = provider_config()
    app = MewCodeApp([config], provider_factory=lambda value: FakeProvider(value))

    async with app.run_test(size=(100, 35)) as pilot:
        prompt = app.query_one("#input", PromptTextArea)
        prompt.load_text("first")
        prompt.move_cursor((0, 5))
        await pilot.press("alt+enter")

        assert prompt.text == "first\n"
        assert app.conversation.messages() == ()


@pytest.mark.asyncio
async def test_prompt_accepts_chinese_unicode() -> None:
    config = provider_config()
    app = MewCodeApp([config], provider_factory=lambda value: FakeProvider(value))

    async with app.run_test(size=(100, 35)) as pilot:
        prompt = app.query_one("#input", PromptTextArea)
        await pilot.press("你", "好")

        assert prompt.text == "你好"


def test_system_prompt_defaults_to_simplified_chinese() -> None:
    assert "始终使用简体中文回答" in SYSTEM_PROMPT

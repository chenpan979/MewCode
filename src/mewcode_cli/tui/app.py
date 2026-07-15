"""Textual application and chat session state machine."""

from __future__ import annotations

import asyncio
import os
import sys
import time
from collections.abc import Callable
from enum import Enum
from typing import ClassVar

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.driver import Driver
from textual.timer import Timer
from textual.widgets import OptionList, RichLog, Static
from textual.widgets.option_list import Option
from textual.worker import Worker

from mewcode_cli import __version__
from mewcode_cli.config import ProviderConfig
from mewcode_cli.conversation import Conversation
from mewcode_cli.llm import Message, Provider, new_provider
from mewcode_cli.prompt import render_banner
from mewcode_cli.tui.input import PromptTextArea
from mewcode_cli.tui.view import (
    assistant_block,
    error_block,
    status_bar,
    streaming_block,
    user_block,
)

type ProviderFactory = Callable[[ProviderConfig], Provider]


def _ime_driver_class() -> type[Driver] | None:
    if sys.platform != "win32":
        return None
    from mewcode_cli.tui.windows_ime_driver import WindowsImeDriver

    return WindowsImeDriver


class SessionState(Enum):
    SELECTING = "selecting"
    IDLE = "idle"
    STREAMING = "streaming"


class MewCodeApp(App[None]):
    TITLE = "MewCode"
    SUB_TITLE = "Phase 1 Chat"

    CSS = """
    Screen {
        layout: vertical;
        background: $surface;
        color: $text;
    }

    #picker {
        width: 100%;
        height: 100%;
        align: center middle;
        padding: 2;
    }

    #picker-title {
        width: 72;
        max-width: 95%;
        height: auto;
        padding: 1 2;
        border: round $accent;
        text-align: center;
        text-style: bold;
    }

    #provider-list {
        width: 72;
        max-width: 95%;
        height: auto;
        max-height: 70%;
        border: round $accent;
    }

    #chat {
        width: 100%;
        height: 100%;
    }

    #log {
        width: 100%;
        height: 1fr;
        padding: 1 2;
        scrollbar-size: 1 1;
    }

    #streaming {
        width: 100%;
        height: auto;
        max-height: 45%;
        padding: 0 3 1 3;
        overflow-y: auto;
    }

    #prompt-row {
        width: 100%;
        height: 5;
        min-height: 3;
        max-height: 9;
        margin: 0 2;
        border: round $accent;
    }

    #prompt-symbol {
        width: 3;
        height: 100%;
        padding: 1 0 0 1;
        color: $accent;
        text-style: bold;
    }

    #input {
        width: 1fr;
        height: 100%;
        border: none;
        background: transparent;
        padding: 0 1;
    }

    #input:disabled {
        opacity: 55%;
    }

    #statusbar {
        width: 100%;
        height: 1;
        padding: 0 2;
        background: $boost;
    }
    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("ctrl+c", "quit", "Quit", show=False, priority=True),
    ]

    def __init__(
        self,
        providers: tuple[ProviderConfig, ...] | list[ProviderConfig],
        *,
        provider_factory: ProviderFactory = new_provider,
        cwd: str | None = None,
    ) -> None:
        if not providers:
            raise ValueError("providers 不能为空")
        super().__init__(driver_class=_ime_driver_class())
        self.providers = tuple(providers)
        self.provider_factory = provider_factory
        self.cwd = cwd or os.getcwd()
        self.session_state = SessionState.SELECTING
        self.provider: Provider | None = None
        self.provider_config: ProviderConfig | None = None
        self.conversation = Conversation()
        self.current_user = ""
        self.current_reply = ""
        self.turn_started = 0.0
        self._stream_worker: Worker[None] | None = None
        self._timer: Timer | None = None

    def compose(self) -> ComposeResult:
        options = [
            Option(f"{provider.name}  ·  {provider.model}", id=str(index))
            for index, provider in enumerate(self.providers)
        ]
        with Vertical(id="picker"):
            yield Static("Choose a provider", id="picker-title")
            yield OptionList(*options, id="provider-list")

        with Vertical(id="chat"):
            yield RichLog(id="log", wrap=True, markup=False, min_width=1)
            yield Static(id="streaming")
            with Horizontal(id="prompt-row"):
                yield Static("❯", id="prompt-symbol")
                yield PromptTextArea(
                    id="input",
                    placeholder="输入消息… (Alt+Enter 换行)",
                    soft_wrap=True,
                    show_line_numbers=False,
                    tab_behavior="focus",
                )
            yield Static(id="statusbar")

    def on_mount(self) -> None:
        if len(self.providers) == 1:
            self._activate_provider(0)
        else:
            self._show_picker()

    def _show_picker(self) -> None:
        self.session_state = SessionState.SELECTING
        self.query_one("#picker").display = True
        self.query_one("#chat").display = False
        self.query_one("#provider-list", OptionList).focus()

    def _activate_provider(self, index: int) -> None:
        config = self.providers[index]
        provider = self.provider_factory(config)
        self.provider_config = config
        self.provider = provider
        self.session_state = SessionState.IDLE

        self.query_one("#picker").display = False
        self.query_one("#chat").display = True
        self.query_one("#log", RichLog).write(render_banner(__version__, self.cwd))
        self.query_one("#statusbar", Static).update(status_bar(provider.name, provider.model))
        self.query_one("#input", PromptTextArea).focus()

    @on(OptionList.OptionSelected, "#provider-list")
    def select_provider(self, event: OptionList.OptionSelected) -> None:
        if event.option.id is None:
            return
        self._activate_provider(int(event.option.id))

    @on(PromptTextArea.Submitted, "#input")
    def submit_prompt(self, event: PromptTextArea.Submitted) -> None:
        if self.session_state is not SessionState.IDLE:
            return
        text = event.value.strip()
        if not text:
            return
        if text == "/exit":
            self.action_quit()
            return
        self._start_turn(text)

    def _start_turn(self, text: str) -> None:
        if self.provider is None:
            raise RuntimeError("provider 尚未选择")

        prompt = self.query_one("#input", PromptTextArea)
        self.query_one("#log", RichLog).write(user_block(text))
        prompt.load_text("")
        prompt.disabled = True

        self.current_user = text
        self.current_reply = ""
        self.turn_started = time.monotonic()
        self.session_state = SessionState.STREAMING
        self._refresh_streaming()
        self._timer = self.set_interval(0.2, self._refresh_streaming)
        messages = self.conversation.pending(text)
        self._stream_worker = self.run_worker(
            self._consume_stream(messages),
            name="provider-stream",
            exclusive=True,
            exit_on_error=False,
        )

    async def _consume_stream(self, messages: tuple[Message, ...]) -> None:
        assert self.provider is not None
        try:
            async for text in self.provider.stream(messages):
                self.current_reply += text
                self._refresh_streaming()
            if not self.current_reply.strip():
                raise RuntimeError("provider 返回了空回复")
            self._finish_success()
        except asyncio.CancelledError:
            raise
        except Exception as error:
            self._finish_error(error)

    def _refresh_streaming(self) -> None:
        if self.session_state is not SessionState.STREAMING:
            return
        elapsed = time.monotonic() - self.turn_started
        self.query_one("#streaming", Static).update(streaming_block(self.current_reply, elapsed))

    def _finish_success(self) -> None:
        elapsed = time.monotonic() - self.turn_started
        reply = self.current_reply
        self.query_one("#log", RichLog).write(assistant_block(reply, elapsed))
        self.conversation.commit(self.current_user, reply)
        self._reset_after_turn()

    def _finish_error(self, error: BaseException) -> None:
        elapsed = time.monotonic() - self.turn_started
        api_key = self.provider_config.api_key if self.provider_config else ""
        self.query_one("#log", RichLog).write(error_block(error, elapsed, api_key))
        self._reset_after_turn()

    def _reset_after_turn(self) -> None:
        self._stop_timer()
        self._stream_worker = None
        self.current_user = ""
        self.current_reply = ""
        self.query_one("#streaming", Static).update("")
        prompt = self.query_one("#input", PromptTextArea)
        prompt.disabled = False
        self.session_state = SessionState.IDLE
        prompt.focus()

    def _stop_timer(self) -> None:
        if self._timer is not None:
            self._timer.stop()
            self._timer = None

    def action_quit(self) -> None:
        if self._stream_worker is not None:
            self._stream_worker.cancel()
            self._stream_worker = None
        self._stop_timer()
        self.exit()

    def on_unmount(self) -> None:
        self._stop_timer()
        if self._stream_worker is not None:
            self._stream_worker.cancel()

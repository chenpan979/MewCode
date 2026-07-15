from __future__ import annotations

import sys

import pytest
from prompt_toolkit.key_binding.key_processor import KeyPress
from prompt_toolkit.keys import Keys
from textual import events
from textual.drivers import win32

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows-only driver")

from mewcode_cli.tui.windows_ime_driver import (  # noqa: E402
    WindowsKeyTranslator,
    ime_console_mode,
)


def test_ime_console_mode_disables_vt_but_keeps_window_and_mouse_events() -> None:
    current = (
        win32.ENABLE_ECHO_INPUT
        | win32.ENABLE_LINE_INPUT
        | win32.ENABLE_PROCESSED_INPUT
        | win32.ENABLE_QUICK_EDIT_MODE
        | win32.ENABLE_VIRTUAL_TERMINAL_INPUT
    )

    mode = ime_console_mode(current)

    assert mode & win32.ENABLE_WINDOW_INPUT
    assert mode & win32.ENABLE_MOUSE_INPUT
    assert mode & win32.ENABLE_EXTENDED_FLAGS
    assert not mode & win32.ENABLE_VIRTUAL_TERMINAL_INPUT
    assert not mode & win32.ENABLE_LINE_INPUT
    assert not mode & win32.ENABLE_ECHO_INPUT


def test_translator_emits_chinese_textual_key_without_rewriting() -> None:
    translated = list(WindowsKeyTranslator().feed(KeyPress("你", "你")))

    assert len(translated) == 1
    assert isinstance(translated[0], events.Key)
    assert translated[0].key == "你"
    assert translated[0].character == "你"


def test_translator_preserves_unicode_paste() -> None:
    translated = list(WindowsKeyTranslator().feed(KeyPress(Keys.BracketedPaste, "中文\nEnglish")))

    assert len(translated) == 1
    assert isinstance(translated[0], events.Paste)
    assert translated[0].text == "中文\nEnglish"


def test_translator_converts_legacy_mouse_record() -> None:
    translated = list(
        WindowsKeyTranslator().feed(KeyPress(Keys.WindowsMouseEvent, "LEFT;MOUSE_DOWN;4;5"))
    )

    assert len(translated) == 1
    assert isinstance(translated[0], events.MouseDown)
    assert translated[0].screen_x == 4
    assert translated[0].screen_y == 5
    assert translated[0].button == 1

"""Textual Windows driver that preserves native IME composition."""

from __future__ import annotations

import shutil
import sys
import time
from collections.abc import Callable, Iterable
from threading import Event, Thread
from typing import TYPE_CHECKING, ClassVar

from prompt_toolkit.input.win32 import ConsoleInputReader
from prompt_toolkit.key_binding.key_processor import KeyPress
from prompt_toolkit.keys import Keys
from textual import constants, events
from textual._xterm_parser import XTermParser
from textual.drivers import win32
from textual.drivers._writer_thread import WriterThread
from textual.drivers.windows_driver import WindowsDriver
from textual.geometry import Size

if TYPE_CHECKING:
    from textual.app import App


def ime_console_mode(current_mode: int, *, mouse: bool = True) -> int:
    """Return raw Win32 input flags without virtual-terminal input."""
    disabled = (
        win32.ENABLE_ECHO_INPUT
        | win32.ENABLE_LINE_INPUT
        | win32.ENABLE_PROCESSED_INPUT
        | win32.ENABLE_QUICK_EDIT_MODE
        | win32.ENABLE_VIRTUAL_TERMINAL_INPUT
    )
    mode = current_mode & ~disabled
    mode |= win32.ENABLE_EXTENDED_FLAGS | win32.ENABLE_WINDOW_INPUT
    if mouse:
        mode |= win32.ENABLE_MOUSE_INPUT
    else:
        mode &= ~win32.ENABLE_MOUSE_INPUT
    return mode


def enable_ime_application_mode(*, mouse: bool = True) -> Callable[[], None]:
    """Enable Textual output while keeping legacy Win32 Unicode input."""
    terminal_in = sys.__stdin__
    terminal_out = sys.__stdout__
    current_in = win32.get_console_mode(terminal_in)
    current_out = win32.get_console_mode(terminal_out)

    def restore() -> None:
        win32.set_console_mode(terminal_in, current_in)
        win32.set_console_mode(terminal_out, current_out)

    win32.set_console_mode(
        terminal_out,
        current_out | win32.ENABLE_VIRTUAL_TERMINAL_PROCESSING,
    )
    win32.set_console_mode(terminal_in, ime_console_mode(current_in, mouse=mouse))
    return restore


class WindowsKeyTranslator:
    """Translate prompt_toolkit Win32 key records into Textual events."""

    _BUTTONS: ClassVar[dict[str, int]] = {
        "LEFT": 1,
        "MIDDLE": 2,
        "RIGHT": 3,
        "NONE": 0,
        "UNKNOWN": 0,
    }

    def __init__(self) -> None:
        self._parser = XTermParser(debug=constants.DEBUG)
        self._last_mouse = (0, 0)
        self._pressed_button = 0

    def feed(self, key_press: KeyPress) -> Iterable[events.Event]:
        if key_press.key == Keys.BracketedPaste:
            return (events.Paste(key_press.data),)
        if key_press.key == Keys.WindowsMouseEvent:
            mouse_event = self._mouse_event(key_press.data)
            return () if mouse_event is None else (mouse_event,)
        if not key_press.data:
            return ()
        return tuple(self._parser.feed(key_press.data))

    def tick(self) -> Iterable[events.Event]:
        return tuple(self._parser.tick())

    def _mouse_event(self, data: str) -> events.Event | None:
        try:
            button_name, event_name, x_text, y_text = data.split(";", 3)
            x, y = int(x_text), int(y_text)
        except (TypeError, ValueError):
            return None

        button = self._BUTTONS.get(button_name, 0)
        if event_name == "MOUSE_DOWN":
            self._pressed_button = button
        elif event_name == "MOUSE_UP":
            button = self._pressed_button or button
            self._pressed_button = 0

        last_x, last_y = self._last_mouse
        self._last_mouse = (x, y)
        event_class = {
            "MOUSE_DOWN": events.MouseDown,
            "MOUSE_UP": events.MouseUp,
            "MOUSE_MOVE": events.MouseMove,
            "SCROLL_UP": events.MouseScrollUp,
            "SCROLL_DOWN": events.MouseScrollDown,
        }.get(event_name)
        if event_class is None:
            return None
        return event_class(
            None,
            x,
            y,
            x - last_x,
            y - last_y,
            button,
            False,
            False,
            False,
        )


class WindowsImeEventMonitor(Thread):
    """Poll legacy Win32 records and forward translated events to Textual."""

    def __init__(
        self,
        app: App,
        exit_event: Event,
        process_event: Callable[[events.Event], None],
    ) -> None:
        super().__init__(name="mewcode-ime-input")
        self.app = app
        self.exit_event = exit_event
        self.process_event = process_event

    def run(self) -> None:
        reader = ConsoleInputReader(recognize_paste=True)
        translator = WindowsKeyTranslator()
        terminal_size = shutil.get_terminal_size((80, 24))
        next_size_check = 0.0
        try:
            while not self.exit_event.is_set():
                for key_press in reader.read():
                    for event in translator.feed(key_press):
                        self.process_event(event)
                for event in translator.tick():
                    self.process_event(event)

                now = time.monotonic()
                if now >= next_size_check:
                    new_size = shutil.get_terminal_size((80, 24))
                    if new_size != terminal_size:
                        terminal_size = new_size
                        size = Size(new_size.columns, new_size.lines)
                        self.process_event(events.Resize(size, size))
                    next_size_check = now + 0.1
                self.exit_event.wait(0.01)
        except Exception as error:
            self.app.log.error("IME EVENT MONITOR ERROR", error)
        finally:
            reader.close()


class WindowsImeDriver(WindowsDriver):
    """Windows Textual driver with native IME-compatible input."""

    def start_application_mode(self) -> None:
        self._restore_console = enable_ime_application_mode(mouse=self._mouse)
        self._writer_thread = WriterThread(self._file)
        self._writer_thread.start()

        self.write("\x1b[?1049h")
        self.write("\x1b[?25l")
        self.flush()
        self._enable_bracketed_paste()

        self._event_thread = WindowsImeEventMonitor(
            self._app,
            self.exit_event,
            self.process_message,
        )
        self._event_thread.start()

    def disable_input(self) -> None:
        try:
            if not self.exit_event.is_set():
                self.exit_event.set()
                if self._event_thread is not None:
                    self._event_thread.join()
                    self._event_thread = None
                self.exit_event.clear()
        except Exception:
            pass

    def stop_application_mode(self) -> None:
        self._disable_bracketed_paste()
        self.disable_input()
        self.write("\x1b[?1049l\x1b[?25h")
        self.flush()

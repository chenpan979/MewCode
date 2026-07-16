from __future__ import annotations

import os
import sys
from typing import Any

if sys.platform == "win32":
    from ctypes import byref, wintypes

    from textual import constants
    from textual._xterm_parser import XTermParser
    from textual.drivers import win32 as _win32
    from textual.drivers.windows_driver import WindowsDriver as _BaseDriver
else:
    from textual.drivers.linux_driver import LinuxDriver as _BaseDriver


def _windows_key_text(key_event: Any) -> str:
    """Return committed Unicode text, including IME-generated characters."""
    if not key_event.bKeyDown:
        return ""
    return key_event.uChar.UnicodeChar or ""


if sys.platform == "win32":

    class _IMEEventMonitor(_win32.EventMonitor):
        """Textual event monitor that preserves Windows IME Unicode events."""

        def run(self) -> None:
            exit_requested = self.exit_event.is_set
            parser = XTermParser(debug=constants.DEBUG)

            try:
                read_count = wintypes.DWORD(0)
                input_handle = _win32.GetStdHandle(_win32.STD_INPUT_HANDLE)
                max_events = 1024
                input_records = (_win32.INPUT_RECORD * max_events)()
                read_console_input = _win32.KERNEL32.ReadConsoleInputW
                keys: list[str] = []

                while not exit_requested():
                    for event in parser.tick():
                        self.process_event(event)

                    if _win32.wait_for_handles([input_handle], 100) is None:
                        continue

                    read_console_input(
                        input_handle,
                        byref(input_records),
                        max_events,
                        byref(read_count),
                    )
                    records = input_records[: read_count.value]

                    keys.clear()
                    new_size: tuple[int, int] | None = None
                    for record in records:
                        if record.EventType == 0x0001:
                            key = _windows_key_text(record.Event.KeyEvent)
                            if key:
                                keys.append(key)
                        elif record.EventType == 0x0004:
                            size = record.Event.WindowBufferSizeEvent.dwSize
                            new_size = (size.X, size.Y)

                    if keys:
                        text = "".join(keys)
                        for event in parser.feed(
                            text.encode("utf-16", "surrogatepass").decode("utf-16")
                        ):
                            self.process_event(event)

                    if new_size is not None:
                        self.on_size_change(*new_size)
            except Exception as error:
                self.app.log.error("IME EVENT MONITOR ERROR", error)


class NoAltScreenDriver(_BaseDriver):
    """Keep terminal history while providing Windows IME-compatible input."""

    def start_application_mode(self) -> None:
        try:
            rows = os.get_terminal_size().lines
        except OSError:
            rows = 24

        sys.stdout.write("\n" * rows)
        sys.stdout.flush()

        if sys.platform == "win32":
            original_monitor = _win32.EventMonitor
            _win32.EventMonitor = _IMEEventMonitor
            try:
                super().start_application_mode()
            finally:
                _win32.EventMonitor = original_monitor

            # Windows positions IME composition UI at the real terminal caret.
            self.write("\x1b[?25h")
            self.flush()
        else:
            super().start_application_mode()

    def write(self, data: str) -> None:
        data = data.replace("\x1b[?1049h", "").replace("\x1b[?1049l", "")
        if data:
            super().write(data)

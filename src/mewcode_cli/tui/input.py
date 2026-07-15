"""Chat prompt input widget."""

from __future__ import annotations

from typing import ClassVar

from textual.binding import Binding
from textual.message import Message
from textual.widgets import TextArea


class PromptTextArea(TextArea):
    """A multiline text area where Enter submits and Alt+Enter inserts a newline."""

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("enter", "submit", "Submit", show=False, priority=True),
        Binding("alt+enter", "newline", "New line", show=False, priority=True),
        *TextArea.BINDINGS,
    ]

    class Submitted(Message):
        def __init__(self, text_area: PromptTextArea, value: str) -> None:
            super().__init__()
            self.text_area = text_area
            self.value = value

        @property
        def control(self) -> PromptTextArea:
            return self.text_area

    def action_submit(self) -> None:
        self.post_message(self.Submitted(self, self.text))

    def action_newline(self) -> None:
        self.insert("\n")

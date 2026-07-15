"""In-memory, success-only conversation history."""

from __future__ import annotations

from mewcode_cli.llm import Message


class Conversation:
    def __init__(self) -> None:
        self._messages: list[Message] = []

    def pending(self, user_text: str) -> tuple[Message, ...]:
        """Build a request snapshot without mutating committed history."""
        text = _non_empty(user_text, "user_text")
        return (*self._messages, Message(role="user", content=text))

    def commit(self, user_text: str, assistant_text: str) -> None:
        """Atomically commit one complete user/assistant turn."""
        user = _non_empty(user_text, "user_text")
        assistant = _non_empty(assistant_text, "assistant_text")
        self._messages.extend(
            (
                Message(role="user", content=user),
                Message(role="assistant", content=assistant),
            )
        )

    def messages(self) -> tuple[Message, ...]:
        return tuple(self._messages)


def _non_empty(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} 不能为空")
    return value.strip()

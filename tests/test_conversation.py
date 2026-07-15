import pytest

from mewcode_cli.conversation import Conversation
from mewcode_cli.llm import Message


def test_pending_does_not_mutate_history() -> None:
    conversation = Conversation()

    pending = conversation.pending(" first ")

    assert pending == (Message(role="user", content="first"),)
    assert conversation.messages() == ()


def test_commit_preserves_turn_order_and_returns_tuple() -> None:
    conversation = Conversation()
    conversation.commit("one", "answer one")
    conversation.commit("two", "answer two")

    assert conversation.messages() == (
        Message(role="user", content="one"),
        Message(role="assistant", content="answer one"),
        Message(role="user", content="two"),
        Message(role="assistant", content="answer two"),
    )


@pytest.mark.parametrize(("user", "assistant"), [("", "ok"), ("ok", "   ")])
def test_commit_rejects_incomplete_turn(user: str, assistant: str) -> None:
    conversation = Conversation()

    with pytest.raises(ValueError):
        conversation.commit(user, assistant)

    assert conversation.messages() == ()

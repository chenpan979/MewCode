from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

from mewcode.app import MewCodeApp, _set_windows_native_cursor
from mewcode.config import ProviderConfig
from mewcode.driver import _windows_key_text


class _Driver:
    def __init__(self) -> None:
        self.output: list[str] = []
        self.flush_count = 0

    def write(self, value: str) -> None:
        self.output.append(value)

    def flush(self) -> None:
        self.flush_count += 1


def _provider(name: str = "provider") -> ProviderConfig:
    return ProviderConfig(
        name=name,
        protocol="openai-compat",
        base_url="https://example.invalid/v1",
        model="test-model",
        api_key="top-secret-key",
    )


def test_native_cursor_visibility_sequences() -> None:
    driver = _Driver()
    app = SimpleNamespace(_driver=driver)

    _set_windows_native_cursor(app, True)
    _set_windows_native_cursor(app, False)

    assert driver.output == ["\x1b[?25h", "\x1b[?25l"]
    assert driver.flush_count == 2


def test_ime_generated_unicode_is_not_filtered() -> None:
    key_event = SimpleNamespace(
        bKeyDown=True,
        wVirtualKeyCode=0,
        dwControlKeyState=0x00800000,
        uChar=SimpleNamespace(UnicodeChar="中"),
    )

    assert _windows_key_text(key_event) == "中"


def test_empty_control_key_is_ignored() -> None:
    key_event = SimpleNamespace(
        bKeyDown=True,
        wVirtualKeyCode=0,
        dwControlKeyState=0x10,
        uChar=SimpleNamespace(UnicodeChar=""),
    )

    assert _windows_key_text(key_event) == ""


def test_duplicate_provider_selection_is_ignored(monkeypatch) -> None:
    selected = _provider("selected")
    app = MewCodeApp.__new__(MewCodeApp)
    app._selected_provider = selected
    create_client = Mock()
    monkeypatch.setattr("mewcode.app.create_client", create_client)

    app._select_provider(_provider("duplicate"))

    create_client.assert_not_called()
    assert app._selected_provider is selected


def test_provider_repr_hides_api_key() -> None:
    rendered = repr(_provider())
    assert "top-secret-key" not in rendered
    assert "api_key" not in rendered

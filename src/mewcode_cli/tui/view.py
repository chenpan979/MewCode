"""Pure Rich renderable builders for the TUI."""

from __future__ import annotations

from rich.console import Group, RenderableType
from rich.markdown import Markdown
from rich.table import Table
from rich.text import Text

from mewcode_cli.llm import safe_error_text


def user_block(text: str) -> RenderableType:
    table = Table.grid(padding=(0, 1))
    table.add_column(width=2)
    table.add_column(ratio=1, overflow="fold")
    table.add_row(Text("❯", style="bold bright_magenta"), Text(text, style="bold"))
    return Group(table, Text())


def assistant_block(text: str, elapsed: float) -> RenderableType:
    return Group(
        Markdown(text),
        Text(f"Completed in {elapsed:.1f}s", style="dim cyan"),
        Text(),
    )


def error_block(error: BaseException, elapsed: float, api_key: str) -> RenderableType:
    return Group(
        Text("Request failed", style="bold red"),
        Text(safe_error_text(error, api_key), style="red"),
        Text(f"Failed after {elapsed:.1f}s", style="dim red"),
        Text(),
    )


def streaming_block(text: str, elapsed: float) -> RenderableType:
    status = Text(f"Imagining… ({int(elapsed)}s)", style="bold bright_cyan")
    if not text:
        return status
    return Group(Text(text), status)


def status_bar(provider_name: str, model: str) -> RenderableType:
    table = Table.grid(expand=True)
    table.add_column(ratio=1)
    table.add_column(justify="right")
    table.add_row(
        Text(provider_name, style="bold bright_magenta"),
        Text(model, style="cyan"),
    )
    return table

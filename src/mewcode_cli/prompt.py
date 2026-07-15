"""Built-in prompts and the startup banner."""

from rich.console import Group
from rich.text import Text

SYSTEM_PROMPT = """你是 MewCode, 一个运行在终端中的 AI 编程助手。
除非用户明确要求使用其他语言, 否则始终使用简体中文回答。
回答应清晰、准确; Markdown 能提升可读性时请使用 Markdown。
不要声称拥有当前对话中并不存在的工具、文件或权限。"""

CAT_BANNER = r""" /\_/\\
( o.o )
 > ^ <"""


def render_banner(version: str, cwd: str) -> Group:
    """Build the startup banner as Rich renderables."""
    cat = Text(CAT_BANNER, style="bold bright_cyan")
    title = Text.assemble(
        ("MewCode ", "bold bright_magenta"),
        (f"v{version}", "bold white"),
    )
    location = Text.assemble(("cwd  ", "dim"), (cwd, "cyan"))
    ready = Text("准备就绪, 可以开始提问。", style="green")
    return Group(cat, title, location, ready, Text())

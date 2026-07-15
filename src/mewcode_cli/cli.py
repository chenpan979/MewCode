"""Command-line entry point."""

from __future__ import annotations

import sys
from pathlib import Path

from mewcode_cli.config import ConfigError, load
from mewcode_cli.tui import MewCodeApp

DEFAULT_CONFIG_PATH = Path(".mewcode/config.yaml")


def main() -> None:
    try:
        config = load(DEFAULT_CONFIG_PATH)
    except ConfigError as error:
        print(f"MewCode 配置错误: {error}", file=sys.stderr)
        raise SystemExit(2) from None

    MewCodeApp(config.providers).run()

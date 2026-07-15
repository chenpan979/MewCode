"""YAML configuration loading and validation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml

type ProtocolName = Literal["anthropic", "openai"]


class ConfigError(ValueError):
    """Raised when the MewCode configuration cannot be loaded safely."""


@dataclass(frozen=True, slots=True)
class ProviderConfig:
    name: str
    protocol: ProtocolName
    api_key: str
    model: str
    base_url: str | None = None
    thinking: bool = False


@dataclass(frozen=True, slots=True)
class Config:
    providers: tuple[ProviderConfig, ...]


def load(path: str | Path) -> Config:
    """Load a config file and return a fully validated immutable snapshot."""
    config_path = Path(path)
    try:
        raw_text = config_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ConfigError(f"配置文件不存在: {config_path}") from exc
    except OSError as exc:
        raise ConfigError(f"无法读取配置文件 {config_path}: {exc}") from exc

    try:
        document = yaml.safe_load(raw_text)
    except yaml.YAMLError as exc:
        detail = getattr(exc, "problem", None) or "YAML 格式无效"
        raise ConfigError(f"配置文件解析失败 {config_path}: {detail}") from exc

    root = _mapping(document, "配置根节点")
    raw_providers = root.get("providers")
    if not isinstance(raw_providers, list) or not raw_providers:
        raise ConfigError("providers 必须是非空列表")

    providers = tuple(
        _provider(_mapping(raw_provider, f"providers[{index}]"), index)
        for index, raw_provider in enumerate(raw_providers)
    )
    return Config(providers=providers)


def _mapping(value: object, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ConfigError(f"{field} 必须是对象")
    return value


def _provider(raw: dict[str, Any], index: int) -> ProviderConfig:
    prefix = f"providers[{index}]"
    name = _required_string(raw, "name", prefix)
    protocol_value = _required_string(raw, "protocol", prefix)
    if protocol_value not in {"anthropic", "openai"}:
        raise ConfigError(f"{prefix}.protocol 必须是 anthropic 或 openai")

    api_key = _required_string(raw, "api_key", prefix)
    model = _required_string(raw, "model", prefix)

    base_url_value = raw.get("base_url")
    if base_url_value is None:
        base_url = None
    elif isinstance(base_url_value, str) and base_url_value.strip():
        base_url = base_url_value.strip().rstrip("/")
    else:
        raise ConfigError(f"{prefix}.base_url 必须是非空字符串或省略")

    thinking_value = raw.get("thinking", False)
    if not isinstance(thinking_value, bool):
        raise ConfigError(f"{prefix}.thinking 必须是布尔值")

    return ProviderConfig(
        name=name,
        protocol=protocol_value,
        api_key=api_key,
        model=model,
        base_url=base_url,
        thinking=thinking_value,
    )


def _required_string(raw: dict[str, Any], field: str, prefix: str) -> str:
    value = raw.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{prefix}.{field} 必须是非空字符串")
    return value.strip()

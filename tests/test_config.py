from pathlib import Path

import pytest

from mewcode_cli.config import ConfigError, load


def write_config(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "config.yaml"
    path.write_text(content, encoding="utf-8")
    return path


def test_load_valid_providers(tmp_path: Path) -> None:
    path = write_config(
        tmp_path,
        """
providers:
  - name: Claude
    protocol: anthropic
    api_key: secret-a
    model: claude-test
    thinking: true
  - name: Compatible
    protocol: openai
    api_key: secret-b
    model: model-b
    base_url: https://example.test/v1/
""",
    )

    config = load(path)

    assert len(config.providers) == 2
    assert config.providers[0].thinking is True
    assert config.providers[1].base_url == "https://example.test/v1"


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("{}", "providers 必须是非空列表"),
        ("providers: []", "providers 必须是非空列表"),
        ("providers: [42]", "providers[0] 必须是对象"),
        (
            "providers: [{name: A, protocol: other, api_key: x, model: m}]",
            "providers[0].protocol",
        ),
        (
            "providers: [{name: A, protocol: openai, model: m}]",
            "providers[0].api_key",
        ),
        (
            'providers: [{name: A, protocol: openai, api_key: x, model: m, thinking: "yes"}]',
            "providers[0].thinking",
        ),
    ],
)
def test_invalid_config_has_precise_error(tmp_path: Path, content: str, message: str) -> None:
    path = write_config(tmp_path, content)

    with pytest.raises(ConfigError, match=r".*") as caught:
        load(path)

    assert message in str(caught.value)


def test_missing_file_is_readable_error(tmp_path: Path) -> None:
    missing = tmp_path / "missing.yaml"

    with pytest.raises(ConfigError) as caught:
        load(missing)

    assert "配置文件不存在" in str(caught.value)
    assert str(missing) in str(caught.value)


def test_bad_yaml_is_wrapped(tmp_path: Path) -> None:
    path = write_config(tmp_path, "providers: [")

    with pytest.raises(ConfigError, match="配置文件解析失败"):
        load(path)

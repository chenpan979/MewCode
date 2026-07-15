from pathlib import Path

import pytest

from mewcode_cli import cli


def test_missing_default_config_exits_cleanly(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)

    with pytest.raises(SystemExit) as caught:
        cli.main()

    captured = capsys.readouterr()
    assert caught.value.code == 2
    assert "MewCode 配置错误" in captured.err
    assert "配置文件不存在" in captured.err
    assert "Traceback" not in captured.err

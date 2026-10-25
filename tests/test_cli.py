from __future__ import annotations

import json
from pathlib import Path

import pytest

from cloudhub.cli import main


def test_list_shows_builtin_task(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["list"]) == 0
    assert "hello" in capsys.readouterr().out


def test_check_outputs_json(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["check"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert "hello" in payload["tasks"]
    assert "version" in payload


def test_run_hello_writes_artifact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    out_dir = tmp_path / "out"
    monkeypatch.setenv("CLOUDHUB_OUTPUT_DIR", str(out_dir))
    assert main(["run", "hello", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["pushed"] is True
    assert (out_dir / "hello.json").is_file()


def test_run_dry_run_does_not_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    out_dir = tmp_path / "out"
    monkeypatch.setenv("CLOUDHUB_OUTPUT_DIR", str(out_dir))
    assert main(["run", "hello", "--dry-run"]) == 0
    assert "dry-run" in capsys.readouterr().out
    assert not out_dir.exists()


def test_run_unknown_task_returns_2(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["run", "no-such-task"]) == 2
    assert "未知任务" in capsys.readouterr().err

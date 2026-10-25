from __future__ import annotations

from pathlib import Path

import pytest

from cloudhub.config import Settings


def test_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "CLOUDHUB_OUTPUT_DIR",
        "CLOUDHUB_LOG_LEVEL",
        "CLOUDHUB_CHANNEL",
        "CLOUDHUB_DRY_RUN",
        "GITHUB_ACTIONS",
    ):
        monkeypatch.delenv(key, raising=False)

    settings = Settings.from_env()
    assert settings.output_dir == Path("output")
    assert settings.log_level == "INFO"
    assert settings.channel == "auto"
    assert settings.dry_run is False
    assert settings.ci is False


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("1", True), ("true", True), ("YES", True), ("0", False), ("", False)],
)
def test_dry_run_flags(monkeypatch: pytest.MonkeyPatch, raw: str, expected: bool) -> None:
    monkeypatch.setenv("CLOUDHUB_DRY_RUN", raw)
    assert Settings.from_env().dry_run is expected


def test_github_context_is_collected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_REPOSITORY", "youzunzhang/cloud-hub")
    monkeypatch.setenv("GITHUB_RUN_ID", "42")

    settings = Settings.from_env()
    assert settings.ci is True
    assert settings.github["repository"] == "youzunzhang/cloud-hub"
    assert settings.github["run_id"] == "42"


def test_ensure_output_dir_creates(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "deep" / "nested"
    monkeypatch.setenv("CLOUDHUB_OUTPUT_DIR", str(target))
    assert Settings.from_env().ensure_output_dir() == target
    assert target.is_dir()


def test_settings_is_frozen() -> None:
    settings = Settings.from_env()
    with pytest.raises(AttributeError):
        settings.channel = "smtp"  # type: ignore[misc]

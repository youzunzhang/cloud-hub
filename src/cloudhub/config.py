"""运行配置：一律来自环境变量，便于 GitHub Actions 传入 / Secrets 注入。

约定前缀 ``CLOUDHUB_``，例如：

    CLOUDHUB_OUTPUT_DIR=output
    CLOUDHUB_LOG_LEVEL=INFO
    CLOUDHUB_CHANNEL=auto

宿主环境（GitHub Actions）自带的变量通过 ``Settings.ci`` 暴露，
任务实现里不需要自己判断 ``os.environ["GITHUB_ACTIONS"]``。
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

ENV_PREFIX = "CLOUDHUB_"


def _env(key: str, default: str = "") -> str:
    return os.environ.get(f"{ENV_PREFIX}{key}", default)


def _env_bool(key: str, default: bool = False) -> bool:
    raw = _env(key).strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class Settings:
    """运行时配置快照（不可变，任务之间不会互相污染）。"""

    output_dir: Path = Path("output")
    log_level: str = "INFO"
    channel: str = "auto"
    dry_run: bool = False
    ci: bool = False
    github: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> Settings:
        output_dir = Path(_env("OUTPUT_DIR", "output")).expanduser()
        github_keys = {
            "repository": "GITHUB_REPOSITORY",
            "ref_name": "GITHUB_REF_NAME",
            "sha": "GITHUB_SHA",
            "run_id": "GITHUB_RUN_ID",
            "actor": "GITHUB_ACTOR",
            "server_url": "GITHUB_SERVER_URL",
            "event_name": "GITHUB_EVENT_NAME",
        }
        github = {
            alias: os.environ[key] for alias, key in github_keys.items() if os.environ.get(key)
        }
        return cls(
            output_dir=output_dir,
            log_level=_env("LOG_LEVEL", "INFO").upper(),
            channel=_env("CHANNEL", "auto").lower(),
            dry_run=_env_bool("DRY_RUN"),
            ci=os.environ.get("GITHUB_ACTIONS") == "true",
            github=github,
        )

    def ensure_output_dir(self) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        return self.output_dir

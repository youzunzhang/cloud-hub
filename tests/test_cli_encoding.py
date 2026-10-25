from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_cli_survives_non_utf8_stdio() -> None:
    """回归用例：stdout 被重定向且码表非 UTF-8 时，打印中文不得崩溃。

    这条对应 CI 上 ``test (py3.13 / windows-latest)`` 的真实故障：
    Windows 运行器是 en-US，Python 输出被重定向时使用 cp1252，
    打印全角字符抛 ``UnicodeEncodeError`` 导致退出码 1。
    用 ``PYTHONIOENCODING=cp1252`` + 管道捕获，可在任意平台复现同一场景。
    """

    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "cp1252"
    env["PYTHONPATH"] = str(ROOT / "src")

    proc = subprocess.run(
        [sys.executable, "-m", "cloudhub", "run", "hello", "--dry-run", "--json"],
        capture_output=True,
        env=env,
        cwd=ROOT,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr.decode("utf-8", "replace")
    assert b"hello" in proc.stdout

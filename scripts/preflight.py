"""环境预检：把「现状检查」变成一条可反复执行的命令。

    python scripts/preflight.py
    python scripts/preflight.py --json
    python scripts/preflight.py --deep      # 额外探测 PyPI 与 gh CLI

退出码：0 = 关键项全部通过；1 = 存在关键项失败。

设计要点（本机实测踩坑）：
- WorkBuddy 宿主会注入 HTTP_PROXY/HTTPS_PROXY=http://127.0.0.1:8522，该端口无监听，
  任何走代理的请求都会卡 15 秒。本脚本默认**忽略代理环境变量**，直连探测。
- github.com 的 443 网页端口在本网络不通，但 ssh.github.com:443 / api.github.com /
  *.github.io 通 —— 所以判断「GitHub 可用」不能只看 https://github.com。
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path

TIMEOUT = 8
PROXY_KEYS = ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy")


@dataclass
class Check:
    name: str
    ok: bool
    detail: str
    critical: bool = True
    fix: str = ""


@dataclass
class Report:
    checks: list[Check] = field(default_factory=list)

    def add(self, check: Check) -> None:
        self.checks.append(check)

    @property
    def failed(self) -> list[Check]:
        return [c for c in self.checks if not c.ok]

    @property
    def critical_failed(self) -> list[Check]:
        return [c for c in self.failed if c.critical]


def _opener() -> urllib.request.OpenerDirector:
    """直连 opener：显式忽略任何代理设置。"""
    return urllib.request.build_opener(urllib.request.ProxyHandler({}))


def _http(url: str, headers: dict[str, str] | None = None) -> tuple[int, str]:
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "cloudhub-preflight"})
    with _opener().open(req, timeout=TIMEOUT) as resp:
        return resp.status, resp.read(4096).decode("utf-8", "replace")


def check_python() -> Check:
    info = f"{sys.version.split()[0]} @ {sys.executable}"
    ok = sys.version_info >= (3, 11)
    return Check("Python >= 3.11", ok, info, fix="安装 3.11+ 并在 venv 中运行")


def check_git() -> Check:
    exe = shutil.which("git")
    if not exe:
        return Check("git", False, "未找到 git", fix="安装 Git for Windows")
    out = subprocess.run([exe, "--version"], capture_output=True, text=True, check=False)
    return Check("git", out.returncode == 0, out.stdout.strip() or out.stderr.strip())


def check_gh() -> Check:
    exe = shutil.which("gh")
    if not exe:
        return Check(
            "gh CLI",
            False,
            "未安装（非必需：仓库初始化走 REST API + SSH）",
            critical=False,
            fix="winget install --id GitHub.cli -e（需管理员）或用便携版",
        )
    out = subprocess.run([exe, "--version"], capture_output=True, text=True, check=False)
    return Check("gh CLI", out.returncode == 0, out.stdout.splitlines()[0], critical=False)


def check_ssh_key() -> Check:
    key = Path.home() / ".ssh" / "id_ed25519.pub"
    if not key.is_file():
        return Check("SSH 公钥", False, str(key), fix="ssh-keygen -t ed25519 -C youzunzhang")
    return Check("SSH 公钥", True, key.read_text(encoding="utf-8").strip()[:60] + "…")


def check_ssh_auth() -> Check:
    try:
        proc = subprocess.run(
            ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", "-T", "git@github.com"],
            capture_output=True,
            text=True,
            timeout=25,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return Check(
            "GitHub SSH 认证", False, f"{type(exc).__name__}: {exc}", fix="检查 ~/.ssh/config"
        )
    text = (proc.stdout + proc.stderr).strip()
    ok = "successfully authenticated" in text
    return Check("GitHub SSH 认证", ok, text.splitlines()[-1] if text else "无输出")


def check_api() -> Check:
    try:
        status, _ = _http("https://api.github.com/rate_limit")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return Check("api.github.com", False, str(exc), fix="检查 DNS / 防火墙")
    return Check("api.github.com", status == 200, f"HTTP {status}")


def check_rate_limit() -> Check:
    try:
        status, body = _http("https://api.github.com/rate_limit")
        core = json.loads(body)["resources"]["core"]
    except Exception as exc:  # noqa: BLE001 - 预检脚本需要兜住一切异常
        return Check("API 认证状态", False, f"读取失败：{exc}", critical=False)
    limit = core["limit"]
    authed = limit > 60
    detail = f"core 限额 {limit}/h，剩余 {core['remaining']} → {'已认证' if authed else '匿名'}"
    return Check(
        "API 认证状态",
        authed,
        detail,
        critical=False,
        fix="导出 GH_TOKEN=<PAT> 后可提额到 5000/h，并能创建仓库",
    )


def check_web() -> Check:
    """github.com 网页端口：本网络不通属预期，标记为非关键。"""
    sock = socket.socket()
    sock.settimeout(TIMEOUT)
    try:
        sock.connect(("github.com", 443))
        return Check("github.com:443", True, "可连通", critical=False)
    except OSError as exc:
        return Check(
            "github.com:443",
            False,
            f"不可达（{exc.__class__.__name__}）→ 必须走 SSH 通道",
            critical=False,
            fix="无需修复；已改用 ssh.github.com:443 与 REST API",
        )
    finally:
        sock.close()


def check_pages_domain() -> Check:
    try:
        socket.gethostbyname("github.io")
    except OSError as exc:
        return Check("*.github.io 解析", False, str(exc), critical=False, fix="检查 DNS")
    return Check("*.github.io 解析", True, "DNS 正常", critical=False)


def check_proxy_env() -> Check:
    set_keys = [k for k in PROXY_KEYS if os.environ.get(k)]
    if not set_keys:
        return Check("代理环境变量", True, "未设置", critical=False)
    values = {k: os.environ[k] for k in set_keys}
    return Check(
        "代理环境变量",
        False,
        f"已注入 {values}（若端口无监听会导致 pip/curl 全部超时）",
        critical=False,
        fix="env -u HTTP_PROXY -u HTTPS_PROXY NO_PROXY='*' <命令>",
    )


def check_venv() -> Check:
    venv = Path(__file__).resolve().parent.parent / ".venv"
    if not venv.is_dir():
        return Check("本地 venv", False, "未创建 .venv", critical=False, fix="python -m venv .venv")
    py = venv / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    return Check("本地 venv", py.is_file(), str(py), critical=False)


def check_pypi() -> Check:
    try:
        status, _ = _http("https://pypi.org/simple/")
    except Exception as exc:  # noqa: BLE001
        return Check(
            "PyPI 源", False, f"{type(exc).__name__}", critical=False, fix="换镜像或走代理"
        )
    return Check(
        "PyPI 源", status == 200, f"HTTP {status}（本机实测较慢，约 20 KB/s）", critical=False
    )


def build_report(deep: bool) -> Report:
    report = Report()
    report.add(check_python())
    report.add(check_git())
    report.add(check_ssh_key())
    report.add(check_ssh_auth())
    report.add(check_api())
    report.add(check_rate_limit())
    report.add(check_web())
    report.add(check_pages_domain())
    report.add(check_proxy_env())
    report.add(check_venv())
    report.add(check_gh())
    if deep:
        report.add(check_pypi())
    return report


def print_table(report: Report) -> None:
    print(f"{'检查项':<22} {'结果':<6} {'关键':<4} 说明")
    print("-" * 96)
    for c in report.checks:
        flag = "PASS" if c.ok else ("FAIL" if c.critical else "WARN")
        print(f"{c.name:<22} {flag:<6} {'是' if c.critical else '否':<4} {c.detail}")
    fixes = [c for c in report.checks if not c.ok and c.fix]
    if fixes:
        print("\n修复建议：")
        for c in fixes:
            print(f"  - {c.name}: {c.fix}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="github 云端环境预检")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    parser.add_argument("--deep", action="store_true", help="额外探测 PyPI")
    args = parser.parse_args(argv)

    report = build_report(deep=args.deep)
    if args.json:
        print(json.dumps([asdict(c) for c in report.checks], ensure_ascii=False, indent=2))
    else:
        print_table(report)

    if report.critical_failed:
        print(f"\n[FAIL] {len(report.critical_failed)} 个关键项未通过")
        return 1
    print("\n[OK] 关键项全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())

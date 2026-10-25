"""本地质量门：与 CI 完全一致的 lint / format / test / build。

用法：
    python scripts/dev.py lint      # ruff check
    python scripts/dev.py fmt       # ruff format（改文件）
    python scripts/dev.py test      # pytest
    python scripts/dev.py build     # wheel + sdist + site.zip
    python scripts/dev.py all       # check + format --check + test + build

说明：脚本用当前解释器（``sys.executable``）调用同名模块，
所以先激活 venv 或直接用 ``.venv/Scripts/python scripts/dev.py``。
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
DIST = ROOT / "dist"
SITE_ZIP = ROOT / "site.zip"


def _run(cmd: list[str]) -> int:
    print(f"$ {' '.join(cmd)}", flush=True)
    return subprocess.run(cmd, cwd=ROOT, check=False).returncode


def _tool(name: str) -> list[str]:
    """优先用 venv 里的可执行文件，回退到 ``python -m``。"""
    exe = Path(sys.executable).parent / (name + (".exe" if sys.platform == "win32" else ""))
    if exe.is_file():
        return [str(exe)]
    return [sys.executable, "-m", name]


def task_lint() -> int:
    return _run([*_tool("ruff"), "check", "."])


def task_fmt(check_only: bool) -> int:
    args = [*_tool("ruff"), "format", "."]
    if check_only:
        args.insert(2, "--check")
    return _run(args)


def task_test() -> int:
    return _run([*_tool("pytest"), "-q"])


def task_build() -> int:
    DIST.mkdir(exist_ok=True)
    code = _run([*_tool("build")])
    if code != 0:
        return code
    if not SITE.is_dir():
        print("[WARN] 未找到 site/ 目录，跳过站点打包")
        return 0
    with zipfile.ZipFile(SITE_ZIP, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(SITE.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(SITE).as_posix())
    size_kb = SITE_ZIP.stat().st_size / 1024
    print(f"[OK] 站点已打包：{SITE_ZIP}（{size_kb:.1f} KB）")
    return 0


def task_clean() -> int:
    for target in (DIST, SITE_ZIP, ROOT / "build", ROOT / ".pytest_cache", ROOT / ".ruff_cache"):
        if target.is_dir():
            shutil.rmtree(target, ignore_errors=True)
            print(f"[OK] 已删除目录 {target}")
        elif target.is_file():
            target.unlink()
            print(f"[OK] 已删除文件 {target}")
    for cache in ROOT.rglob("__pycache__"):
        shutil.rmtree(cache, ignore_errors=True)
    return 0


def task_all() -> int:
    steps = (
        ("lint", task_lint),
        ("format --check", lambda: task_fmt(check_only=True)),
        ("test", task_test),
        ("build", task_build),
    )
    for name, step in steps:
        code = step()
        if code != 0:
            print(f"[FAIL] 质量门在 {name} 处中断（退出码 {code}）")
            return code
    print("[OK] 全部通过：lint / format / test / build")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="cloud-hub 本地质量门")
    parser.add_argument(
        "command",
        choices=["lint", "fmt", "test", "build", "clean", "all"],
        help="要执行的步骤",
    )
    args = parser.parse_args(argv)

    match args.command:
        case "lint":
            return task_lint()
        case "fmt":
            return task_fmt(check_only=False)
        case "test":
            return task_test()
        case "build":
            return task_build()
        case "clean":
            return task_clean()
        case "all":
            return task_all()
    return 2


if __name__ == "__main__":
    sys.exit(main())

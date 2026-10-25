"""命令行入口：``cloudhub <子命令>``。

子命令刻意保持很少，重点是 ``run`` —— 云端定时任务只需要一条命令：
    cloudhub run hello --json
退出码约定（供工作流与本地兜底脚本判定）：
    0  成功
    1  任务执行失败
    2  参数或环境错误
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from cloudhub import __version__
from cloudhub.config import Settings
from cloudhub.registry import all_tasks, get_task, load_builtin_tasks


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cloudhub",
        description="以 GitHub 为云端的任务执行器",
    )
    parser.add_argument("--version", action="version", version=f"cloudhub {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="列出已注册任务")
    sub.add_parser("check", help="打印当前运行配置（不含任何密钥）")

    run_p = sub.add_parser("run", help="执行一个任务")
    run_p.add_argument("task", help="任务名，见 `cloudhub list`")
    run_p.add_argument("--json", action="store_true", help="以 JSON 输出结果")
    run_p.add_argument("--dry-run", action="store_true", help="只演练，不落盘/不发送")

    return parser


def _cmd_list() -> int:
    tasks = all_tasks()
    if not tasks:
        print("（无已注册任务）")
        return 0
    width = max(len(name) for name in tasks)
    for name, cls in tasks.items():
        print(f"{name:<{width}}  {cls.description or '-'}")
    return 0


def _cmd_check(settings: Settings) -> int:
    info = {
        "version": __version__,
        "cwd": str(Path.cwd()),
        "output_dir": str(settings.output_dir),
        "channel": settings.channel,
        "log_level": settings.log_level,
        "dry_run": settings.dry_run,
        "ci": settings.ci,
        "github": settings.github,
        "tasks": list(all_tasks()),
    }
    print(json.dumps(info, ensure_ascii=False, indent=2))
    return 0


def _cmd_run(task_name: str, as_json: bool, dry_run: bool) -> int:
    settings = Settings.from_env()
    if dry_run:
        settings = Settings(
            output_dir=settings.output_dir,
            log_level=settings.log_level,
            channel=settings.channel,
            dry_run=True,
            ci=settings.ci,
            github=settings.github,
        )
    try:
        task_cls = get_task(task_name)
    except KeyError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2

    result = task_cls(settings).run()
    if as_json:
        print(json.dumps(result.as_dict(), ensure_ascii=False, indent=2))
    else:
        flag = "OK" if result.ok else "FAIL"
        print(f"[{flag}] {result.task}: {result.message}")
    return 0 if result.ok else 1


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    load_builtin_tasks()
    settings = Settings.from_env()

    if args.command == "list":
        return _cmd_list()
    if args.command == "check":
        return _cmd_check(settings)
    if args.command == "run":
        return _cmd_run(args.task, args.json, args.dry_run)

    parser.error(f"未知子命令：{args.command}")
    return 2

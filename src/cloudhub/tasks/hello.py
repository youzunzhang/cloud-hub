"""示例任务：自检用，同时演示「幂等键 + 产物落盘」的标准写法。

真正的业务任务应当照这个骨架来写：
1. 用 ``settings.output_dir`` 落盘产物（工作流再统一上传/发布）；
2. 幂等键取「任务名:日期」，已推过就返回 ``pushed=False``，不重复对外发送。
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from cloudhub.registry import Task, TaskResult, register_task

BEIJING = timezone(timedelta(hours=8))


@register_task("hello")
class HelloTask(Task):
    """输出一份最小可用的运行信息清单。"""

    description = "自检任务：打印运行环境并写出一份 JSON 产物"

    def run(self) -> TaskResult:
        now = datetime.now(BEIJING)
        payload = {
            "task": self.name,
            "idempotency_key": f"{self.name}:{now:%Y-%m-%d}",
            "generated_at": now.isoformat(timespec="seconds"),
            "channel": self.settings.channel,
            "dry_run": self.settings.dry_run,
            "ci": self.settings.ci,
            "github": self.settings.github,
        }

        if self.settings.dry_run:
            return TaskResult(
                task=self.name,
                ok=True,
                pushed=False,
                message="dry-run：未写出产物",
                data=payload,
            )

        out_dir = self.settings.ensure_output_dir()
        target = out_dir / "hello.json"
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

        return TaskResult(
            task=self.name,
            ok=True,
            pushed=True,
            message=f"已写出 {target}",
            data=payload,
        )

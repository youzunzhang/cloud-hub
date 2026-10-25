"""任务注册表：一个宿主托管 N 个任务，靠 task 名分发。

新增任务的完整动作只有两步：
1. 建一个模块继承 ``Task`` 并实现 ``run()``；
2. 用 ``@register_task("任务名")`` 装饰。

不需要改 CLI，也不需要改工作流的主循环。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from cloudhub.config import Settings


@dataclass(slots=True)
class TaskResult:
    """任务执行结果。``pushed`` 供幂等判定与上层编排使用。"""

    task: str
    ok: bool
    pushed: bool = False
    message: str = ""
    data: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "task": self.task,
            "ok": self.ok,
            "pushed": self.pushed,
            "message": self.message,
            "data": self.data,
        }


class Task(ABC):
    """任务基类。子类只需实现 ``run()``。"""

    name: str = ""
    description: str = ""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @abstractmethod
    def run(self) -> TaskResult:
        """执行任务并返回结果。不得在此处 ``sys.exit()``。"""

    def __repr__(self) -> str:
        return f"<Task {self.name}>"


_REGISTRY: dict[str, type[Task]] = {}


def register_task(name: str) -> Callable[[type[Task]], type[Task]]:
    """把任务类登记到全局注册表。重名直接报错，避免静默覆盖。"""

    if not name:
        raise ValueError("task name must not be empty")

    def _decorator(cls: type[Task]) -> type[Task]:
        if not issubclass(cls, Task):
            raise TypeError(f"{cls.__name__} 必须继承 cloudhub.registry.Task")
        if name in _REGISTRY and _REGISTRY[name] is not cls:
            raise ValueError(f"任务名重复注册：{name}")
        cls.name = name
        _REGISTRY[name] = cls
        return cls

    return _decorator


def get_task(name: str) -> type[Task]:
    try:
        return _REGISTRY[name]
    except KeyError as exc:
        known = ", ".join(sorted(_REGISTRY)) or "<无>"
        raise KeyError(f"未知任务：{name}（已注册：{known}）") from exc


def all_tasks() -> dict[str, type[Task]]:
    return dict(sorted(_REGISTRY.items()))


def load_builtin_tasks() -> None:
    """导入内置任务模块，触发装饰器注册。"""

    from cloudhub.tasks import hello  # noqa: F401  # 导入即注册

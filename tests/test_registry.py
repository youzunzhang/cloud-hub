from __future__ import annotations

import pytest

from cloudhub.registry import (
    Task,
    TaskResult,
    all_tasks,
    get_task,
    load_builtin_tasks,
    register_task,
)


class _ProbeTask(Task):
    """未装饰的探针任务，避免污染全局注册表。"""

    description = "测试用"

    def run(self) -> TaskResult:
        return TaskResult(task=self.name, ok=True)


def test_builtin_task_registered() -> None:
    load_builtin_tasks()
    assert "hello" in all_tasks()


def test_duplicate_registration_rejected() -> None:
    register_task("dup-probe")(_ProbeTask)

    class _AnotherTask(_ProbeTask):
        pass

    with pytest.raises(ValueError, match="重复注册"):
        register_task("dup-probe")(_AnotherTask)


def test_same_class_reregistration_is_idempotent() -> None:
    """模块被重复导入时会再次注册同一个类，应视为幂等而非报错。"""
    register_task("idem-probe")(_ProbeTask)
    register_task("idem-probe")(_ProbeTask)
    assert get_task("idem-probe") is _ProbeTask


def test_empty_name_rejected() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        register_task("")


def test_non_task_class_rejected() -> None:
    with pytest.raises(TypeError):
        register_task("bad-probe")(object)  # type: ignore[arg-type]


def test_get_task_unknown_lists_known() -> None:
    load_builtin_tasks()
    with pytest.raises(KeyError, match="未知任务"):
        get_task("nope")


def test_all_tasks_sorted() -> None:
    names = list(all_tasks())
    assert names == sorted(names)


def test_registered_task_carries_name() -> None:
    register_task("probe-named")(_ProbeTask)
    assert get_task("probe-named").name == "probe-named"


def test_task_result_roundtrip() -> None:
    result = TaskResult(task="x", ok=True, pushed=False, message="m", data={"k": 1})
    assert result.as_dict() == {
        "task": "x",
        "ok": True,
        "pushed": False,
        "message": "m",
        "data": {"k": 1},
    }

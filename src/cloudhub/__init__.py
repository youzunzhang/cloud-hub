"""cloudhub —— 以 GitHub 为默认云端的任务执行与交付基础框架。

设计取向：
- 一个入口托管 N 个任务，靠 task 名分发（不为每个任务建一套脚本）。
- 任务实现零第三方依赖，可直接在 GitHub Actions 的 ubuntu/windows 运行器上跑。
- 所有对外输出（HTML 交付物、构建产物）统一走 ``output/``，再由工作流上传/发布。
"""

from __future__ import annotations

__version__ = "0.1.0"
__all__ = ["__version__"]

# cloud-hub

以 **GitHub 为默认云端**的任务执行与交付基础框架。

- **一个入口托管 N 个任务**：`cloudhub run <task>`，靠任务名分发，不为每个任务新建一套脚本。
- **零运行时依赖**：只用 Python 标准库，GitHub Actions 运行器上开箱即跑。
- **交付形态固定**：产物统一落到 `output/`，由工作流上传为 Artifact / 发布到 Pages / 挂到 Release。
- **云端优先、本地兜底**：定时任务由 Actions `schedule` 驱动，本地可随时用同一条命令补跑。

## 目录结构

```
.
├── .github/
│   ├── workflows/          # CI / Pages / Release / 定时任务 / CodeQL
│   ├── ISSUE_TEMPLATE/     # 议题表单
│   ├── CODEOWNERS
│   ├── dependabot.yml      # 依赖与 Actions 版本自动升级
│   └── PULL_REQUEST_TEMPLATE.md
├── src/cloudhub/
│   ├── cli.py              # 命令行入口（list / check / run）
│   ├── config.py           # 环境变量配置（CLOUDHUB_* 前缀）
│   ├── registry.py         # 任务注册表与 Task 基类
│   └── tasks/hello.py      # 示例任务（幂等键 + 产物落盘）
├── tests/                  # pytest，23 个用例
├── site/                   # GitHub Pages 静态站点（单文件、无外部依赖）
├── scripts/
│   ├── dev.py              # lint / test / build 本地快捷入口
│   └── bootstrap_remote.py # 用 PAT 创建远程仓库并完成初始化
├── docs/                   # 现状检查报告 / 基础设施说明 / GitHub 功能清单
├── pyproject.toml          # 打包、ruff、pytest 单一配置源
└── CONTRIBUTING.md         # 提交规范与分支策略
```

## 快速开始

```bash
# 1. 建虚拟环境并装开发依赖
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"      # Windows
# source .venv/bin/activate && pip install -e ".[dev]" # macOS / Linux

# 2. 自检
cloudhub check          # 打印当前配置（不含密钥）
cloudhub list           # 列出已注册任务
cloudhub run hello      # 跑示例任务，产物写入 output/hello.json

# 3. 本地质量门（与 CI 完全一致）
python scripts/dev.py all
```

> **网络提示（本机实测）**：WorkBuddy 宿主会注入 `HTTP_PROXY/HTTPS_PROXY=http://127.0.0.1:8522`，
> 该端口无服务监听，所有走代理的 pip / curl 都会超时。安装依赖时请清掉：

```bash
env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy NO_PROXY='*' \
  .venv/Scripts/python -m pip install -e ".[dev]"
```

## 新增一个任务

```python
# src/cloudhub/tasks/my_task.py
from cloudhub.registry import Task, TaskResult, register_task


@register_task("my-task")
class MyTask(Task):
    description = "做什么，一句话"

    def run(self) -> TaskResult:
        out = self.settings.ensure_output_dir() / "my-task.json"
        out.write_text('{"ok": true}', encoding="utf-8")
        return TaskResult(task=self.name, ok=True, pushed=True, message=str(out))
```

再把模块名加进 `src/cloudhub/registry.py` 的 `load_builtin_tasks()`，然后在
`.github/workflows/scheduled-task.yml` 的 `with.task` 里填任务名即可。CI 主循环无需改动。

## 用到的 GitHub 功能

| 功能 | 用途 | 配置位置 |
|---|---|---|
| Repository | 代码与配置的唯一真源 | 由 `scripts/bootstrap_remote.py` 创建 |
| Branch protection | 保护 `main`：必须过 CI、禁止强推 | 脚本 `--protect` 参数 |
| GitHub Actions | CI（lint/test/build）、定时任务、发布 | `.github/workflows/ci.yml` 等 |
| Actions Cache | pip 依赖缓存，缩短流水线 | `setup-python` 的 `cache: pip` |
| Actions Artifacts | 保存 dist、站点包、任务产物 | `actions/upload-artifact@v4` |
| GitHub Pages | 托管 `site/` 静态交付物 | `.github/workflows/pages.yml` |
| Releases | 打 tag 自动生成发布页并附产物 | `.github/workflows/release.yml` |
| Issues 模板 / PR 模板 | 收集缺陷与需求、统一 PR 描述 | `.github/ISSUE_TEMPLATE/`、`PULL_REQUEST_TEMPLATE.md` |
| Dependabot | 自动升级 pip 依赖与 Actions 版本 | `.github/dependabot.yml` |
| CodeQL | Python 静态安全扫描 | `.github/workflows/codeql.yml` |
| CODEOWNERS | 自动指派评审人 | `.github/CODEOWNERS` |

详见 [`docs/03-GitHub功能清单.md`](docs/03-GitHub功能清单.md)。

## 待办与已知限制

- 仓库为**私有**时，GitHub Pages 需要 Pro/Team 套餐；Free 账号只能对公开仓库开 Pages。
- `github.com` 网页端口在本网络不通，**只能走 SSH**（`ssh.github.com:443`）与 REST API（`api.github.com`）。
- Release 附件的下载域名（`objects.githubusercontent.com`）在本网络不可达，下载需走 API 或代理。
- `LICENSE` 尚未添加，视仓库公开/私有决定。

## 许可

Proprietary（未定，暂不对外授权）。

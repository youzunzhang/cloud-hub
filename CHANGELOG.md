# 变更日志

格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

## [0.1.0] - 2026-10-25

### Added

- 项目骨架：`src/cloudhub`（CLI / 配置 / 任务注册表 / 示例任务）、`tests`、`site`、`scripts`、`docs`。
- `cloudhub` CLI：`list`（列任务）、`check`（打印配置）、`run <task>`（执行，支持 `--json` / `--dry-run`）。
- 任务注册表机制：一个宿主托管 N 个任务，靠任务名分发；重名注册与非法类型直接报错。
- 配置体系：`CLOUDHUB_*` 环境变量前缀，GitHub Actions 上下文自动映射为 `Settings.github`。
- 工程规范：`.gitignore`、`.gitattributes`、`.editorconfig`、`.gitmessage`、
  `pyproject.toml`（打包 + ruff + pytest 单一配置源）、`.pre-commit-config.yaml`。
- GitHub Actions 工作流：`ci.yml`（lint/test/build）、`pages.yml`（Pages 部署）、
  `release.yml`（tag → Release）、`scheduled-task.yml`（cron 定时任务）、`codeql.yml`（安全扫描）。
- 仓库治理：Dependabot、CODEOWNERS、PR 模板、Issue 表单。
- `scripts/bootstrap_remote.py`：用 PAT 经 REST API 创建远程仓库、关联 remote、推送、可选开启分支保护与 Pages。
- `scripts/dev.py`：本地 lint / test / build 快捷入口，与 CI 保持一致。
- `site/index.html`：单文件、无外部依赖的基础设施状态页，作为 Pages 部署通道的验证载体。

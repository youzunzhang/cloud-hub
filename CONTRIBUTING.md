# 贡献规范

## 一、分支策略（trunk-based）

| 分支 | 用途 | 生命周期 |
|---|---|---|
| `main` | 唯一长期分支，始终保持可发布 | 永久 |
| `feat/<slug>` | 新功能 | 合并后删除 |
| `fix/<slug>` | 缺陷修复 | 合并后删除 |
| `chore/<slug>` | 构建、配置、依赖、文档 | 合并后删除 |
| `hotfix/<slug>` | 线上紧急修复（从 tag 拉出） | 合并后删除 |
| `vX.Y.Z`（tag） | 发布锚点，触发 Release 工作流 | 永久 |

规则：

1. **任何改动都不直接推 `main`**，一律走 PR。
2. PR 合并方式统一用 **Squash and merge**，保证 `main` 上一条提交对应一个完整变更。
3. PR 标题即最终提交信息，必须符合下面的提交规范。
4. 删除分支交给 GitHub（仓库设置里勾选 *Automatically delete head branches*）。
5. 发布用 **SemVer** 打 tag：`v0.1.0` → 触发 `.github/workflows/release.yml`。

## 二、提交信息规范（Conventional Commits）

```
<type>(<scope>): <subject>

<body>

<footer>
```

- `type`：`feat` / `fix` / `docs` / `style` / `refactor` / `perf` / `test` / `build` / `ci` / `chore` / `revert`
- `scope`：受影响模块，如 `cli`、`registry`、`ci`、`pages`，可省略
- `subject`：≤ 50 字，祈使语气，句末不加句号
- `body`：说明**为什么改**与影响范围，而非复述改了什么
- `footer`：`BREAKING CHANGE: ...` 或 `Closes #123`

示例：

```
feat(registry): 支持按任务名前缀批量查询

定时任务需要在工作流里一次列出同族任务（如 daily-*），
逐个 import 太重，故在注册表加前缀索引。

Closes #12
```

启用提交模板（一次性）：

```bash
git config commit.template .gitmessage
```

## 三、质量门（本地必须与 CI 一致）

```bash
python scripts/dev.py all     # = ruff check + ruff format --check + pytest + build
```

CI 中额外跑：Python 3.11 / 3.12 / 3.13 × Ubuntu，以及 3.13 × Windows。

## 四、代码约定

- 仅用标准库；引入第三方运行时依赖需在 PR 里说明理由。
- 全部函数带类型注解，`from __future__ import annotations` 兜底。
- 行宽 100，由 `ruff format` 统一，不手工对齐。
- 不允许静默失败：任务出错必须返回 `ok=False` 并让 CLI 退出码非 0。
- 任何涉及密钥的读取一律走环境变量 / GitHub Secrets，禁止写进仓库。

## 五、评审

- `main` 至少 1 个 approving review（保护规则开启后强制）。
- 改动 `.github/workflows/` 必须单独说明，避免流水线被意外放宽。

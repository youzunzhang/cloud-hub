# GitHub 功能清单

本项目的默认云端方案完全建立在 GitHub 之上。下表逐项列出**用到的功能、用在哪、怎么验证**。

## 一、代码托管

| 功能 | 用途 | 配置位置 | 验证方式 |
|---|---|---|---|
| **Repository** | 代码与配置的唯一真源 | `scripts/bootstrap_remote.py`（API 创建）或网页新建 | `git remote -v` |
| **SSH 访问** | 唯一可用的 git 传输通道（443 端口） | `~/.ssh/config` 的 `Host github.com → ssh.github.com:443` | `ssh -T git@github.com` |
| **Branch protection** | 保护 `main`：禁强推、禁删除、需解决评论（⚠️ Free + 私有库不可用，见第五节） | `bootstrap_remote.py --protect` | 仓库 Settings → Branches |

| **Tags** | 发布锚点 `vX.Y.Z` | `git tag v0.1.0 && git push origin v0.1.0` | 仓库 Tags 页面 |
| **CODEOWNERS** | 自动指派评审人 | `.github/CODEOWNERS` | 提 PR 后观察 Reviewers |

## 二、自动化（Actions）

| 功能 | 用途 | 配置位置 | 验证方式 |
|---|---|---|---|
| **Workflows** | 5 条流水线：CI / Pages / Release / Scheduled / CodeQL | `.github/workflows/*.yml` | 仓库 Actions 页 |
| **Matrix** | Python 3.11/3.12/3.13 × Ubuntu + 3.13 × Windows | `ci.yml` 的 `strategy.matrix` | 一次 PR 触发 4 个 test job |
| **Concurrency** | 同分支新提交取消上一次运行 | `ci.yml` / `pages.yml` / `scheduled-task.yml` | 连续两次 push 观察前一次变 Cancelled |
| **Cache** | pip 依赖缓存 | `setup-python` 的 `cache: pip` | 第二次运行日志出现 `Cache restored` |
| **Artifacts** | 保存 dist、site.zip、任务产物 | `actions/upload-artifact@v4` | 运行详情页底部 Artifacts |
| **cron schedule** | 每日北京 07:00 执行任务（UTC 23:00） | `scheduled-task.yml` | Actions → Scheduled Task → 查看运行记录 |
| **workflow_dispatch** | 手动触发 + 传参（task / dry_run） | 同上 | Actions 页点 `Run workflow` |
| **Environments** | `github-pages` 环境承载部署 URL | `pages.yml` 的 `environment:` | 仓库 Settings → Environments |
| **Secrets / GITHUB_TOKEN** | 发布与 API 调用的自动凭据 | `release.yml` 的 `secrets.GITHUB_TOKEN` | 无需手工创建，权限由 `permissions:` 声明 |
| **permissions 最小化** | 每个工作流只申请必要权限 | 各工作流顶层 `permissions:` | 代码审查即可确认 |

## 三、发布与交付

| 功能 | 用途 | 配置位置 | 验证方式 |
|---|---|---|---|
| **GitHub Pages** | 托管 `site/` 静态交付物 | `.github/workflows/pages.yml` + Settings → Pages = GitHub Actions | 访问 `https://youzunzhang.github.io/cloud-hub/` |

| **Releases** | tag 触发自动发布，附 wheel/sdist/site.zip | `.github/workflows/release.yml`（用运行器自带 `gh` CLI） | 仓库 Releases 页 |
| **自动发布说明** | `gh release create --generate-notes` | 同上 | Release 正文自动生成变更列表 |

> **Pages 首次启用必须人工点一次（2026-10-25 实测确认）**
> `actions/configure-pages@v5` 的 `enablement` 输入在官方 `action.yml` 里写明：
> *"This option requires a token other than `GITHUB_TOKEN` to be provided."*
> —— 用工作流自带的 `GITHUB_TOKEN` **一定失败**。因此首次开通只能由仓库管理员在
> **Settings → Pages → Build and deployment → Source** 选 **GitHub Actions**，
> 之后工作流每次推送即可自动发布。


## 四、协作与治理

| 功能 | 用途 | 配置位置 | 验证方式 |
|---|---|---|---|
| **Issues + 表单** | 结构化的缺陷/需求收集 | `.github/ISSUE_TEMPLATE/*.yml` | New issue 时出现表单 |
| **PR 模板** | 统一 PR 描述与自检清单 | `.github/PULL_REQUEST_TEMPLATE.md` | 提 PR 时自动带入 |
| **Dependabot** | 每周自动升级 pip 依赖与 Actions 版本 | `.github/dependabot.yml` | 仓库 Insights → Dependency graph |
| **Code scanning (CodeQL)** | Python 静态安全扫描（⚠️ Free + 私有库不可用，见第五节） | `.github/workflows/codeql.yml` | Security → Code scanning |

## 五、个人 Free 账号的实际可用性（2026-10-25 核对官方文档）

**关键前提**：以下三项在「Free 计划 + 私有仓库」组合下**不可用**，只在公开仓库或付费计划下可用。
本项目默认按私有仓库设计，因此这三项属于「已配置但需换条件才生效」。

| 功能 | Free + 公开仓库 | Free + 私有仓库 | 官方依据 |
|---|---|---|---|
| GitHub Pages | ✅ 可用 | ❌ 不可用（需 Pro/Team/Enterprise） | What is GitHub Pages → Who can use this feature |
| Branch protection / Rulesets | ✅ 可用 | ❌ 不可用（需 Pro/Team/Enterprise） | Managing a branch protection rule；About rulesets |
| Code scanning (CodeQL) | ✅ 可用 | ❌ 不可用（需 GitHub Code Security 授权） | Code scanning → Who can use this feature |
| GitHub Actions | ✅ 不限量 | ✅ 2,000 分钟/月 | GitHub Actions billing |

**相应的免费替代方案**：

| 失效项 | 替代 |
|---|---|
| Pages | 改公开仓库 / 用 Release 附件分发 HTML / 升级 Pro |
| 分支保护 | 本地 `pre-commit` 钩子 + CI 失败即拒绝合并（靠流程约束） |
| CodeQL | 公开仓库启用；私有仓库改为 `ruff` + `pip-audit`（CI 内免费跑） |

## 六、REST API（绕开 gh CLI 的关键）


本机没有 gh CLI 且无管理员权限，因此仓库初始化直接用 REST API（`api.github.com`，实测直连可用）：

| 端点 | 用途 |
|---|---|
| `GET /user` | 校验 token、取登录名 |
| `POST /user/repos`（或 `/orgs/{org}/repos`） | 创建仓库 |
| `PATCH /repos/{owner}/{repo}` | 设置合并策略（仅 squash、合并后删分支） |
| `PUT /repos/{o}/{r}/branches/main/protection` | 开启分支保护（需 admin 权限） |
| `POST /repos/{o}/{r}/pages` | 启用 Pages，`build_type=workflow` |

封装在 `scripts/bootstrap_remote.py`，一条命令跑完：

```bash
set GH_TOKEN=github_pat_xxx
python scripts/bootstrap_remote.py --repo cloud-hub --protect --pages
```

## 七、未使用但已预留

| 功能 | 为什么不启用 | 什么情况下启用 |
|---|---|---|
| **GitHub Container Registry (ghcr.io)** | 当前交付物是 Python 包与静态站点，不需要镜像 | 需要交付可执行容器时 |
| **Packages (PyPI 镜像)** | 包不对外分发 | 需要多机共用同一版本时 |
| **Projects (看板)** | 单人项目，Issues 足够 | 任务量上升后 |
| **Discussions** | 无社区交流需求 | 仓库公开后 |
| **Self-hosted runner** | 公共运行器够用且免费额度充足 | 需要访问内网资源或 GPU 时 |

## 八、额度与费用提示

| 项 | 公共仓库 | 私有仓库（Free 套餐） |
|---|---|---|
| Actions 分钟数 | 无限 | 2,000 分钟/月 |
| Pages | 支持 | **不支持**（需 Pro/Team） |
| Code scanning | 支持 | 需 GitHub Advanced Security |
| Release 存储 | 无限制（单文件 ≤ 2 GB） | 同左 |
| API 匿名额度 | 60 次/小时/账户 | 同左（认证后 5,000） |

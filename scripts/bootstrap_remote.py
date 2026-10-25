"""用 PAT 经 GitHub REST API 完成「远程仓库初始化」这一唯一需要凭据的动作。

它做四件事（可分别开关）：
1. 创建远程仓库（默认私有）
2. 把本地 origin 指向 SSH 地址并推送 main
3. 设置仓库合并策略（只允许 squash、合并后自动删分支）
4. 可选：开启分支保护、开启 Pages（Source = GitHub Actions）

用法：
    # 交互式（推荐，token 不回显、不落盘）
    python scripts/bootstrap_remote.py

    # 非交互
    set GH_TOKEN=github_pat_xxx && python scripts/bootstrap_remote.py --repo cloud-hub --protect --pages

为什么不用 gh CLI：本机没有管理员权限、且 github.com 网页端口不通，装不了也用不上。
REST API 走 api.github.com，本机实测直连可用。

⚠️ 本脚本不会把 token 写进任何文件，也不打印 token 内容。
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

API = "https://api.github.com"
ROOT = Path(__file__).resolve().parent.parent


# --------------------------------------------------------------------- HTTP
def _opener(proxy: str | None) -> urllib.request.OpenerDirector:
    if proxy:
        handler = urllib.request.ProxyHandler({"http": proxy, "https": proxy})
    else:
        handler = urllib.request.ProxyHandler({})  # 显式直连，绕开失效的宿主代理
    return urllib.request.build_opener(handler)


def api(
    method: str,
    path: str,
    token: str,
    payload: dict[str, Any] | None = None,
    proxy: str | None = None,
) -> tuple[int, Any]:
    url = path if path.startswith("http") else f"{API}{path}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("User-Agent", "cloudhub-bootstrap")
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with _opener(proxy).open(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        try:
            return exc.code, json.loads(body)
        except json.JSONDecodeError:
            return exc.code, {"message": body}


def _msg(resp: Any) -> str:
    if isinstance(resp, dict):
        return str(resp.get("message") or resp.get("error") or resp)[:200]
    return str(resp)[:200]


# --------------------------------------------------------------------- git
def git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=False)
    if check and proc.returncode != 0:
        raise SystemExit(f"[FAIL] git {' '.join(args)}\n{proc.stderr.strip()}")
    return proc


def ensure_git_identity() -> None:
    name = git("config", "--get", "user.name", check=False).stdout.strip()
    email = git("config", "--get", "user.email", check=False).stdout.strip()
    if not name:
        git("config", "user.name", "youzunzhang")
        print("[SET] user.name = youzunzhang（仅本仓库）")
    if not email:
        git("config", "user.email", "youzunzhang@users.noreply.github.com")
        print("[SET] user.email = youzunzhang@users.noreply.github.com（仅本仓库）")


# --------------------------------------------------------------------- steps
def resolve_token(args: argparse.Namespace) -> str:
    token = args.token or os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        print("未从环境变量读到 token，请粘贴 GitHub PAT（输入不回显）：")
        token = getpass.getpass("  token: ").strip()
    if not token:
        raise SystemExit("[FAIL] 未提供 token")
    return token


def whoami(token: str, proxy: str | None) -> str:
    status, resp = api("GET", "/user", token, proxy=proxy)
    if status != 200:
        raise SystemExit(f"[FAIL] token 无效或权限不足（HTTP {status}）：{_msg(resp)}")
    print(f"[OK] token 有效，账号：{resp['login']}（{resp.get('type')}）")
    return str(resp["login"])


def ensure_repo(
    args: argparse.Namespace, token: str, owner: str, login: str, proxy: str | None
) -> None:
    status, resp = api("GET", f"/repos/{owner}/{args.repo}", token, proxy=proxy)
    if status == 200:
        print(f"[SKIP] 远程仓库已存在：{owner}/{args.repo}")
        return

    payload = {
        "name": args.repo,
        "description": args.description,
        "private": args.private,
        "has_issues": True,
        "has_wiki": False,
        "has_projects": False,
        "auto_init": False,
        "delete_branch_on_merge": True,
        "allow_squash_merge": True,
        "allow_merge_commit": False,
        "allow_rebase_merge": False,
    }
    endpoint = "/user/repos" if owner == login else f"/orgs/{owner}/repos"
    status, resp = api("POST", endpoint, token, payload, proxy=proxy)
    if status == 201:
        print(f"[OK] 已创建仓库：{resp['full_name']}（private={resp['private']}）")
        return
    raise SystemExit(f"[FAIL] 创建仓库失败（HTTP {status}）：{_msg(resp)}")


def configure_repo(args: argparse.Namespace, token: str, owner: str, proxy: str | None) -> None:
    payload = {
        "delete_branch_on_merge": True,
        "allow_squash_merge": True,
        "allow_merge_commit": False,
        "allow_rebase_merge": False,
        "squash_merge_commit_title": "PR_TITLE",
        "squash_merge_commit_message": "COMMIT_MESSAGES",
    }
    status, resp = api("PATCH", f"/repos/{owner}/{args.repo}", token, payload, proxy=proxy)
    print(
        f"[{'OK' if status == 200 else 'WARN'}] 合并策略（HTTP {status}）{_msg(resp) if status != 200 else ''}"
    )


def set_remote_and_push(args: argparse.Namespace, owner: str) -> None:
    ssh_url = f"git@github.com:{owner}/{args.repo}.git"
    existing = git("remote", "get-url", "origin", check=False)
    if existing.returncode == 0:
        git("remote", "set-url", "origin", ssh_url)
        print(f"[SET] origin → {ssh_url}")
    else:
        git("remote", "add", "origin", ssh_url)
        print(f"[ADD] origin → {ssh_url}")

    if args.no_push:
        print("[SKIP] 按要求跳过推送")
        return
    proc = git("push", "-u", "origin", "main", check=False)
    if proc.returncode == 0:
        print("[OK] 已推送 main（SSH 通道）")
    else:
        raise SystemExit(f"[FAIL] 推送失败：\n{proc.stderr.strip()}")


def protect_branch(token: str, owner: str, repo: str, proxy: str | None) -> None:
    payload: dict[str, Any] = {
        "required_status_checks": None,
        "enforce_admins": False,
        "required_pull_request_reviews": None,
        "restrictions": None,
        "allow_force_pushes": False,
        "allow_deletions": False,
        "required_conversation_resolution": True,
    }
    status, resp = api(
        "PUT", f"/repos/{owner}/{repo}/branches/main/protection", token, payload, proxy
    )
    if status == 200:
        print("[OK] main 分支保护已开启（禁强推 / 禁删除 / 需解决评论）")
    else:
        print(f"[WARN] 分支保护未开启（HTTP {status}）：{_msg(resp)}")
        print(
            "       经典 PAT 需 repo 勾选 admin:repo_hook 之上的 repo 全权；细粒度 PAT 需 Administration: write"
        )


def enable_pages(token: str, owner: str, repo: str, proxy: str | None) -> None:
    status, resp = api(
        "POST", f"/repos/{owner}/{repo}/pages", token, {"build_type": "workflow"}, proxy
    )
    if status in (201, 204):
        print(
            f"[OK] Pages 已启用，发布源 = GitHub Actions；站点地址 https://{owner.lower()}.github.io/{repo}/"
        )
        return
    hint = ""
    if status == 422:
        hint = "（可能已启用，或私有仓库在 Free 套餐下不支持）"
    print(f"[WARN] Pages 启用失败（HTTP {status}）{hint}：{_msg(resp)}")


# --------------------------------------------------------------------- main
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="初始化 GitHub 远程仓库")
    parser.add_argument("--repo", default="cloud-hub", help="仓库名")
    parser.add_argument("--owner", default="", help="账号或组织名，默认取 token 对应用户")
    parser.add_argument("--description", default="以 GitHub 为云端的任务执行与交付基础框架")
    parser.add_argument("--private", dest="private", action="store_true", default=True)
    parser.add_argument("--public", dest="private", action="store_false")
    parser.add_argument("--token", default="", help="PAT；不传则读 GH_TOKEN 或交互输入")
    parser.add_argument(
        "--protect", action="store_true", help="开启 main 分支保护（需 admin 权限）"
    )
    parser.add_argument("--pages", action="store_true", help="启用 Pages（Source=GitHub Actions）")
    parser.add_argument("--no-push", action="store_true", help="只关联 remote，不推送")
    parser.add_argument("--proxy", default="", help="显式指定代理，如 http://127.0.0.1:7897")
    args = parser.parse_args(argv)

    if not (ROOT / ".git").is_dir():
        raise SystemExit("[FAIL] 当前目录还不是 git 仓库，请先执行 git init -b main")

    token = resolve_token(args)
    login = whoami(token, args.proxy)
    owner = args.owner.strip() or login

    ensure_git_identity()
    ensure_repo(args, token, owner, login, args.proxy)
    configure_repo(args, token, owner, args.proxy)
    set_remote_and_push(args, owner)

    if args.protect:
        protect_branch(token, owner, args.repo, args.proxy)
    if args.pages:
        enable_pages(token, owner, args.repo, args.proxy)

    print("\n下一步：")
    print("  1. 到仓库 Settings → Pages 确认 Source = GitHub Actions")
    print("  2. Actions 首次运行需在 Actions 页面点一次 Enable（新仓库默认就会跑）")
    print("  3. 打第一个发布 tag： git tag v0.1.0 && git push origin v0.1.0")
    return 0


if __name__ == "__main__":
    sys.exit(main())

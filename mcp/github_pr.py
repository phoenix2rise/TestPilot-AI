"""
GitHub PR helper for CI demos.

Uses:
- git CLI (branch/commit/push)
- gh CLI (create PR)

Requirements in GitHub Actions:
- permissions: contents: write, pull-requests: write
- env: GITHUB_TOKEN set (gh uses it automatically)

This is intentionally narrow: apply a patch file and open a PR.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any
import subprocess
import os

@dataclass
class PRRequest:
    patch_path: str
    branch: str
    title: str
    body: str
    base: str = "main"

def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=False, capture_output=True, text=True)

def ensure_git_identity() -> None:
    _run(["git", "config", "user.email", os.getenv("GIT_USER_EMAIL", "testpilot-ai-bot@users.noreply.github.com")])
    _run(["git", "config", "user.name", os.getenv("GIT_USER_NAME", "testpilot-ai-bot")])

def create_branch(branch: str) -> None:
    _run(["git", "checkout", "-B", branch])

def apply_patch(patch_path: str) -> None:
    if not os.path.exists(patch_path):
        raise FileNotFoundError(patch_path)
    p = _run(["git", "apply", patch_path])
    if p.returncode != 0:
        raise RuntimeError(f"git apply failed: {p.stderr}")

def commit_all(message: str) -> None:
    _run(["git", "add", "-A"])
    p = _run(["git", "commit", "-m", message])
    if p.returncode != 0:
        raise RuntimeError(f"git commit failed: {p.stderr}")

def push_branch(branch: str) -> None:
    p = _run(["git", "push", "-u", "origin", branch])
    if p.returncode != 0:
        raise RuntimeError(f"git push failed: {p.stderr}")

def create_pr(req: PRRequest) -> Dict[str, Any]:
    ensure_git_identity()
    create_branch(req.branch)
    apply_patch(req.patch_path)
    commit_all(req.title)
    push_branch(req.branch)

    p = _run([
        "gh", "pr", "create",
        "--title", req.title,
        "--body", req.body,
        "--base", req.base,
        "--head", req.branch
    ])
    if p.returncode != 0:
        raise RuntimeError(f"gh pr create failed: {p.stderr}")

    url = None
    for line in (p.stdout or "").splitlines():
        if line.strip().startswith("http"):
            url = line.strip()
            break
    return {"pr_url": url, "stdout": p.stdout[-2000:], "stderr": p.stderr[-2000:]}

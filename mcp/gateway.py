"""
Minimal MCP-like gateway (tool registry + policy gating).

This is NOT a full MCP implementation.
It provides:
- a tool registry
- a single entrypoint to invoke tools
- a security gate that requires a valid QKD session for privileged tools

You can evolve this into a proper MCP server later.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Any, Optional, Tuple
import subprocess
import sys
import json
import os
import time
from pathlib import Path

from utils.triage import (
    classify_pytest_output,
    load_locator_events,
    summarize_locator_events,
    triage_failures,
)

from security.qkd.policy import is_session_valid, PolicyDecision

ToolFn = Callable[[Dict[str, Any]], Dict[str, Any]]

@dataclass
class SessionContext:
    qkd_created_ts: float
    qkd_expires_ts: float
    qkd_accepted: bool
    qkd_key_fingerprint: str

class MCPGateway:
    def __init__(self) -> None:
        self.tools: Dict[str, Tuple[ToolFn, bool]] = {}  # name -> (fn, privileged)

    def register(self, name: str, fn: ToolFn, *, privileged: bool = False) -> None:
        self.tools[name] = (fn, privileged)

    def invoke(self, name: str, args: Dict[str, Any], *, session: Optional[SessionContext] = None) -> Dict[str, Any]:
        if name not in self.tools:
            return {"ok": False, "error": f"UNKNOWN_TOOL:{name}"}
        fn, privileged = self.tools[name]

        if privileged:
            if session is None:
                return {"ok": False, "error": "DENY:NO_SESSION"}
            decision: PolicyDecision = is_session_valid(session.qkd_created_ts, session.qkd_expires_ts, session.qkd_accepted)
            if not decision.allowed:
                return {"ok": False, "error": decision.reason}

        try:
            out = fn(args)
            return {"ok": True, "result": out}
        except Exception as e:
            return {"ok": False, "error": f"EXCEPTION:{type(e).__name__}:{e}"}

# --- Built-in tools (wrapping your existing framework) ---

def tool_run_pytest(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run pytest as a subprocess.
    args:
      - extra: list[str] additional pytest args
    """
    extra = args.get("extra", [])
    if not isinstance(extra, list):
        extra = []
    cmd = [sys.executable, "-m", "pytest"] + extra
    p = subprocess.run(cmd, capture_output=True, text=True)
    return {"returncode": p.returncode, "stdout": p.stdout[-4000:], "stderr": p.stderr[-4000:]}

def tool_allure_generate(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate allure report if allure is installed and results exist.
    Safe no-op if allure isn't available.
    """
    results_dir = args.get("results_dir", "reports/allure-results")
    out_dir = args.get("out_dir", "reports/allure-report")
    # Try calling 'allure' CLI, fallback to no-op
    try:
        p = subprocess.run(["allure", "generate", results_dir, "-o", out_dir, "--clean"], capture_output=True, text=True)
        return {"returncode": p.returncode, "stdout": p.stdout[-2000:], "stderr": p.stderr[-2000:], "out_dir": out_dir}
    except FileNotFoundError:
        return {"returncode": 127, "stdout": "", "stderr": "allure CLI not found", "out_dir": out_dir}

def tool_security_status(args: Dict[str, Any]) -> Dict[str, Any]:
    return {"status": "ok", "ts": time.time()}

def tool_summarize_self_heal(args: Dict[str, Any]) -> Dict[str, Any]:
    path = args.get("path", "reports/self_heal/locator_events.jsonl")
    top_n = int(args.get("top_n", 5))
    events = load_locator_events(Path(path))
    summary = summarize_locator_events(events, top_n=top_n)
    return {
        "total_events": summary.total_events,
        "fallback_events": summary.fallback_events,
        "top_fallbacks": summary.top_fallbacks,
        "latest_event_ts": summary.latest_event_ts,
        "confidence": summary.confidence,
    }

def tool_classify_pytest(args: Dict[str, Any]) -> Dict[str, Any]:
    output = args.get("output", "")
    if not output and args.get("path"):
        output = Path(args["path"]).read_text(encoding="utf-8")
    return classify_pytest_output(output)

def tool_triage_failures(args: Dict[str, Any]) -> Dict[str, Any]:
    output = args.get("output", "")
    if not output and args.get("path"):
        output = Path(args["path"]).read_text(encoding="utf-8")
    summary = None
    if args.get("self_heal_path"):
        events = load_locator_events(Path(args["self_heal_path"]))
        summary = summarize_locator_events(events)
    return triage_failures(output, summary)

def default_gateway() -> MCPGateway:
    g = MCPGateway()
    g.register("run_pytest", tool_run_pytest, privileged=False)
    g.register("allure_generate", tool_allure_generate, privileged=False)
    g.register("security_status", tool_security_status, privileged=False)
    g.register("summarize_self_heal", tool_summarize_self_heal, privileged=False)
    g.register("classify_pytest_failures", tool_classify_pytest, privileged=False)
    g.register("triage_failures", tool_triage_failures, privileged=False)

    # Privileged tool: apply patch and open PR (CI demo)
    def tool_privileged_commit(args: Dict[str, Any]) -> Dict[str, Any]:
        """
        args:
          - patch_path: path to a unified diff patch file
          - branch: branch name
          - title: PR title / commit message
          - body: PR body
          - base: base branch (default main)
        """
        from mcp.github_pr import PRRequest, create_pr
        patch_path = args.get("patch_path")
        branch = args.get("branch")
        title = args.get("title")
        body = args.get("body", "")
        base = args.get("base", "main")
        min_confidence = float(os.getenv("MIN_EVIDENCE_CONFIDENCE", "0.6"))
        evidence_confidence = args.get("evidence_confidence")
        evidence_summary = args.get("evidence_summary")
        if evidence_confidence is None and isinstance(evidence_summary, dict):
            evidence_confidence = evidence_summary.get("confidence")
        if evidence_confidence is not None and float(evidence_confidence) < min_confidence:
            raise ValueError(
                f"Evidence confidence {evidence_confidence} below threshold {min_confidence}"
            )
        if not patch_path or not branch or not title:
            raise ValueError("patch_path, branch, title required")
        return create_pr(PRRequest(patch_path=patch_path, branch=branch, title=title, body=body, base=base))

    g.register("commit_fix", tool_privileged_commit, privileged=True)
    return g

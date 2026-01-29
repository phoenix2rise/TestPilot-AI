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

from utils.self_heal_summary import write_summary
from utils.triage import (
    classify_pytest_output,
    load_locator_events,
    summarize_locator_events,
    triage_failures,
)

from security.qkd.policy import evaluate_tool_policy, is_session_valid, PolicyDecision

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
        self.tool_metadata: Dict[str, Dict[str, Any]] = {}

    def register(
        self,
        name: str,
        fn: ToolFn,
        *,
        privileged: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.tools[name] = (fn, privileged)
        if metadata is not None:
            self.tool_metadata[name] = metadata

    def list_tools(self) -> Dict[str, Any]:
        tools = []
        for name, (_fn, privileged) in self.tools.items():
            tools.append(
                {
                    "name": name,
                    "privileged": privileged,
                    "metadata": self.tool_metadata.get(name, {}),
                }
            )
        return {"tools": tools}

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
            evidence_confidence = args.get("evidence_confidence")
            if evidence_confidence is None and isinstance(args.get("evidence_summary"), dict):
                evidence_confidence = args["evidence_summary"].get("confidence")
            tool_decision = evaluate_tool_policy(
                tool_name=name,
                evidence_confidence=evidence_confidence,
                min_confidence=float(os.getenv("MIN_EVIDENCE_CONFIDENCE", "0.6")),
            )
            if not tool_decision.allowed:
                return {"ok": False, "error": tool_decision.reason}

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
    if args.get("write_report"):
        output_dir = Path(args.get("output_dir", "reports/self_heal"))
        write_summary(Path(path), output_dir)
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
    g.register(
        "run_pytest",
        tool_run_pytest,
        privileged=False,
        metadata={"description": "Run pytest with optional extra args."},
    )
    g.register(
        "allure_generate",
        tool_allure_generate,
        privileged=False,
        metadata={"description": "Generate an Allure HTML report from results."},
    )
    g.register(
        "security_status",
        tool_security_status,
        privileged=False,
        metadata={"description": "Return security plane status."},
    )
    g.register(
        "summarize_self_heal",
        tool_summarize_self_heal,
        privileged=False,
        metadata={"description": "Summarize self-heal locator fallback evidence."},
    )
    g.register(
        "classify_pytest_failures",
        tool_classify_pytest,
        privileged=False,
        metadata={"description": "Classify pytest output using deterministic rules."},
    )
    g.register(
        "triage_failures",
        tool_triage_failures,
        privileged=False,
        metadata={"description": "Generate recommendations for pytest failures."},
    )
    g.register(
        "list_tools",
        lambda _args: g.list_tools(),
        privileged=False,
        metadata={"description": "List available tools and metadata."},
    )

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
        evidence_confidence = args.get("evidence_confidence")
        evidence_summary = args.get("evidence_summary")
        if evidence_confidence is None and isinstance(evidence_summary, dict):
            evidence_confidence = evidence_summary.get("confidence")
        if not patch_path or not branch or not title:
            raise ValueError("patch_path, branch, title required")
        if isinstance(evidence_summary, dict):
            evidence_block = "\n\n## Self-heal Evidence\n"
            evidence_block += f"- Confidence: {evidence_summary.get('confidence')}\n"
            top_fallbacks = evidence_summary.get("top_fallbacks") or []
            if top_fallbacks:
                evidence_block += "- Top fallbacks:\n"
                for fallback in top_fallbacks:
                    evidence_block += (
                        f"  - {fallback.get('class_name')}.{fallback.get('field')}: "
                        f"{fallback.get('chosen')} (count {fallback.get('count')})\n"
                    )
            body = body + evidence_block
        return create_pr(PRRequest(patch_path=patch_path, branch=branch, title=title, body=body, base=base))

    g.register("commit_fix", tool_privileged_commit, privileged=True)
    return g

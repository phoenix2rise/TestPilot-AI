from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, List

from agents.self_heal_agent import propose_fix
from agents.test_designer_agent import propose_tests
from agents.triage_agent import triage
from mcp.gateway import default_gateway
from utils.self_heal_summary import write_summary
from utils.triage import summarize_locator_events, load_locator_events


def _read_changed_files(diff_path: Path) -> List[str]:
    files = []
    for line in diff_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("+++ b/"):
            files.append(line.replace("+++ b/", "").strip())
    return sorted(set(files))


def main() -> int:
    parser = argparse.ArgumentParser(description="Run TestPilot agent pipeline.")
    parser.add_argument("--pytest-args", nargs="*", default=[], help="Additional pytest args")
    parser.add_argument("--diff", type=str, default="", help="Path to git diff for test design context")
    parser.add_argument("--output", type=str, default="reports/agent_pipeline.json", help="Output JSON path")
    parser.add_argument(
        "--self-heal-dir",
        type=str,
        default=os.getenv("SELF_HEAL_DIR", "reports/self_heal"),
        help="Directory containing self-heal evidence",
    )
    args = parser.parse_args()

    gateway = default_gateway()
    run_result = gateway.invoke("run_pytest", {"extra": args.pytest_args}).get("result", {})
    triage_result = triage(run_result)

    self_heal_dir = Path(args.self_heal_dir)
    events_path = self_heal_dir / "locator_events.jsonl"
    summary = write_summary(events_path, self_heal_dir)

    locator_events = load_locator_events(events_path)
    locator_summary = summarize_locator_events(locator_events)
    evidence_payload = {
        "confidence": locator_summary.confidence,
        "top_fallbacks": locator_summary.top_fallbacks,
        "events": summary.get("events", 0),
    }

    self_heal_plan = propose_fix(triage_result, evidence_payload)

    design_context: Dict[str, Any] = {}
    if args.diff:
        diff_path = Path(args.diff)
        if diff_path.exists():
            design_context["changed_files"] = _read_changed_files(diff_path)
    test_design = propose_tests(design_context)

    payload = {
        "triage": triage_result,
        "self_heal_summary": summary,
        "self_heal_plan": self_heal_plan,
        "test_design": test_design,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

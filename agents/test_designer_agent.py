"""
Test Designer Agent skeleton.

Later: read PR diff + user story and propose tests.
For now: placeholder that returns structured guidance.
"""
from __future__ import annotations
from typing import Dict, Any, List

def propose_tests(context: Dict[str, Any]) -> Dict[str, Any]:
    changed_files = context.get("changed_files", [])
    suggestions: List[str] = [
        "Add smoke test for new endpoint/route",
        "Add negative test for invalid inputs",
        "Add visual baseline update if UI changed intentionally",
    ]
    if changed_files:
        suggestions.append(f"Target regression coverage for: {', '.join(changed_files)}")
    return {
        "action": "SUGGEST_TESTS",
        "suggestions": suggestions,
        "context_keys_seen": sorted(list(context.keys()))
    }

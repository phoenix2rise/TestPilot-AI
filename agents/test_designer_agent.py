"""
Test Designer Agent skeleton.

Later: read PR diff + user story and propose tests.
For now: placeholder that returns structured guidance.
"""
from __future__ import annotations
from typing import Dict, Any

def propose_tests(context: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "action": "SUGGEST_TESTS",
        "suggestions": [
            "Add smoke test for new endpoint/route",
            "Add negative test for invalid inputs",
            "Add visual baseline update if UI changed intentionally"
        ],
        "context_keys_seen": sorted(list(context.keys()))
    }

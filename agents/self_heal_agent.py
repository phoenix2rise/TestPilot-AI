"""
Self-Heal Agent skeleton.

For now, it produces a "suggested fix" bundle rather than directly editing.
You can later connect it to your locator strategy utilities.
"""
from __future__ import annotations
from typing import Dict, Any

def propose_fix(triage_result: Dict[str, Any]) -> Dict[str, Any]:
    cat = triage_result.get("classification", {}).get("category")
    if cat != "SELECTOR_DRIFT":
        return {"action": "NONE", "reason": "Not a selector drift case"}
    return {
        "action": "PROPOSE_LOCATOR_UPDATE",
        "reason": "Selector drift detected. Recommend rerunning with DOM snapshot and generating robust locator candidates.",
        "next_steps": [
            "Capture DOM + screenshot on failure",
            "Generate candidate locators (role/text/data-testid)",
            "Validate candidate by rerun",
            "Create patch and open PR (privileged tool)"
        ]
    }

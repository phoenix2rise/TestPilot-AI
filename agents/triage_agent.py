"""
Triage Agent: reads test results (stdout/Allure) and classifies failures.

This is a skeleton designed to be extended with an LLM.
For "realtime proof", keep deterministic baseline rules so results are reproducible.
"""
from __future__ import annotations
from typing import Dict, Any, List

def classify_pytest_output(stdout: str, stderr: str) -> Dict[str, Any]:
    text = (stdout or "") + "\n" + (stderr or "")
    # Minimal heuristics (extend later):
    flaky_markers = ["flaky", "rerun", "timed out", "TimeoutError"]
    selector_markers = ["locator", "selector", "strict mode violation", "Element not found"]
    if any(m.lower() in text.lower() for m in selector_markers):
        return {"category": "SELECTOR_DRIFT", "confidence": 0.65}
    if any(m.lower() in text.lower() for m in flaky_markers):
        return {"category": "FLAKY_OR_TIMING", "confidence": 0.55}
    return {"category": "PRODUCT_OR_TEST_BUG", "confidence": 0.5}

def triage(run_result: Dict[str, Any]) -> Dict[str, Any]:
    stdout = run_result.get("stdout", "")
    stderr = run_result.get("stderr", "")
    rc = run_result.get("returncode", 1)
    classification = classify_pytest_output(stdout, stderr) if rc != 0 else {"category": "PASS", "confidence": 1.0}
    return {"returncode": rc, "classification": classification}

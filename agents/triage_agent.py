"""
Triage Agent: reads test results (stdout/Allure) and classifies failures.

This is a skeleton designed to be extended with an LLM.
For "realtime proof", keep deterministic baseline rules so results are reproducible.
"""
from __future__ import annotations
from typing import Dict, Any, List

from utils.triage import classify_pytest_output


def classify_pytest_output_with_category(stdout: str, stderr: str) -> Dict[str, Any]:
    text = (stdout or "") + "\n" + (stderr or "")
    classification = classify_pytest_output(text)
    categories = classification.get("categories", {})
    if categories.get("locator"):
        return {"category": "SELECTOR_DRIFT", "confidence": 0.7, "details": classification}
    if categories.get("timeout"):
        return {"category": "FLAKY_OR_TIMING", "confidence": 0.6, "details": classification}
    if categories:
        return {"category": "PRODUCT_OR_TEST_BUG", "confidence": 0.55, "details": classification}
    return {"category": "PASS", "confidence": 1.0, "details": classification}

def triage(run_result: Dict[str, Any]) -> Dict[str, Any]:
    stdout = run_result.get("stdout", "")
    stderr = run_result.get("stderr", "")
    rc = run_result.get("returncode", 1)
    classification = (
        classify_pytest_output_with_category(stdout, stderr)
        if rc != 0
        else {"category": "PASS", "confidence": 1.0}
    )
    return {"returncode": rc, "classification": classification}

from __future__ import annotations

import json
import re
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


@dataclass(frozen=True)
class LocatorFallbackSummary:
    total_events: int
    fallback_events: int
    top_fallbacks: List[Dict[str, Any]]
    latest_event_ts: Optional[float]
    confidence: float


FAILURE_PATTERNS = {
    "timeout": [
        r"TimeoutError",
        r"Timeout\s+\d+ms\s+exceeded",
        r"timed out",
    ],
    "assertion": [
        r"AssertionError",
        r"assert\s+",
        r"expect\(.+\)\.to",
    ],
    "locator": [
        r"strict mode violation",
        r"locator",
        r"no element",
        r"not found",
    ],
    "network": [
        r"ERR_CONNECTION",
        r"ECONNREFUSED",
        r"ENOTFOUND",
    ],
    "auth": [
        r"401",
        r"403",
        r"unauthorized",
        r"forbidden",
    ],
}


def _coerce_event(raw: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "ts": raw.get("ts"),
        "class_name": raw.get("class_name", raw.get("site", "")),
        "field": raw.get("field", ""),
        "action": raw.get("action", ""),
        "primary": raw.get("primary", ""),
        "chosen": raw.get("chosen", ""),
        "error": raw.get("error", ""),
    }


def load_locator_events(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    events: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError:
            continue
        events.append(_coerce_event(raw))
    return events


def summarize_locator_events(events: Iterable[Dict[str, Any]], *, top_n: int = 5) -> LocatorFallbackSummary:
    events_list = list(events)
    total_events = len(events_list)
    fallback_events = 0
    latest_event_ts: Optional[float] = None
    fallback_counter: Counter[str] = Counter()

    for event in events_list:
        ts = event.get("ts")
        if isinstance(ts, (int, float)):
            if latest_event_ts is None or ts > latest_event_ts:
                latest_event_ts = ts
        if event.get("primary") and event.get("chosen") and event["primary"] != event["chosen"]:
            fallback_events += 1
            key = f"{event.get('class_name','')}::{event.get('field','')}::{event.get('chosen','')}"
            fallback_counter[key] += 1

    top_fallbacks = []
    for key, count in fallback_counter.most_common(top_n):
        class_name, field, chosen = key.split("::", maxsplit=2)
        top_fallbacks.append(
            {
                "class_name": class_name,
                "field": field,
                "chosen": chosen,
                "count": count,
            }
        )

    confidence = _compute_confidence(total_events, fallback_events, latest_event_ts)
    return LocatorFallbackSummary(
        total_events=total_events,
        fallback_events=fallback_events,
        top_fallbacks=top_fallbacks,
        latest_event_ts=latest_event_ts,
        confidence=confidence,
    )


def _compute_confidence(total_events: int, fallback_events: int, latest_event_ts: Optional[float]) -> float:
    if total_events == 0:
        return 0.0
    fallback_ratio = fallback_events / total_events
    confidence = min(0.8, fallback_ratio)
    if latest_event_ts is not None:
        age_days = (time.time() - latest_event_ts) / 86400
        if age_days <= 7:
            confidence += 0.2
        elif age_days <= 30:
            confidence += 0.1
    return round(min(confidence, 1.0), 3)


def classify_pytest_output(output: str) -> Dict[str, Any]:
    categories = defaultdict(int)
    matched_patterns: Dict[str, List[str]] = defaultdict(list)
    for category, patterns in FAILURE_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, output, flags=re.IGNORECASE):
                categories[category] += 1
                matched_patterns[category].append(pattern)

    failed_tests = _extract_failed_tests(output)
    return {
        "categories": dict(categories),
        "matched_patterns": dict(matched_patterns),
        "failed_tests": failed_tests,
    }


def _extract_failed_tests(output: str) -> List[str]:
    failed = []
    for line in output.splitlines():
        if line.startswith("FAILED "):
            failed.append(line.replace("FAILED ", "").strip())
    return failed


def triage_failures(
    output: str,
    locator_summary: Optional[LocatorFallbackSummary] = None,
) -> Dict[str, Any]:
    classification = classify_pytest_output(output)
    recommendations: List[str] = []

    if classification["categories"].get("timeout"):
        recommendations.append("Check for slow page loads or increase timeouts on flaky steps.")
    if classification["categories"].get("locator"):
        recommendations.append("Review selector stability; consider using self-heal fallbacks.")
    if classification["categories"].get("assertion"):
        recommendations.append("Inspect expected vs actual UI state; update assertions if needed.")
    if classification["categories"].get("network"):
        recommendations.append("Investigate network dependency outages or mock external calls.")
    if classification["categories"].get("auth"):
        recommendations.append("Validate credentials/permissions for the test environment.")

    evidence_note = None
    if locator_summary:
        evidence_note = {
            "confidence": locator_summary.confidence,
            "top_fallbacks": locator_summary.top_fallbacks,
        }
        if locator_summary.confidence >= 0.6:
            recommendations.append(
                "High-confidence locator fallback evidence found; consider promoting fallback selectors."
            )

    return {
        "classification": classification,
        "recommendations": recommendations,
        "evidence": evidence_note,
    }


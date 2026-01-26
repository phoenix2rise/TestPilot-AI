"""
Self-heal learning curve experiment.

Goal:
- Convert runtime self-heal evidence (summary + decision) into a per-run metrics point.
- Store it under reports/self_heal/learning_curve_point.json for CI artifacting.
- Provide an offline aggregator to build a time-series across many downloaded artifacts.

This keeps the repo "realtime proven" while allowing academics to reconstruct trends.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

SUMMARY_PATH = Path(os.getenv("SELF_HEAL_DIR", "reports/self_heal")) / "self_heal_summary.json"
DECISION_PATH = Path(os.getenv("SELF_HEAL_DIR", "reports/self_heal")) / "self_heal_decision.json"
OUT_PATH = Path(os.getenv("SELF_HEAL_DIR", "reports/self_heal")) / "learning_curve_point.json"

def main() -> int:
    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8")) if SUMMARY_PATH.exists() else {"events": 0, "items": []}
    decision = json.loads(DECISION_PATH.read_text(encoding="utf-8")) if DECISION_PATH.exists() else {}

    items = summary.get("items", []) or []
    # Compute a simple "evidence strength" across items: average posterior mean weighted by total
    weighted = 0.0
    weight_sum = 0.0
    for it in items:
        pm = float(it.get("posterior_mean", 0.0))
        total = float(it.get("total", it.get("count", 0)))
        weighted += pm * max(1.0, total)
        weight_sum += max(1.0, total)
    evidence_score = (weighted / weight_sum) if weight_sum > 0 else 0.0

    point = {
        "ts": time.time(),
        "run_id": os.getenv("GITHUB_RUN_ID") or "",
        "sha": os.getenv("GITHUB_SHA") or "",
        "mode": decision.get("mode", "UNKNOWN"),
        "events": int(summary.get("events", 0)),
        "items": len(items),
        "evidence_score": evidence_score,
        # policy thresholds (if present)
        "promote_min_count": decision.get("promote_min_count"),
        "promote_min_posterior": decision.get("promote_min_posterior"),
        "promote_min_ci_lo": decision.get("promote_min_ci_lo"),
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(point, indent=2), encoding="utf-8")
    print(f"Wrote: {OUT_PATH}")
    print(json.dumps(point, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

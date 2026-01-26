from __future__ import annotations

import os
import sys
import json
from pathlib import Path
from collections import defaultdict
from typing import Dict, Any, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.bayes_confidence import beta_posterior, normal_approx_credible_interval

EVENTS_PATH = Path(os.getenv("SELF_HEAL_DIR", "reports/self_heal")) / "locator_events.jsonl"

def load_events() -> List[dict]:
    if not EVENTS_PATH.exists():
        return []
    events = []
    for line in EVENTS_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        events.append(json.loads(line))
    return events

def summarize(events: List[dict]) -> Dict[str, Any]:
    # Count fallback successes by (file, class, field, action, chosen)
    counts = defaultdict(int)
    for e in events:
        fp = e.get("file_path","")
        cls = e.get("class_name","")
        field = e.get("field","")
        action = e.get("action","")
        chosen = e.get("chosen","")
        primary = e.get("primary","")
        k = (fp, cls, field, action, primary, chosen)
        counts[k] += 1

    # Group by (file, class, field, action)
    group_totals = defaultdict(int)
    for (fp, cls, field, action, primary, chosen), c in counts.items():
        group_totals[(fp, cls, field, action)] += c

    items = []
    for (fp, cls, field, action, primary, chosen), c in sorted(counts.items(), key=lambda x: (-x[1], x[0])):
        total = group_totals[(fp, cls, field, action)]
        # Bayesian: successes=c, failures=total-c
        post = beta_posterior(c, max(0, total - c), prior_alpha=1.0, prior_beta=1.0)
        lo, hi = normal_approx_credible_interval(post)
        items.append({
            "file_path": fp,
            "class_name": cls,
            "field": field,
            "action": action,
            "primary": primary,
            "chosen": chosen,
            "count": c,
            "total": total,
            "posterior_mean": post.mean,
            "credible_interval_95": [lo, hi],
            "posterior_alpha": post.alpha,
            "posterior_beta": post.beta
        })

    return {
        "events": len(events),
        "items": items
    }

def to_markdown(summary: Dict[str, Any], max_rows: int = 10) -> str:
    lines = []
    lines.append(f"Self-heal events: **{summary.get('events',0)}**")
    lines.append("")
    lines.append("| File | Class.Field | Action | Primary -> Chosen | Count/Total | Posterior mean | 95% CI |")
    lines.append("|---|---|---:|---|---:|---:|---:|")
    for item in summary.get("items", [])[:max_rows]:
        fp = Path(item["file_path"]).name if item.get("file_path") else ""
        cf = f'{item.get("class_name","")}.{item.get("field","")}'
        action = item.get("action","")
        arrow = f'`{item.get("primary","")}` → `{item.get("chosen","")}`'
        ct = f'{item.get("count",0)}/{item.get("total",0)}'
        pm = item.get("posterior_mean", 0.0)
        lo, hi = item.get("credible_interval_95", [0.0, 0.0])
        lines.append(f"| {fp} | {cf} | {action} | {arrow} | {ct} | {pm:.2f} | [{lo:.2f}, {hi:.2f}] |")
    if len(summary.get("items", [])) > max_rows:
        lines.append("")
        lines.append(f"_({len(summary['items'])-max_rows} more rows omitted)_")
    return "\n".join(lines)

def main() -> int:
    events = load_events()
    summary = summarize(events)

    out_dir = Path(os.getenv("SELF_HEAL_DIR", "reports/self_heal"))
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "self_heal_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (out_dir / "self_heal_summary.md").write_text(to_markdown(summary), encoding="utf-8")

    print(f"Wrote: {out_dir / 'self_heal_summary.json'}")
    print(f"Wrote: {out_dir / 'self_heal_summary.md'}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import os, json, sys
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.bayes_confidence import beta_posterior, normal_approx_credible_interval

EVENTS_PATH = Path(os.getenv("SELF_HEAL_DIR", "reports/self_heal")) / "locator_events.jsonl"
OUT_PATH = Path(os.getenv("SELF_HEAL_DIR", "reports/self_heal")) / "self_heal_decision.json"

PROMOTE_MIN_COUNT = int(os.getenv("SELF_HEAL_PROMOTE_MIN_COUNT", "2"))
PROMOTE_MIN_POSTERIOR = float(os.getenv("SELF_HEAL_PROMOTE_MIN_POSTERIOR", "0.75"))
PROMOTE_MIN_CI_LO = float(os.getenv("SELF_HEAL_PROMOTE_MIN_CI_LO", "0.55"))

def load_events():
    if not EVENTS_PATH.exists():
        return []
    out=[]
    for line in EVENTS_PATH.read_text(encoding="utf-8").splitlines():
        line=line.strip()
        if line:
            out.append(json.loads(line))
    return out

def main()->int:
    events=load_events()

    counts=defaultdict(int)
    for e in events:
        k=(e.get("file_path",""), e.get("class_name",""), e.get("field",""), e.get("action",""), e.get("chosen",""))
        counts[k]+=1

    totals=defaultdict(int)
    for (fp, cls, field, action, chosen), c in counts.items():
        totals[(fp,cls,field,action)] += c

    grouped=defaultdict(list)
    for (fp, cls, field, action, chosen), c in counts.items():
        gk=(fp, cls, field, action)
        grouped[gk].append((chosen, c))

    candidates=[]
    for gk, opts in grouped.items():
        opts.sort(key=lambda x:(-x[1], x[0]))
        chosen, c = opts[0]
        total = totals[gk]
        post = beta_posterior(c, max(0, total - c), prior_alpha=1.0, prior_beta=1.0)
        lo, hi = normal_approx_credible_interval(post)
        candidates.append({
            "file_path": gk[0],
            "class_name": gk[1],
            "field": gk[2],
            "action": gk[3],
            "chosen": chosen,
            "count": c,
            "total": total,
            "posterior_mean": post.mean,
            "ci95": [lo, hi],
            "posterior_alpha": post.alpha,
            "posterior_beta": post.beta
        })

    promote=[c for c in candidates
             if c["count"]>=PROMOTE_MIN_COUNT
             and c["posterior_mean"]>=PROMOTE_MIN_POSTERIOR
             and c["ci95"][0]>=PROMOTE_MIN_CI_LO]

    decision = {
        "events": len(events),
        "promote_min_count": PROMOTE_MIN_COUNT,
        "promote_min_posterior": PROMOTE_MIN_POSTERIOR,
        "promote_min_ci_lo": PROMOTE_MIN_CI_LO,
        "mode": "PROMOTE_PRIMARY" if promote else "EXPAND_FALLBACKS",
        "candidates": candidates,
        "promote_candidates": promote
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(decision, indent=2), encoding="utf-8")
    print(f"Wrote: {OUT_PATH}")
    print("Mode:", decision["mode"])
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

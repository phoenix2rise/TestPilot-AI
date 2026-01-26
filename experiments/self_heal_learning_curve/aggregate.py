"""
Offline aggregator.

Usage:
  python -m experiments.self_heal_learning_curve.aggregate /path/to/artifacts_dir

Where artifacts_dir contains one or more files named:
  learning_curve_point.json

It outputs:
  learning_curve.csv
  learning_curve.json
  learning_curve.png  (requires matplotlib)

This is meant for academics and portfolio visuals.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
import csv

def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python -m experiments.self_heal_learning_curve.aggregate <artifacts_dir>")
        return 2
    root = Path(sys.argv[1])
    files = list(root.rglob("learning_curve_point.json"))
    if not files:
        print("No learning_curve_point.json files found.")
        return 1

    points = []
    for fp in files:
        try:
            points.append(json.loads(fp.read_text(encoding="utf-8")))
        except Exception:
            continue
    points.sort(key=lambda p: float(p.get("ts", 0.0)))

    out_json = root / "learning_curve.json"
    out_csv = root / "learning_curve.csv"
    out_json.write_text(json.dumps(points, indent=2), encoding="utf-8")

    # CSV
    fieldnames = ["ts","run_id","sha","mode","events","items","evidence_score","promote_min_count","promote_min_posterior","promote_min_ci_lo"]
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for p in points:
            row = {k: p.get(k,"") for k in fieldnames}
            w.writerow(row)

    # Plot if matplotlib available
    try:
        import matplotlib.pyplot as plt
        xs = [p.get("ts",0) for p in points]
        ys = [p.get("evidence_score",0) for p in points]
        plt.figure()
        plt.plot(xs, ys)
        plt.title("Self-heal evidence score over time")
        plt.xlabel("timestamp")
        plt.ylabel("evidence_score")
        out_png = root / "learning_curve.png"
        plt.savefig(out_png, dpi=180, bbox_inches="tight")
        print(f"Wrote: {out_png}")
    except Exception as e:
        print("Plot skipped (matplotlib missing or error):", e)

    print(f"Wrote: {out_json}")
    print(f"Wrote: {out_csv}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

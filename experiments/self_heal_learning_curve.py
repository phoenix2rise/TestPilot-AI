from __future__ import annotations

import json
from pathlib import Path
import matplotlib.pyplot as plt

DATA_PATH = Path("reports/self_heal/self_heal_summary.json")
OUT_PATH = Path("reports/self_heal/self_heal_learning_curve.png")

def main():
    if not DATA_PATH.exists():
        print("No summary data found.")
        return 1

    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    items = data.get("items", [])

    if not items:
        print("No items to plot.")
        return 0

    xs = list(range(1, len(items)+1))
    ys = [item.get("posterior_mean", 0.0) for item in items]

    plt.figure()
    plt.plot(xs, ys, marker="o")
    plt.xlabel("Self-heal candidate index")
    plt.ylabel("Posterior mean probability")
    plt.title("Self-heal learning curve (Bayesian confidence)")
    plt.grid(True)
    plt.savefig(OUT_PATH)
    print(f"Saved: {OUT_PATH}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

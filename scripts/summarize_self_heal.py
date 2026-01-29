from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Dict, Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.self_heal_summary import write_summary

EVENTS_PATH = Path(os.getenv("SELF_HEAL_DIR", "reports/self_heal")) / "locator_events.jsonl"

def main() -> int:
    out_dir = Path(os.getenv("SELF_HEAL_DIR", "reports/self_heal"))
    summary = write_summary(EVENTS_PATH, out_dir)

    print(f"Wrote: {out_dir / 'self_heal_summary.json'}")
    print(f"Wrote: {out_dir / 'self_heal_summary.md'}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

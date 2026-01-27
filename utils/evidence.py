from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Any


def evidence_dir() -> Path:
    return Path(os.getenv("SELF_HEAL_DIR", "reports/self_heal"))


@dataclass
class LocatorEvent:
    ts: float
    site: str
    field: str
    action: str
    primary: str
    chosen: str
    ok: bool
    meta: Dict[str, Any]

    def to_jsonl(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)


def write_event(ev: LocatorEvent) -> None:
    d = evidence_dir()
    d.mkdir(parents=True, exist_ok=True)
    path = d / "locator_events.jsonl"
    with path.open("a", encoding="utf-8") as f:
        f.write(ev.to_jsonl() + "\n")


def now_ts() -> float:
    return time.time()

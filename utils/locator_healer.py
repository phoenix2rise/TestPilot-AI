from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional, Dict, Any

@dataclass(frozen=True)
class LocatorEvent:
    ts: float
    page_object: str
    field: str
    primary: str
    chosen: str
    error: str

def _events_path() -> Path:
    out_dir = Path(os.getenv("SELF_HEAL_DIR", "reports/self_heal"))
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir / "locator_events.jsonl"

def record_event(event: LocatorEvent) -> None:
    p = _events_path()
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(event), ensure_ascii=False) + "\n")

def fill_with_fallback(page, *, primary: str, fallbacks: List[str], value: str, page_object: str, field: str) -> str:
    """
    Try filling using primary selector; if it fails, try fallbacks.
    Records a LocatorEvent when a fallback is used.

    Returns the selector that succeeded.
    """
    try:
        page.fill(primary, value)
        return primary
    except Exception as e:
        last_err = repr(e)
        for fb in fallbacks:
            try:
                page.fill(fb, value)
                record_event(LocatorEvent(
                    ts=time.time(),
                    page_object=page_object,
                    field=field,
                    primary=primary,
                    chosen=fb,
                    error=last_err
                ))
                return fb
            except Exception as e2:
                last_err = repr(e2)
        # If all fail, raise original-ish error
        raise RuntimeError(f"All selectors failed for {page_object}.{field}. Last error: {last_err}")

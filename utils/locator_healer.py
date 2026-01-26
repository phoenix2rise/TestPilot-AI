from __future__ import annotations

import json
import os
import time
import inspect
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Any, Optional, Callable

from playwright.sync_api import expect

@dataclass(frozen=True)
class LocatorEvent:
    ts: float
    class_name: str
    module: str
    file_path: str
    field: str
    action: str
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

def _infer_file_path(page_object: Any) -> str:
    try:
        fp = inspect.getsourcefile(page_object.__class__)
        if not fp:
            return ""
        p = Path(fp).resolve()
        repo_root = Path(__file__).resolve().parents[1]  # repo root
        try:
            return str(p.relative_to(repo_root))
        except Exception:
            return str(p.name)
    except Exception:
        return ""

def _record(owner: Any, field: str, action: str, primary: str, chosen: str, error: str) -> None:
    record_event(LocatorEvent(
        ts=time.time(),
        class_name=owner.__class__.__name__,
        module=getattr(owner.__class__, "__module__", ""),
        file_path=_infer_file_path(owner),
        field=field,
        action=action,
        primary=primary,
        chosen=chosen,
        error=error
    ))

def _try_sequence(
    *,
    do: Callable[[str], None],
    primary: str,
    fallbacks: List[str],
    owner: Any,
    field: str,
    action: str
) -> str:
    try:
        do(primary)
        return primary
    except Exception as e:
        last_err = repr(e)
        for fb in fallbacks:
            try:
                do(fb)
                _record(owner, field, action, primary, fb, last_err)
                return fb
            except Exception as e2:
                last_err = repr(e2)
        raise RuntimeError(f"All selectors failed for {owner.__class__.__name__}.{field} ({action}). Last error: {last_err}")

def fill_with_fallback(
    page,
    *,
    primary: str,
    fallbacks: List[str],
    value: str,
    owner: Any,
    field: str,
) -> str:
    """Fill input using primary selector, else fallbacks; record event on fallback."""
    return _try_sequence(
        do=lambda sel: page.fill(sel, value),
        primary=primary,
        fallbacks=fallbacks,
        owner=owner,
        field=field,
        action="fill"
    )

def click_with_fallback(
    page,
    *,
    primary: str,
    fallbacks: List[str],
    owner: Any,
    field: str,
    timeout_ms: int = 10_000
) -> str:
    """Click using primary selector, else fallbacks; record event on fallback."""
    return _try_sequence(
        do=lambda sel: page.locator(sel).click(timeout=timeout_ms),
        primary=primary,
        fallbacks=fallbacks,
        owner=owner,
        field=field,
        action="click"
    )

def expect_visible_with_fallback(
    page,
    *,
    primary: str,
    fallbacks: List[str],
    owner: Any,
    field: str,
    timeout_ms: int = 10_000
) -> str:
    """Assert visible using primary selector, else fallbacks; record event on fallback."""
    return _try_sequence(
        do=lambda sel: expect(page.locator(sel)).to_be_visible(timeout=timeout_ms),
        primary=primary,
        fallbacks=fallbacks,
        owner=owner,
        field=field,
        action="expect_visible"
    )

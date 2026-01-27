from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Any, Tuple, Optional

from .evidence import LocatorEvent, write_event, now_ts


@dataclass(frozen=True)
class LocatorSpec:
    primary: str
    fallbacks: List[str]


def _coerce_spec(raw: Any) -> LocatorSpec:
    if not isinstance(raw, dict):
        raise ValueError("Locator must be a mapping with keys: primary, fallbacks")
    primary = str(raw.get("primary", "")).strip()
    if not primary:
        raise ValueError("Locator.primary is required")
    fallbacks = raw.get("fallbacks", []) or []
    if not isinstance(fallbacks, list):
        raise ValueError("Locator.fallbacks must be a list")
    fallbacks = [str(x) for x in fallbacks if str(x).strip()]
    return LocatorSpec(primary=primary, fallbacks=fallbacks)


class LocatorRegistry:
    """Website-agnostic locator resolution with evidence logging."""

    def __init__(self, site: str, locators: Dict[str, Any]):
        self.site = site
        self._specs: Dict[str, LocatorSpec] = {k: _coerce_spec(v) for k, v in locators.items()}

    def spec(self, field: str) -> LocatorSpec:
        if field not in self._specs:
            raise KeyError(f"Unknown field '{field}' in locators.yaml")
        return self._specs[field]

    def try_locators(
        self,
        page,
        field: str,
        action: str,
        *,
        timeout_ms: int = 2000,
        state: str = "attached",
    ) -> Tuple[str, bool]:
        spec = self.spec(field)
        candidates = [spec.primary] + list(spec.fallbacks)

        last_err: Optional[str] = None
        for sel in candidates:
            try:
                page.wait_for_selector(sel, timeout=timeout_ms, state=state)
                write_event(LocatorEvent(
                    ts=now_ts(),
                    site=self.site,
                    field=field,
                    action=action,
                    primary=spec.primary,
                    chosen=sel,
                    ok=True,
                    meta={},
                ))
                return sel, True
            except Exception as e:
                last_err = str(e)

        write_event(LocatorEvent(
            ts=now_ts(),
            site=self.site,
            field=field,
            action=action,
            primary=spec.primary,
            chosen=spec.primary,
            ok=False,
            meta={"error": last_err or "not found"},
        ))
        return spec.primary, False

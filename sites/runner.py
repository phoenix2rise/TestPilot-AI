from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any, Dict

from utils.locator_registry import LocatorRegistry

_VAR_RE = re.compile(r"\$\{([A-Z0-9_]+)\}")


def _substitute(value: str, variables: Dict[str, str]) -> str:
    def repl(m):
        key = m.group(1)
        return variables.get(key, os.getenv(key, ""))
    return _VAR_RE.sub(repl, value)


@dataclass
class FlowContext:
    base_url: str
    vars: Dict[str, str]
    registry: LocatorRegistry


class FlowRunner:
    """Executes a flow.yaml 'steps' list against any site."""

    def __init__(self, ctx: FlowContext):
        self.ctx = ctx

    def run(self, page, flow_name: str, flows: Dict[str, Any]) -> None:
        flow = flows.get(flow_name)
        if not isinstance(flow, dict):
            raise KeyError(f"Flow '{flow_name}' not found in flow.yaml")
        steps = flow.get("steps", [])
        if not isinstance(steps, list):
            raise ValueError(f"Flow '{flow_name}' steps must be a list")

        for step in steps:
            if not isinstance(step, dict) or len(step) != 1:
                raise ValueError(f"Invalid step: {step!r}")
            op, payload = next(iter(step.items()))

            if op == "goto":
                path = str(payload)
                url = self.ctx.base_url.rstrip("/") + "/" + path.lstrip("/")
                page.goto(url)
                continue

            if op == "click":
                field = str(payload.get("field"))
                sel, ok = self.ctx.registry.try_locators(page, field, action="click")
                if not ok:
                    raise RuntimeError(f"click failed: field={field} selectors not found")
                page.click(sel)
                continue

            if op == "fill":
                field = str(payload.get("field"))
                raw = str(payload.get("value", ""))
                val = _substitute(raw, self.ctx.vars)
                sel, ok = self.ctx.registry.try_locators(page, field, action="fill")
                if not ok:
                    raise RuntimeError(f"fill failed: field={field} selectors not found")
                page.fill(sel, val)
                continue

            if op == "expect":
                if not isinstance(payload, dict):
                    raise ValueError("expect step must be a mapping")
                if "url_contains" in payload:
                    needle = str(payload["url_contains"])
                    page.wait_for_url(f"**{needle}**", timeout=10000)
                    continue
                if "selector" in payload:
                    sel = str(payload["selector"])
                    page.wait_for_selector(sel, timeout=10000, state="visible")
                    continue
                raise ValueError(f"Unknown expect condition: {payload}")

            raise ValueError(f"Unknown op '{op}' in flow steps")

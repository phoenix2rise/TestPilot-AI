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

    def _click_recaptcha_if_present(self, page, *, timeout_ms: int = 1500) -> tuple[bool, bool]:
        iframe_selector = "iframe[title*='reCAPTCHA'], iframe[src*='recaptcha']"
        checkbox_selectors = [
            "span#recaptcha-anchor",
            "div.recaptcha-checkbox-border",
        ]
        checked_selectors = [
            "span#recaptcha-anchor[aria-checked='true']",
            ".recaptcha-checkbox-checked",
        ]

        try:
            if page.locator(iframe_selector).count() == 0:
                return False, False
        except Exception:
            return False, False

        try:
            page.wait_for_selector(iframe_selector, timeout=timeout_ms, state="attached")
        except Exception:
            return True, False

        frame = page.frame(url=re.compile("recaptcha")) or page.frame(name=re.compile("recaptcha"))
        frame_locator = page.frame_locator(iframe_selector)
        clicked = False
        for checkbox_selector in checkbox_selectors:
            try:
                checkbox = (frame.locator(checkbox_selector) if frame else frame_locator.locator(checkbox_selector))
                checkbox.wait_for(state="visible", timeout=timeout_ms)
                checkbox.click()
                clicked = True
                break
            except Exception:
                continue
        if not clicked:
            return True, False

        for checked_selector in checked_selectors:
            try:
                checked = (frame.locator(checked_selector) if frame else frame_locator.locator(checked_selector))
                checked.wait_for(state="visible", timeout=timeout_ms)
                return True, True
            except Exception:
                continue
        return True, False

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
                raw = str(payload)
                path = _substitute(raw, self.ctx.vars)
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

            if op == "click_if_present":
                field = str(payload.get("field"))
                sel, ok = self.ctx.registry.try_locators(
                    page,
                    field,
                    action="click_if_present",
                    timeout_ms=1500,
                    state="visible",
                )
                if ok:
                    page.click(sel)
                continue

            if op == "check_recaptcha_if_present":
                timeout_ms = 1500
                require_checked = False
                if isinstance(payload, dict) and "timeout_ms" in payload:
                    timeout_ms = int(payload.get("timeout_ms", timeout_ms))
                if isinstance(payload, dict) and "require_checked" in payload:
                    require_checked = bool(payload.get("require_checked"))
                present, checked = self._click_recaptcha_if_present(page, timeout_ms=timeout_ms)
                if present and require_checked and not checked:
                    raise RuntimeError("reCAPTCHA checkbox detected but could not be checked")
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

            if op == "press_key":
                if not isinstance(payload, dict):
                    raise ValueError("press_key step must be a mapping")
                key = str(payload.get("key", "")).strip()
                if not key:
                    raise ValueError("press_key requires 'key'")
                if "field" in payload:
                    field = str(payload.get("field"))
                    sel, ok = self.ctx.registry.try_locators(page, field, action="press_key")
                    if not ok:
                        raise RuntimeError(f"press_key failed: field={field} selectors not found")
                    page.press(sel, key)
                    continue
                if "selector" in payload:
                    sel = str(payload.get("selector"))
                    page.press(sel, key)
                    continue
                raise ValueError("press_key requires 'field' or 'selector'")

            if op == "select_option":
                if not isinstance(payload, dict):
                    raise ValueError("select_option step must be a mapping")
                raw = str(payload.get("value", ""))
                val = _substitute(raw, self.ctx.vars)
                if "field" in payload:
                    field = str(payload.get("field"))
                    sel, ok = self.ctx.registry.try_locators(page, field, action="select_option")
                    if not ok:
                        raise RuntimeError(f"select_option failed: field={field} selectors not found")
                    page.select_option(sel, value=val)
                    continue
                if "selector" in payload:
                    sel = str(payload.get("selector"))
                    page.select_option(sel, value=val)
                    continue
                raise ValueError("select_option requires 'field' or 'selector'")

            if op == "scroll":
                if isinstance(payload, str):
                    if payload == "top":
                        page.evaluate("window.scrollTo(0, 0)")
                        continue
                    if payload == "bottom":
                        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        continue
                    raise ValueError("scroll string payload must be 'top' or 'bottom'")
                if not isinstance(payload, dict):
                    raise ValueError("scroll step must be a mapping or 'top'/'bottom'")
                if "field" in payload:
                    field = str(payload.get("field"))
                    sel, ok = self.ctx.registry.try_locators(page, field, action="scroll")
                    if not ok:
                        raise RuntimeError(f"scroll failed: field={field} selectors not found")
                    page.eval_on_selector(
                        sel,
                        "el => el.scrollIntoView({block: 'center', inline: 'center'})",
                    )
                    continue
                if "selector" in payload:
                    sel = str(payload.get("selector"))
                    page.eval_on_selector(
                        sel,
                        "el => el.scrollIntoView({block: 'center', inline: 'center'})",
                    )
                    continue
                raise ValueError("scroll requires 'field' or 'selector'")

            if op == "wait_for_network_idle":
                timeout_ms = 10000
                if isinstance(payload, dict) and "timeout_ms" in payload:
                    timeout_ms = int(payload.get("timeout_ms", timeout_ms))
                page.wait_for_load_state("networkidle", timeout=timeout_ms)
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

            if op == "expect_visible":
                field = str(payload.get("field"))
                sel, ok = self.ctx.registry.try_locators(
                    page,
                    field,
                    action="expect_visible",
                    timeout_ms=10000,
                    state="visible",
                )
                if not ok:
                    raise RuntimeError(f"expect_visible failed: field={field} selectors not found")
                page.wait_for_selector(sel, timeout=10000, state="visible")
                continue

            raise ValueError(f"Unknown op '{op}' in flow steps")

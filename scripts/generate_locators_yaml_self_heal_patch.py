from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Tuple

try:
    import yaml  # type: ignore
except Exception:
    yaml = None  # type: ignore

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SELF_HEAL_DIR = Path(os.getenv("SELF_HEAL_DIR", "reports/self_heal"))
EVENTS_PATH = SELF_HEAL_DIR / "locator_events.jsonl"

SITE = os.getenv("TP_SITE", "demo")
LOCATORS_PATH = PROJECT_ROOT / "sites" / SITE / "locators.yaml"
PATCH_DIR = PROJECT_ROOT / "reports" / "patches"
PATCH_PATH = PATCH_DIR / "locators_yaml_self_heal.patch"

MIN_COUNT = int(os.getenv("SELF_HEAL_MIN_COUNT", "1"))


def _require_yaml():
    if yaml is None:
        raise RuntimeError("PyYAML required: pip install pyyaml")


def run(cmd: List[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)


def load_events() -> List[Dict[str, Any]]:
    if not EVENTS_PATH.exists():
        return []
    out = []
    for line in EVENTS_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        out.append(json.loads(line))
    return out


def choose_promotions(events: List[Dict[str, Any]]) -> Dict[str, str]:
    counts: Dict[Tuple[str, str], int] = {}
    for e in events:
        if not e.get("ok"):
            continue
        field = str(e.get("field", "")).strip()
        chosen = str(e.get("chosen", "")).strip()
        primary = str(e.get("primary", "")).strip()
        if not field or not chosen or not primary:
            continue
        if chosen == primary:
            continue
        counts[(field, chosen)] = counts.get((field, chosen), 0) + 1

    promos: Dict[str, str] = {}
    by_field: Dict[str, List[Tuple[str, int]]] = {}
    for (field, chosen), c in counts.items():
        by_field.setdefault(field, []).append((chosen, c))

    for field, opts in by_field.items():
        opts.sort(key=lambda x: (-x[1], x[0]))
        chosen, c = opts[0]
        if c >= MIN_COUNT:
            promos[field] = chosen
    return promos


def main() -> int:
    _require_yaml()
    if not LOCATORS_PATH.exists():
        raise FileNotFoundError(f"Missing locators: {LOCATORS_PATH}")

    promos = choose_promotions(load_events())
    if not promos:
        print("No promotions from evidence; no patch produced.")
        return 1

    data = yaml.safe_load(LOCATORS_PATH.read_text(encoding="utf-8"))  # type: ignore
    if not isinstance(data, dict) or "locators" not in data:
        raise ValueError("locators.yaml must contain top-level key: locators")
    locs = data["locators"]
    if not isinstance(locs, dict):
        raise ValueError("locators must be a mapping")

    changed = False
    for field, new_primary in promos.items():
        spec = locs.get(field)
        if not isinstance(spec, dict):
            continue
        old_primary = str(spec.get("primary", "")).strip()
        if old_primary and old_primary != new_primary:
            fallbacks = spec.get("fallbacks", []) or []
            if not isinstance(fallbacks, list):
                fallbacks = []
            if old_primary not in fallbacks:
                fallbacks.insert(0, old_primary)
            spec["primary"] = new_primary
            spec["fallbacks"] = fallbacks
            changed = True

    if not changed:
        print("No effective changes; no patch produced.")
        return 1

    PATCH_DIR.mkdir(parents=True, exist_ok=True)

    original = LOCATORS_PATH.read_text(encoding="utf-8")
    updated = yaml.safe_dump(data, sort_keys=False, allow_unicode=True)  # type: ignore
    LOCATORS_PATH.write_text(updated, encoding="utf-8")

    try:
        rel = str(LOCATORS_PATH.relative_to(PROJECT_ROOT))
        run(["git", "add", "-N", rel])
        diff = run(["git", "diff", "--", rel])
        PATCH_PATH.write_text(diff.stdout, encoding="utf-8")

        run(["git", "checkout", "--", rel])

        chk = run(["git", "apply", "--check", str(PATCH_PATH)])
        if chk.returncode != 0:
            print("Patch failed git apply --check:")
            print(chk.stderr)
            return 3

        print(f"Patch created: {PATCH_PATH}")
        return 0
    finally:
        LOCATORS_PATH.write_text(original, encoding="utf-8")
        run(["git", "checkout", "--", str(LOCATORS_PATH.relative_to(PROJECT_ROOT))])


if __name__ == "__main__":
    raise SystemExit(main())

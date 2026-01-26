from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple
import difflib

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

EVENTS_PATH = Path(os.getenv("SELF_HEAL_DIR", "reports/self_heal")) / "locator_events.jsonl"

# Minimal mapping from PageObject -> file path in this repo
PAGE_OBJECT_FILES = {
    "LoginPage": PROJECT_ROOT / "pages" / "login_page.py",
}

def parse_events() -> List[dict]:
    if not EVENTS_PATH.exists():
        return []
    out = []
    for line in EVENTS_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        import json
        out.append(json.loads(line))
    return out

def choose_updates(events: List[dict]) -> Dict[Tuple[str, str], str]:
    """Return {(page_object, field): chosen_selector} for latest events."""
    updates: Dict[Tuple[str, str], str] = {}
    for e in sorted(events, key=lambda x: float(x.get("ts", 0))):
        po = e.get("page_object")
        field = e.get("field")
        chosen = e.get("chosen")
        if po and field and chosen:
            updates[(po, field)] = chosen
    return updates

def update_assignment_text(txt: str, field: str, new_selector: str) -> Tuple[str, bool]:
    pattern = rf"(self\.{re.escape(field)}\s*=\s*)(['\"])(.*?)(\2)"
    m = re.search(pattern, txt)
    if not m:
        return txt, False
    quote = m.group(2)
    new_txt = re.sub(pattern, rf"\1{quote}{new_selector}{quote}", txt, count=1)
    return new_txt, True

def main() -> int:
    events = parse_events()
    if not events:
        print("No locator events found; nothing to patch.")
        return 0

    updates = choose_updates(events)

    patches: List[str] = []
    changed_any = False

    for (po, field), selector in updates.items():
        fp = PAGE_OBJECT_FILES.get(po)
        if not fp or not fp.exists():
            print(f"Skip: no file mapping for {po}")
            continue

        original = fp.read_text(encoding="utf-8").splitlines(keepends=True)
        updated_text, ok = update_assignment_text("".join(original), field, selector)
        print(f"Update {po}.{field} -> {selector}: {'OK' if ok else 'NOT_FOUND'}")
        if not ok:
            continue

        updated = updated_text.splitlines(keepends=True)
        diff = difflib.unified_diff(
            original,
            updated,
            fromfile=str(fp.relative_to(PROJECT_ROOT)),
            tofile=str(fp.relative_to(PROJECT_ROOT)),
            lineterm=""
        )
        patches.extend(list(diff))
        changed_any = True

    if not changed_any:
        print("No changes applied.")
        return 1

    patch_dir = PROJECT_ROOT / "reports" / "patches"
    patch_dir.mkdir(parents=True, exist_ok=True)
    patch_path = patch_dir / "locator_self_heal.patch"
    patch_path.write_text("\n".join(patches) + "\n", encoding="utf-8")
    print(f"Patch created: {patch_path}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

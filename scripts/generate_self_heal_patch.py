from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple
import difflib
import json

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

EVENTS_PATH = Path(os.getenv("SELF_HEAL_DIR", "reports/self_heal")) / "locator_events.jsonl"
MIN_COUNT = int(os.getenv("SELF_HEAL_MIN_COUNT", "1"))  # promote after N fallback successes

def parse_events() -> List[dict]:
    if not EVENTS_PATH.exists():
        return []
    out = []
    for line in EVENTS_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        out.append(json.loads(line))
    return out

def key(e: dict) -> Tuple[str, str, str, str, str]:
    return (
        (e.get("file_path") or "").strip(),
        (e.get("class_name") or "").strip(),
        (e.get("field") or "").strip(),
        (e.get("action") or "").strip(),
        (e.get("chosen") or "").strip(),
    )

def choose_updates(events: List[dict]) -> Dict[Tuple[str, str, str, str], Tuple[str,int]]:
    """
    Return {(file_path, class_name, field, action): (chosen_selector, count)}.
    Picks the most frequent chosen selector per key, then most recent.
    """
    counts: Dict[Tuple[str,str,str,str,str], int] = {}
    last_ts: Dict[Tuple[str,str,str,str,str], float] = {}
    for e in events:
        k = key(e)
        counts[k] = counts.get(k, 0) + 1
        last_ts[k] = max(last_ts.get(k, 0.0), float(e.get("ts", 0.0)))

    # group by (file, class, field, action)
    grouped: Dict[Tuple[str,str,str,str], List[Tuple[str,int,float]]] = {}
    for (fp, cls, field, action, chosen), c in counts.items():
        gk = (fp, cls, field, action)
        grouped.setdefault(gk, []).append((chosen, c, last_ts[(fp,cls,field,action,chosen)]))

    updates: Dict[Tuple[str,str,str,str], Tuple[str,int]] = {}
    for gk, options in grouped.items():
        # sort by count desc then ts desc
        options.sort(key=lambda x: (-x[1], -x[2]))
        chosen, c, _ = options[0]
        if c >= MIN_COUNT and all(gk):
            updates[gk] = (chosen, c)
    return updates

def update_assignment_text(txt: str, field: str, new_selector: str) -> Tuple[str, bool]:
    pattern = rf"(self\.{re.escape(field)}\s*=\s*)(['\"])(.*?)(\2)"
    m = re.search(pattern, txt)
    if not m:
        return txt, False
    quote = m.group(2)
    new_txt = re.sub(pattern, rf"\1{quote}{new_selector}{quote}", txt, count=1)
    return new_txt, True

def pick_target_field(file_text: str, base_field: str, action: str) -> str:
    """If self.<base_field>_<action> exists, update that; else update base_field."""
    candidate = f"{base_field}_{action}"
    if re.search(rf"self\.{re.escape(candidate)}\s*=", file_text):
        return candidate
    return base_field

def to_repo_relative(path_str: str) -> Path:
    p = Path(path_str)
    try:
        return p.relative_to(PROJECT_ROOT)
    except Exception:
        return Path(path_str)

def main() -> int:
    events = parse_events()
    if not events:
        print("No locator events found; nothing to patch.")
        return 0

    updates = choose_updates(events)
    if not updates:
        print("No updates met the minimum evidence threshold.")
        return 1

    # Aggregate per file
    file_updates: Dict[Path, List[Tuple[str, str, str, str, int]]] = {}
    for (fp, cls, field, action), (selector, count) in updates.items():
        rel = to_repo_relative(fp)
        file_path = (PROJECT_ROOT / rel) if not rel.is_absolute() else rel
        file_updates.setdefault(file_path, []).append((cls, field, action, selector, count))

    patches: List[str] = []
    changed_any = False

    for file_path, items in file_updates.items():
        if not file_path.exists():
            print(f"Skip missing file: {file_path}")
            continue

        original_lines = file_path.read_text(encoding="utf-8").splitlines(keepends=True)
        txt = "".join(original_lines)
        file_changed = False

        for (cls, base_field, action, selector, count) in items:
            target_field = pick_target_field(txt, base_field, action)
            txt2, ok = update_assignment_text(txt, target_field, selector)
            print(f"Update {file_path.name}:{cls}.{target_field} ({action}) -> {selector} [count={count}]: {'OK' if ok else 'NOT_FOUND'}")
            txt = txt2
            file_changed = file_changed or ok

        if not file_changed:
            continue

        updated_lines = txt.splitlines(keepends=True)
        rel_name = str(file_path.relative_to(PROJECT_ROOT)) if str(file_path).startswith(str(PROJECT_ROOT)) else str(file_path)
        diff = difflib.unified_diff(
            original_lines,
            updated_lines,
            fromfile=rel_name,
            tofile=rel_name,
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

from __future__ import annotations

import os, sys, json, re
from pathlib import Path
from typing import List, Dict, Tuple
import difflib

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DECISION_PATH = Path(os.getenv("SELF_HEAL_DIR", "reports/self_heal")) / "self_heal_decision.json"

def load_decision()->dict:
    if not DECISION_PATH.exists():
        raise FileNotFoundError(str(DECISION_PATH))
    return json.loads(DECISION_PATH.read_text(encoding="utf-8"))

def to_repo_relative(path_str: str) -> Path:
    p = Path(path_str)
    try:
        return p.relative_to(PROJECT_ROOT)
    except Exception:
        return Path(path_str)

def add_to_fallbacks(text: str, selector: str) -> Tuple[str, bool]:
    """Add selector to a fallbacks=[...] list in the first matching call block if absent."""
    # crude but effective for demo: find 'fallbacks=[...]' and insert if missing
    m = re.search(r"fallbacks\s*=\s*\[(.*?)\]", text, flags=re.DOTALL)
    if not m:
        return text, False
    inside = m.group(1)
    if selector in inside:
        return text, False
    # insert before closing bracket
    new_inside = inside.strip()
    if new_inside and not new_inside.endswith(","):
        new_inside += ", "
    new_inside += repr(selector)
    new_text = text[:m.start(1)] + new_inside + text[m.end(1):]
    return new_text, True

def main()->int:
    d=load_decision()
    candidates = d.get("candidates", [])
    # group per file: use chosen selector to expand fallbacks
    file_to_selectors: Dict[Path, List[str]] = {}
    for c in candidates:
        fp = (c.get("file_path") or "").strip()
        sel = c.get("chosen")
        if not fp or not sel:
            continue
        rel = to_repo_relative(fp)
        file_path = (PROJECT_ROOT / rel) if not rel.is_absolute() else rel
        file_to_selectors.setdefault(file_path, []).append(sel)

    patches=[]
    changed=False
    for file_path, sels in file_to_selectors.items():
        if not file_path.exists():
            print("Skip missing:", file_path)
            continue
        original = file_path.read_text(encoding="utf-8").splitlines(keepends=True)
        txt = "".join(original)
        file_changed=False
        for sel in sels:
            txt2, ok = add_to_fallbacks(txt, sel)
            if ok:
                txt = txt2
                file_changed=True
        if not file_changed:
            continue
        updated = txt.splitlines(keepends=True)
        rel_name = str(file_path.relative_to(PROJECT_ROOT)) if str(file_path).startswith(str(PROJECT_ROOT)) else str(file_path)
        diff = difflib.unified_diff(original, updated, fromfile=rel_name, tofile=rel_name, lineterm="")
        patches.extend(list(diff))
        changed=True

    out_dir = PROJECT_ROOT / "reports" / "patches"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "fallback_expansion.patch"
    out_path.write_text("\n".join(patches) + "\n", encoding="utf-8")
    print("Patch created:", out_path)
    return 0 if changed else 1

if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import json
import os
import re
import sys
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DECISION_PATH = Path(os.getenv("SELF_HEAL_DIR", "reports/self_heal")) / "self_heal_decision.json"
PATCH_DIR = PROJECT_ROOT / "reports" / "patches"
PATCH_PATH = PATCH_DIR / "fallback_expansion.patch"


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)


def load_decision() -> dict:
    if not DECISION_PATH.exists():
        raise FileNotFoundError(str(DECISION_PATH))
    return json.loads(DECISION_PATH.read_text(encoding="utf-8"))


def to_repo_path(file_path: str) -> Path:
    p = Path(file_path)
    try:
        return p.relative_to(PROJECT_ROOT)
    except Exception:
        return p if p.is_absolute() else (PROJECT_ROOT / p)


def parse_fallbacks_list(text: str) -> Tuple[List[str], Tuple[int, int]] | Tuple[None, None]:
    """
    Find the first `fallbacks=[ ... ]` and parse it as a list of strings.
    Returns (list, (start_idx, end_idx)) where indices are the inside-of-brackets span.
    Very pragmatic parser: only supports string literals inside.
    """
    m = re.search(r"fallbacks\s*=\s*\[(.*?)\]", text, flags=re.DOTALL)
    if not m:
        return None, None
    inner = m.group(1).strip()
    start, end = m.start(1), m.end(1)

    if not inner:
        return [], (start, end)

    # Extract string literals safely-ish
    # Matches '...' or "..." (no nested quotes handling, but fine for our generated code)
    lits = re.findall(r"""(['"])(.*?)(\1)""", inner, flags=re.DOTALL)
    fallbacks = [s for _, s, _ in lits]
    return fallbacks, (start, end)


def replace_fallbacks_list(text: str, new_list: List[str], span: Tuple[int, int]) -> str:
    """
    Replace the inside of fallbacks=[ ... ] with a JSON-dumped list (valid Python list of strings).
    """
    start, end = span
    # json.dumps returns ["a", "b"] using double quotes; valid in Python
    dumped = json.dumps(new_list, ensure_ascii=False)
    # We only replace the inside; the brackets remain in place.
    return text[:start] + dumped[1:-1] + text[end:]


def main() -> int:
    d = load_decision()
    candidates = d.get("candidates", []) or []

    # group selectors per file (take chosen selectors)
    file_to_selectors: Dict[Path, List[str]] = {}
    for c in candidates:
        fp = (c.get("file_path") or "").strip()
        sel = (c.get("chosen") or "").strip()
        if not fp or not sel:
            continue
        repo_path = to_repo_path(fp)
        file_path = repo_path if repo_path.is_absolute() else (PROJECT_ROOT / repo_path)
        file_to_selectors.setdefault(file_path, []).append(sel)

    if not file_to_selectors:
        print("No candidates to expand fallbacks.")
        return 1

    PATCH_DIR.mkdir(parents=True, exist_ok=True)

    changed_any = False
    try:
        for file_path, selectors in file_to_selectors.items():
            if not file_path.exists():
                print(f"Skip missing file: {file_path}")
                continue

            original = file_path.read_text(encoding="utf-8")
            fallbacks, span = parse_fallbacks_list(original)
            if fallbacks is None or span is None:
                print(f"No fallbacks=[...] list found in {file_path}")
                continue

            new_list = list(fallbacks)
            for sel in selectors:
                if sel not in new_list:
                    new_list.append(sel)

            if new_list == fallbacks:
                print(f"No fallback changes needed in {file_path.name}")
                continue

            updated = replace_fallbacks_list(original, new_list, span)
            file_path.write_text(updated, encoding="utf-8")
            changed_any = True
            print(f"Expanded fallbacks in {file_path.name}: +{len(new_list)-len(fallbacks)} selector(s)")

        if not changed_any:
            print("No changes applied.")
            return 1

        run(["git", "add", "-N", "."])
        diff = run(["git", "diff", "--"])
        PATCH_PATH.write_text(diff.stdout, encoding="utf-8")

        chk = run(["git", "apply", "--check", str(PATCH_PATH)])
        if chk.returncode != 0:
            print("Patch failed git apply --check:")
            print(chk.stderr)
            return 2

        print(f"Patch created: {PATCH_PATH}")
        return 0

    finally:
        run(["git", "checkout", "--", "."])


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DECISION_PATH = Path(os.getenv("SELF_HEAL_DIR", "reports/self_heal")) / "self_heal_decision.json"
PATCH_DIR = PROJECT_ROOT / "reports" / "patches"
PATCH_PATH = PATCH_DIR / "fallback_expansion.patch"


def run(cmd: List[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)


def normalize_repo_path(fp: str) -> Path:
    """
    Normalize file paths coming from evidence so they work on GitHub runners.
    Handles:
      - repo-relative paths: pages/login_page.py
      - absolute local paths: /mnt/data/.../TestPilot-AI/.../pages/login_page.py
      - Windows paths: C:\\...\\TestPilot-AI\\pages\\login_page.py
    """
    p = Path(fp)

    if not p.is_absolute():
        return p

    s = str(p).replace("\\", "/")

    # Strip everything before /TestPilot-AI/ if present
    marker = "/TestPilot-AI/"
    if marker in s:
        return Path(s.split(marker, 1)[1])

    # Fallback: strip everything before /pages/ if present
    if "/pages/" in s:
        return Path("pages" + s.split("/pages/", 1)[1])

    # Last resort: filename only
    return Path(p.name)


def parse_fallbacks_list(text: str) -> Tuple[Optional[List[str]], Optional[Tuple[int, int]]]:
    """
    Find the first `fallbacks=[ ... ]` and parse string literals.
    Returns (fallbacks, (start_idx, end_idx)) where indices cover the inside of brackets.
    """
    m = re.search(r"fallbacks\s*=\s*\[(.*?)\]", text, flags=re.DOTALL)
    if not m:
        return None, None

    inner = m.group(1).strip()
    start, end = m.start(1), m.end(1)

    if not inner:
        return [], (start, end)

    # Extract string literals '...' or "..."
    lits = re.findall(r"""(['"])(.*?)(\1)""", inner, flags=re.DOTALL)
    fallbacks = [s for _, s, _ in lits]
    return fallbacks, (start, end)


def replace_fallbacks_list(text: str, new_list: List[str], span: Tuple[int, int]) -> str:
    """
    Replace the inside of `fallbacks=[ ... ]` with the contents of json.dumps(list)[1:-1]
    which yields a valid Python list interior:  "a", "b"
    """
    start, end = span
    dumped = json.dumps(new_list, ensure_ascii=False)  # ["a","b"] is valid Python too
    return text[:start] + dumped[1:-1] + text[end:]


def main() -> int:
    if not DECISION_PATH.exists():
        raise FileNotFoundError(f"Decision file not found: {DECISION_PATH}")

    decision = json.loads(DECISION_PATH.read_text(encoding="utf-8"))
    candidates = decision.get("candidates", []) or []

    # file -> selectors to add
    file_map: Dict[Path, List[str]] = {}
    for c in candidates:
        fp = (c.get("file_path") or "").strip()
        sel = (c.get("chosen") or "").strip()
        if not fp or not sel:
            continue

        rel_path = normalize_repo_path(fp)
        file_path = PROJECT_ROOT / rel_path
        file_map.setdefault(file_path, []).append(sel)

    if not file_map:
        print("No candidates found to expand fallbacks.")
        return 1

    PATCH_DIR.mkdir(parents=True, exist_ok=True)

    changed_files: List[Path] = []
    try:
        for file_path, selectors in file_map.items():
            if not file_path.exists():
                print(f"Skip missing file: {file_path}")
                continue

            original = file_path.read_text(encoding="utf-8")
            fallbacks, span = parse_fallbacks_list(original)
            if fallbacks is None or span is None:
                print(f"No fallbacks=[...] list found in {file_path}")
                continue

            # merge unique, preserve order
            new_list = list(fallbacks)
            for sel in selectors:
                if sel not in new_list:
                    new_list.append(sel)

            if new_list == fallbacks:
                print(f"No fallback changes needed in {file_path.name}")
                continue

            updated = replace_fallbacks_list(original, new_list, span)
            file_path.write_text(updated, encoding="utf-8")
            changed_files.append(file_path)
            print(f"Expanded fallbacks in {file_path.name}: +{len(new_list) - len(fallbacks)} selector(s)")

        if not changed_files:
            print("No files changed; no patch produced.")
            return 1

        # Generate patch ONLY for changed files
        rel_files = [str(p.relative_to(PROJECT_ROOT)) for p in changed_files]

        run(["git", "add", "-N", *rel_files])
        diff = run(["git", "diff", "--", *rel_files])
        PATCH_PATH.write_text(diff.stdout, encoding="utf-8")

        # Sanity-check patch
        chk = run(["git", "apply", "--check", str(PATCH_PATH)])
        if chk.returncode != 0:
            print("Patch failed git apply --check:")
            print(chk.stderr)
            return 2

        print(f"Patch created: {PATCH_PATH}")
        return 0

    finally:
        if changed_files:
            run(["git", "checkout", "--", *[str(p.relative_to(PROJECT_ROOT)) for p in changed_files]])


if __name__ == "__main__":
    raise SystemExit(main())

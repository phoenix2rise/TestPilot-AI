from __future__ import annotations

import ast
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

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

    Returns a *relative* path inside the repo.
    """
    p = Path(fp)
    if not p.is_absolute():
        return p

    s = str(p).replace("\\", "/")

    marker = "/TestPilot-AI/"
    if marker in s:
        return Path(s.split(marker, 1)[1])

    if "/pages/" in s:
        tail = s.split("/pages/", 1)[1]
        return Path("pages") / Path(tail)

    # last resort: keep filename only
    return Path(p.name)


def find_fallbacks_span(text: str) -> Tuple[Optional[Tuple[int, int]], Optional[List[str]]]:
    """
    Finds the span (start,end) of the *inside* of the list for `fallbacks=[ ... ]`
    and returns also a parsed list of string literals.

    We do not try to be a full parser; instead we:
      - locate the bracketed list using a small balanced-brackets scan
      - parse the interior using ast.literal_eval on a reconstructed list

    Returns:
      span: (inner_start, inner_end) inside the brackets
      items: list of string items (best effort)
    """
    # Locate "fallbacks" assignment
    m = re.search(r"\bfallbacks\s*=\s*\[", text)
    if not m:
        return None, None

    # m.end() points just after the opening '['
    inner_start = m.end()
    i = inner_start
    depth = 1
    in_str: Optional[str] = None
    esc = False

    # Balanced bracket scan to find the matching closing ']'
    while i < len(text):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == in_str:
                in_str = None
        else:
            if ch in ("'", '"'):
                in_str = ch
            elif ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0:
                    inner_end = i  # points at closing ']'
                    break
        i += 1
    else:
        return None, None

    inner = text[inner_start:inner_end].strip()

    # Parse existing list items safely
    items: List[str] = []
    if inner:
        try:
            reconstructed = "[" + inner + "]"
            val = ast.literal_eval(reconstructed)
            if isinstance(val, list):
                items = [str(x) for x in val if isinstance(x, (str, int, float, bool))]
                # keep only strings (selectors should be strings)
                items = [x for x in items if isinstance(x, str)]
        except Exception:
            # If parsing fails, fall back to extracting quoted strings
            lits = re.findall(r"""(['"])(.*?)(\1)""", inner, flags=re.DOTALL)
            items = [s for _, s, _ in lits]

    return (inner_start, inner_end), items


def build_list_interior_py(items: List[str]) -> str:
    """
    Returns a Python-valid list interior (without the surrounding brackets),
    using json.dumps for safe quoting/escaping.

    Example:
      ["a", "b"] -> "\"a\", \"b\""
    """
    dumped = json.dumps(items, ensure_ascii=False)  # ["a","b"]
    return dumped[1:-1]  # "a","b"


def dedupe_preserve_order(seq: List[str]) -> List[str]:
    seen = set()
    out = []
    for x in seq:
        if x not in seen:
            out.append(x)
            seen.add(x)
    return out


def main() -> int:
    if not DECISION_PATH.exists():
        raise FileNotFoundError(f"Decision file not found: {DECISION_PATH}")

    decision = json.loads(DECISION_PATH.read_text(encoding="utf-8"))
    candidates = decision.get("candidates", []) or []

    # Map file -> selectors to add
    file_map: Dict[Path, List[str]] = {}
    for c in candidates:
        fp = (c.get("file_path") or "").strip()
        sel = (c.get("chosen") or "").strip()
        if not fp or not sel:
            continue
        rel = normalize_repo_path(fp)
        file_path = (PROJECT_ROOT / rel).resolve()
        file_map.setdefault(file_path, []).append(sel)

    if not file_map:
        print("No candidates found to expand fallbacks.")
        return 1

    PATCH_DIR.mkdir(parents=True, exist_ok=True)

    changed_files: List[Path] = []
    rel_files: List[str] = []

    try:
        for file_path, selectors in file_map.items():
            if not file_path.exists():
                print(f"Skip missing file: {file_path}")
                continue

            original = file_path.read_text(encoding="utf-8")

            span, current = find_fallbacks_span(original)
            if span is None:
                print(f"No fallbacks=[...] found in {file_path}")
                continue

            # Merge + dedupe
            new_list = dedupe_preserve_order((current or []) + selectors)

            if new_list == (current or []):
                print(f"No fallback changes needed in {file_path.name}")
                continue

            inner_start, inner_end = span

            # IMPORTANT: replace ONLY the list interior; brackets remain.
            interior = build_list_interior_py(new_list)
            updated = original[:inner_start] + interior + original[inner_end:]

            # Generator-side hard guard: never write invalid Python
            try:
                ast.parse(updated)
            except SyntaxError as e:
                print(f"Generated invalid Python for {file_path}: {e}")
                return 2

            file_path.write_text(updated, encoding="utf-8")
            changed_files.append(file_path)
            rel_files.append(str(file_path.relative_to(PROJECT_ROOT)))
            print(f"Expanded fallbacks in {file_path.name}: +{len(new_list) - len(current or [])} selector(s)")

        if not changed_files:
            print("No files changed; no patch produced.")
            return 1

        # Create patch ONLY for changed files
        run(["git", "add", "-N", *rel_files])
        diff = run(["git", "diff", "--", *rel_files])
        PATCH_PATH.write_text(diff.stdout, encoding="utf-8")

        # Revert then check patch applies to a clean tree
        run(["git", "checkout", "--", *rel_files])

        chk = run(["git", "apply", "--check", str(PATCH_PATH)])
        if chk.returncode != 0:
            print("Patch failed git apply --check:")
            print(chk.stderr)
            return 3

        print(f"Patch created: {PATCH_PATH}")
        return 0

    finally:
        # Ensure the repo ends clean
        if rel_files:
            run(["git", "checkout", "--", *rel_files])


if __name__ == "__main__":
    raise SystemExit(main())

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

EVENTS_PATH = Path(os.getenv("SELF_HEAL_DIR", "reports/self_heal")) / "locator_events.jsonl"
PATCH_DIR = PROJECT_ROOT / "reports" / "patches"
PATCH_PATH = PATCH_DIR / "locator_self_heal.patch"

# promote after N fallback successes
MIN_COUNT = int(os.getenv("SELF_HEAL_MIN_COUNT", "2"))


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)


def parse_events() -> List[dict]:
    if not EVENTS_PATH.exists():
        return []
    out: List[dict] = []
    for line in EVENTS_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        out.append(json.loads(line))
    return out


def choose_updates(events: List[dict]) -> Dict[Tuple[str, str, str, str], Tuple[str, int]]:
    """
    Return {(file_path, class_name, field, action): (chosen_selector, count)} using most frequent chosen.
    """
    counts: Dict[Tuple[str, str, str, str, str], int] = {}
    for e in events:
        fp = (e.get("file_path") or "").strip()
        cls = (e.get("class_name") or "").strip()
        field = (e.get("field") or "").strip()
        action = (e.get("action") or "").strip()
        chosen = (e.get("chosen") or "").strip()
        if not (fp and cls and field and action and chosen):
            continue
        k = (fp, cls, field, action, chosen)
        counts[k] = counts.get(k, 0) + 1

    grouped: Dict[Tuple[str, str, str, str], List[Tuple[str, int]]] = {}
    for (fp, cls, field, action, chosen), c in counts.items():
        grouped.setdefault((fp, cls, field, action), []).append((chosen, c))

    updates: Dict[Tuple[str, str, str, str], Tuple[str, int]] = {}
    for gk, opts in grouped.items():
        # pick most frequent chosen
        opts.sort(key=lambda x: (-x[1], x[0]))
        chosen, c = opts[0]
        if c >= MIN_COUNT:
            updates[gk] = (chosen, c)
    return updates


def to_repo_path(file_path: str) -> Path:
    p = Path(file_path)
    try:
        return p.relative_to(PROJECT_ROOT)
    except Exception:
        # if absolute path, still try to resolve
        return p if p.is_absolute() else (PROJECT_ROOT / p)


def pick_target_field(file_text: str, base_field: str, action: str) -> str:
    """
    If `self.<base_field>_<action> = ...` exists, update that, else update base_field.
    """
    candidate = f"{base_field}_{action}"
    if re.search(rf"self\.{re.escape(candidate)}\s*=", file_text):
        return candidate
    return base_field


def update_assignment_text(file_text: str, field: str, new_selector: str) -> tuple[str, bool]:
    """
    Update the first occurrence of: self.<field> = "<...>" to new_selector.
    """
    pattern = rf"(self\.{re.escape(field)}\s*=\s*)(['\"])(.*?)(\2)"
    m = re.search(pattern, file_text)
    if not m:
        return file_text, False
    quote = m.group(2)
    updated = re.sub(pattern, rf"\1{quote}{new_selector}{quote}", file_text, count=1)
    return updated, True


def main() -> int:
    events = parse_events()
    if not events:
        print("No locator events found; nothing to patch.")
        return 0

    updates = choose_updates(events)
    if not updates:
        print(f"No updates met MIN_COUNT={MIN_COUNT}.")
        return 1

    PATCH_DIR.mkdir(parents=True, exist_ok=True)

    changed_files: List[Path] = []
    try:
        for (fp, cls, field, action), (selector, count) in updates.items():
            repo_path = to_repo_path(fp)
            file_path = repo_path if repo_path.is_absolute() else (PROJECT_ROOT / repo_path)
            if not file_path.exists():
                print(f"Skip missing file: {file_path}")
                continue

            original = file_path.read_text(encoding="utf-8")
            target_field = pick_target_field(original, field, action)
            updated, ok = update_assignment_text(original, target_field, selector)

            print(
                f"Update {file_path.name}:{cls}.{target_field} ({action}) -> {selector} [count={count}] : "
                f"{'OK' if ok else 'NOT_FOUND'}"
            )
            if not ok:
                continue

            if updated != original:
                file_path.write_text(updated, encoding="utf-8")
                changed_files.append(file_path)

        if not changed_files:
            print("No changes applied.")
            return 1

        # Ensure git sees modifications even if file wasn't tracked yet
        run(["git", "add", "-N", "."])

        # Produce canonical patch
        diff = run(["git", "diff", "--"])
        PATCH_PATH.write_text(diff.stdout, encoding="utf-8")

        # Sanity check
        chk = run(["git", "apply", "--check", str(PATCH_PATH)])
        if chk.returncode != 0:
            print("Patch failed git apply --check:")
            print(chk.stderr)
            return 2

        print(f"Patch created: {PATCH_PATH}")
        return 0

    finally:
        # Revert working tree
        run(["git", "checkout", "--", "."])


if __name__ == "__main__":
    raise SystemExit(main())

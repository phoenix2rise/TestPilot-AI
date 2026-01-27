from __future__ import annotations

import ast
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EVENTS_PATH = Path(os.getenv('SELF_HEAL_DIR', 'reports/self_heal')) / 'locator_events.jsonl'
PATCH_DIR = PROJECT_ROOT / 'reports' / 'patches'
PATCH_PATH = PATCH_DIR / 'locator_self_heal.patch'
MIN_COUNT = int(os.getenv('SELF_HEAL_MIN_COUNT', '2'))


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)


def normalize_repo_path(fp: str) -> Path:
    p = Path(fp)
    if not p.is_absolute():
        return p
    s = str(p).replace('\\', '/')
    marker = '/TestPilot-AI/'
    if marker in s:
        return Path(s.split(marker, 1)[1])
    if '/pages/' in s:
        tail = s.split('/pages/', 1)[1]
        return Path('pages') / Path(tail)
    return Path(p.name)


def parse_events() -> List[dict]:
    if not EVENTS_PATH.exists():
        return []
    return [json.loads(l) for l in EVENTS_PATH.read_text(encoding='utf-8').splitlines() if l.strip()]


def choose_updates(events: List[dict]) -> Dict[Tuple[str, str, str, str], Tuple[str, int]]:
    counts: Dict[Tuple[str, str, str, str, str], int] = {}
    for e in events:
        fp = (e.get('file_path') or '').strip()
        cls = (e.get('class_name') or '').strip()
        field = (e.get('field') or '').strip()
        action = (e.get('action') or '').strip()
        chosen = (e.get('chosen') or '').strip()
        if not all([fp, cls, field, action, chosen]):
            continue
        fp_norm = str(normalize_repo_path(fp))
        k = (fp_norm, cls, field, action, chosen)
        counts[k] = counts.get(k, 0) + 1

    grouped: Dict[Tuple[str, str, str, str], List[Tuple[str, int]]] = {}
    for (fp, cls, field, action, chosen), c in counts.items():
        grouped.setdefault((fp, cls, field, action), []).append((chosen, c))

    updates: Dict[Tuple[str, str, str, str], Tuple[str, int]] = {}
    for gk, opts in grouped.items():
        opts.sort(key=lambda x: (-x[1], x[0]))
        chosen, c = opts[0]
        if c >= MIN_COUNT:
            updates[gk] = (chosen, c)
    return updates


def update_assignment_text(text: str, field: str, selector: str) -> str:
    pat = rf'(self\.{re.escape(field)}\s*=\s*)([\'\"])(.*?)(\2)'
    return re.sub(pat, rf'\1\2{selector}\2', text, count=1)


def main() -> int:
    updates = choose_updates(parse_events())
    if not updates:
        print('No updates.')
        return 1

    PATCH_DIR.mkdir(parents=True, exist_ok=True)

    changed_files: List[Path] = []
    rel_files: List[str] = []

    try:
        for (fp, cls, field, action), (selector, count) in updates.items():
            file_path = (PROJECT_ROOT / Path(fp)).resolve()
            if not file_path.exists():
                print(f'Skip missing file: {file_path}')
                continue

            original = file_path.read_text(encoding='utf-8')
            updated = update_assignment_text(original, field, selector)
            if updated == original:
                continue

            try:
                ast.parse(updated)
            except SyntaxError as e:
                print(f'Generated invalid Python for {file_path}: {e}')
                return 2

            file_path.write_text(updated, encoding='utf-8')
            changed_files.append(file_path)
            rel_files.append(str(file_path.relative_to(PROJECT_ROOT)))

        if not changed_files:
            print('No changes.')
            return 1

        run(['git', 'add', '-N', *rel_files])
        diff = run(['git', 'diff', '--', *rel_files])
        PATCH_PATH.write_text(diff.stdout, encoding='utf-8')

        run(['git', 'checkout', '--', *rel_files])

        chk = run(['git', 'apply', '--check', str(PATCH_PATH)])
        if chk.returncode != 0:
            print(chk.stderr)
            return 3

        print(f'Patch created: {PATCH_PATH}')
        return 0

    finally:
        if rel_files:
            run(['git', 'checkout', '--', *rel_files])


if __name__ == '__main__':
    raise SystemExit(main())

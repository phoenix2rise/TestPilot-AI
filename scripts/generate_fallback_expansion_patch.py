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


def find_fallbacks_span(text: str) -> Tuple[Optional[Tuple[int, int]], Optional[List[str]]]:
    m = re.search(r'\bfallbacks\s*=\s*\[', text)
    if not m:
        return None, None

    inner_start = m.end()
    i = inner_start
    depth = 1
    in_str: Optional[str] = None
    esc = False

    while i < len(text):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == '\\':
                esc = True
            elif ch == in_str:
                in_str = None
        else:
            if ch in ('\'', '"'):
                in_str = ch
            elif ch == '[':
                depth += 1
            elif ch == ']':
                depth -= 1
                if depth == 0:
                    inner_end = i
                    break
        i += 1
    else:
        return None, None

    inner = text[inner_start:inner_end].strip()
    items: List[str] = []
    if inner:
        try:
            val = ast.literal_eval('[' + inner + ']')
            if isinstance(val, list):
                items = [x for x in val if isinstance(x, str)]
        except Exception:
            lits = re.findall(r"""(['\"])(.*?)(\1)""", inner, flags=re.DOTALL)
            items = [s for _, s, _ in lits]

    return (inner_start, inner_end), items


def build_list_interior_py(items: List[str]) -> str:
    dumped = json.dumps(items, ensure_ascii=False)
    return dumped[1:-1]


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
        raise FileNotFoundError(f'Decision file not found: {DECISION_PATH}')

    decision = json.loads(DECISION_PATH.read_text(encoding='utf-8'))
    candidates = decision.get('candidates', []) or []

    file_map: Dict[Path, List[str]] = {}
    for c in candidates:
        fp = (c.get('file_path') or '').strip()
        sel = (c.get('chosen') or '').strip()
        if not fp or not sel:
            continue
        rel = normalize_repo_path(fp)
        file_map.setdefault((PROJECT_ROOT / rel).resolve(), []).append(sel)

    if not file_map:
        print('No candidates found to expand fallbacks.')
        return 1

    PATCH_DIR.mkdir(parents=True, exist_ok=True)

    changed_files: List[Path] = []
    rel_files: List[str] = []

    try:
        for file_path, selectors in file_map.items():
            if not file_path.exists():
                print(f'Skip missing file: {file_path}')
                continue

            original = file_path.read_text(encoding='utf-8')
            span, current = find_fallbacks_span(original)
            if span is None:
                print(f'No fallbacks=[...] found in {file_path}')
                continue

            new_list = dedupe_preserve_order((current or []) + selectors)
            if new_list == (current or []):
                print(f'No fallback changes needed in {file_path.name}')
                continue

            inner_start, inner_end = span
            updated = original[:inner_start] + build_list_interior_py(new_list) + original[inner_end:]

            try:
                ast.parse(updated)
            except SyntaxError as e:
                print(f'Generated invalid Python for {file_path}: {e}')
                return 2

            file_path.write_text(updated, encoding='utf-8')
            changed_files.append(file_path)
            rel_files.append(str(file_path.relative_to(PROJECT_ROOT)))
            print(f'Expanded fallbacks in {file_path.name}: +{len(new_list) - len(current or [])} selector(s)')

        if not changed_files:
            print('No files changed; no patch produced.')
            return 1

        run(['git', 'add', '-N', *rel_files])
        diff = run(['git', 'diff', '--', *rel_files])
        PATCH_PATH.write_text(diff.stdout, encoding='utf-8')

        run(['git', 'checkout', '--', *rel_files])

        chk = run(['git', 'apply', '--check', str(PATCH_PATH)])
        if chk.returncode != 0:
            print('Patch failed git apply --check:')
            print(chk.stderr)
            return 3

        print(f'Patch created: {PATCH_PATH}')
        return 0

    finally:
        if rel_files:
            run(['git', 'checkout', '--', *rel_files])


if __name__ == '__main__':
    raise SystemExit(main())

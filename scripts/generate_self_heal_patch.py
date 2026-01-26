from __future__ import annotations

import json, os, re, sys, subprocess
from pathlib import Path
from typing import Dict, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

EVENTS_PATH = Path(os.getenv("SELF_HEAL_DIR", "reports/self_heal")) / "locator_events.jsonl"
PATCH_DIR = PROJECT_ROOT / "reports" / "patches"
PATCH_PATH = PATCH_DIR / "locator_self_heal.patch"
MIN_COUNT = int(os.getenv("SELF_HEAL_MIN_COUNT", "2"))


def run(cmd: list[str]):
    return subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)


def parse_events() -> List[dict]:
    if not EVENTS_PATH.exists():
        return []
    return [json.loads(l) for l in EVENTS_PATH.read_text().splitlines() if l.strip()]


def choose_updates(events):
    counts = {}
    for e in events:
        fp = e.get("file_path","").strip()
        cls = e.get("class_name","").strip()
        field = e.get("field","").strip()
        action = e.get("action","").strip()
        chosen = e.get("chosen","").strip()
        if not all([fp, cls, field, action, chosen]):
            continue
        k = (fp, cls, field, action, chosen)
        counts[k] = counts.get(k,0)+1

    grouped = {}
    for (fp,cls,field,action,chosen),c in counts.items():
        grouped.setdefault((fp,cls,field,action),[]).append((chosen,c))

    updates={}
    for gk,opts in grouped.items():
        opts.sort(key=lambda x:(-x[1],x[0]))
        chosen,c=opts[0]
        if c>=MIN_COUNT:
            updates[gk]=(chosen,c)
    return updates


def update_assignment_text(text, field, selector):
    pat = rf"(self\.{re.escape(field)}\s*=\s*)(['\"])(.*?)(\2)"
    return re.sub(pat, rf"\1\2{selector}\2", text, count=1)

def normalize_repo_path(fp: str) -> Path:
    p = Path(fp)
    if p.is_absolute():
        # try to strip everything up to the repo folder name if present
        s = str(p).replace("\\", "/")
        marker = "/TestPilot-AI/"
        if marker in s:
            return Path(s.split(marker, 1)[1])
        # fallback: try last 2-3 parts (pages/login_page.py)
        parts = p.parts
        if "pages" in parts:
            idx = parts.index("pages")
            return Path(*parts[idx:])
        return Path(p.name)
    return Path(fp)

def main():
    events=parse_events()
    updates=choose_updates(events)
    if not updates:
        print("No updates.")
        return 0

    PATCH_DIR.mkdir(parents=True,exist_ok=True)
    changed_files=[]

    try:
        for (fp,cls,field,action),(selector,count) in updates.items():
            rel_path = normalize_repo_path(fp)
            file_path = PROJECT_ROOT / rel_path
            if not file_path.exists():
                print(f"Skip missing file: {file_path}")
                continue

            original=file_path.read_text()
            updated=update_assignment_text(original, field, selector)
            if updated!=original:
                file_path.write_text(updated)
                changed_files.append(file_path)

        if not changed_files:
            print("No changes.")
            return 1

        files=[str(p.relative_to(PROJECT_ROOT)) for p in changed_files]
        run(["git","add","-N"]+files)
        diff=run(["git","diff","--"]+files)

        PATCH_PATH.write_text(diff.stdout)
        chk=run(["git","apply","--check",str(PATCH_PATH)])
        if chk.returncode!=0:
            print(chk.stderr)
            return 2

        print(f"Patch created: {PATCH_PATH}")
        return 0

    finally:
        run(["git","checkout","--"]+[str(p) for p in changed_files])


if __name__=="__main__":
    raise SystemExit(main())

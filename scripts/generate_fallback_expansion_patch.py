from __future__ import annotations

import json, os, re, sys, subprocess
from pathlib import Path
from typing import Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT_ROOT))

DECISION_PATH = Path(os.getenv("SELF_HEAL_DIR","reports/self_heal"))/"self_heal_decision.json"
PATCH_DIR = PROJECT_ROOT/"reports"/"patches"
PATCH_PATH = PATCH_DIR/"fallback_expansion.patch"


def run(cmd):
    return subprocess.run(cmd,cwd=PROJECT_ROOT,capture_output=True,text=True)


def parse_fallbacks(text):
    m=re.search(r"fallbacks\s*=\s*\[(.*?)\]",text,re.DOTALL)
    if not m:
        return None,None
    inner=m.group(1)
    vals=re.findall(r"""['"](.*?)['"]""",inner)
    return vals,(m.start(1),m.end(1))


def main():
    d=json.loads(DECISION_PATH.read_text())
    file_map:Dict[Path,List[str]]={}

    for c in d.get("candidates",[]):
        fp=c.get("file_path")
        sel=c.get("chosen")
        if fp and sel:
            file_map.setdefault(PROJECT_ROOT/fp,[]).append(sel)

    PATCH_DIR.mkdir(parents=True,exist_ok=True)
    changed_files=[]

    try:
        for file_path,sels in file_map.items():
            if not file_path.exists():
                print(f"Skip missing file: {file_path}")
                continue

            text=file_path.read_text()
            fallbacks,span=parse_fallbacks(text)
            if fallbacks is None:
                continue

            new=list(dict.fromkeys(fallbacks+sels))
            if new==fallbacks:
                continue

            dumped=json.dumps(new,ensure_ascii=False)
            updated=text[:span[0]]+dumped[1:-1]+text[span[1]:]
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

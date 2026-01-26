from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
POINT_PATH = PROJECT_ROOT / "reports" / "self_heal" / "learning_curve_point.json"

SITE_DIR = PROJECT_ROOT / "docs_site"
SITE_DIR.mkdir(parents=True, exist_ok=True)

def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=False, capture_output=True, text=True)

HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>TestPilot-AI Evidence Trend</title>
  <style>
    body{font-family:system-ui,Segoe UI,Roboto,Arial,sans-serif;margin:24px;max-width:1000px}
    .card{border:1px solid #e5e7eb;border-radius:14px;padding:16px;margin:16px 0;box-shadow:0 1px 4px rgba(0,0,0,.05)}
    h1{margin:0 0 10px 0}
    code{background:#f3f4f6;padding:2px 6px;border-radius:8px}
    canvas{width:100%;height:360px}
    .muted{color:#6b7280}
    table{border-collapse:collapse;width:100%}
    td,th{border-bottom:1px solid #eee;padding:8px;text-align:left;font-size:14px}
  </style>
</head>
<body>
  <h1>TestPilot-AI Evidence Trend</h1>
  <p class="muted">Self-heal evidence_score over time, generated from CI artifacts.</p>

  <div class="card">
    <h2>Evidence score</h2>
    <canvas id="chart" width="1000" height="360"></canvas>
    <p class="muted">Y-axis: evidence_score (0..1). X-axis: run order.</p>
  </div>

  <div class="card">
    <h2>Latest run</h2>
    <pre id="latest" class="muted"></pre>
  </div>

  <div class="card">
    <h2>Runs</h2>
    <table id="tbl">
      <thead><tr><th>#</th><th>ts</th><th>mode</th><th>events</th><th>items</th><th>evidence_score</th><th>sha</th></tr></thead>
      <tbody></tbody>
    </table>
  </div>

<script>
async function load() {
  const res = await fetch('learning_curve.json', {cache:'no-store'});
  const data = await res.json();
  const latest = data[data.length-1] || {};
  document.getElementById('latest').textContent = JSON.stringify(latest, null, 2);

  // table
  const tbody = document.querySelector('#tbl tbody');
  tbody.innerHTML = '';
  data.forEach((p, idx) => {
    const tr = document.createElement('tr');
    const ts = p.ts ? new Date(p.ts*1000).toISOString() : '';
    const sha = (p.sha || '').toString().slice(0,7);
    tr.innerHTML = `<td>${idx+1}</td><td>${ts}</td><td>${p.mode||''}</td><td>${p.events??''}</td><td>${p.items??''}</td><td>${(p.evidence_score??0).toFixed(3)}</td><td><code>${sha}</code></td>`;
    tbody.appendChild(tr);
  });

  // simple canvas chart
  const c = document.getElementById('chart');
  const ctx = c.getContext('2d');
  ctx.clearRect(0,0,c.width,c.height);

  const padding = 40;
  const W = c.width - padding*2;
  const H = c.height - padding*2;

  const ys = data.map(p => p.evidence_score ?? 0);
  const maxY = 1.0;
  const minY = 0.0;

  // axes
  ctx.strokeStyle = '#111';
  ctx.beginPath();
  ctx.moveTo(padding, padding);
  ctx.lineTo(padding, padding+H);
  ctx.lineTo(padding+W, padding+H);
  ctx.stroke();

  // grid + labels
  ctx.fillStyle = '#111';
  ctx.font = '12px system-ui';
  for (let i=0;i<=5;i++){
    const y = padding + H - (H*i/5);
    ctx.strokeStyle = '#eee';
    ctx.beginPath();
    ctx.moveTo(padding, y);
    ctx.lineTo(padding+W, y);
    ctx.stroke();
    const v = (minY + (maxY-minY)*i/5).toFixed(2);
    ctx.fillText(v, 8, y+4);
  }

  if (data.length === 0) return;

  // line
  ctx.strokeStyle = '#2563eb';
  ctx.lineWidth = 2;
  ctx.beginPath();
  data.forEach((p, i) => {
    const x = padding + (W * (data.length===1 ? 0.5 : i/(data.length-1)));
    const yv = (p.evidence_score ?? 0);
    const y = padding + H - (H * ((yv-minY)/(maxY-minY)));
    if (i===0) ctx.moveTo(x,y); else ctx.lineTo(x,y);
  });
  ctx.stroke();

  // points
  ctx.fillStyle = '#2563eb';
  data.forEach((p,i)=>{
    const x = padding + (W * (data.length===1 ? 0.5 : i/(data.length-1)));
    const yv = (p.evidence_score ?? 0);
    const y = padding + H - (H * ((yv-minY)/(maxY-minY)));
    ctx.beginPath();
    ctx.arc(x,y,4,0,Math.PI*2);
    ctx.fill();
  });
}
load();
</script>
</body>
</html>
"""

def ensure_site_files(points: list[dict]) -> None:
    (SITE_DIR / "index.html").write_text(HTML_TEMPLATE, encoding="utf-8")
    (SITE_DIR / "learning_curve.json").write_text(json.dumps(points, indent=2), encoding="utf-8")

def main() -> int:
    if not POINT_PATH.exists():
        print(f"Missing {POINT_PATH}; run self-heal workflow first.")
        return 2

    point = json.loads(POINT_PATH.read_text(encoding="utf-8"))

    # Work in a temp directory for gh-pages
    tmp = PROJECT_ROOT / ".tmp_gh_pages"
    if tmp.exists():
        run(["rm","-rf",str(tmp)])
    tmp.mkdir(parents=True, exist_ok=True)

    # Fetch and checkout gh-pages
    run(["git","fetch","origin","gh-pages:gh-pages"])
    r = run(["git","worktree","add",str(tmp),"gh-pages"])
    if r.returncode != 0:
        # Create gh-pages if missing
        run(["git","checkout","--orphan","gh-pages"])
        run(["git","reset","--hard"])
        run(["git","commit","--allow-empty","-m","init gh-pages"])
        run(["git","checkout","-"])
        run(["git","worktree","add",str(tmp),"gh-pages"])

    # Read existing points
    lc_path = tmp / "learning_curve.json"
    points = []
    if lc_path.exists():
        try:
            points = json.loads(lc_path.read_text(encoding="utf-8"))
        except Exception:
            points = []

    points.append(point)
    # keep last 200
    points = points[-200:]

    # Write site files into worktree
    (tmp / "index.html").write_text(HTML_TEMPLATE, encoding="utf-8")
    (tmp / "learning_curve.json").write_text(json.dumps(points, indent=2), encoding="utf-8")

    # Commit + push
    run(["git","-C",str(tmp),"add","-A"])
    msg = f"Update evidence trend ({point.get('mode','UNKNOWN')})"
    c = run(["git","-C",str(tmp),"commit","-m",msg])
    if c.returncode != 0:
        print("No changes to commit.")
    p = run(["git","-C",str(tmp),"push","origin","HEAD:gh-pages"])
    if p.returncode != 0:
        raise RuntimeError(p.stderr)

    print("Published to gh-pages.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import os
import time
import sys
from pathlib import Path

# Ensure project root is on sys.path when running as a script
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from security.qkd.bb84 import BB84Params
from security.qkd.channel import establish_qkd_session
from mcp.gateway import default_gateway, SessionContext

def make_demo_patch(patch_path: str) -> None:
    """Create a tiny patch that updates a demo file. This stands in for a locator fix."""
    demo_file = PROJECT_ROOT / "agents" / "SELF_HEAL_DEMO.md"
    if not demo_file.exists():
        demo_file.write_text("# Self-Heal Demo\n\nThis file is modified by the secure self-heal workflow.\n", encoding="utf-8")

    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    demo_file.write_text(demo_file.read_text(encoding="utf-8") + f"\n- Demo patch applied at {stamp} UTC\n", encoding="utf-8")

    # produce patch
    os.system("git add -N agents/SELF_HEAL_DEMO.md >/dev/null 2>&1")
    os.system(f"git diff -- agents/SELF_HEAL_DEMO.md > {patch_path}")

    # revert working tree change; patch will be applied by privileged tool
    os.system("git checkout -- agents/SELF_HEAL_DEMO.md >/dev/null 2>&1")

def main() -> int:
    enable_pr = os.getenv("ENABLE_PR", "false").lower() == "true"
    if not enable_pr:
        print("ENABLE_PR is false; exiting without opening PR.")
        return 0

    params = BB84Params()
    sess = establish_qkd_session(params, intercept_resend=False, ttl_seconds=300)
    print("QKD:", "accepted" if sess.accepted else "rejected", "qber=", round(sess.qber, 3), "fp=", sess.key_fingerprint)
    if not sess.accepted:
        print("SECURITY_ABORT: QKD session not accepted.")
        return 2

    patch_dir = PROJECT_ROOT / "reports" / "patches"
    patch_dir.mkdir(parents=True, exist_ok=True)
    patch_path = str(patch_dir / "secure_self_heal_demo.patch")
    make_demo_patch(patch_path)

    g = default_gateway()
    ctx = SessionContext(
        qkd_created_ts=sess.created_ts,
        qkd_expires_ts=sess.expires_ts,
        qkd_accepted=sess.accepted,
        qkd_key_fingerprint=sess.key_fingerprint,
    )

    branch = f"secure-self-heal/{int(time.time())}"
    title = "Secure self-heal demo (QKD-gated)"
    body = "\n".join([
        "This PR was created by TestPilot-AI's secure self-heal demo.",
        "",
        f"- QKD session fingerprint: `{sess.key_fingerprint}`",
        f"- QBER: `{sess.qber:.3f}`",
        "- Policy: privileged actions allowed only when QKD is accepted and not expired.",
        "",
        f"Patch applied: `{patch_path}`",
        ""
    ])

    res = g.invoke("commit_fix", {
        "patch_path": patch_path,
        "branch": branch,
        "title": title,
        "body": body,
        "base": os.getenv("BASE_BRANCH", "main"),
    }, session=ctx)

    print(res)
    return 0 if res.get("ok") else 3

if __name__ == "__main__":
    raise SystemExit(main())

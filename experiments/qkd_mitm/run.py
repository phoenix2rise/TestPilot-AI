"""
Run QKD MITM experiment:
- baseline channel (no intercept) expected to ACCEPT (low QBER)
- intercept-resend expected to REJECT (high QBER)
Outputs a JSON artifact for CI.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import asdict

from security.qkd.bb84 import BB84Params
from security.qkd.channel import establish_qkd_session

def main() -> int:
    n = int(os.getenv("QKD_N_QUBITS", "2048"))
    sample = int(os.getenv("QKD_SAMPLE_SIZE", "256"))
    thresh = float(os.getenv("QKD_QBER_THRESHOLD", "0.11"))
    ttl = int(os.getenv("QKD_TTL_SECONDS", "60"))

    params = BB84Params(n_qubits=n, sample_size=sample, qber_threshold=thresh)

    clean = establish_qkd_session(params, intercept_resend=False, ttl_seconds=ttl, include_transcript=False)
    mitm = establish_qkd_session(params, intercept_resend=True, ttl_seconds=ttl, include_transcript=False)

    artifact = {
        "ts": time.time(),
        "params": asdict(params),
        "clean": asdict(clean),
        "mitm": asdict(mitm),
        "assertions": {
            "clean_should_accept": clean.accepted,
            "mitm_should_reject": (not mitm.accepted),
        }
    }

    out_dir = os.getenv("QKD_ARTIFACT_DIR", "reports/qkd")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "qkd_mitm_artifact.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(artifact, f, indent=2)

    # Exit code: fail if assertions not met
    if not artifact["assertions"]["clean_should_accept"]:
        print("SECURITY_ABORT: Clean channel was rejected (unexpected).")
        print(f"QBER(clean)={clean.qber:.3f} threshold={thresh}")
        return 2
    if not artifact["assertions"]["mitm_should_reject"]:
        print("SECURITY_ABORT: MITM channel was accepted (unexpected).")
        print(f"QBER(mitm)={mitm.qber:.3f} threshold={thresh}")
        return 3

    print("QKD experiment OK")
    print(f"QBER(clean)={clean.qber:.3f} accepted={clean.accepted}")
    print(f"QBER(mitm)={mitm.qber:.3f} accepted={mitm.accepted} (expected False)")
    print(f"Artifact: {out_path}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

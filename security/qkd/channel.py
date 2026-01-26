"""
Channel models for BB84 experiments and "realtime proof" demos.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, Any
import time
from .bb84 import BB84Params, simulate_bb84, derive_session_key, BB84Transcript

@dataclass
class QKDSession:
    created_ts: float
    expires_ts: float
    qber: float
    accepted: bool
    reason: str
    key_fingerprint: str
    transcript: Optional[BB84Transcript] = None

def establish_qkd_session(
    params: BB84Params,
    *,
    intercept_resend: bool = False,
    ttl_seconds: int = 60,
    include_transcript: bool = False
) -> QKDSession:
    t = simulate_bb84(params, intercept_resend=intercept_resend)
    now = time.time()

    key_fp = "N/A"
    if t.accepted:
        key = derive_session_key(t)
        import hashlib
        key_fp = hashlib.sha256(key).hexdigest()[:16]

    return QKDSession(
        created_ts=now,
        expires_ts=now + ttl_seconds,
        qber=t.qber,
        accepted=t.accepted,
        reason=t.reason,
        key_fingerprint=key_fp,
        transcript=t if include_transcript else None
    )

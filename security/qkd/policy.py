"""
Policy engine: gate privileged tool execution on QKD session validity.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import time

@dataclass
class PolicyDecision:
    allowed: bool
    reason: str

def is_session_valid(created_ts: float, expires_ts: float, accepted: bool) -> PolicyDecision:
    now = time.time()
    if not accepted:
        return PolicyDecision(False, "DENY:QKD_NOT_ACCEPTED")
    if now >= expires_ts:
        return PolicyDecision(False, "DENY:QKD_SESSION_EXPIRED")
    return PolicyDecision(True, "ALLOW:QKD_SESSION_VALID")

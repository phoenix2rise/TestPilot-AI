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


def evaluate_tool_policy(
    *,
    tool_name: str,
    evidence_confidence: Optional[float] = None,
    min_confidence: float = 0.6,
) -> PolicyDecision:
    if tool_name == "commit_fix":
        if evidence_confidence is None:
            return PolicyDecision(False, "DENY:EXTERNAL_EVIDENCE_REQUIRED")
        if evidence_confidence < min_confidence:
            return PolicyDecision(False, "DENY:EVIDENCE_CONFIDENCE_TOO_LOW")
    return PolicyDecision(True, "ALLOW:TOOL_POLICY_OK")

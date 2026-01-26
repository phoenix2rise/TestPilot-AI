"""
Metrics helpers for experiments.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict
import statistics

@dataclass(frozen=True)
class QKDSummary:
    runs: int
    accepted: int
    rejected: int
    acceptance_rate: float
    qber_mean: float
    qber_median: float
    qber_stdev: float

def summarize_qber(qbers: List[float], accepted_flags: List[bool]) -> QKDSummary:
    if len(qbers) == 0:
        raise ValueError("No runs to summarize")
    acc = sum(1 for a in accepted_flags if a)
    rej = len(accepted_flags) - acc
    mean = statistics.mean(qbers)
    median = statistics.median(qbers)
    stdev = statistics.pstdev(qbers) if len(qbers) > 1 else 0.0
    return QKDSummary(
        runs=len(qbers),
        accepted=acc,
        rejected=rej,
        acceptance_rate=acc / len(accepted_flags),
        qber_mean=mean,
        qber_median=median,
        qber_stdev=stdev
    )

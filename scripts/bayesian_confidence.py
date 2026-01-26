from __future__ import annotations
import math

def beta_posterior(successes: int, failures: int, alpha: float = 1.0, beta: float = 1.0) -> float:
    """Return posterior mean of Beta distribution."""
    return (alpha + successes) / (alpha + beta + successes + failures)

def credible_interval(successes: int, failures: int, alpha: float = 1.0, beta: float = 1.0, z: float = 1.96):
    """Approximate 95% CI using normal approx."""
    mean = beta_posterior(successes, failures, alpha, beta)
    var = (mean * (1 - mean)) / (successes + failures + alpha + beta + 1)
    sd = math.sqrt(var)
    return max(0.0, mean - z * sd), min(1.0, mean + z * sd)

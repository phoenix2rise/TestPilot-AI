from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Tuple

@dataclass(frozen=True)
class BetaPosterior:
    alpha: float
    beta: float

    @property
    def mean(self) -> float:
        return self.alpha / (self.alpha + self.beta)

def beta_posterior(successes: int, failures: int, *, prior_alpha: float = 1.0, prior_beta: float = 1.0) -> BetaPosterior:
    """Beta-Binomial posterior for Bernoulli success probability."""
    if successes < 0 or failures < 0:
        raise ValueError("successes/failures must be >= 0")
    return BetaPosterior(prior_alpha + successes, prior_beta + failures)

def normal_approx_credible_interval(p: BetaPosterior, z: float = 1.96) -> Tuple[float, float]:
    """
    Approximate 95% credible interval for Beta using normal approximation.
    Works well for moderate counts; for tiny counts this is still a useful *signal* for portfolio.
    """
    a, b = p.alpha, p.beta
    mean = a / (a + b)
    var = (a * b) / (((a + b) ** 2) * (a + b + 1))
    sd = math.sqrt(var)
    lo = max(0.0, mean - z * sd)
    hi = min(1.0, mean + z * sd)
    return lo, hi

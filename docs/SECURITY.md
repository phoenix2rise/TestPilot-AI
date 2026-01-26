# Security Model

## Threat model (examples)
- MITM on agent-to-tool channel
- Replay of tool invocations
- Compromised CI runner
- Prompt injection / tool misuse by an agent

## Goals
- Prevent privileged actions unless the session is trusted.
- Detect interception attempts in the (simulated) QKD exchange.
- Produce auditable evidence in CI runs.

## QKD note
This project uses a **protocol-accurate BB84 simulation** to demonstrate:
- key agreement via sifting
- QBER-based interception detection
- session gating based on acceptance + TTL

## Authentication
QKD does not authenticate endpoints by itself.
In production, authenticate the classical channel with signatures (ideally post-quantum) and use QKD for key material.

## Policies
- Privileged tools require: QKD accepted AND not expired.
- If QKD acceptance fails: terminate privileged actions and log `SECURITY_ABORT`.

## Limitations
- No physical quantum channel is assumed.
- Privacy amplification here is demo-grade (hash-based KDF) used for gating, not a formal PA scheme.


## Self-heal safety ladder
Locator updates follow a conservative policy:
- If evidence is weak, we **expand fallbacks** (reduce flakiness without changing primary locators).
- If evidence meets thresholds (count + confidence), we **promote** the proven fallback selector to the primary locator.
This reduces the risk of incorrect auto-fixes.


## Bayesian evidence scoring
Self-heal promotion decisions use a Beta-Binomial posterior over the probability that a candidate selector is the correct stable choice. We gate promotion on:
- minimum observed count
- posterior mean above a threshold
- lower bound of an approximate 95% credible interval above a threshold
This keeps the policy explainable while adding research-friendly rigor.

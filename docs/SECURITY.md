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

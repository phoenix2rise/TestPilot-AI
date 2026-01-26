# Experiments (Research-style)

## Experiment: BB84 Intercept-Resend Detection
Location: `experiments/qkd_mitm/`

### Parameters
- n_qubits: default 2048
- sample_size: default 256
- qber_threshold: default 0.11

### Method
1. Simulate BB84 with no interception (clean channel).
2. Simulate BB84 with intercept-resend eavesdropper.
3. Perform sifting and sample-based QBER estimation.
4. Accept session if QBER <= threshold.

### Metrics
- QBER (clean vs MITM)
- Acceptance decision
- False accept (MITM accepted) rate (should be near 0 with defaults)

### Repro steps (CI)
Run:
`python -m experiments.qkd_mitm.run`

Artifact:
`reports/qkd/qkd_mitm_artifact.json`

### Threats to validity
- Simulation simplifies quantum effects and assumes idealized intercept-resend.
- Authentication of endpoints is out of scope for the simulation.

## Bayesian confidence model
Self-heal promotion uses a Beta posterior over fallback success events. We compute posterior mean and 95% credible intervals to decide whether to promote selectors.


## Experiment: Self-heal learning curve
Location: `experiments/self_heal_learning_curve/`

- `run.py` produces a per-run metrics point: `reports/self_heal/learning_curve_point.json`
- `aggregate.py` can combine many points (downloaded from CI artifacts) into a time-series CSV/JSON and an optional plot.

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

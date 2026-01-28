# Reproducibility

## Determinism
The BB84 simulation uses `secrets` for randomness.
For academic-style deterministic runs, you can extend the simulator to accept a seeded PRNG.
For CI proof-of-behavior, nondeterminism is acceptable as long as the assertions hold robustly.

## CI artifacts
- Allure outputs under `reports/` (multi-browser runs share the same results directory; each test is labeled with the `browser` parameter so the report can be filtered/grouped by browser).
- QKD artifact under `reports/qkd/qkd_mitm_artifact.json`

## How to rerun locally
1. Create venv
2. `pip install -r requirements.txt`
3. `python -m experiments.qkd_mitm.run`
4. `pytest`

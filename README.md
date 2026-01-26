[![Evidence Trend](https://img.shields.io/badge/Live-Evidence%20Trend-success)](https://phoenix2rise.github.io/TestPilot-AI/)
[![Secure Self-Heal](https://github.com/phoenix2rise/TestPilot-AI/actions/workflows/secure-self-heal.yml/badge.svg)](https://github.com/phoenix2rise/TestPilot-AI/actions/workflows/secure-self-heal.yml)
# TestPilot-AI

## Badges

- **Live Evidence Trend**: opens the GitHub Pages dashboard that charts `evidence_score` over time.
- **Secure Self-Heal**: opens the workflow runs where you can download the latest evidence artifacts (QKD MITM proof, self-heal summaries, patches, and learning-curve point).

Evidence Trend: `https://phoenix2rise.github.io/TestPilot-AI/`
Workflow: `https://github.com/phoenix2rise/TestPilot-AI/actions/workflows/secure-self-heal.yml`

An advanced Python Playwright automation framework featuring:

- ✅ UI & API tests
- 🔁 Retry logic for flaky tests
- 📊 HTML and Allure reporting
- 🔔 Slack notifications via GitHub Actions
- 🌐 Cross-browser CI
- 📂 Self-healing locators and modular design
- 🖼 Visual comparison testing
- ⚡ Performance testing
- 🤖 ChatGPT-assisted test script generation

## 🚀 How to Use

1. Install dependencies:
    ```bash
    pip install -r requirements.txt
    playwright install
    ```

2. Run tests with:
    ```bash
    pytest --browser chromium
    ```

3. View reports:
    ```bash
    chmod +x run_allure.sh
    ./run_allure.sh
    ```

4. GitHub Actions handles CI across Chromium, Firefox, and WebKit.
---

## Agentic AI + MCP Control Plane (New)

This repo now includes a minimal **MCP-like gateway** (`mcp/gateway.py`) and agent skeletons:

- `agents/triage_agent.py` (failure classification)
- `agents/self_heal_agent.py` (self-heal proposal)
- `agents/test_designer_agent.py` (coverage suggestions)

The gateway registers tools (e.g., run pytest, generate Allure report) and can **gate privileged tools** behind a security policy.

## Quantum Cryptography Layer (QKD, Protocol-Accurate Simulation)

To showcase quantum-safe safeguarding of sensitive AI pipelines, this repo includes a **BB84 QKD simulation**:

- `security/qkd/bb84.py` (BB84 simulation + sifting + QBER)
- `security/qkd/channel.py` (clean vs intercept-resend sessions)
- `security/qkd/policy.py` (tool gating based on session validity)

### Real-time proof (CI artifacts)
Run the MITM detection experiment:

```bash
python -m experiments.qkd_mitm.run
```

It produces:

- `reports/qkd/qkd_mitm_artifact.json`

CI workflow:
- `.github/workflows/qkd-security-gate.yml`

## Docs for both hiring managers and academics
- `docs/ARCHITECTURE.md`
- `docs/SECURITY.md`
- `docs/EXPERIMENTS.md`
- `docs/REPRODUCIBILITY.md`


### QKD-gated PR demo
Run the workflow **Secure Self-Heal (QKD-gated PR)** with `enable_pr=true` to open a PR using a privileged tool that is gated by a valid QKD session.


### Secure self-heal (real locator) PR demo
Run the workflow **Secure Self-Heal (QKD-gated PR, real locator)** with `enable_pr=true`. It forces a controlled locator break, records the fallback usage, generates a patch that promotes the working fallback selector to the primary locator, and opens a PR using a QKD-gated privileged tool.


### Self-heal confidence evidence
Each self-heal run produces `reports/self_heal/self_heal_summary.md` (human-readable) and `.json` (machine-readable) with simple confidence scoring based on repeated fallback successes.


### Self-heal learning curve experiment
Each run produces `reports/self_heal/self_heal_learning_curve.png`, plotting Bayesian posterior confidence of healed locators over time.


### Evidence Trend (GitHub Pages)
After running the secure self-heal workflow, publish the evidence trend to `gh-pages` (see workflow **Publish Evidence Pages (gh-pages)**). The site reads `learning_curve.json` and renders an evidence-score chart.

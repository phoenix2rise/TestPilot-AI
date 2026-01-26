# TestPilot-AI

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

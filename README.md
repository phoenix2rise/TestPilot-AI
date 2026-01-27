# TestPilot-AI – Secure Self-Healing Test Automation with QKD

This repository demonstrates an **agentic AI-driven self-healing test automation system** protected by **Quantum Key Distribution (QKD)** and governed by an evidence-based safety ladder.

It is designed to speak to **both hiring managers and academics**:

* Engineers see a practical CI/CD pipeline that repairs brittle UI tests.
* Researchers see a reproducible experiment with Bayesian evidence, learning curves, and cryptographic gating.

---

## 🚀 Key Concepts

### Agentic Self-Heal

The system intentionally breaks a UI locator, observes fallback selector behavior, and decides whether to:

* **Promote a new primary locator**, or
* **Expand fallback lists**, or
* **Do nothing (NO_OP)** if already healed.

### Evidence-Based Decision

Decisions are made using:

* `locator_events.jsonl`
* Bayesian confidence thresholds
* Credible intervals

Only statistically justified fixes produce patches.

### Quantum Key Distribution (QKD)

Before any automated Pull Request is created:

* A BB84 QKD session is established
* QBER and fingerprint are validated
* PR creation is cryptographically gated

This demonstrates how **future quantum-safe pipelines** can protect AI-driven code changes.

---

## 🧠 Secure Self-Heal Workflow (High Level)

1. Intentionally break a UI locator (`BREAK_LOCATOR=true`)
2. Run Playwright UI test
3. Capture fallback selector usage
4. Summarize evidence (Bayesian)
5. Decide mode: PROMOTE_PRIMARY or EXPAND_FALLBACKS
6. Generate a patch (or NO_OP)
7. Validate patch:

   * `git apply --check`
   * Python syntax guard (`py_compile`)
8. Run cross-browser matrix (Chromium, Firefox, WebKit)
9. Establish QKD session
10. Open Pull Request:

    * Normal PR if all browsers pass
    * Draft PR if any browser fails

NO_OP runs skip PR creation and learning-curve recording.

---

## 🔐 Safety Ladder

* Evidence gate (Bayesian thresholds)
* Syntax guard (AST compile)
* Cross-browser gate
* Quantum cryptographic gate (QKD)
* Human-in-the-loop PR review

This prevents unsafe autonomous code modification.

---

## 🧪 Learning Curve (Research Angle)

Only successful interventions contribute to the learning curve.

NO_OP runs are excluded to avoid bias:

> "Only statistically justified self-heal interventions are recorded as learning events."

Artifacts are stored as:

* `learning_curve_point.json`
* gh-pages visualization

---

## ▶️ How to Run

### Prerequisites

1. Create a GitHub Personal Access Token (classic) with `repo` scope
2. Add it as a secret:

```
TP_AI_PAT
```

### Run Workflow

1. Go to **Actions → Secure Self-Heal**
2. Click **Run workflow**
3. Set:

```
enable_pr = true
```

---

## 📦 Outputs

Artifacts produced by the workflow:

* **Evidence**

  * `reports/self_heal/locator_events.jsonl`
  * `self_heal_summary.md`
  * `self_heal_decision.json`

* **Patch**

  * `selected_self_heal.patch`

* **Cross-browser artifacts**

  * Playwright traces (`trace_<browser>.zip`)
  * Videos
  * Screenshots

* **QKD proof**

  * `reports/qkd/qkd_mitm_artifact.json`

---

flowchart TD
  A[workflow_dispatch enable_pr] --> B[Clean workspace]
  B --> C[Run test with BREAK_LOCATOR=true]
  C --> D[Collect locator_events.jsonl]
  D --> E[Summarize evidence]
  E --> F[Decide mode: PROMOTE_PRIMARY or EXPAND_FALLBACKS]
  F --> G{Patch produced?}

  G -- No --> H["Stop: already healed<br/>(no PR, no learning-curve)"]
  G -- Yes --> I[git apply --check]
  I --> J[Python syntax guard: py_compile]
  J --> K[Cross-browser matrix: chromium | firefox | webkit]
  K --> L{All green?}

  L -- Yes --> M[QKD session establish]
  L -- No --> N[QKD session establish]

  M --> O[Open PR (normal)]
  N --> P[Open PR (draft)]

  O --> Q[Human review + merge]
  P --> Q
  Q --> R[System improves over time]
```

---

## 👨‍💻 For Hiring Managers

This project demonstrates:

* Advanced Playwright + Pytest automation
* GitHub Actions CI/CD orchestration
* Agentic AI self-healing
* Secure automation (QKD-gated PRs)
* Cross-browser reliability
* Production-grade safety controls

It shows not just test automation, but **autonomous system governance**.

---

## 🎓 For Academics & Researchers

This repository provides:

* A reproducible experimental pipeline
* Bayesian decision-making
* Learning-curve artifacts
* Cryptographic gating of AI actions
* Separation of NO_OP vs intervention events

It can be used as a reference architecture for:

> *Quantum-secured autonomous software engineering systems.*

---

## 📜 License

MIT License

---

## ✨ Vision

TestPilot-AI explores a future where:

> AI agents repair software safely, verifiably, and cryptographically.

From flaky UI tests to quantum-secured DevOps.

---

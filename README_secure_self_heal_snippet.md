## Secure Self-Heal (QKD-gated)

This repository includes a secure, evidence-driven self-healing test automation workflow.

### What it does
1. Intentionally breaks a UI locator (`BREAK_LOCATOR=true`)
2. Captures self-heal evidence (fallback selector used)
3. Summarizes evidence and decides an action (Bayesian confidence)
4. Generates a patch (or produces a no-op if already healed)
5. Validates patch structure and Python syntax
6. Runs cross-browser checks (Chromium, Firefox, WebKit)
7. If authorized by QKD, opens a Pull Request:
   - normal PR if all browsers pass
   - draft PR if any browser fails

### How to run
1. Add a repo secret `TP_AI_PAT` (classic PAT with `repo` scope)
2. Go to **Actions → Secure Self-Heal**
3. Click **Run workflow**
4. Set `enable_pr=true`

### Outputs
- Evidence artifact: `self-heal-evidence`
- Patch artifact: `selected-self-heal-patch`
- Cross-browser artifacts per browser:
  - traces (`trace_<browser>.zip`), videos, screenshots

### No-op behavior
If no patch is produced (system already healed), the workflow skips:
- cross-browser matrix
- PR creation
- learning-curve recording

```mermaid
flowchart TD
  A[workflow_dispatch enable_pr] --> B[Clean workspace]
  B --> C[Run test with BREAK_LOCATOR=true]
  C --> D[Collect locator_events.jsonl]
  D --> E[Summarize evidence]
  E --> F[Decide mode PROMOTE_PRIMARY or EXPAND_FALLBACKS]
  F --> G{Patch produced?}

  G -- No --> H[Stop: already healed\n(no PR, no learning-curve)]
  G -- Yes --> I[git apply --check]
  I --> J[Python syntax guard py_compile]
  J --> K[Cross-browser matrix\nchromium firefox webkit]
  K --> L{All green?}

  L -- Yes --> M[QKD session establish]
  L -- No --> N[QKD session establish]

  M --> O[Open PR (normal)]
  N --> P[Open PR (draft)]

  O --> Q[Human review + merge]
  P --> Q
  Q --> R[System improves over time]
```

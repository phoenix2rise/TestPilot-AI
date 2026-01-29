# TestPilot-AI Architecture

## Goal
Transform TestPilot-AI from a test framework into a real-time, agentic test automation platform with a secured control plane.

## Planes
- **Execution plane**: your existing pytest/page objects/visual baselines.
- **Control plane**: an MCP-like gateway that exposes tools to agents.
- **Security plane**: QKD-derived session gating for privileged tools.

## Agents
- Triage Agent: classifies failures deterministically first, then LLM-augmented later.
- Self-Heal Agent: proposes locator fixes and requests privileged actions via the gateway.
- Test Designer Agent: suggests coverage based on diffs/stories.

## Agent Pipeline
`scripts/run_agent_pipeline.py` runs a deterministic pipeline that executes tests, triages failures,
summarizes self-heal evidence, and produces test design suggestions for changed files.

## Control Plane (MCP-like Gateway)
`mcp/gateway.py` registers tools (run tests, generate reports, privileged commit) and enforces policies.

## Trust boundaries
- Agents do not directly execute privileged actions.
- Privileged tools require a valid QKD session (accepted + not expired).
- Privileged tools require evidence confidence that meets the minimum threshold.

## Artifacts
- Allure results/report
- Visual diffs (baseline/actual)
- QKD experiment artifact JSON

## Generalized self-heal
Locator self-heal events are recorded with page-object class + source file path, enabling multi-file patch generation from runtime evidence.

## Healing actions
Supported self-heal actions via `utils/locator_healer.py`:
- `fill_with_fallback` (type into input)
- `click_with_fallback` (click)
- `expect_visible_with_fallback` (assert visibility)
Each records evidence to `reports/self_heal/locator_events.jsonl` when a fallback succeeds.

## Evidence confidence
Self-heal evidence is summarized (counts + heuristic confidence) in `reports/self_heal/self_heal_summary.*` and included in QKD-gated PR bodies.

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

## Control Plane (MCP-like Gateway)
`mcp/gateway.py` registers tools (run tests, generate reports, privileged commit) and enforces policies.

## Trust boundaries
- Agents do not directly execute privileged actions.
- Privileged tools require a valid QKD session (accepted + not expired).

## Artifacts
- Allure results/report
- Visual diffs (baseline/actual)
- QKD experiment artifact JSON

---
description: Run full unified audit for DIYU Agent (Section 12.6). Executes guard scripts, skill audits, agent/hook/workflow tests, and governance checks.
allowed-tools: ["Bash", "Read", "Grep", "Glob"]
---

Run the full unified audit for DIYU Agent (Section 12.6).

Execute `make full-audit` which runs:
1. Guard scripts (layer-deps, port-compat, RLS)
2. Skill audits (systematic-review, cross-audit, fix-verify)
3. Agent permission tests
4. Hook behavior tests
5. Workflow completeness tests
6. Governance consistency checks
7. Report aggregation to evidence/full-audit-*.json

Review the output and report any failures with recommended remediation.

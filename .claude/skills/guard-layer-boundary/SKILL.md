---
name: guard-layer-boundary
description: >-
  Guard skill that enforces 6-layer hexagonal architecture dependency rules.
  Use after modifying import statements in src/, adding new modules, or
  before merging PRs that touch Brain, Knowledge, Skill, Tool, Gateway,
  or Infrastructure layers.
---

# Guard: Layer Boundary

Validates that layer imports respect the hexagonal architecture constraint:
layers may only depend downward or on Port interfaces.

## Input

- **Scope**: `src/` directory (all `.py` files)
- **Trigger**: Any change to `src/**/*.py`

## Execution

```bash
bash scripts/check_layer_deps.sh --json
```

## Output

JSON with `status` (pass/fail), `violations` array, and `count`.

```json
{"status": "pass", "violations": [], "count": 0}
```

## Failure Condition

Exit code 1 when any layer imports a forbidden module:

| Layer | Forbidden Imports |
|-------|-------------------|
| brain | infra, gateway, tool |
| knowledge | infra, gateway, brain |
| skill | infra, gateway |
| gateway | brain, knowledge, skill |
| tool | infra, brain, knowledge |

## Remediation

1. Replace direct cross-layer import with Port interface import from `src/ports/`
2. If no suitable Port exists, propose a new Port interface (requires ADR)
3. Re-run `bash scripts/check_layer_deps.sh --json` to confirm fix

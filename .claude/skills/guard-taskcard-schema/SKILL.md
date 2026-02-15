---
name: guard-taskcard-schema
description: >-
  Guard skill that validates task card schema compliance against
  task-card-schema-v1.0.md rules. Use after editing task card files,
  before phase gate reviews, or when normalizing card fields.
---

# Guard: Task Card Schema

Validates all task cards against the frozen schema (Tier-A: 10 fields,
Tier-B: 8 fields) with BLOCK/WARNING/INFO severity levels.

## Input

- **Scope**: `docs/task-cards/**/*.md`
- **Authority**: `docs/governance/task-card-schema-v1.0.md`
- **Trigger**: Any change to `docs/task-cards/**/*.md`

## Execution

```bash
uv run python scripts/check_task_schema.py --mode full --json
```

## Output

JSON with `mode`, `total_cards`, `violations` array, and `summary` (block/warning/info counts).

```json
{"mode": "full", "total_cards": 42, "violations": [], "summary": {"block": 0, "warning": 3, "info": 1}}
```

## Failure Condition

Exit code 1 when any BLOCK-level violation exists:
- Missing required fields (per Tier)
- Missing risk field (Tier-A)
- Invalid or missing matrix reference
- Non-executable acceptance command without tag
- Empty Out of Scope field
- Incomplete exception declaration

## Remediation

1. Run with `--verbose` to see all violations with context
2. Use `--filter-file <path>` to validate a specific card
3. Reference `docs/governance/task-card-schema-v1.0.md` for field requirements
4. Re-run `uv run python scripts/check_task_schema.py --mode full --json` to confirm fix

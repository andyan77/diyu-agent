---
name: guard-port-compat
description: >-
  Guard skill that detects breaking changes in Day-1 Port interfaces.
  Use after modifying any file in src/ports/, before merging PRs that
  touch Port contracts, or when reviewing interface evolution.
---

# Guard: Port Compatibility

Detects breaking changes (method removal, rename, type changes) in the
6 Day-1 Port interfaces.

## Input

- **Scope**: `src/ports/` directory
- **Monitored Ports**: memory_core_port.py, knowledge_port.py, llm_call_port.py, skill_registry.py, org_context.py, storage_port.py
- **Trigger**: Any change to `src/ports/*.py`

## Execution

```bash
bash scripts/check_port_compat.sh --json
```

## Output

JSON with `status` (pass/fail), `breaking_changes` array, and `count`.

```json
{"status": "pass", "breaking_changes": [], "count": 0}
```

## Failure Condition

Exit code 1 when any of these are detected:
- Method removed or renamed
- Return type changed
- Required parameter added without default
- ABC/Protocol method removed
- Port file deleted

## Remediation

1. Use Expand-Contract migration pattern (add new method, deprecate old, remove later)
2. See `docs/architecture/00-*.md` Section 12.5 for migration protocol
3. Re-run `bash scripts/check_port_compat.sh --json` to confirm fix

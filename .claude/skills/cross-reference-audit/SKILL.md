---
name: cross-reference-audit
description: >-
  Cross-reference audit verifying documentation claims against actual codebase
  state. Use after modifying governance documents, renaming or moving files
  referenced in docs, changing CI workflows or Makefile targets, or as part
  of a full audit cycle. Invokes /cross-reference-audit command.
---

# Skill: Cross-Reference Audit

> Version: 1.0
> Command: `/cross-reference-audit`
> Output: `evidence/cross-audit-report.json`
> Schema: `scripts/schemas/cross-audit-report.schema.json`

This skill verifies that documentation claims match the actual codebase state, catching stale references, phantom paths, and configuration drift.

---

## When to Use

- After modifying governance documents or execution plans
- After renaming/moving files referenced in docs
- After changing CI workflows or Makefile targets
- As part of a full audit cycle (after `/systematic-review`)

## Workflow

1. Invoke `/cross-reference-audit` command
2. The command extracts verifiable claims from docs
3. For each claim, checks the actual file/script/config
4. Records match/mismatch for every pair
5. Writes `evidence/cross-audit-report.json`
6. Validates output against schema

## Relationship to Other Commands

- **Complemented by**: `/systematic-review` (finds code issues; this finds doc-code drift)
- **Independent of**: `/adversarial-fix-verify` (which verifies fix closure, not doc accuracy)
- **Independent of**: `/gate-review` (which handles phase gate checks)

## Execution

```
/cross-reference-audit
```

Or via script:

```bash
bash scripts/run_cross_audit.sh
```

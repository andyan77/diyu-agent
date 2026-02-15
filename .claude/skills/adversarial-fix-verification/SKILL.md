---
name: adversarial-fix-verification
description: >-
  Adversarial verification that audit fixes are genuine, not superficial. Use
  after implementing fixes for audit findings, before claiming audit closure,
  or when resuming a multi-batch fix verification cycle. Invokes
  /adversarial-fix-verify command.
---

# Skill: Adversarial Fix Verification

> Version: 1.0
> Command: `/adversarial-fix-verify`
> Output: `evidence/fix-verification-report.json`
> Schema: `scripts/schemas/fix-verification-report.schema.json`

This skill verifies that each audit finding has been genuinely fixed using adversarial evidence -- commands that would fail if the fix is superficial.

---

## When to Use

- After implementing fixes for audit findings
- Before claiming audit closure
- When resuming a multi-batch fix verification cycle

## Adversarial Patterns

| Pattern | Example |
|---------|---------|
| Placeholder detection | lint script starts with `echo` |
| Error swallowing | script uses `|| true` to mask failures |
| Safety net dependency | `--passWithNoTests` still present after real tests added |
| Producer-consumer gap | Router gate not consumed in CI |
| Phantom reference | CI references gate that router does not produce |

## Workflow

1. Invoke `/adversarial-fix-verify` command
2. Loads findings from `evidence/review-report.json`
3. For each finding (max 5 per batch):
   - Defines pass/fail criterion
   - Identifies file scope
   - Runs adversarial command
   - Records evidence and verdict (CLOSED/OPEN/PRE_RESOLVED)
4. Writes `evidence/fix-verification-report.json`
5. Updates `evidence/fix-progress.md` with batch results
6. Validates via `scripts/validate_audit_artifacts.py`

## Relationship to Other Commands

- **Requires**: `/systematic-review` output (`evidence/review-report.json`)
- **Complemented by**: `/cross-reference-audit` (separate concern: doc accuracy)
- **Independent of**: `/gate-review` (phase gates, not audit findings)

## Execution

```
/adversarial-fix-verify
```

Or via script:

```bash
bash scripts/run_fix_verify.sh
```

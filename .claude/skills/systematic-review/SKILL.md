---
name: systematic-review
description: >-
  Systematic codebase review producing structured JSON evidence. Use when
  starting an audit cycle, after significant architectural changes, before
  phase gate reviews, or when preparing for external review. Invokes
  /systematic-review command.
---

# Skill: Systematic Review

> Version: 1.0
> Command: `/systematic-review`
> Output: `evidence/review-report.json`
> Schema: `scripts/schemas/review-report.schema.json`

This skill performs a structured review of the DIYU Agent codebase, producing machine-verifiable JSON evidence.

---

## When to Use

- Starting a new audit cycle
- After significant architectural changes
- Before phase gate reviews
- When preparing for external review

## Workflow

1. Invoke `/systematic-review` command
2. The command scans configured scope directories
3. Runs automated guard scripts + manual inspection
4. Classifies findings by severity (CRITICAL/HIGH/MEDIUM/SUGGESTION/NOTE)
5. Writes `evidence/review-report.json`
6. Validates output against schema

## Relationship to Other Commands

- **Input to**: `/adversarial-fix-verify` (consumes the findings list)
- **Complemented by**: `/cross-reference-audit` (verifies doc-to-code alignment)
- **Independent of**: `/gate-review` (which handles phase gate checks, not audit findings)

## Execution

```
/systematic-review
```

Or via script:

```bash
bash scripts/run_systematic_review.sh
```

# Audit Execution Protocol v1.0

> Date: 2026-02-15
> Status: Active
> Authority: docs/reviews/opus-skill-hardening-requirements-v1.0.md (R10)

---

## 1. Three-Phase Execution Order (Mandatory)

Audits must execute in this exact sequence:

1. `/systematic-review` -- Produces `evidence/review-report.json`
2. `/cross-reference-audit` -- Produces `evidence/cross-audit-report.json`
3. `/adversarial-fix-verify` -- Produces `evidence/fix-verification-report.json`

Phase 3 requires Phase 1 output as input. Phase 2 is independent but must run before Phase 3 to ensure doc-code alignment is verified.

---

## 2. Completion Claim Policy

### Prohibited phrases

The following phrases are **banned** from audit outputs:

- "all issues resolved"
- "fully complete"
- "100% fixed"
- "no remaining issues"

### Required status

All audit outputs must end with:

```
Status: SUBMITTED FOR REVIEW
```

Final verdict is determined by the human reviewer, not the audit executor.

---

## 3. Batch Execution Rules

### Batch size limit

- Maximum **5 findings per batch** in `/adversarial-fix-verify`.
- Each batch must update `evidence/fix-progress.md`.

### Progress tracking format

```markdown
## Batch N -- YYYY-MM-DD
- Processed: H1, H2, M1, M2, M3
- CLOSED: 4
- OPEN: 1
- Remaining: 13
```

### Cross-session resume

When resuming across sessions:

1. Read `evidence/fix-progress.md` to determine last completed batch
2. Continue from next unprocessed finding
3. Do not re-verify already-CLOSED findings unless explicitly requested

---

## 4. Evidence Artifacts

| Artifact | Path | Schema |
|----------|------|--------|
| Review report | `evidence/review-report.json` | `scripts/schemas/review-report.schema.json` |
| Cross-audit report | `evidence/cross-audit-report.json` | `scripts/schemas/cross-audit-report.schema.json` |
| Fix verification | `evidence/fix-verification-report.json` | `scripts/schemas/fix-verification-report.schema.json` |
| Progress tracker | `evidence/fix-progress.md` | (markdown, no schema) |

---

## 5. Validation

```bash
# Validate all artifacts
make audit-artifacts

# End-to-end: generate + validate
make audit-e2e

# Single artifact
uv run python scripts/validate_audit_artifacts.py --file <path> --schema <schema>
```

---

## 6. Relationship to Existing Commands

| Command | Purpose | Overlap |
|---------|---------|---------|
| `/gate-review` | Phase gate checks (schema, census, scaffold) | None -- different concern |
| `/systematic-review` | Codebase audit findings | Complementary |
| `/cross-reference-audit` | Doc-code alignment | Complementary |
| `/adversarial-fix-verify` | Fix closure verification | Complementary |

`/gate-review` is a governance tool. The three audit commands are quality assurance tools. They do not replace each other.

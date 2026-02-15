---
name: taskcard-governance
description: >-
  Governance workflows for task-card schema normalization, traceability checks,
  acceptance normalization, and gate evidence reporting. Use when normalizing
  task cards, checking L1-L2-L3 traceability links, auditing acceptance
  commands, or generating phase gate evidence reports.
---

# Skill: Task Card Governance

> Version: 1.0
> Scope: `docs/task-cards/**/*.md` + `docs/governance/milestone-matrix*.md`
> Authority: `docs/governance/task-card-schema-v1.0.md` (Frozen)

This skill provides 4 workflows for task card governance. Use the workflow that matches your current need.

---

## Workflows

### W1: Schema Normalization

**Purpose**: Bring task cards into compliance with Schema v1.0.

**Steps**:

1. Read `docs/governance/task-card-schema-v1.0.md` to understand Tier-A (10 fields) vs Tier-B (8 fields) requirements
2. Read `docs/governance/execution-plan-v1.0.md` Section 1.0 for editing norms and per-layer default Out of Scope
3. Run `python3 scripts/check_task_schema.py --mode full --filter-file <target> --json` to get current violations
4. For each BLOCK violation:
   - `required-field (范围外)`: Add `**范围外 (Out of Scope)**` using per-layer defaults from Section 1.0.2
   - `risk-field-required`: Add `**风险**` with 4 categories (依赖/数据/兼容/回滚), referencing the L1 architecture doc
   - `required-field (决策记录)`: Add `**决策记录**` with 决策/理由/来源, referencing ADRs or architecture doc sections
   - `missing_in_scope_label`: Rename `**范围**` to `**范围 (In Scope)**`
5. Re-run validation to confirm BLOCK = 0

**Key constraint**: Tier-A risk/decision content MUST reference L1 architecture docs. No mechanical template filling.

**L1 mapping**: See `docs/governance/execution-plan-v1.0.md` Section 1.0.1 for layer -> architecture doc mapping.

---

### W2: Traceability Link Check

**Purpose**: Verify L1 (architecture) -> L2 (milestone matrix) -> L3 (task cards) bidirectional traceability.

**Steps**:

1. Run `python3 scripts/count_task_cards.py --json` to get card inventory with orphan detection
2. For each task card file, verify:
   - Every `### TASK-*` heading has a `> 矩阵条目:` reference within 20 lines
   - The referenced matrix ID exists in the corresponding `milestone-matrix-*.md`
3. Cross-check: for each matrix entry, verify at least one task card references it
4. Report:
   - Orphan cards (card exists but no matrix entry)
   - Uncovered matrix entries (matrix entry exists but no card)
   - Bidirectional coverage percentage

---

### W3: Acceptance Normalizer

**Purpose**: Ensure all acceptance commands are executable or properly tagged.

**Steps**:

1. Run `python3 scripts/check_task_schema.py --mode full --json` and filter for `acceptance-not-executable` violations
2. For each violation, determine the appropriate action:
   - **Can be command-ized**: Rewrite as executable shell command
   - **Needs external environment**: Add `[ENV-DEP]` tag
   - **Needs browser/E2E**: Add `[E2E]` tag
   - **Cannot be automated**: Add `[MANUAL-VERIFY]` tag with alternative verification description
3. Re-run validation to confirm no `acceptance-not-executable` BLOCKs remain

**Tag reference**: See `docs/governance/task-card-schema-v1.0.md` Section 2.5 for tag definitions.

---

### W4: Evidence and Gate Report

**Purpose**: Generate Phase Gate review report with evidence assessment.

**Steps**:

1. Run `/gate-review` command to get the full Gate Review Report
2. Assess evidence field coverage:
   - Count cards with `TBD` / `CI-link-pending` / empty evidence fields
   - Calculate evidence coverage percentage
3. Check `docs/governance/execution-plan-v1.0.md` Section 10 for controlled-pending items
4. Produce a combined report:
   - Gate Review results (from /gate-review)
   - Evidence coverage metrics
   - Controlled-pending status
   - Recommended actions for unresolved items

---

## Progressive Disclosure

Each workflow loads ONLY the references needed for its step:

| Workflow | Required Context | Reference |
|----------|-----------------|-----------|
| W1 | Schema rules, Tier definitions | `references/schema-rules.md` |
| W2 | Matrix IDs, card inventory | `scripts/count_task_cards.py --json` |
| W3 | Acceptance tag definitions | `references/schema-rules.md` (Tags section) |
| W4 | All guard script outputs | Runs all guards internally |

Do NOT preload all references at session start. Load per-step only.

## Dedicated Roles (No Mixing)

| Workflow | Role | Responsibility |
|----------|------|---------------|
| W1 | Schema Normalizer | Fix field compliance only |
| W2 | Traceability Auditor | Verify L1-L2-L3 links only |
| W3 | Acceptance Engineer | Normalize commands only |
| W4 | Gate Reviewer | Aggregate evidence only |

**Rule**: Each role performs ONLY its designated function. W1 must not fix
acceptance commands (W3's job). W2 must not add missing fields (W1's job).

## Executable Scripts

Run individual workflows or the full pipeline:

```bash
# Individual
bash .claude/skills/taskcard-governance/scripts/run_w1_schema_normalization.sh
bash .claude/skills/taskcard-governance/scripts/run_w2_traceability_link.sh
bash .claude/skills/taskcard-governance/scripts/run_w3_acceptance_normalizer.sh
bash .claude/skills/taskcard-governance/scripts/run_w4_evidence_gate.sh

# Full pipeline (stops on first failure)
bash .claude/skills/taskcard-governance/scripts/run_all.sh
```

Each script produces artifacts in `evidence/skills/taskcard-governance/<session-id>/W*/`:
- `input.json` - recorded input parameters
- `output.json` - execution results
- `next-step.md` - recommended next action
- `failure.md` - present only on failure

## Usage

Invoke this skill, then specify which workflow to run:

- "Run W1 on `docs/task-cards/01-*/brain.md`" -- normalize a specific file
- "Run W2" -- full traceability check
- "Run W3" -- audit all acceptance commands
- "Run W4" -- comprehensive gate review with evidence

Each workflow is self-contained and can be run independently.

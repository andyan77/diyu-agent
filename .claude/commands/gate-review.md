---
description: Run comprehensive DIYU Agent Phase Gate review (schema, census, phase gate, controlled-pending, scaffold integrity). Supports --phase N for targeted verification.
allowed-tools: ["Bash", "Read"]
---

Run a comprehensive Phase Gate Review for the DIYU Agent project. Execute ALL of the following steps sequentially, capturing the raw output of each command.

If the user specifies `--phase N` (e.g., `/gate-review --phase 1`), use `--phase N` instead of `--current` in the verify_phase.py command below. Otherwise default to `--current`.

## Step 1: Schema Validation

```bash
python3 scripts/check_task_schema.py --mode full --json
```

Record: total_cards, block, warning, info counts.

## Step 2: Card Census

```bash
python3 scripts/count_task_cards.py --json
```

Record: total (top-level), tier_a from summary.by_tier.A, tier_b from summary.by_tier.B, orphan from summary.gaps.orphan_count.

## Step 3: Phase Gate Verification

```bash
# Use --phase N if specified by user, otherwise --current
python3 scripts/verify_phase.py --current --json
# Example: python3 scripts/verify_phase.py --phase 1 --json
```

Record: go_no_go, hard_pass/hard_total, blocking_items.

## Step 4: Controlled-Pending Audit

Read `docs/governance/execution-plan-v1.0.md` Section 10 (Controlled-Pending). For each item (A-D), check:
- Is the deadline Phase gate past current phase?
- If past: flag as OVERDUE

## Step 5: Scaffold Integrity

```bash
python3 scripts/scaffold_phase0.py --check --json
```

Record: total, exists, missing counts.

## Output: Gate Review Report

Produce a structured report in this exact format:

```
## Gate Review Report -- {date}

### 1. Schema Compliance
- Total: {n} cards | BLOCK: {n} | WARNING: {n} | INFO: {n}
- Verdict: {PASS if BLOCK=0, else FAIL}
- [If FAIL: list all BLOCK violations]

### 2. Card Census
- Total: {n} | Tier-A: {n} | Tier-B: {n} | Orphan: {n}
- Verdict: {PASS if orphan=0, else FAIL}

### 3. Phase Gate
- Current Phase: {n} | Go/No-Go: {verdict}
- Hard: {pass}/{total} | Soft: {pass}/{total}
- Verdict: {PASS if GO, else FAIL}
- [If FAIL: list blocking items]

### 4. Controlled-Pending
- Item A: {status} (deadline: Phase 2 gate)
- Item B: {status} (deadline: Phase 2 gate)
- Item C: {status} (deadline: Phase 3 gate)
- Item D: {status} (deadline: Phase 3 gate)
- Verdict: {PASS if no overdue, else FAIL}

### 5. Scaffold Integrity
- Total: {n} | Exists: {n} | Missing: {n}
- Verdict: {PASS if missing=0, else FAIL}

---

### OVERALL: {PASS if all sections pass, else FAIL}
Blockers: {list or "None"}
```

Important:
- Run ALL commands from the project root directory
- Do NOT skip any step
- If a command fails, report the error in the corresponding section
- Show both raw JSON output and the formatted report

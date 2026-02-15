---
description: Adversarial fix verification -- verifies each finding from a review report is genuinely closed with executable evidence. Produces evidence/fix-verification-report.json conforming to scripts/schemas/fix-verification-report.schema.json.
allowed-tools: ["Bash", "Read", "Grep", "Glob"]
---

Run adversarial fix verification against findings from a prior systematic review. This command verifies each finding with executable evidence, not just visual inspection.

**Output path**: `evidence/fix-verification-report.json`
**Schema**: `scripts/schemas/fix-verification-report.schema.json`

## Batch Rules

- Process at most **5 findings per batch**.
- After each batch, update `evidence/fix-progress.md` with batch results.
- If more findings remain, state how many are pending and stop. Resume with next invocation.

## Execution Steps

### Step 1: Load source review

Read `evidence/review-report.json` to get the findings list. If the file does not exist, fail immediately:

```bash
test -f evidence/review-report.json || { echo "ERROR: No review report found. Run /systematic-review first."; exit 1; }
```

### Step 2: For each finding (max 5 per batch)

For finding with `id`, `severity`, `files`:

#### 2a. Define criterion

Write a precise pass/fail criterion. Example: "lint script must not start with 'echo'" or "file X must contain pattern Y".

#### 2b. Define scope

List the exact files that must be checked.

#### 2c. Execute adversarial check

Run a concrete command that would FAIL if the fix is not genuine:

```bash
# Example: verify lint is real, not a stub
grep -q "^echo" frontend/packages/shared/package.json && echo "FAIL: still echo stub" || echo "PASS"
```

```bash
# Example: verify a file exists
test -f <expected_path> && echo "PASS" || echo "FAIL: file missing"
```

```bash
# Example: verify test passes
uv run pytest tests/unit/scripts/test_specific.py -v --tb=short 2>&1
```

#### 2d. Record evidence

Capture the exact command and a summary of its output (not the full dump).

#### 2e. Assign verdict

- `CLOSED`: Fix verified by adversarial evidence
- `OPEN`: Fix not verified or verification failed
- `PRE_RESOLVED`: Finding was already correct before any fix

### Step 3: Write report

```bash
mkdir -p evidence
```

Write `evidence/fix-verification-report.json` conforming to the schema.

Validate:

```bash
uv run python scripts/validate_audit_artifacts.py --file evidence/fix-verification-report.json --schema scripts/schemas/fix-verification-report.schema.json
```

### Step 4: Update progress tracker

Append batch results to `evidence/fix-progress.md`:

```markdown
## Batch N -- {date}
- Processed: {ids}
- CLOSED: {count}
- OPEN: {count}
- Remaining: {count}
```

### Step 5: Cross-validate counts

```bash
uv run python scripts/validate_audit_artifacts.py
```

This checks: review findings count == fix-verification findings count, and every CLOSED finding has evidence.

Do NOT claim "all complete". Output `Status: SUBMITTED FOR REVIEW`.

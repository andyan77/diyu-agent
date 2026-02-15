---
description: Run a systematic review of the DIYU Agent codebase. Produces evidence/review-report.json conforming to scripts/schemas/review-report.schema.json.
allowed-tools: ["Bash", "Read", "Grep", "Glob"]
---

Run a systematic review of the DIYU Agent project. This command produces a structured JSON report at `evidence/review-report.json`.

**Output path**: `evidence/review-report.json`
**Schema**: `scripts/schemas/review-report.schema.json`

## Execution Steps

### Step 1: Define review scope

```bash
mkdir -p evidence
```

Determine the set of files to review. Default scope:
- `src/` (backend source)
- `scripts/` (guard scripts, validators)
- `.claude/` (commands, skills, agents)
- `docs/governance/` (governance docs)
- `frontend/` (frontend packages -- package.json, configs)

Count total files:

```bash
find src/ scripts/ .claude/ docs/governance/ frontend/ -type f | wc -l
```

### Step 2: Run automated checks

Execute all existing guard scripts and capture results:

```bash
uv run ruff check src/ tests/ scripts/ 2>&1
bash scripts/check_layer_deps.sh --json 2>&1
bash scripts/check_port_compat.sh 2>&1
uv run python scripts/check_task_schema.py --mode full --json 2>&1
```

### Step 3: Manual review pass

For each scope directory, read key files and identify:
- Layer boundary violations (src/ cross-imports)
- Missing or stale documentation references
- Security issues (secrets, injection, RLS bypass)
- Configuration drift (CI vs Makefile vs scripts)
- Governance gaps (orphan task cards, missing traceability)

### Step 4: Classify findings

Assign each finding:
- `id`: Sequential `C1`, `H1`, `M1`, `S1`, `N1` etc.
- `severity`: CRITICAL / HIGH / MEDIUM / SUGGESTION / NOTE
- `category`: e.g. "layer-boundary", "security", "governance", "config-drift"
- `description`: What is wrong and why it matters
- `files`: List of affected file paths

### Step 5: Write report

Write `evidence/review-report.json` conforming to the schema. Validate:

```bash
uv run python scripts/validate_audit_artifacts.py --file evidence/review-report.json --schema scripts/schemas/review-report.schema.json
```

### Step 6: Summary

Print a table of findings by severity. Do NOT claim "all issues resolved" -- output `Status: SUBMITTED FOR REVIEW`.

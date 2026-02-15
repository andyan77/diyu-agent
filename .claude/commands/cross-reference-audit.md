---
description: Cross-reference audit verifying documentation claims match actual file state. Produces evidence/cross-audit-report.json conforming to scripts/schemas/cross-audit-report.schema.json.
allowed-tools: ["Bash", "Read", "Grep", "Glob"]
---

Run a cross-reference audit of the DIYU Agent project. This command verifies that documentation claims match the actual codebase state.

**Output path**: `evidence/cross-audit-report.json`
**Schema**: `scripts/schemas/cross-audit-report.schema.json`

## Execution Steps

### Step 1: Prepare output directory

```bash
mkdir -p evidence
```

### Step 2: Identify claim-pairs to verify

Read these documents and extract verifiable claims:

1. `docs/governance/execution-plan-v1.0.md` -- references to scripts, agents, file paths
2. `docs/governance/milestone-matrix.md` -- phase statuses, task card references
3. `CLAUDE.md` -- command references, file layout claims
4. `delivery/manifest.yaml` -- declared deliverables
5. `.claude/skills/*/SKILL.md` -- command references, workflow steps
6. `.claude/commands/*.md` -- tool references, script paths

For each claim, create a pair:
- `source`: Document making the claim
- `target`: File/path/command being claimed
- `claim`: What the document says
- `actual`: What actually exists

### Step 3: Verify each pair

For each claim-pair:

1. Check if referenced files exist:
   ```bash
   test -f <path> && echo "EXISTS" || echo "MISSING"
   ```

2. Check if referenced commands/scripts are executable:
   ```bash
   test -x <script> && echo "EXECUTABLE" || echo "NOT_EXECUTABLE"
   ```

3. Check if content claims match (e.g., "script contains X"):
   ```bash
   grep -q "pattern" <file> && echo "MATCH" || echo "MISMATCH"
   ```

### Step 4: Write report

Write `evidence/cross-audit-report.json` conforming to the schema. Include all pairs, separating mismatches.

Validate:

```bash
uv run python scripts/validate_audit_artifacts.py --file evidence/cross-audit-report.json --schema scripts/schemas/cross-audit-report.schema.json
```

### Step 5: Summary

Print mismatch count and list. Do NOT claim "all verified" -- output `Status: SUBMITTED FOR REVIEW`.

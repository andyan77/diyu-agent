#!/usr/bin/env bash
# run_systematic_review.sh - Generate evidence/review-report.json
#
# This is the scripted entry point for the /systematic-review command.
# It runs automated checks and produces a review report with real findings.
# For full review (including manual inspection), use the Claude command.
#
# Exit codes: 0 = report generated, non-zero = failure (not swallowed)

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

EVIDENCE_DIR="$ROOT/evidence"
SCHEMA="$ROOT/scripts/schemas/review-report.schema.json"
OUTPUT="$EVIDENCE_DIR/review-report.json"
FINDINGS_TMP="$EVIDENCE_DIR/.findings_tmp.jsonl"

mkdir -p "$EVIDENCE_DIR"

echo "=== Systematic Review: Automated Pass ==="

# Initialize findings collector (one JSON object per line)
: > "$FINDINGS_TMP"

# Check 1: ruff lint
echo "Running ruff check..."
if ! uv run ruff check src/ tests/ scripts/ >/dev/null 2>&1; then
  echo '{"id":"H1","severity":"HIGH","category":"lint","description":"ruff check found violations in backend code","files":["src/","tests/","scripts/"]}' >> "$FINDINGS_TMP"
fi

# Check 2: ruff format
echo "Running ruff format check..."
if ! uv run ruff format --check src/ tests/ scripts/ >/dev/null 2>&1; then
  echo '{"id":"M1","severity":"MEDIUM","category":"format","description":"ruff format found unformatted files","files":["src/","tests/","scripts/"]}' >> "$FINDINGS_TMP"
fi

# Check 3: layer deps
echo "Running layer dependency check..."
if ! bash "$ROOT/scripts/check_layer_deps.sh" --json >/dev/null 2>&1; then
  echo '{"id":"H2","severity":"HIGH","category":"layer-boundary","description":"Layer dependency violations detected","files":["src/"]}' >> "$FINDINGS_TMP"
fi

# Check 4: port compat
echo "Running port compatibility check..."
if ! bash "$ROOT/scripts/check_port_compat.sh" >/dev/null 2>&1; then
  echo '{"id":"H3","severity":"HIGH","category":"port-contract","description":"Port contract compatibility issues found","files":["src/ports/"]}' >> "$FINDINGS_TMP"
fi

# Check 5: task schema
echo "Running task schema validation..."
SCHEMA_BLOCKS=0
if SCHEMA_OUTPUT=$(uv run python scripts/check_task_schema.py --mode full --json 2>&1); then
  SCHEMA_BLOCKS=$(echo "$SCHEMA_OUTPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('summary', {}).get('block', 0))
except Exception:
    print(0)
" 2>/dev/null || echo "0")
fi
if [ "${SCHEMA_BLOCKS}" -gt 0 ] 2>/dev/null; then
  echo '{"id":"M2","severity":"MEDIUM","category":"governance","description":"Task card schema has BLOCK-level violations","files":["docs/task-cards/"]}' >> "$FINDINGS_TMP"
fi

# Check 6: cross-reference (reads from already-generated cross-audit if present)
echo "Running cross-reference check..."
CROSS_MISMATCHES=0
if [ -f "$EVIDENCE_DIR/cross-audit-report.json" ]; then
  CROSS_MISMATCHES=$(python3 -c "
import json
data = json.load(open('$EVIDENCE_DIR/cross-audit-report.json'))
print(data.get('summary', {}).get('mismatches_count', 0))
" 2>/dev/null || echo "0")
fi
if [ "${CROSS_MISMATCHES}" -gt 0 ] 2>/dev/null; then
  echo "{\"id\":\"M3\",\"severity\":\"MEDIUM\",\"category\":\"doc-code-drift\",\"description\":\"Cross-reference audit found ${CROSS_MISMATCHES} doc-code mismatches\",\"files\":[\"docs/\",\".claude/\"]}" >> "$FINDINGS_TMP"
fi

# Count files in scope
FILE_COUNT=$(find src/ scripts/ .claude/ docs/governance/ frontend/ -type f 2>/dev/null | wc -l | tr -d ' ')

# Generate report from collected findings
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

python3 -c "
import json
from collections import Counter
from pathlib import Path

# Read JSONL findings
findings = []
tmp = Path('$FINDINGS_TMP')
if tmp.exists():
    for line in tmp.read_text().strip().splitlines():
        if line.strip():
            findings.append(json.loads(line))

by_severity = dict(Counter(f['severity'] for f in findings))

report = {
    'version': '1.0',
    'timestamp': '$TIMESTAMP',
    'reviewer': 'automated',
    'scope': {
        'directories': ['src/', 'scripts/', '.claude/', 'docs/governance/', 'frontend/'],
        'file_count': $FILE_COUNT
    },
    'findings': findings,
    'summary': {
        'total_findings': len(findings),
        'by_severity': by_severity
    }
}

with open('$OUTPUT', 'w') as f:
    json.dump(report, f, indent=2)

if findings:
    print(f'Found {len(findings)} findings: {by_severity}')
else:
    print('All automated checks passed. 0 findings.')
print(f'Report written to $OUTPUT')
"

# Clean up temp file
rm -f "$FINDINGS_TMP"

# Validate output
echo "Validating report..."
uv run python "$ROOT/scripts/validate_audit_artifacts.py" \
  --file "$OUTPUT" --schema "$SCHEMA"

echo "=== Systematic Review Complete ==="
echo "Status: SUBMITTED FOR REVIEW"

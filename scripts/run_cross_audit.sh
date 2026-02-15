#!/usr/bin/env bash
# run_cross_audit.sh - Generate evidence/cross-audit-report.json
#
# This is the scripted entry point for the /cross-reference-audit command.
# It checks documentation claims against actual file state.
#
# Exit codes: 0 = report generated, non-zero = failure (not swallowed)

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
EVIDENCE_DIR="$ROOT/evidence"
SCHEMA="$ROOT/scripts/schemas/cross-audit-report.schema.json"
OUTPUT="$EVIDENCE_DIR/cross-audit-report.json"

mkdir -p "$EVIDENCE_DIR"

echo "=== Cross-Reference Audit ==="

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Run cross-reference checks via python for structured output
python3 -c "
import json, os, re
from pathlib import Path

root = Path('$ROOT')
pairs = []
mismatches = []

# Check 1: CLAUDE.md command references
claude_md = root / 'CLAUDE.md'
if claude_md.exists():
    text = claude_md.read_text()
    # Check make targets referenced in CLAUDE.md
    for target in ['make bootstrap', 'make doctor', 'make lint', 'make test', 'make test-smoke']:
        cmd = target.split()[-1]
        claim = f'CLAUDE.md references {target}'
        # Check Makefile has the target
        makefile = root / 'Makefile'
        mf_text = makefile.read_text() if makefile.exists() else ''
        found = f'{cmd}:' in mf_text
        pair = {
            'source': 'CLAUDE.md',
            'target': 'Makefile',
            'claim': claim,
            'actual': 'EXISTS' if found else 'MISSING',
            'match': found,
        }
        pairs.append(pair)
        if not found:
            mismatches.append({k: v for k, v in pair.items() if k != 'match'})

# Check 2: Skill command references
skills_dir = root / '.claude' / 'skills'
commands_dir = root / '.claude' / 'commands'
if skills_dir.exists():
    for skill_file in skills_dir.rglob('SKILL.md'):
        text = skill_file.read_text()
        # Find /command-name references (backtick-wrapped or after whitespace)
        # Exclude paths (src/, home/, usr/, etc.) and version-like patterns
        PATH_PREFIXES = {
            'src', 'home', 'usr', 'bin', 'etc', 'tmp', 'var', 'opt',
            'dev', 'lib', 'app', 'apps', 'docs', 'frontend', 'scripts',
            'evidence', 'packages', 'migrations', 'tests', 'claude',
            'diyu', 'node_modules', 'v1', 'v2', 'v3',
        }
        refs = re.findall(r'(?:^|\s)/([\w][\w-]*)', text, re.MULTILINE)
        for ref in refs:
            if ref.lower() in PATH_PREFIXES:
                continue
            if len(ref) <= 1:
                continue
            cmd_path = commands_dir / f'{ref}.md'
            found = cmd_path.exists()
            rel_skill = skill_file.relative_to(root)
            pair = {
                'source': str(rel_skill),
                'target': f'.claude/commands/{ref}.md',
                'claim': f'Skill references /{ref}',
                'actual': 'EXISTS' if found else 'MISSING',
                'match': found,
            }
            pairs.append(pair)
            if not found:
                mismatches.append({k: v for k, v in pair.items() if k != 'match'})

# Check 3: Script paths in commands (skip code-block examples)
if commands_dir.exists():
    for cmd_file in commands_dir.glob('*.md'):
        text = cmd_file.read_text()
        # Strip fenced code blocks to avoid matching example paths
        text_no_code = re.sub(r'\x60\x60\x60.*?\x60\x60\x60', '', text, flags=re.DOTALL)
        # Find script path references outside code blocks
        script_refs = re.findall(r'scripts/[\w/_.-]+\.(?:py|sh)', text_no_code)
        for sref in set(script_refs):
            spath = root / sref
            found = spath.exists()
            pair = {
                'source': str(cmd_file.relative_to(root)),
                'target': sref,
                'claim': f'Command references {sref}',
                'actual': 'EXISTS' if found else 'MISSING',
                'match': found,
            }
            pairs.append(pair)
            if not found:
                mismatches.append({k: v for k, v in pair.items() if k != 'match'})

report = {
    'version': '1.0',
    'timestamp': '$TIMESTAMP',
    'pairs_checked': pairs,
    'mismatches': mismatches,
    'summary': {
        'total_pairs': len(pairs),
        'matches': len([p for p in pairs if p['match']]),
        'mismatches_count': len(mismatches),
    },
}

with open('$OUTPUT', 'w') as f:
    json.dump(report, f, indent=2)

print(f'Checked {len(pairs)} claim-pairs, {len(mismatches)} mismatches')
print(f'Report written to $OUTPUT')
"

# Validate output
echo "Validating report..."
uv run python "$ROOT/scripts/validate_audit_artifacts.py" \
  --file "$OUTPUT" --schema "$SCHEMA"

echo "=== Cross-Reference Audit Complete ==="
echo "Status: SUBMITTED FOR REVIEW"

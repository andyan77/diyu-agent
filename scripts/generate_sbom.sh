#!/usr/bin/env bash
# generate_sbom.sh - Generate SPDX 2.3 SBOM for DIYU Agent
#
# Produces delivery/sbom.json in SPDX 2.3 JSON format.
#
# Strategy:
#   1. If `syft` is available: use it (best quality, native SPDX)
#   2. Fallback: generate minimal SPDX 2.3 from uv/pip metadata
#
# CI: Use anchore/sbom-action@v0 in GitHub Actions (preferred)
#
# Usage:
#   bash scripts/generate_sbom.sh              # Generate SBOM
#   bash scripts/generate_sbom.sh --validate   # Generate + validate
#   bash scripts/generate_sbom.sh --json       # JSON status output
#
# Exit codes: 0 = success, 1 = generation failed

set -euo pipefail

VALIDATE=false
JSON_OUTPUT=false
SBOM_PATH="delivery/sbom.json"

while [ $# -gt 0 ]; do
  case "$1" in
    --validate) VALIDATE=true ;;
    --json)     JSON_OUTPUT=true ;;
  esac
  shift
done

mkdir -p delivery

generate_with_syft() {
  syft dir:. -o spdx-json="$SBOM_PATH" 2>/dev/null
}

generate_fallback() {
  # Fallback: build minimal SPDX 2.3 from pip/uv metadata
  uv run python -c "
import json
import subprocess
import sys
from datetime import datetime, timezone

# Get installed packages
result = subprocess.run(
    ['uv', 'pip', 'list', '--format=json'],
    capture_output=True, text=True
)
if result.returncode != 0:
    # Try pip as fallback
    result = subprocess.run(
        [sys.executable, '-m', 'pip', 'list', '--format=json'],
        capture_output=True, text=True
    )

packages = json.loads(result.stdout) if result.stdout.strip() else []

# Build SPDX 2.3 document
spdx = {
    'spdxVersion': 'SPDX-2.3',
    'dataLicense': 'CC0-1.0',
    'SPDXID': 'SPDXRef-DOCUMENT',
    'name': 'diyu-agent',
    'documentNamespace': 'https://diyu.dev/spdx/diyu-agent',
    'creationInfo': {
        'created': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'creators': ['Tool: diyu-agent/scripts/generate_sbom.sh'],
        'licenseListVersion': '3.22',
    },
    'packages': [],
}

for pkg in packages:
    spdx['packages'].append({
        'SPDXID': f\"SPDXRef-Package-{pkg['name'].replace('.', '-')}\",
        'name': pkg['name'],
        'versionInfo': pkg.get('version', 'NOASSERTION'),
        'downloadLocation': 'NOASSERTION',
        'filesAnalyzed': False,
        'licenseConcluded': 'NOASSERTION',
        'licenseDeclared': 'NOASSERTION',
        'copyrightText': 'NOASSERTION',
    })

with open('$SBOM_PATH', 'w') as f:
    json.dump(spdx, f, indent=2, ensure_ascii=False)

print(f'Generated {len(packages)} packages', file=sys.stderr)
"
}

validate_spdx() {
  uv run python -c "
import json, sys
d = json.load(open('$SBOM_PATH'))
assert 'spdxVersion' in d, 'Missing spdxVersion'
assert d['spdxVersion'].startswith('SPDX-2'), f\"Bad version: {d['spdxVersion']}\"
assert 'packages' in d, 'Missing packages array'
print(f\"SPDX {d['spdxVersion']}: {len(d['packages'])} packages\")
"
}

# Generate
if command -v syft &>/dev/null; then
  METHOD="syft"
  generate_with_syft
else
  METHOD="fallback"
  generate_fallback
fi

# Validate if requested or always for JSON output
if [ "$VALIDATE" = true ] || [ "$JSON_OUTPUT" = true ]; then
  if validate_spdx 2>/dev/null; then
    VALID=true
  else
    VALID=false
  fi
else
  VALID="not_checked"
fi

if [ "$JSON_OUTPUT" = true ]; then
  PKG_COUNT=$(uv run python -c "import json;print(len(json.load(open('$SBOM_PATH')).get('packages',[])))" 2>/dev/null || echo 0)
  echo "{\"status\":\"pass\",\"method\":\"$METHOD\",\"path\":\"$SBOM_PATH\",\"packages\":$PKG_COUNT,\"valid_spdx\":$VALID}"
else
  echo "SBOM generated: $SBOM_PATH (method=$METHOD)"
  if [ "$VALIDATE" = true ]; then
    if [ "$VALID" = true ]; then
      echo "SPDX validation: PASS"
    else
      echo "SPDX validation: FAIL"
      exit 1
    fi
  fi
fi

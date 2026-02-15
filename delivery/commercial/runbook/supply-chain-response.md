# Supply Chain Compromise Response Runbook

> Priority: P1 | Response SLA: 1 hour
> Milestone: OS5-6

## Trigger Conditions

- Dependency vulnerability scanner flags Critical/High CVE
- Docker image scan detects malicious layer
- Upstream package compromised (advisory from PyPI/npm/GitHub)
- Unexpected behavior after dependency update

## Immediate Actions (0-30 min)

```bash
# 1. Identify affected dependencies
# Python
uv run pip-audit --format=json > /tmp/pip-audit.json
uv run safety check --json > /tmp/safety-check.json

# Frontend
cd frontend && pnpm audit --json > /tmp/pnpm-audit.json

# Docker images
docker scout cves diyu-api:latest --format sarif > /tmp/docker-scout.json 2>/dev/null || true
```

## Containment (30-120 min)

1. Pin known-good versions in lockfiles

```bash
# If specific package is compromised: pin to last known-good
# Python: edit pyproject.toml, then:
uv lock
uv sync

# Frontend: edit package.json, then:
cd frontend && pnpm install --frozen-lockfile=false
```

2. If docker image compromised: rebuild from scratch

```bash
# Use --no-cache to ensure fresh layers
docker compose build --no-cache
docker compose up -d
```

3. Audit recent deployments for the compromised dependency

```bash
# Check when compromised version was introduced
git log --oneline -- uv.lock frontend/pnpm-lock.yaml | head -10
```

## Recovery

1. Apply patched version of affected dependency
2. Run full test suite to verify no behavioral changes
3. Re-scan all dependencies: `uv run pip-audit && cd frontend && pnpm audit`
4. Update SBOM: `make sbom` (when available)
5. If data integrity is suspect: compare DB checksums with last known-good backup

## Prevention

- CI runs `pip-audit` + `pnpm audit` + Docker Scout on every PR
- Renovate/Dependabot auto-updates with CI validation
- Lock files committed and reviewed in PRs
- SBOM generated per release for supply chain transparency

## Evidence Collection

- Vulnerability scan reports (before/after)
- Git diff of lockfile changes
- Deployment timeline vs. advisory publication date
- Store in `evidence/incidents/YYYY-MM-DD-supply-chain/`

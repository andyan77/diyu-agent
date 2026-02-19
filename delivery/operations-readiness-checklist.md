# Operations Readiness Checklist

Phase 5 Go-Live gate. All items must be checked before release sign-off.

Gate ID: `p5-operations-readiness`

---

## A. Engineering Gates (automated, CI-verified)

- [ ] Phase gate passes: `make verify-phase-5`
- [ ] Test coverage >= 80%: CI `test-backend` with `--cov-fail-under=80`
- [ ] Security scan clean: CI `security-scan` job (bandit + semgrep)
- [ ] Image build + trivy scan: CI `build-image` job
- [ ] Integration tests pass: CI `integration-tests` job (PG + Redis)
- [ ] Frontend E2E pass: CI `test-e2e` job
- [ ] Cross-layer xnode coverage = 100%: `make check-xnode-coverage-5`
- [ ] Merge-readiness gate: all 15 CI jobs green

## B. Operations Gates (drill-verified)

- [ ] Release rollback drill: `bash scripts/drill_release.sh --dry-run` exit 0, < 5min
  - Evidence: `evidence/release/drill-release-*.json`
- [ ] DR restore drill: `bash scripts/drill_dr_restore.sh --dry-run` exit 0
  - Evidence: `evidence/release/drill-dr-restore-*.json`
- [ ] Incident SLA defined: `delivery/commercial/incident-sla.yaml` (P0/P1/P2 tiers)
- [ ] On-call rotation configured: weekly rotation, 24x7 coverage
- [ ] Alert routing verified: `uv run python scripts/check_alert_routing.py` exit 0
- [ ] Compliance artifacts present: `uv run python scripts/check_compliance_artifacts.py` exit 0

## C. Human Review (manual sign-off required)

### C1. Billing

- [ ] Dual-ledger consistency verified (application ledger vs payment provider)
- [ ] Idempotent charge operations confirmed
- [ ] Daily reconciliation report operational
- [ ] Evidence: business test report + finance audit

### C2. Data Governance

- [ ] Data classification document complete (`delivery/commercial/dpa-template.md`)
- [ ] Retention policy defined (`delivery/commercial/data-retention-policy.md`)
- [ ] Deletion provability (`delivery/commercial/data-deletion-proof-template.md`)
- [ ] Privacy policy published (`delivery/commercial/privacy-policy.md`)

### C3. Capacity and Performance

- [ ] Load test baseline report (k6/artillery): p99 < 500ms at projected peak
- [ ] Capacity model documented (users/requests/storage projections)
- [ ] Auto-scaling policy defined and tested
- [ ] Evidence: load test results archived to `evidence/release/`

### C4. Customer Operations

- [ ] Status page operational
- [ ] Support SOP documented
- [ ] SLA reporting template ready
- [ ] Customer communication templates (incident, maintenance, changelog)

### C5. Commercial Delivery

- [ ] License and entitlement system configured
- [ ] Version compatibility matrix published
- [ ] Upgrade/migration strategy documented
- [ ] SBOM signed and verifiable: `bash scripts/sign_sbom.sh` exit 0

---

## Sign-Off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Engineering Lead | | | |
| Security Lead | | | |
| Operations Lead | | | |

Release version: ___________
Release evidence: `evidence/release/template.json` (filled)

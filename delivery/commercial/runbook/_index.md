# DIYU Agent Runbook Index

> Audience: Operations team, on-call engineers
> Milestone: OS5-6 (Security Incident Runbook)

## Runbook Files

| File | Scope | Priority |
|------|-------|----------|
| [common-operations.md](common-operations.md) | Day-to-day ops: health check, DB, cache, upgrade, monitoring | All |
| [data-breach-response.md](data-breach-response.md) | Data breach / unauthorized data access | P0 |
| [key-leak-response.md](key-leak-response.md) | API key / credential leak | P0 |
| [ddos-response.md](ddos-response.md) | DDoS / traffic anomaly | P1 |
| [supply-chain-response.md](supply-chain-response.md) | Supply chain compromise (dependency, image) | P1 |

## Escalation Matrix

| Priority | Response SLA | Escalation |
|----------|-------------|------------|
| P0 | 15 min | Security lead + CTO |
| P1 | 1 hour | Security lead |
| P2 | 4 hours | On-call engineer |

## Post-Incident

Every P0/P1 incident must produce:
1. Incident timeline (5W: who/what/when/where/why)
2. Root cause analysis
3. Remediation actions with owner + deadline
4. Runbook update PR if procedure was inadequate

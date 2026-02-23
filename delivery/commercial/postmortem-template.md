# Incident Postmortem Report

> Template version: 1.0 | Gate: p4-postmortem-capa
> Fill in all sections within 48h of incident resolution.

## Incident Summary

| Field | Value |
|-------|-------|
| **Incident ID** | INC-YYYY-NNN |
| **Severity** | P0 / P1 / P2 |
| **Duration** | HH:MM (from detection to resolution) |
| **Impact** | Brief description of user/business impact |
| **Date** | YYYY-MM-DD |
| **Author** | Name |
| **Status** | Draft / Reviewed / Closed |

## Timeline

| Time (UTC) | Event |
|------------|-------|
| HH:MM | First alert / detection |
| HH:MM | Incident declared |
| HH:MM | Root cause identified |
| HH:MM | Mitigation applied |
| HH:MM | Service restored |
| HH:MM | All-clear confirmed |

## Root Cause

Describe the root cause in technical detail:

- **What happened**: ...
- **Why it happened**: ... (use 5-Whys if applicable)
- **Contributing factors**: ...

## Impact

- **Users affected**: N users / N% of traffic
- **Data impact**: None / Read-only / Data loss (describe)
- **Revenue impact**: None / Estimated $X
- **SLO impact**: Error budget consumed: X min of Y min monthly budget

## Action Items

| ID | Action | Owner | Priority | Deadline | Status |
|----|--------|-------|----------|----------|--------|
| AI-1 | ... | ... | P0/P1/P2 | YYYY-MM-DD | Open / Done |
| AI-2 | ... | ... | P0/P1/P2 | YYYY-MM-DD | Open / Done |

> Action items MUST be registered in `delivery/commercial/capa-register.yaml`
> with matching incident ID for traceability.

## Lessons Learned

### What went well
- ...

### What could be improved
- ...

### Where we got lucky
- ...

## References

- Alert: link to alert/dashboard
- Logs: link to log query
- CAPA register entry: `delivery/commercial/capa-register.yaml#INC-YYYY-NNN`
- Evidence archive: `evidence/incidents/INC-YYYY-NNN/`

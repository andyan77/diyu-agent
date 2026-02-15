# Incident Post-Mortem Template

> Incident ID: INC-YYYY-NNN
> Date: YYYY-MM-DD
> Severity: P0 / P1 / P2 / P3
> Status: Draft / Reviewed / Closed

---

## 1. Summary

**Impact**: [One sentence: what was affected, how many users, duration]
**Root Cause**: [One sentence: why it happened]
**Resolution**: [One sentence: how it was fixed]

---

## 2. Timeline

| Time (UTC) | Event |
|-----------|-------|
| HH:MM | Alert triggered: [description] |
| HH:MM | On-call acknowledged |
| HH:MM | Root cause identified |
| HH:MM | Fix deployed |
| HH:MM | Service restored |
| HH:MM | Monitoring confirms stable |

---

## 3. Root Cause Analysis

### What happened
[Detailed technical description]

### Why it happened
[Chain of causes: immediate -> contributing -> root]

### Why it wasn't caught earlier
[Gap in monitoring / testing / review]

---

## 4. Impact Assessment

| Dimension | Detail |
|-----------|--------|
| Users affected | [count / percentage] |
| Duration | [minutes] |
| Data impact | [none / partial / full] |
| Revenue impact | [estimated] |
| SLA breach | [yes/no, which metric] |

---

## 5. Corrective Actions

| # | Action | Owner | Deadline | Status |
|---|--------|-------|----------|--------|
| 1 | [Immediate fix] | | | Done |
| 2 | [Prevent recurrence] | | | TODO |
| 3 | [Improve detection] | | | TODO |
| 4 | [Update runbook] | | | TODO |

---

## 6. Lessons Learned

- **What went well**: [quick detection, clear escalation, etc.]
- **What went poorly**: [slow diagnosis, missing runbook, etc.]
- **Where we got lucky**: [could have been worse because...]

---

> Review: This post-mortem must be reviewed by the on-call lead within 48h.
> Archive: Store final version in `evidence/` with incident ID.

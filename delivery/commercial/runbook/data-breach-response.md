# Data Breach Response Runbook

> Priority: P0 | Response SLA: 15 min
> Milestone: OS5-6

## Trigger Conditions

- Unauthorized access to tenant data detected in audit logs
- RLS bypass evidence in `audit_events`
- Customer report of seeing another tenant's data
- Abnormal data export volume alert

## Immediate Actions (0-15 min)

```bash
# 1. Identify affected org(s) from audit logs
psql -h localhost -U diyu -d diyu -c "
  SELECT org_id, user_id, action, created_at
  FROM audit_events
  WHERE created_at > NOW() - INTERVAL '1 hour'
  AND action IN ('data_export', 'cross_tenant_access')
  ORDER BY created_at DESC LIMIT 50;
"

# 2. Revoke all tokens for affected org
psql -h localhost -U diyu -d diyu -c "
  UPDATE user_sessions SET revoked = true
  WHERE org_id = '<AFFECTED_ORG_ID>';
"

# 3. Enable enhanced logging
export DIYU_AUDIT_LEVEL=verbose
docker compose restart api
```

## Containment (15-60 min)

1. Isolate affected org: set `org_settings.suspended = true`
2. Snapshot current DB state for forensics
3. Review RLS policies: `scripts/check_rls.sh --verbose`
4. Check for RLS bypass in recent code changes

```bash
# Forensic snapshot
pg_dump -h localhost -U diyu -d diyu -F c \
  -f forensic-$(date +%Y%m%dT%H%M%S).dump

# RLS policy audit
psql -h localhost -U diyu -d diyu -c "
  SELECT schemaname, tablename, policyname, permissive, qual
  FROM pg_policies WHERE schemaname = 'public';
"
```

## Recovery

1. Fix RLS gap if found -> apply migration -> verify with isolation tests
2. Restore org access after verification
3. Notify affected customers per PIPL/GDPR Article 33 (72-hour window)

## Evidence Collection

- `audit_events` export for incident window
- RLS policy diff (before/after)
- Access logs from reverse proxy
- Store in `evidence/incidents/YYYY-MM-DD-data-breach/`

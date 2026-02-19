# Disaster Recovery Restore Runbook

## Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| RTO (Recovery Time Objective) | 30 minutes | Service available for user requests |
| RPO (Recovery Point Objective) | 1 hour | Maximum data loss window |

## Backup Strategy

### PostgreSQL

- WAL archiving: continuous (every 60s or 16MB)
- Full backup: daily at 02:00 UTC
- Retention: 30 days
- Location: object storage (encrypted at rest)

### Redis

- RDB snapshot: every 15 minutes
- AOF: appendfsync everysec
- Retention: 7 days

### Object Storage (MinIO/S3)

- Cross-region replication enabled
- Versioning enabled (30-day retention)

## Recovery Procedure

### 1. Assess Scope

```bash
# Determine failure domain
# - Single service failure -> restart/redeploy
# - Data corruption -> point-in-time recovery
# - Full infrastructure loss -> full restore
```

### 2. PostgreSQL Restore

```bash
# Point-in-time recovery
pg_restore --host=$RESTORE_HOST --dbname=diyu \
  --clean --if-exists \
  $BACKUP_PATH

# Apply WAL to target timestamp
# recovery_target_time = '$TARGET_TIMESTAMP'
```

### 3. Redis Restore

```bash
# Stop Redis, replace dump file, restart
redis-cli -h $REDIS_HOST SHUTDOWN NOSAVE
cp $BACKUP_PATH /var/lib/redis/dump.rdb
redis-server /etc/redis/redis.conf
redis-cli -h $REDIS_HOST PING
```

### 4. Application Restore

```bash
# Redeploy from last known good image
kubectl rollout restart deployment/diyu-agent --namespace=production
kubectl rollout status deployment/diyu-agent --timeout=300s
```

### 5. Data Consistency Verification

```bash
# Verify record counts match pre-disaster snapshot
# Verify no orphaned references
# Verify RLS policies intact
uv run python scripts/verify_data_consistency.py --post-restore
```

## Post-Recovery

1. Document timeline and actions in incident report
2. Archive recovery evidence to `evidence/release/`
3. Update RPO/RTO measurements
4. Schedule follow-up drill if recovery exceeded targets

## Drill Schedule

Quarterly dry-run via `scripts/drill_dr_restore.sh --dry-run`

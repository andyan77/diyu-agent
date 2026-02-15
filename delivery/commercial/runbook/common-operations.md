# DIYU Agent Operations Runbook

> Version: 1.0 (Draft)
> Audience: Operations team, on-call engineers

---

## 1. Service Health Check

```bash
# Quick health
curl -sf http://localhost:8000/health | python3 -m json.tool

# Full doctor
make doctor

# Phase gate verification
make verify-phase-current
```

## 2. Database Operations

### 2.1 Apply Migrations

```bash
# Check pending migrations
alembic history --indicate-current

# Apply all pending
alembic upgrade head

# Rollback last migration
alembic downgrade -1
```

### 2.2 Backup

```bash
# PostgreSQL backup
pg_dump -h localhost -U diyu -d diyu -F c -f backup-$(date +%Y%m%d).dump

# Restore
pg_restore -h localhost -U diyu -d diyu -c backup-YYYYMMDD.dump
```

### 2.3 Connection Issues

```bash
# Check PostgreSQL connectivity
psql -h localhost -U diyu -d diyu -c "SELECT 1"

# Check Redis
redis-cli -h localhost ping

# Check all services
docker compose ps
```

## 3. Application Operations

### 3.1 Restart Services

```bash
# Restart API server
docker compose restart api

# Restart all
docker compose down && docker compose up -d

# Check logs
docker compose logs -f api --tail=100
```

### 3.2 Clear Cache

```bash
# Redis flush (caution: clears all sessions)
redis-cli FLUSHDB

# Clear specific cache prefix
redis-cli KEYS "cache:*" | xargs redis-cli DEL
```

### 3.3 Celery Worker Issues

```bash
# Check worker status
celery -A src.infra.celery inspect active

# Purge stuck tasks
celery -A src.infra.celery purge

# Restart workers
docker compose restart celery-worker
```

## 4. Monitoring & Alerts

### 4.1 Key Metrics to Watch

| Metric | Warning | Critical |
|--------|---------|----------|
| API P95 latency | > 2s | > 5s |
| Error rate | > 1% | > 5% |
| DB connection pool | > 80% | > 95% |
| Redis memory | > 80% | > 95% |
| Disk usage | > 80% | > 90% |

### 4.2 Common Alert Responses

**High Error Rate**:
1. Check API logs: `docker compose logs api --tail=200`
2. Check DB connectivity
3. Check LLM provider status
4. If LLM provider down: verify fallback model activates

**High Latency**:
1. Check DB slow queries: `SELECT * FROM pg_stat_activity WHERE state = 'active'`
2. Check Redis: `redis-cli INFO memory`
3. Check Celery queue depth
4. Consider scaling replicas

## 5. Upgrade Procedure

```bash
# 1. Backup
pg_dump -h localhost -U diyu -d diyu -F c -f pre-upgrade-$(date +%Y%m%d).dump

# 2. Pull new version
git pull origin main

# 3. Apply migrations
alembic upgrade head

# 4. Rebuild and restart
docker compose build
docker compose up -d

# 5. Verify
make doctor
curl -sf http://localhost:8000/health
```

**Rollback**:
```bash
# 1. Stop services
docker compose down

# 2. Revert code
git checkout <previous-tag>

# 3. Rollback migration
alembic downgrade -1

# 4. Restart
docker compose up -d
```

## 6. Security Incidents

1. **Suspected data breach**: Immediately revoke affected tokens, isolate affected org
2. **Malicious input detected**: Check `security_status` field in media table
3. **Unauthorized access**: Check audit logs, rotate credentials
4. **Escalation**: Contact security lead within 15 minutes for P0

---

> Updates: This runbook must be updated after every P0/P1 incident post-mortem.
> Evidence: Runbook execution logs stored in `evidence/` during drills.

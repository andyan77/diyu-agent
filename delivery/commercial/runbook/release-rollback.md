# Release Rollback Runbook

## Scope

Covers: canary deploy, progressive rollout, full rollout, and rollback procedures.

## Pre-Conditions

- Container image tagged and pushed to registry
- Previous stable image tag known (from `evidence/release/` manifest)
- Database migration compatibility verified (forward-only or backward-compatible)

## Rollout Procedure

### 1. Canary Deploy (5% traffic)

```bash
# Deploy canary with new image tag
kubectl set image deployment/diyu-agent app=diyu-agent:$NEW_TAG \
  --namespace=production --record
kubectl rollout status deployment/diyu-agent --timeout=120s

# Verify health
curl -sf https://api.diyu.app/healthz | jq .status
```

### 2. Progressive Rollout (25% -> 50% -> 100%)

Monitor golden signals at each stage:
- Error rate < 1%
- p99 latency < 500ms
- Request rate stable (no drops)
- Saturation (CPU/memory) within budget

### 3. Full Rollout

```bash
kubectl rollout status deployment/diyu-agent --timeout=300s
```

## Rollback Procedure

### Trigger Conditions

- Error rate > 5% sustained for 2 minutes
- p99 latency > 2s sustained for 5 minutes
- Health check failures on > 10% of pods
- Any data corruption signal

### Rollback Steps

```bash
# Step 1: Rollback deployment
kubectl rollout undo deployment/diyu-agent --namespace=production

# Step 2: Verify rollback
kubectl rollout status deployment/diyu-agent --timeout=120s

# Step 3: Health check
curl -sf https://api.diyu.app/healthz | jq .status

# Step 4: Verify golden signals recovered
# Check dashboard: deploy/monitoring/grafana-dashboard.json
```

### Target: Rollback < 5 minutes

## Post-Rollback

1. Create incident ticket (P1 minimum)
2. Archive rollback evidence to `evidence/release/`
3. Root cause analysis within 24 hours
4. Fix verified in staging before re-deploy attempt

## Drill Schedule

Monthly dry-run via `scripts/drill_release.sh --dry-run`

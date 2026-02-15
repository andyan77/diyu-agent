# Key / Credential Leak Response Runbook

> Priority: P0 | Response SLA: 15 min
> Milestone: OS5-6

## Trigger Conditions

- Secret scanning (gitleaks/trufflehog) alert in CI
- Customer reports leaked credentials
- Third-party disclosure (GitHub secret scanning alert)
- Anomalous API usage from unknown IP

## Immediate Actions (0-15 min)

```bash
# 1. Identify what was leaked
# Check CI scan results
cat evidence/security-scan-latest.json | python3 -m json.tool

# 2. Rotate affected credentials immediately
# -- LLM API keys --
# Update .env on all deployed instances, then restart
docker compose restart api celery-worker

# -- Database credentials --
psql -h localhost -U postgres -c "ALTER USER diyu PASSWORD '<NEW_PASSWORD>';"
# Update .env -> restart all

# -- JWT signing key --
# Generate new key, update .env -> all active sessions invalidated
openssl rand -hex 64 > /dev/null  # Generate locally, set in vault
```

## Containment (15-60 min)

1. Revoke leaked key at provider (OpenAI/Anthropic/etc dashboard)
2. If git-committed: `git filter-branch` or BFG to remove from history
3. Force-rotate all credentials in same category (defense in depth)
4. Check `audit_events` for unauthorized usage during exposure window

```bash
# Check for unauthorized LLM calls during exposure
psql -h localhost -U diyu -d diyu -c "
  SELECT user_id, org_id, model_id, token_count, created_at
  FROM llm_usage_records
  WHERE created_at > '<LEAK_DISCOVERY_TIME>'::timestamp - INTERVAL '7 days'
  ORDER BY created_at DESC;
"
```

## Recovery

1. Verify new credentials work: `make doctor`
2. Monitor for continued unauthorized usage (24-hour watch)
3. Update secret scanning rules if detection was delayed

## Evidence Collection

- CI scan report that detected the leak
- Git commit history showing when secret was introduced
- Usage logs during exposure window
- Provider dashboard screenshots (API call volume)
- Store in `evidence/incidents/YYYY-MM-DD-key-leak/`

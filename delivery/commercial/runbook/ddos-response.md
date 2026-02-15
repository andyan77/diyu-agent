# DDoS / Traffic Anomaly Response Runbook

> Priority: P1 | Response SLA: 1 hour
> Milestone: OS5-6

## Trigger Conditions

- API 429 rate dramatically exceeds normal baseline
- P95 latency > 5s sustained for > 5 min
- Connection pool saturation alert (> 95%)
- External monitoring reports service unavailability

## Immediate Actions (0-15 min)

```bash
# 1. Assess current traffic
docker compose logs api --tail=500 | grep -c "429"
docker compose logs api --tail=500 | grep -c "503"

# 2. Check rate limiting effectiveness
redis-cli KEYS "ratelimit:*" | wc -l

# 3. Identify top offenders by IP/org
docker compose logs api --tail=5000 | \
  grep -oP '"remote_ip":"\K[^"]+' | sort | uniq -c | sort -rn | head -20
```

## Containment (15-60 min)

1. Tighten rate limits for non-authenticated traffic

```bash
# Temporary rate limit reduction (via env var)
export DIYU_RATE_LIMIT_ANON=10   # requests/min (default: 60)
export DIYU_RATE_LIMIT_AUTH=30   # requests/min (default: 300)
docker compose restart api
```

2. If reverse proxy available: block top offending IPs

```bash
# nginx example
echo "deny <OFFENDING_IP>;" >> /etc/nginx/conf.d/blocklist.conf
nginx -s reload
```

3. If cloud-hosted: enable cloud provider DDoS protection

## Recovery

1. Monitor traffic patterns for 24 hours after mitigation
2. Restore normal rate limits once attack subsides
3. Review and update rate limiting thresholds based on attack profile
4. Consider adding CAPTCHA for suspicious patterns

## Evidence Collection

- Access logs (last 24 hours)
- Rate limit trigger counts by IP/org
- Latency/error time series from Prometheus
- Store in `evidence/incidents/YYYY-MM-DD-ddos/`

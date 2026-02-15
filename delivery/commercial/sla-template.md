# DIYU Agent -- Service Level Agreement (SLA) Template

> Version: 1.0 (Draft)
> Scope: Production deployment of DIYU Agent platform

---

## 1. Service Availability

| Tier | Target | Measurement Window |
|------|--------|--------------------|
| Platform API | 99.9% | Monthly (rolling 30d) |
| Admin Console | 99.5% | Monthly |
| Background Jobs (Celery) | 99.0% | Monthly |

**Exclusions**: Scheduled maintenance (announced 48h in advance), force majeure, customer-caused outages.

---

## 2. Response Time

| Endpoint Category | P50 | P95 | P99 |
|-------------------|-----|-----|-----|
| Chat API (sync) | < 500ms | < 2s | < 5s |
| Chat API (streaming first token) | < 300ms | < 1s | < 3s |
| Knowledge Query | < 200ms | < 800ms | < 2s |
| Admin CRUD | < 300ms | < 1s | < 3s |
| File Upload (< 10MB) | < 2s | < 5s | < 10s |

---

## 3. Data Durability & Recovery

| Metric | Target |
|--------|--------|
| RPO (Recovery Point Objective) | < 1 hour |
| RTO (Recovery Time Objective) | < 4 hours |
| Backup Frequency | Every 6 hours (automated) |
| Backup Retention | 30 days |
| Cross-region Replication | Optional (customer configurable) |

---

## 4. Incident Response

| Severity | Definition | Response Time | Resolution Target |
|----------|-----------|---------------|-------------------|
| P0 (Critical) | Service down, data loss risk | 15 min | 4 hours |
| P1 (Major) | Core feature degraded | 1 hour | 8 hours |
| P2 (Minor) | Non-core feature affected | 4 hours | 24 hours |
| P3 (Low) | Cosmetic / documentation | Next business day | 5 business days |

---

## 5. Monitoring & Reporting

- Real-time status page (public)
- Monthly SLA compliance report
- Quarterly service review meeting
- Incident post-mortem within 48h for P0/P1

---

## 6. Penalties & Credits

| Availability | Credit |
|-------------|--------|
| 99.9% - 99.5% | 0% |
| 99.5% - 99.0% | 10% of monthly fee |
| 99.0% - 95.0% | 25% of monthly fee |
| < 95.0% | 50% of monthly fee |

---

> Customization: Replace targets with customer-specific values during contract negotiation.
> Evidence: All SLA metrics backed by `evidence/` CI artifacts and monitoring dashboards.

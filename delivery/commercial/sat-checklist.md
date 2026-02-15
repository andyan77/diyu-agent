# Site Acceptance Test (SAT) Checklist

> Version: 1.0 (Draft)
> Purpose: Customer deployment verification checklist
> Usage: Execute each section sequentially. All MUST PASS before handover.

---

## 1. Installation Verification

- [ ] `make bootstrap` completes without FAIL
- [ ] `make doctor` reports 0 FAIL
- [ ] `docker compose up -d` starts all 5 services (PG/Redis/Qdrant/Neo4j/MinIO)
- [ ] `alembic upgrade head` applies all migrations
- [ ] Frontend accessible at configured URL
- [ ] Admin console accessible at configured URL

## 2. Authentication & Authorization

- [ ] User login with valid credentials succeeds
- [ ] User login with invalid credentials fails with proper error
- [ ] Token refresh works before expiry
- [ ] Organization switching changes data scope
- [ ] Admin-only routes blocked for regular users
- [ ] RLS isolation: User A cannot see User B's data

## 3. Core Functionality

- [ ] Create new conversation
- [ ] Send message and receive AI response
- [ ] Streaming response works (tokens appear incrementally)
- [ ] Knowledge query returns relevant results
- [ ] File upload succeeds (image + document)
- [ ] Skill execution produces expected output

## 4. Data Isolation (Multi-tenant)

- [ ] Create 2 test organizations
- [ ] Data created in Org A not visible in Org B
- [ ] API requests with Org A token cannot access Org B resources
- [ ] Admin can view both organizations

## 5. Backup & Recovery

- [ ] Trigger manual backup
- [ ] Verify backup file exists and is non-empty
- [ ] Simulate data deletion
- [ ] Restore from backup
- [ ] Verify data integrity after restore

## 6. Monitoring & Audit

- [ ] Health endpoint returns 200
- [ ] Metrics endpoint returns Prometheus format
- [ ] Structured logs contain trace_id, request_id, org_id
- [ ] Audit log records login events
- [ ] Error tracking captures exceptions

## 7. Upgrade Path

- [ ] Apply schema migration (alembic upgrade)
- [ ] Verify no data loss after migration
- [ ] Rollback migration (alembic downgrade)
- [ ] Verify rollback integrity
- [ ] Zero-downtime deployment verification (if applicable)

---

## Sign-off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Customer Technical Lead | | | |
| Delivery Engineer | | | |
| Project Manager | | | |

> Evidence: Completed checklist stored in `evidence/release/` with deployment version tag.

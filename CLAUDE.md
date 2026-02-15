# DIYU Agent - Project Context

## Architecture
- 6-layer: Brain(+MemoryCore) / Knowledge / Skill / Tool / Gateway / Infrastructure
- Dual SSOT: Memory Core (hard dep) + Knowledge Stores (soft dep, pluggable)
- 6 Day-1 Ports: MemoryCorePort, KnowledgePort, LLMCallPort, SkillRegistry, OrgContext, StoragePort
- Backend: Python 3.12 + FastAPI + SQLAlchemy + Alembic + uv
- Frontend: Next.js 15 (App Router) + Turborepo + pnpm (apps/web + apps/admin)
- DB: PostgreSQL 16 + pgvector | Cache: Redis | Queue: Celery

## Governance
- Schema: `docs/governance/task-card-schema-v1.0.md` (Frozen, dual-Tier: A=10 fields, B=8 fields)
- Milestones: `docs/governance/milestone-matrix*.md` (L2) -> `docs/task-cards/` (L3)
- Execution: `docs/governance/execution-plan-v1.0.md`
- Validation: `scripts/check_task_schema.py` | `scripts/count_task_cards.py`

## Layer Boundaries (STRICT)
- Brain imports only Port interfaces, never Infrastructure directly
- Knowledge accessed via KnowledgePort, never direct DB queries from Brain
- Gateway handles auth/routing, never business logic
- Infrastructure implements Ports, never imported by Brain/Knowledge/Skill

## Commands
- `make bootstrap` - Install toolchain + deps
- `make doctor` - Diagnose dev environment
- `make verify-phase-N` - Phase gate verification (JSON output)
- `make lint` - ruff check + ruff format --check + frontend lint
- `make test` - pytest (unit) + frontend test
- `make test-smoke` - Fast smoke subset

## File Layout
- `src/` - Backend source (ports/, brain/, knowledge/, skill/, tool/, gateway/, infra/)
- `frontend/` - Frontend monorepo (apps/web, apps/admin, packages/*)
- `docs/` - Architecture (SSOT L1), governance, task-cards
- `delivery/` - Manifest, milestone-matrix.yaml, commercial templates
- `scripts/` - Guard scripts, doctor, verify_phase
- `migrations/` - Alembic migrations (NEVER delete, only add)
- `tests/` - unit/, isolation/, smoke/

## Red Lines
- NO cross-layer imports bypassing Ports
- NO migrations without rollback plan
- NO RLS bypass (org_id isolation mandatory)
- NO secrets in code (use .env + vault)
- NO force push to main

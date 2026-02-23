# Guardian System Completion Plan v1.0

> **Type**: Execution Plan (not audit report)
> **Goal**: Convert `audit-gap-report-v2.md` findings into persistent, automated guardian capabilities
> **Baseline commit**: `15c6fd8` (Phase 4 Stage 2)
> **Created**: 2026-02-24

---

## 1. Context & Positioning

This plan addresses the **guardian system gaps** identified through meta-audit of `audit-gap-report-v2.md`.
It is NOT a list of code bugs to fix, but a blueprint for building the **immune system** that detects problems at first contact.

**Core thesis**: Code problems are symptoms; guardian system incompleteness is the disease.

### 1.1 Derived From

| Source | Contribution |
|--------|-------------|
| `docs/governance/audit-gap-report-v2.md` 四层断裂分析 (line 461) | 4-layer verification model |
| `docs/governance/audit-gap-report-v2.md` 治理基础设施缺陷 (line 489) | INF-1~INF-7 bug inventory |
| `docs/governance/audit-gap-report-v2.md` 视角5 治理工具链审计 (line 609) | Guard script coverage gaps |
| Multi-round meta-audit discussion | 7 structural blind spots + 5-measure framework |

### 1.2 Guardian System Three-Piece Target

1. **Decomposition Audit** (分解审计): Architecture Promise -> Phase -> Task Card -> AC -> Gate -> Evidence -> Owner
2. **Contract Audit** (契约审计): Port/API/Event/DDL/ACL/Payload 6-type consistency
3. **Runtime Evidence Audit** (运行时证据审计): Evidence grading (A-F) + temporal integrity

---

## 2. Current Guard Infrastructure Inventory

### 2.1 Existing Scripts (14 check scripts)

| Script | Category | What It Does |
|--------|----------|-------------|
| `check_layer_deps.sh` | Architecture | Grep-based layer import check (5 layers only) |
| `check_port_compat.sh` | Architecture | Port interface compatibility |
| `check_rls.sh` | Security | RLS policy existence |
| `check_migration.sh` | Data | Migration safety |
| `check_cross_validation.py` | Multi-dimensional | 5-category diagnostic (8 Design Claims) |
| `check_acceptance_gate.py` | Gate | AC command validation |
| `check_xnode_coverage.py` | Gate | X-node coverage tracking |
| `check_task_schema.py` | Governance | Task card schema validation |
| `check_env_completeness.py` | Infra | Environment variable completeness |
| `check_compliance_artifacts.py` | Compliance | SBOM + runbook existence |
| `check_no_mock.py` | Testing | Mock usage detection |
| `check_no_vacuous_pass.py` | Testing | Empty test detection |
| `check_agent_dispatch.py` | Architecture | Agent routing validation |
| `check_slo_budget.py` | Observability | SLO budget monitoring |

### 2.2 Orchestration

- `full_audit.sh`: 9 categories, weekly cron (Monday 06:00 UTC)
- CI: `guard-checks` (L1 blocking) + `cross-validation` (informational, non-blocking)
- Makefile: 13 guard-related targets

### 2.3 Identified Gaps (What's Missing)

| Gap | Severity |
|-----|----------|
| No promise traceability (architecture -> task card -> gate) | Critical |
| No ADR individual verification (53 ADRs, 0 gates) | High |
| No contract consistency checking (6 types) | High |
| No frontend depth audit (84% task cards zero coverage) | High |
| No reverse audit direction (code -> design) | Medium |
| No evidence grading framework | Medium |
| No temporal integrity verification | Medium |
| Existing guard bugs (INF-4/5/7) | High |

---

## 3. Phase A: Fix Existing Guard Bugs

### A1. Fix `check_layer_deps.sh` — missing 3 layers

- **File**: `scripts/check_layer_deps.sh`
- **Current state**: `FORBIDDEN_IMPORTS` dict (lines 57-61) and for-loop (line 97) only cover **5 layers**: brain, knowledge, skill, gateway, tool
- **Missing**: memory, infra, shared (all three exist in `src/` as active directories)
- **Reference**: `check_cross_validation.py` LAYER_RULES (lines 72-80) already covers memory + infra (7 layers) but also misses shared
- **Fix**:
  - Add `FORBIDDEN_IMPORTS[memory]`, `FORBIDDEN_IMPORTS[infra]`, `FORBIDDEN_IMPORTS[shared]` to bash script
  - Add `"shared"` key to `check_cross_validation.py` LAYER_RULES
  - Define shared's forbidden imports: `{"src.brain", "src.gateway", "src.knowledge", "src.memory"}` (shared is utility-only, should not import business layers)
  - Update both for-loops to include all 8 layers

### A2. Fix `full_audit.sh` — phase passthrough bug

- **File**: `scripts/full_audit.sh`
- **Current state**: Line 33 correctly parses `--phase N` into `$PHASE` variable. Line 193 correctly passes `$PHASE` into the report JSON. But line 161 calls `verify_phase.py --current --json`, **ignoring `$PHASE` entirely**.
- **Impact**: Running `bash full_audit.sh --phase 2` still verifies whatever `current_phase` is in `milestone-matrix.yaml` (currently `phase_3`), not Phase 2.
- **Fix**: Line 161 -> `uv run python scripts/verify_phase.py --phase $PHASE --json 2>&1`

### A3. Upgrade Phase 0 gates from existence-only to content-structural

- **File**: `delivery/milestone-matrix.yaml` (lines 74-127)
- **Current state**: 12 exit_criteria (10 hard + 2 soft). Breakdown:
  - `test -f` only (5): p0-backend-skeleton, p0-frontend-skeleton, p0-env-template, p0-schema-validation, p0-hooks
  - `grep` existence (2): p0-makefile, p0-gitignore
  - Python execution (2): p0-toolchain (doctor.py), p0-milestone-matrix (yaml.safe_load)
  - `wc -l` (1): p0-claude-md
  - `test -x` (1): p0-guards
  - `test -f` in soft (1): p0-adr-index
- **Fix**: Replace existence-only checks with **content-structural** checks:
  - `p0-backend-skeleton`: `uv run python -c "import tomllib; d=tomllib.load(open('pyproject.toml','rb')); assert 'project' in d and 'name' in d['project']"`
  - `p0-env-template`: `python3 -c "lines=[l.strip() for l in open('.env.example') if l.strip() and not l.startswith('#')]; assert len(lines) >= 5, f'only {len(lines)} env vars defined'"`
  - `p0-schema-validation`: `test -f docs/governance/task-card-schema-v1.0.md && uv run python scripts/check_task_schema.py --mode warning --json | python3 -c "import sys,json; d=json.load(sys.stdin); sys.exit(0 if d.get('status')!='error' else 1)"`
  - `p0-adr-index`: `test -f docs/adr/README.md && python3 -c "content=open('docs/adr/README.md').read(); assert 'ADR-' in content, 'no ADR references in index'"`
  - Principle: JSON -> key set check; YAML -> required field check; scripts -> executable + import check. **Never use line count as semantic proxy.**

### A4. Audit coverage gate scope alignment (PARTIAL)

- **File**: `.github/workflows/ci.yml`
- **Current state**: CI already enforces `--cov-fail-under=80` (lines 140-141). This is correctly in place.
- **Actual gap**: Coverage gate only counts `tests/unit/` (line 139: `uv run pytest tests/unit/`), while some task card ACs require integration-level evidence. The coverage number measures unit test breadth, not verification depth.
- **Fix (3 parts)**:
  - [x] **(A4a) Done**: Add coverage scope annotation comment in CI to clarify "unit-only coverage"
  - [ ] **(A4b) Deferred to Phase D**: Create evidence mapping — which ACs need integration/E2E coverage vs. unit-only. This depends on `check_evidence_grade.py` (D2).
  - [ ] **(A4c) Deferred to Phase D**: Connect coverage results to evidence grading framework — coverage grade = "C" (unit-tested) for gate criteria that only have unit tests

---

## 4. Phase B: Promise Traceability

### B1. New script: `scripts/check_promise_registry.py`

- **Purpose**: Build and verify the **Architecture Promise -> Phase -> Task Card -> AC -> Gate -> Evidence -> Owner** chain
- **Inputs**: Architecture docs (`docs/architecture/0*.md`), delivery map (`docs/governance/architecture-phase-delivery-map.md`), task cards (`docs/task-cards/`), milestone-matrix.yaml
- **Logic**:
  1. Parse architecture docs for promises: Section headers with "Phase N" markers, "LAW"/"RULE" markers, ADR references, DDL definitions, API endpoint definitions
  2. Cross-reference with delivery map Table 2 entries (task card ID linkage)
  3. Cross-reference with actual task card files for AC existence
  4. Verify each promise has at least one gate check in milestone-matrix.yaml
  5. Report: unmapped promises, orphaned task cards (no architecture source), phase mismatches
- **Output**: JSON `{promise_id, source_doc, source_section, mapped_task_cards[], mapped_gates[], coverage_grade}`
- **Validation fixture**: At baseline commit `15c6fd8`, must detect at least the sample set of known unmapped promises (BookmarkPort, Task Orchestration, AssemblyProfile, Epistemic Tagging, legal_profiles DDL, etc.)
- **Est. size**: ~400 lines

### B2. New script: `scripts/check_adr_consistency.py`

- **Purpose**: Verify each ADR has implementation evidence + gate linkage
- **Inputs**: `docs/architecture/08-附录.md` (ADR-001~052), `docs/adr/ADR-053-*.md`, task cards, test files, gate checks
- **Logic**:
  1. Parse all 53 ADR entries from source docs
  2. For each ADR: search for references in task cards, gate checks, test files
  3. Flag: orphaned ADRs (040/041 — exist only in `docs/reviews/memory-system-upgrade-review.md`, not in `08-附录.md`), deprecated without supersession chain, zero-reference ADRs
  4. Cross-check ADR decisions against code patterns (e.g., ADR-052 says "no ETag" -> grep for ETag usage; ADR-018 says "Knowledge never reads MemoryCore" -> import check)
- **Output**: JSON `{adr_id, status, defined_in, task_card_refs[], gate_refs[], test_refs[], code_violations[]}`
- **Validation fixture**: At baseline commit, must flag ADR-040/041 as orphaned; ADR-005 through ADR-016 as zero-gate-coverage
- **Est. size**: ~350 lines

### B3. Expand `check_cross_validation.py` DESIGN_CLAIMS to 25+

- **File**: `scripts/check_cross_validation.py` (lines 89-149)
- **Current**: 8 Design Claims (DC-1 ~ DC-8)
- **Add DC-9 through DC-25+**, covering:
  - DC-9: Privacy hard boundary (Knowledge never imports src.memory) — ADR-018
  - DC-10: Epistemic Tagging (epistemic_type column + pipeline) — Brain §3.1.0.2
  - DC-11: Experiment Engine (experiments + experiment_assignments DDL) — Infra §5
  - DC-12: Media Security FSM (6-state: pending/scanning/safe/rejected/quarantined/expired) — ADR-051
  - DC-13: Unified Event Model (decision_event/deletion_event/degrade_event) — Infra §6.3
  - DC-14: Legal Profiles (legal_profiles table + GDPR/PIPL/DEFAULT rows) — Infra §9
  - DC-15: BYOM endpoint registration (vLLM/Ollama) — Gateway §5.6
  - DC-16: WS close codes as LAW (4001/4002/4003/1000) — Gateway §7.1
  - DC-17: Skill lifecycle FSM (draft/active/deprecated/disabled) — Skill §(Governance)
  - DC-18: ToolCall schema v1 + SkillResult schema v1 — Skill §2
  - DC-19: Three-layer version separation (DB/WS/event) — ADR-050
  - DC-20: Checksum spec (SHA-256, not ETag) — ADR-052
  - DC-21: Event outbox idempotency_key UNIQUE constraint — Infra §6.2
  - DC-22: Deletion pipeline 8-state FSM — ADR-039
  - DC-23: Context budget allocator — ADR-035
  - DC-24: Memory Quality 7 SLIs — ADR-038
  - DC-25: Dual-domain media storage (personal + enterprise) — ADR-044
- Each claim includes: `id`, `claim`, `source`, `risk`, `verification_pattern`

---

## 5. Phase C: Gate Capability Upgrades

### C1. New script: `scripts/check_frontend_depth.py`

- **Purpose**: L2-L4 depth audit for frontend task cards (currently at L1-only across the board)
- **Background**: Of 50 active frontend task cards, the V3.1 audit covered 8 (16%), all at L1 (file/directory existence + grep). Zero `.tsx`/`.ts` files were read during audit. At least 1 confirmed false negative (DOMPurify marked unverified but IS implemented in `frontend/apps/web/lib/sanitize.ts`).
- **Inputs**: `docs/task-cards/frontend/` (8 files, 50 task cards), `frontend/` source tree
- **Logic**:
  1. Parse all frontend task card ACs
  2. For each AC: locate corresponding source file via path conventions + grep
  3. Grade depth: L1 (file exists) -> L2 (exports/components match AC) -> L3 (logic verified via AST patterns) -> L4 (test file exists + covers AC)
  4. Security checks: DOMPurify usage on user content, auth consistency (sessionStorage vs AuthProvider context), stub detection (`// Placeholder`, `// TODO`), XSS surfaces (unescaped error messages)
- **Output**: Per-task-card depth grade + specific findings
- **Validation fixture**: Must detect the chat page upload stub (`handleUpload` returning `crypto.randomUUID()`) and the auth token key inconsistency (`"admin_token"` vs `"token"`)
- **Est. size**: ~500 lines

### C2. New script: `scripts/check_reverse_audit.py`

- **Purpose**: Code -> Design reverse direction audit (detect shadow features + drift)
- **Background**: Standard audit direction is Design -> Code. Missing: Code artifacts that have no architecture backing (shadow features) or diverge from spec (drift).
- **Inputs**: `src/` Python files, `docs/architecture/` docs, `docs/task-cards/`
- **Logic**:
  1. AST-scan all `src/` Python files for: class definitions, FastAPI `@router` decorators, Port ABC implementations, Alembic migration operations, SQLAlchemy model classes
  2. For each discovered artifact: search for corresponding architecture doc reference + task card reference
  3. Classify: `mapped` (both found), `shadow` (code exists, no architecture), `drift` (code diverges from spec), `dead` (architecture reference, no implementation)
- **Known shadows at baseline**: `src/brain/skill/orchestrator.py` (no architecture backing), `src/knowledge/api/write_adapter.py` (drift code), `src/shared/rls_tables.py`, `src/shared/trace_context.py`
- **Output**: JSON `{file, artifact_type, architecture_ref, task_card_ref, status}`
- **Validation fixture**: Must detect the known shadow set at baseline commit
- **Est. size**: ~400 lines

### C3. New script: `scripts/check_xnode_deep.py`

- **Purpose**: Deep verification of DONE X-nodes (many marked done but never deep-verified beyond exit code)
- **Inputs**: `delivery/milestone-matrix.yaml` (X-node definitions), task cards, evidence directory
- **Logic**:
  1. Parse all X-nodes (crosscutting verification nodes) from milestone-matrix
  2. For each DONE node: **actually execute** exit_criteria command and verify pass
  3. For each DONE node: check evidence artifact exists, is non-empty, and is newer than last relevant code change
  4. Flag: vacuous passes (test -f on empty file), stale evidence (artifact timestamp < code mtime), commands that pass trivially
- **Output**: JSON per-node `{node_id, status, exit_criteria_result, evidence_path, evidence_age, verdict}`
- **Est. size**: ~300 lines

### C4. Expand `check_cross_validation.py` with 3 new check categories

- **File**: `scripts/check_cross_validation.py`
- **Current**: 5 categories (Gate Coverage, Acceptance Execution, Gate-vs-Acceptance Consistency, Architecture Boundary AST, Design Claims)
- **Add**:
  - **Category 6: Call Graph Verification** — Verify Port implementations are called through Port interfaces in Brain/Knowledge/Skill, not via direct import of infra modules. Uses AST to trace import chains.
  - **Category 7: Stub Detection** — AST scan production code (`src/`) for `pass` bodies, `raise NotImplementedError`, `# TODO`, `# Placeholder`, `# FIXME` in non-test files. Each stub must be linked to a task card or flagged as tech debt.
  - **Category 8: LLM Call Verification** — Verify all LLM API calls go through `LLMCallPort`, not direct `httpx`/`openai`/`litellm`/`anthropic` imports in Brain/Knowledge/Skill layers.

---

## 6. Phase D: Evidence & Contract Framework

### D1. New script: `scripts/check_contract_alignment.py`

- **Purpose**: 6-type contract consistency verification
- **Contract types**:
  1. **Port interfaces**: Python ABC method signatures -> implementation method signatures (parameter names, types, return types)
  2. **API contracts**: FastAPI route response_model schemas -> frontend API client TypeScript interfaces
  3. **Event schemas**: `event_outbox` payload structures -> consumer handler expectations
  4. **DDL schemas**: Alembic migration final state -> SQLAlchemy model definitions -> architecture DDL specs in docs
  5. **ACL rules**: RLS policy definitions -> Gateway permission middleware -> frontend PermissionGate component props
  6. **Frontend-Backend payloads**: Backend Pydantic response schemas -> Frontend TypeScript fetch call type assertions
- **Logic**: For each contract type, parse both sides and produce a structured diff
- **Output**: `{contract_type, source_a, source_b, status: aligned|drifted|missing, diff_details}`
- **Est. size**: ~600 lines

### D2. New script: `scripts/check_evidence_grade.py`

- **Purpose**: Grade evidence quality for every gate check using A-F taxonomy
- **Grading scale**:
  - **A**: Runtime-verified (integration test with real DB + actual HTTP calls, or E2E test)
  - **B**: Integration-tested (docker-compose + pytest with real services)
  - **C**: Unit-tested (isolated pytest with mocks/fixtures)
  - **D**: Static-verified (AST/grep/file-existence/`test -f` check only)
  - **F**: No evidence (gate exists in milestone-matrix but no corresponding test or check)
- **Inputs**: `delivery/milestone-matrix.yaml` exit_criteria, `tests/` directory, CI job definitions
- **Logic**: For each exit_criteria command, classify its evidence grade by analyzing what it actually executes (parses command structure, checks if it runs pytest, checks test markers for integration vs unit, etc.)
- **Connection to A4**: Coverage results from `--cov-fail-under=80` feed into this grading — a gate check backed only by unit tests gets grade C even if coverage is 100%.
- **Output**: Distribution histogram + per-gate grade + upgrade recommendations
- **Est. size**: ~350 lines

### D3. New script: `scripts/check_temporal_integrity.py`

- **Purpose**: Migration chain + rollback + idempotency verification
- **Checks**:
  1. **Migration chain integrity**: Alembic versions have no gaps, no orphaned heads, linear chain
  2. **Rollback coverage**: Every `upgrade()` has a corresponding non-empty `downgrade()` implementation (not just `pass`)
  3. **Idempotency check**: Migration up-down-up cycle produces identical schema (requires DB, can be --skip-db for static analysis only)
  4. **Schema version monotonicity**: `content_schema_version` and `payload_version` fields only increment, never decrement
- **Red line alignment**: "NO migrations without rollback plan" (CLAUDE.md)
- **Est. size**: ~300 lines

### D4. Update `full_audit.sh` to 14 categories

- **File**: `scripts/full_audit.sh`
- **Current**: 9 categories (lines 1-13)
- **Add categories 10-14**:
  - 10: Promise Registry (`check_promise_registry.py`)
  - 11: ADR Consistency (`check_adr_consistency.py`)
  - 12: Contract Alignment (`check_contract_alignment.py`)
  - 13: Evidence Grading (`check_evidence_grade.py`)
  - 14: Temporal Integrity (`check_temporal_integrity.py`)
- Frontend depth, reverse audit, X-node deep integrate into existing category 2 (skill audits) or run as part of cross-validation expansion

### D5. Update Makefile + CI integration

- **Makefile**: Add targets for each new script:
  - `check-promises`, `check-adr`, `check-contracts`, `check-evidence-grade`, `check-temporal`
  - `check-frontend-depth`, `check-reverse-audit`, `check-xnode-deep`
- **CI**: Promote `cross-validation` job from informational to **L2 blocking** gate (it currently runs but does not block merge)
- Update weekly full-audit cron to include all 14 categories

---

## 7. Execution Order & Checkpoints

```
Phase A (fix guard bugs)
  -> checkpoint: make lint && make test && make verify-phase-current
Phase B (promise tracing)
  -> checkpoint: make cross-validate shows new claims detected
Phase C (depth upgrades)
  -> checkpoint: make check-frontend-depth + check-reverse-audit produce non-empty results
Phase D (evidence framework)
  -> checkpoint: make full-audit runs 14 categories without error
```

Each phase is independently deployable and adds value incrementally.

---

## 8. Deliverables Summary

| Phase | New Scripts | Modified Files | Est. Lines |
|-------|-----------|---------------|-----------|
| A | 0 | 4 (`check_layer_deps.sh`, `full_audit.sh`, `milestone-matrix.yaml`, `ci.yml`) | ~100 |
| B | 2 (`check_promise_registry.py`, `check_adr_consistency.py`) | 1 (`check_cross_validation.py`) | ~850 |
| C | 3 (`check_frontend_depth.py`, `check_reverse_audit.py`, `check_xnode_deep.py`) | 1 (`check_cross_validation.py`) | ~1300 |
| D | 3 (`check_contract_alignment.py`, `check_evidence_grade.py`, `check_temporal_integrity.py`) | 3 (`full_audit.sh`, `Makefile`, `ci.yml`) | ~1350 |
| **Total** | **8 new scripts** | **8 modified files** | **~3600 lines** |

Each new script requires a corresponding test file in `tests/unit/scripts/`.

---

## 9. Success Criteria

All criteria use **validation fixtures** (known sample sets) rather than hard-coded counts that drift with code changes.

- [ ] All existing `make lint && make test` pass after each phase
- [ ] `check_promise_registry.py`: detects the known-unmapped fixture set (BookmarkPort, Task Orchestration, AssemblyProfile, Epistemic Tagging, legal_profiles DDL — verified against baseline commit `15c6fd8`)
- [ ] `check_adr_consistency.py`: flags ADR-040/041 as orphaned; flags ADR-005~016 as zero-gate-coverage
- [ ] `check_frontend_depth.py`: detects the DOMPurify false negative correction + chat upload stub + auth token key inconsistency
- [ ] `check_reverse_audit.py`: detects the known shadow feature fixture set (orchestrator.py, write_adapter.py, rls_tables.py, trace_context.py)
- [ ] `check_contract_alignment.py`: covers all 6 contract types with at least 1 test case each
- [ ] `check_evidence_grade.py`: classifies 100% of milestone-matrix exit_criteria into A-F grades
- [ ] `check_temporal_integrity.py`: verifies migration chain has zero gaps + all downgrade() are non-pass
- [ ] `full_audit.sh` runs all 14 categories end-to-end
- [ ] CI `cross-validation` job promoted to L2 blocking gate

---

## 10. Relationship to Existing Documents

| Document | Relationship |
|----------|-------------|
| `docs/governance/audit-gap-report-v2.md` | **Input**: Findings and INF items drive this plan |
| `docs/governance/architecture-phase-delivery-map.md` | **Input**: Promise mapping baseline |
| `delivery/milestone-matrix.yaml` | **Modified by**: Phase A (gate upgrades), Phase D (new categories) |
| `docs/governance/execution-plan-v1.0.md` | **Sibling**: That covers feature delivery; this covers guardian infrastructure |

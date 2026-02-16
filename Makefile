.PHONY: bootstrap doctor lint test test-smoke test-isolation verify-phase-% \
       scaffold-phase-0 scaffold-adr audit-report audit-artifacts audit-e2e \
       full-audit skills-validate skills-smoke check-acceptance-commands \
       replay-skill-session clean help

PYTHON := python3
SCRIPTS := scripts

# ============================================================
# Lifecycle Commands (Golden Path)
# ============================================================

bootstrap: ## Install toolchain + dependencies + verify
	@echo "=== DIYU Agent Bootstrap ==="
	@command -v python3.12 >/dev/null 2>&1 || (echo "NEED: Python 3.12+"; exit 1)
	@command -v uv >/dev/null 2>&1          || (echo "NEED: uv (https://docs.astral.sh/uv/)"; exit 1)
	@command -v node >/dev/null 2>&1        || (echo "NEED: Node.js 22 LTS"; exit 1)
	@command -v pnpm >/dev/null 2>&1        || (echo "NEED: pnpm (https://pnpm.io/)"; exit 1)
	uv sync --dev
	cd frontend && pnpm install
	cp -n .env.example .env 2>/dev/null || true
	@$(MAKE) doctor

doctor: ## Diagnose dev environment health
	@$(PYTHON) $(SCRIPTS)/doctor.py

# ============================================================
# Quality Gates
# ============================================================

lint: ## Run all linters
	uv run ruff check src/ tests/ scripts/
	uv run ruff format --check src/ tests/ scripts/
	cd frontend && pnpm run lint

test: ## Run unit tests
	uv run pytest tests/unit/ -v --tb=short
	cd frontend && pnpm run test

test-smoke: ## Fast smoke test subset
	uv run pytest tests/ -m smoke -v --tb=short

test-isolation: ## RLS isolation tests (needs DB)
	uv run pytest tests/isolation/ -v --tb=short || test $$? -eq 5

test-coverage: ## Run tests with coverage report
	uv run pytest tests/unit/ --cov=src --cov-report=term-missing --cov-fail-under=80

# ============================================================
# Phase Verification
# ============================================================

verify-phase-%: ## Verify phase gate (e.g., make verify-phase-0)
	@$(PYTHON) $(SCRIPTS)/verify_phase.py --phase $* --json

verify-phase-current: ## Verify current phase from milestone-matrix.yaml
	@$(PYTHON) $(SCRIPTS)/verify_phase.py --current --json

verify-phase-%-archive: ## Verify phase + archive to evidence/ (e.g., make verify-phase-0-archive)
	@$(PYTHON) $(SCRIPTS)/verify_phase.py --phase $* --json --archive

scaffold-phase-0: ## Generate Phase 0 directory structure and skeleton files
	@$(PYTHON) $(SCRIPTS)/scaffold_phase0.py

scaffold-adr: ## Create new ADR from template (TITLE="decision title")
	@$(PYTHON) $(SCRIPTS)/scaffold_adr.py "$(TITLE)"

# ============================================================
# Guard Scripts
# ============================================================

check-layer-deps: ## Check layer dependency violations
	@bash $(SCRIPTS)/check_layer_deps.sh

check-port-compat: ## Check Port contract compatibility
	@bash $(SCRIPTS)/check_port_compat.sh

check-migration: ## Check migration safety
	@bash $(SCRIPTS)/check_migration.sh

check-rls: ## Check RLS isolation
	@bash $(SCRIPTS)/check_rls.sh

check-impact: ## Route change impact (reviewer + CI gates)
	@bash $(SCRIPTS)/change_impact_router.sh

risk-score: ## Calculate risk score for current changes
	@bash $(SCRIPTS)/risk_scorer.sh

# ============================================================
# Schema Validation
# ============================================================

check-acceptance: ## Validate acceptance commands (hard gate)
	@$(PYTHON) $(SCRIPTS)/check_acceptance_gate.py --json

check-acceptance-commands: ## Check [E2E] acceptance command quality (milestone-check mirror)
	@bash $(SCRIPTS)/check_acceptance_commands.sh

check-schema: ## Validate task card schema
	@$(PYTHON) $(SCRIPTS)/check_task_schema.py --mode warning

check-schema-full: ## Full task card schema validation
	@$(PYTHON) $(SCRIPTS)/check_task_schema.py --mode full --json

count-cards: ## Count and analyze task cards
	@$(PYTHON) $(SCRIPTS)/count_task_cards.py --json

# ============================================================
# Audit
# ============================================================

audit-report: ## Generate audit aggregation report
	@$(PYTHON) $(SCRIPTS)/audit_aggregator.py .audit/

audit-artifacts: ## Validate audit evidence artifacts against schemas
	uv run python $(SCRIPTS)/validate_audit_artifacts.py

audit-e2e: ## End-to-end: generate all audit artifacts + validate
	bash $(SCRIPTS)/run_systematic_review.sh
	bash $(SCRIPTS)/run_cross_audit.sh
	bash $(SCRIPTS)/run_fix_verify.sh
	uv run python $(SCRIPTS)/validate_audit_artifacts.py

full-audit: ## Run unified full audit (Section 12.6)
	@bash $(SCRIPTS)/full_audit.sh

# ============================================================
# Skills Governance
# ============================================================

skills-validate: ## Validate all skills governance requirements
	@$(PYTHON) $(SCRIPTS)/skills/validate_skills_governance.py

skills-smoke: ## Run skills governance test suite
	uv run pytest tests/unit/scripts/test_skills_governance_requirements.py \
		tests/unit/scripts/test_skills_best_practices.py \
		tests/unit/scripts/test_taskcard_workflow_handoff.py -v --tb=short

replay-skill-session: ## Replay latest skill session log (or FILE=path for specific)
	@$(PYTHON) $(SCRIPTS)/skills/replay_skill_session.py $(if $(FILE),--file $(FILE),--latest)

# ============================================================
# Utilities
# ============================================================

clean: ## Clean build artifacts
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf .coverage htmlcov/
	cd frontend && pnpm run clean 2>/dev/null || true

help: ## Show this help
	@grep -E '^[a-zA-Z0-9_%-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-24s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help

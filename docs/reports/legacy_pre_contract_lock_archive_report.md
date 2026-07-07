# Legacy Pre-Contract-Lock Archive Report

- task_id: GKB-WORKSPACE-LEGACY-ARCHIVE-001
- generated_at: 2026-07-06T21:21:42.456545-07:00
- archive_root: `/home/diyu/笛语领域通用数据库/archive/legacy_pre_contract_lock/2026-07-07`
- candidate_roots_archived: 18
- files_archived: 107
- files_deleted: 0
- canonical_inputs_touched: false
- project_infra_touched: false
- readiness_flags_changed: false
- legacy_archive_is_not_active_authority: true

## Archived Roots

- `knowledge_intake`: legacy GPT 5.5 intake workspace; superseded by canonical stage directories and contract-lock route
- `tools/gkb_intake`: legacy GPT 5.5 intake local tools; superseded by future contract-lock checkers
- `fixtures/gkb_intake`: legacy GPT 5.5 intake fixtures; not active contract-lock fixtures
- `ci/checkers/README_gkb_intake.md`: legacy intake checker documentation; not active contract-lock checker
- `ci/checkers/check_capability_routing_composability.py`: legacy intake checker; not active contract-lock checker
- `ci/checkers/check_declared_semantics_alignment.py`: legacy intake checker; not active contract-lock checker
- `ci/checkers/check_gold_hooks_as_release_input.py`: legacy intake checker; not active contract-lock checker
- `ci/checkers/check_hard_claim_and_brand_fact_leak.py`: legacy intake checker; not active contract-lock checker
- `ci/checkers/check_no_readiness_leak.py`: legacy intake checker; not active contract-lock checker
- `ci/checkers/check_rich_body_structure_consistency.py`: legacy intake checker; not active contract-lock checker
- `ci/checkers/check_semantic_fingerprint_dedupe.py`: legacy intake checker; not active contract-lock checker
- `ci/checkers/check_serving_spec_no_passage_text.py`: legacy intake checker; not active contract-lock checker
- `ci/checkers/check_source_anchor_coverage.py`: legacy intake checker; not active contract-lock checker
- `ci/checkers/gkb_intake_common.py`: legacy intake checker helper; not active contract-lock checker
- `tools.txt`: legacy local tool note from old workspace
- `落盘总方案.txt`: legacy implementation note from old workspace
- `SKILL/diyu-gkb-draft-intake.md`: legacy skill mirror retained as archived reference only
- `.agents/skills/diyu-gkb-draft-intake`: legacy active skill package retired from workspace skill discovery

## Notes For Next Task

- Future contract-lock checks should treat `archive/legacy_pre_contract_lock/**` as archived legacy evidence, not active status authority.
- Active canonical inputs remain under `00_source_inputs/**`.
- Active workspace status remains `project-infra/current_workspace_status.yaml`.
- `ci/checkers/.gitkeep` preserves the future checker write surface after legacy checker retirement.

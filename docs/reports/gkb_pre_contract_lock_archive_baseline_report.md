# GKB Pre-Contract-Lock Archive Baseline Report

- task_id: GKB-PRE-CONTRACT-LOCK-ARCHIVE-BASELINE-001
- generated_at: 2026-07-06T21:32:19.450541-07:00
- repository: `/home/diyu/笛语领域通用数据库`
- branch: master
- commit_before: 90dc9ae7e28c3443702885e953edec88b6da9e78
- commit_after: pending_until_git_commit; see final delivery and tmp receipt after commit
- worktree_before: dirty_only_from_controlled_archive_and_execution_prompt
- source_repo_reference_HEAD: d56e62abb7cbe831c8e67656746ee76397dd1042
- source_repo_reference_status: clean
- files_moved_to_archive: 107
- files_deleted: 0
- execution_prompt_versioned: true
- current_workspace_status_updated: true
- readiness_flags_all_false: true
- active_source_inputs_verified: true
- forbidden_scope_touched: false
- external_resources_touched: false
- self_verdict: PRECOMMIT_PASS_READY_TO_STAGE_AND_COMMIT

## Archive

- archive_root: `archive/legacy_pre_contract_lock/2026-07-07`
- archive_manifest: `archive/legacy_archive_manifest.yaml`
- archive_report: `docs/reports/legacy_pre_contract_lock_archive_report.md`
- archived_file_count: 107

## Status Manifest

- Added `pre_contract_lock_archive_baseline.status: completed`.
- Preserved `phase.current_next_step: CODEX-KNOWLEDGE-GENERATION-CONTRACT-LOCK-001`.
- Preserved all readiness / generation / production flags as false.

## Checks

- `git status --short`
- `git rev-parse --abbrev-ref HEAD`
- `git rev-parse HEAD`
- `git -C /home/faye/笛语agent status --short`
- `git -C /home/faye/笛语agent rev-parse --abbrev-ref HEAD`
- `git -C /home/faye/笛语agent rev-parse HEAD`
- `test -f archive/legacy_archive_manifest.yaml`
- `test -f docs/reports/legacy_pre_contract_lock_archive_report.md`
- `test -f 01_generation_contracts/CODEX-KNOWLEDGE-GENERATION-CONTRACT-LOCK-001.execution_prompt.md`
- `test -d archive/legacy_pre_contract_lock/2026-07-07`
- `test -d 00_source_inputs/W7_master_map`
- `test -d 00_source_inputs/founder_overlay`
- `test -d 00_source_inputs/generation_assignments`
- `test -d 00_source_inputs/source_gap_seeds`
- `test -d 00_source_inputs/unresolved_decisions`
- `python3 YAML parse check`
- `python3 readiness false scan`
- `python3 dirty scope manifest reconciliation`

## Notes

- The repository copy of this report is committed in the same baseline commit, so the final commit hash is recorded in the final delivery and post-commit `/tmp/codex-ipc` receipt.
- `archive/legacy_pre_contract_lock/**` is archived legacy evidence, not active status authority.

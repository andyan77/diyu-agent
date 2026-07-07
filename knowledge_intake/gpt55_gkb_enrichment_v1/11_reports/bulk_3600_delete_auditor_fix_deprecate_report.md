# GKB-INTAKE-BULK-3600-DELETE-AUDITOR-FIX-DEPRECATE-001 · Delivery Report

> Founder verdict: **C_bulk_run_not_usable**. This package deleted the bulk 3600 payload,
> fixed the auditor rich_body_blocks nesting bug, and deprecated the one-shot bulk route.
> No knowledge generated, no source binding, no CandidatePack/KE/Serving/RAG/DIFY, no readiness flipped.

## 0. Run metadata

| field | value |
|---|---|
| task_id | GKB-INTAKE-BULK-3600-DELETE-AUDITOR-FIX-DEPRECATE-001 |
| workspace | /home/diyu/笛语领域通用数据库 |
| git_repo | false (non-git manifest sha256 mode) |
| python | 3.10.12 |

## 1. Actions completed (all 3 objectives)

- ✅ **O1 bulk_generated_payload_deleted**
- ✅ **O2 auditor_body_nesting_bug_fixed**
- ✅ **O3 bulk_generation_route_deprecated**

## 2. Deleted summary

| phase | count | size | manifest |
|---|---|---|---|
| Step 2 (allowlist) | 36 deleted, 1 already_absent | 34,460,194 B (32.9 MB) | `12_ledger/bulk_generation_deleted_manifest.yaml` |
| Step 3 (generator) | 1 deleted (`tools/gkb_intake/generate_gpt55_drafts.py`) | 25,423 B | `12_ledger/bulk_generator_delete_ledger.yaml` |
| Cleanup (founder-authorized "删除干净") | 18 files (2 matrices + 14-file `knowledge_candidate_cards_by_batch/` + 2 empty outbox stubs) | 10,370,446 B (9.9 MB) | `12_ledger/bulk_generation_deleted_manifest_supplement.yaml` |
| **workspace total** | **189 → 141 files** | **45.1 MB → 0.3 MB (~44.8 MB freed)** | before/after manifests in `11_reports/` |

- `already_absent` (1): `stratified_review_sample.md` (never generated in the prior audit) — recorded, not a failure.
- All deleted files' sha256 + size recorded **before** unlink (manifest-first).
- Post-cleanup, `04_aligned_candidates/` and `08_outbox/` contain only `.gitkeep` (clean scaffold placeholder).

### Cleanup authorization (transparency)
The scaffold validator flagged 5 leftover bulk-derived content items **not enumerated in the Step 2 allowlist**. When I stopped and reported (per the brief's own `validate_batch` STOP condition), the founder replied **"删除干净，无需另外授权"** — authorizing completion of the clean deletion of those bulk artifacts, while **declining** the separate scaffold-reset authorization. All 5 were verified bulk-3600-derived (keyed by `GKB-BATCH-*` ids) before deletion.

## 3. Auditor fix

| field | value |
|---|---|
| file | `tools/gkb_intake/audit_gkb_3600_content_snapshot.py` |
| get_rich_block_present | true (module-level helper; nested-first, top-level fallback) |
| read sites migrated | body-block profile loop + stratified sample (3 body columns) — no `b.get(<block>)` remains |
| selftest added | `--selftest` flag + module-level `selftest()` |
| nested_reader_selftest | **PASS** (external importlib selftest + built-in `--selftest`) |
| nested_fixture_created | true (positive: all 10 blocks non-empty; negative: ≥3 blocks missing) |
| boundary/readiness rules | **unchanged** — no relaxation of any boundary / readiness / candidatepack / forbidden-path check; no quality-fail flipped to pass; no external dependency added |

Fixtures: `fixtures/gkb_intake/positive/rich_body_nested_shape.yaml`, `fixtures/gkb_intake/negative/rich_body_missing_nested_blocks.yaml`.

## 4. Deprecation

- bulk_generator_deleted: **true** (`tools/gkb_intake/generate_gpt55_drafts.py` removed)
- deprecation_ledger_written: **true** (`12_ledger/bulk_generation_deprecation_ledger.yaml`)
- deprecated routes: one_shot_3600_generation, bulk_generator_without_micro_batch_review, posthoc_source_binding_for_gpt_bulk
- allowed future: source/prompt-bounded micro-batch, ≤20–40 raw candidates/run, content-quality snapshot before scale
- forbidden future: direct_3600_generation, bulk_source_binding, bulk_candidatepack_eligibility, bulk KE/Serving/RAG/DIFY landing

## 5. Checks run

| check | verdict | note |
|---|---|---|
| AST parse (5 tools) | **PASS** | audit / run_gates / run_batch / validate_batch / audit_pilot_readiness |
| run_gates `--selftest` | **PASS** | 9/9 checkers green (readiness-leak, source-anchor, semantics-alignment, hard-claim/brand-fact-leak, rich-body-structure, fingerprint-dedupe, capability-routing, serving-no-passage-text, gold-hooks) |
| audit rich_body nested reader selftest | **PASS** | nested read + top-level fallback + fixture validation |
| audit_pilot_readiness | **rc=0** | `real_source_pack_content: unverified` — the brief-declared correct result, not a failure |
| bulk payload absence check | **PASS** | 5 core bulk files absent |
| forbidden path absence check | **PASS** | KE / serving_projection / rag / dify / candidatepack_instances / runtime all absent |
| **validate_batch `--scaffold-only --run-gates`** | **⚠️ FAIL (known, un-fixable within authorized scope)** | see §6 |

## 6. validate_batch known-FAIL — root cause & disposition (honest, not fake-green)

`validate_batch --scaffold-only --run-gates` returns `passed:false` (rc=1) with 3 remaining errors:

1. `required file missing: 07_fingerprints/semantic_fingerprint_registry.csv`
2. `required file missing: 07_fingerprints/semantic_fingerprint_delta.csv`
3. `manifest status must be scaffold_only in scaffold-only mode` (current: `gpt_generated_draft_generation_complete`)

**Why these remain, and why I did NOT force them green:**
- Errors 1–2: the two fingerprint CSVs were deleted by the brief's own Step 2. Recreating them as empty scaffold is **outside the allowed write scope** and was **not** part of the founder's cleanup authorization.
- Error 3: the manifest lives in `knowledge_intake/gpt55_gkb_enrichment_v1/00_contracts/gpt55_gkb_intake_manifest.yaml`, which is in the **section-5 forbidden-modify list**. Resetting it would breach a red line.
- Founder explicitly **declined** the scaffold-reset authorization ("无需另外授权"). Therefore validate_batch stays a **by-design known-FAIL**; forcing it to pass would require touching forbidden scope and would be fake-green.
- The earlier `warning: scaffold-only mode found candidate content files` was **cleared** by the founder-authorized cleanup (§2).

This is an internal tension in the brief (Step 2 deletion vs. Step 8 scaffold-pass expectation), surfaced and resolved by founder decision — recorded here rather than papered over.

## 7. Readiness flags (all false — none flipped)

```
candidatepack_ready: false   KE_ready: false          RAG_ready: false
DIFY_ready: false            production_servable: false generation_eligible: false
generation_allowed: false    release_ready: false      production_ready: false
```

## 8. Scope discipline (verified via before/after manifest diff)

| field | value |
|---|---|
| forbidden_scope_touched | **false** (manifest diff: 0 touches of 00_contracts / 01_source_packs / 02_batch_briefs / ci/checkers / AGENTS / .agents/skills / SKILL / tools.txt / 落盘总方案.txt / KE / serving_projection / rag / dify / candidatepack_instances / runtime / candidatepack_etl) |
| source_pack_modified | false |
| AGENTS_modified | false |
| Skill_modified | false |
| checker_modified | false (ci/checkers/*.py unchanged; only their report JSONs under `11_reports/gates/` were regenerated by the mandated `run_gates`, which is inside allowed write scope) |
| KE_RAG_DIFY_touched | false |
| created | 7 (all in `11_reports/` `12_ledger/` `fixtures/gkb_intake/`) + this report + receipt |
| changed | auditor (authorized fix) + 8 gate report JSONs in `11_reports/gates/` (allowed) |
| deleted | 55 (all in authorized delete scope) |

## 9. Allowed next actions

- design_new_micro_batch_generator_contract
- source_or_prompt_bounded_20_item_pilot
- audit_tool_regression_selftest

## 10. Note on delivery files

`bulk_3600_delete_auditor_fix_deprecate_report.md` and `bulk_3600_delete_auditor_fix_deprecate_receipt.json` are written **after** the Step 10 after-manifest (they are the final human/machine deliverables), both inside `11_reports/`.

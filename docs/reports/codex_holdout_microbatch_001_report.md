# Holdout Microbatch 001 Report

Task: `CODEX-SEMANTIC-PILOT-V4_7-PASS-CLOSEOUT-METADATA-CLEANUP-AND-HOLDOUT-MICROBATCH-001`

V4.7 was closed as `PASS_FOR_REPAIR_DIRECTION`, metadata cleanup was recorded as a patch, and a 14-item holdout validation microbatch was created from previously unsampled W7 clusters. This is pilot validation only. It does not write `04_microbatch_generation/**`, does not start `batch_001`, and does not unlock CandidatePack / KE / Serving / RAG / DIFY.

## Selected Clusters

mkc_002, mkc_003, mkc_005, mkc_007, mkc_012, mkc_013, mkc_020, mkc_021, mkc_022, mkc_024, mkc_028, mkc_030, mkc_033, mkc_036

Excluded previously sampled clusters: mkc_004, mkc_006, mkc_009, mkc_010, mkc_026, mkc_027, mkc_032, mkc_034

## Results

- holdout_count: 14
- selected_w7_cluster_count: 14
- body_compiler_family_count: 9
- candidate_card_count: 14
- knowledge_capsule_count: 14
- complete_rich_body_count: 14
- relation_design_hints_count: 28
- index_only_capsule_count: 0
- governance_dump_in_rich_body_count: 0
- real_instance_fact_leak_count: 0
- direct_publish_script_leak_count: 0
- accepted_domain_knowledge_count: 0
- batch_generation_unlocked: false
- ready_for_first_batch_generation: false
- V4_7_original_artifacts_modified: false

## Checks

- V4.7 checker live/selftest: PASS
- Holdout checker live/selftest: PASS
- `python -O` fail-closed: PASS, exit code 2
- Contract lock checker: PASS
- Old route-sync checker live/selftest set: PASS
- Parse checks: PASS
- Expanded readiness false scan: PASS

## Next Step

`CODEX-HOLDOUT-MICROBATCH-001-JUDGE-GO-NOGO-001`

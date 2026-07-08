# Proposition Pack v1 — Closeout (run canary_40_001)

task: GKB-CANARY-40-QUALITY-CLOSEOUT-AND-PROPOSITION-PACK-V1-001 (P5)
role: derived_review_asset (NOT formal knowledge, NOT CandidatePack-ready, NOT production)

## counts
- clusters: 40 (mkc_007..mkc_046), propositions/cluster: 4-4
- total propositions: 160
- owner_candidate distribution: {'GeneralKnowledgeBase': 60, 'EvidencePolicyOutbox': 42, 'GovernanceOutbox': 34, 'SourceGapLedger': 9, 'ExecutionAssetOutbox': 15}
- epistemic_class distribution: {'domain_method': 60, 'claim_boundary_policy': 42, 'governance_control_policy': 34, 'source_gap_candidate': 9, 'execution_asset_method': 15}
- proposition_type distribution: {'definition': 31, 'mechanism': 34, 'boundary_condition': 31, 'evidence_requirement': 20, 'downstream_effect': 4, 'execution_instruction': 11, 'failure_signal': 11, 'applicable_condition': 16, 'owner_split_hint': 2}

## source trace (Codex note 3)
- every proposition carries source_canary_id + source_rich_body_ref + source_text_span + start/end offsets
- ALL 160 source_text_span are EXACT substrings of their canary rich body (recompute-verified by the checker)
- quote-glyph normalization repairs applied at assembly: 1; owner/epistemic consistency normalizations: 0

## boundaries
- EvidencePolicyOutbox propositions never map to GeneralKnowledgeBase (violations: 0)
- relation hints remain design hints, ontology_edge_created: false
- readiness all false; accepted_domain_knowledge false; generation_3600_unlocked false
- external_resources / embedding / web_access / source_repo_live_dependency: all false

## nature
These propositions are a machine-consumable review asset derived from the 40 canary bodies,
for the P6 3600 microbatch briefing/go-no-go. They are NOT accepted domain knowledge and do
NOT unlock 3600 generation.

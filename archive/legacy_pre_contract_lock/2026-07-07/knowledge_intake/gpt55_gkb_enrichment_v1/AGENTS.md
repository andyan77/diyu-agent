# knowledge_intake/gpt55_gkb_enrichment_v1/AGENTS.md

## Required skill

Use the `diyu-gkb-draft-intake` skill for any task that generates, normalizes, reviews, or validates GPT 5.5 GeneralKnowledgeBase rich candidates.

## Workflow boundary

This workspace produces source-grounded rich draft candidates only.

It does not produce:

- CandidatePack instances
- KE landing
- Serving Projection
- approved_passage_text
- RAG context_bundle
- DIFY workflow
- production content
- generation output

## Batch model

- Do not generate the full 3600 in one run.
- Use management batches for domain planning.
- Use micro-batches for actual generation.
- Each micro-batch must have a batch lockfile.
- Each micro-batch target must stay within the Execution Brief.

## Required micro-batch passes

Every micro-batch must complete:

1. Batch Brief Lock
2. Source Binding
3. GPT55 Draft Generation
4. Rich Body Expansion
5. Declared Semantics Parse
6. Semantic Alignment Gate
7. Risk / Dedupe / Routing
8. Capability Routing Composability
9. CandidatePack Eligibility + Gold Hooks

## Required candidate fields

Every KnowledgeCandidateCard must include:

- candidate_id
- batch_id
- source_origin
- source_pack_refs or source_gap route
- target_domain_module
- target_module
- object_type
- one_sentence_definition
- operational_definition
- not_this
- applicable_when
- not_applicable_when
- input_context_required
- output_effect
- relations
- risk_boundary
- evidence_requirement
- claim_policy
- capability_group_refs
- capability_consumption_hint
- serving_projection_hint
- semantic_fingerprint
- duplicate_control
- readiness

## Required rich_body_blocks

Every rich body must include:

- concept_mechanism
- domain_logic
- content_generation_usage
- merchandising_or_retail_usage
- transformation_rules
- generic_micro_scenarios
- anti_patterns
- boundary_language
- retrieval_phrases
- capability_consumption_hint

## Hard reject

Reject the candidate if any of the following occurs:

- readiness true
- concrete brand fact in GeneralKB
- concrete product / SKU / store / city / person / campaign
- hard claim without evidence route
- missing semantic_fingerprint
- missing source anchor while claiming candidatepack eligibility
- generated Serving passage body
- generated RAG context_bundle
- generated DIFY output
- missing capability consumption hint
- duplicate fingerprint unresolved
- rich_body_blocks missing
- body overreaches card structure

## Required checkers

Before delivery, run or report why unavailable:

- check_no_readiness_leak.py
- check_source_anchor_coverage.py
- check_declared_semantics_alignment.py
- check_hard_claim_and_brand_fact_leak.py
- check_rich_body_structure_consistency.py
- check_semantic_fingerprint_dedupe.py
- check_capability_routing_composability.py
- check_serving_spec_no_passage_text.py
- check_gold_hooks_as_release_input.py

## Delivery report

Every delivery report must include:

- input source packs and excerpt digests
- generated count
- aligned count
- rejected count
- source_gap count
- decision_required count
- duplicate count
- readiness true count
- hard claim leak count
- brand fact leak count
- checker results
- changed files
- next safe action
# Intake Contract

## Workspace Role

`knowledge_intake/gpt55_gkb_enrichment_v1` is a source-grounded rich draft intake workspace.
It stores contracts, ledgers, candidate inputs, outbox candidates, specs, hooks, and validation reports.

It is not a truth-source workspace and must not write KE, Serving Projection, RAG, DIFY, CandidatePack
instances, or production generation artifacts.

## Candidate Contract

Every KnowledgeCandidateCard must carry:

- `candidate_id`
- `batch_id`
- `source_origin`
- `source_pack_refs`
- `source_trace`
- `target_owner`
- `target_domain_module`
- `target_module`
- `object_type`
- `one_sentence_definition`
- `operational_definition`
- `not_this`
- `applicable_when`
- `not_applicable_when`
- `input_context_required`
- `output_effect`
- `relations`
- `risk_boundary`
- `evidence_requirement`
- `claim_policy`
- `capability_group_refs`
- `capability_consumption_hint`
- `serving_projection_hint`
- `semantic_fingerprint`
- `duplicate_control`
- `readiness`

`source_pack_refs: []` is allowed only when `candidatepack_eligibility: false` and the item is routed to
`source_gap`.

## Rich Body Contract

Every rich body must include:

- `concept_mechanism`
- `domain_logic`
- `content_generation_usage`
- `merchandising_or_retail_usage`
- `transformation_rules`
- `generic_micro_scenarios`
- `anti_patterns`
- `boundary_language`
- `retrieval_phrases`
- `capability_consumption_hint`

Rich bodies must stay generic. They must not introduce concrete brands, products, stores, people, cities,
campaigns, customer feedback, hard claims, passage text, RAG context bundles, or DIFY outputs.

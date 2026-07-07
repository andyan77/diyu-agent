---
name: diyu-gkb-draft-intake
description: Use for generating, normalizing, reviewing, and validating source-grounded GPT 5.5 GeneralKnowledgeBase rich draft candidates for Diyu knowledge intake. Do not use for KE landing, Serving Projection, RAG context_bundle, DIFY workflow, or production generation.
---

## Purpose

Produce source-grounded rich draft candidates for Diyu GeneralKnowledgeBase intake.

This skill creates draft candidate artifacts only. It never lands KE, Serving, RAG, DIFY, production, or generation assets.

## Required inputs

- Execution Brief
- batch_manifest.yaml
- source_pack_refs or source_gap policy
- existing fingerprint registry
- allowed object_type values
- allowed P0 capability groups
- forbidden scope
- readiness policy

## Required workflow

1. Read the Execution Brief.
2. Verify allowed write files.
3. Read batch lockfile.
4. Read source pack ledger.
5. Generate only within batch scope.
6. Add rich_body_blocks.
7. Run declared semantics alignment.
8. Run risk / dedupe / routing checks.
9. Run capability routing composability checks.
10. Produce validation report.

## Candidate output rules

Every candidate must have one main proposition.

Do not generate:

- concrete brand facts
- concrete products or SKU
- concrete stores
- real persons
- city-specific claims
- customer feedback
- authorization facts
- full scripts
- templates
- serving passage text
- RAG context_bundle
- DIFY output

## Required output files

- knowledge_candidate_cards.yaml
- knowledge_candidate_rich_body_blocks.yaml
- relation_edge_candidates.csv
- fingerprint_registry_delta.csv
- review_queue.csv
- source_gap_candidates.yaml
- decision_packet_candidates.yaml
- batch_validation_report.json

## Definition of done

- YAML / CSV parse passes.
- Required fields present.
- readiness flags all false.
- No brand fact leakage.
- No hard claim leakage.
- No serving passage text.
- No RAG / DIFY artifact.
- Semantic fingerprints present.
- Capability consumption hints present.
- Batch validation report produced.
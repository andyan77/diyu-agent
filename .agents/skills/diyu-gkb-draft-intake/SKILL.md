---
name: diyu-gkb-draft-intake
description: Use for scaffold-only setup, generation planning, normalization, review, and validation of source-grounded GPT 5.5 GeneralKnowledgeBase rich draft candidates in the Diyu knowledge intake workspace. Use when working under knowledge_intake/gpt55_gkb_enrichment_v1, creating contracts, batch briefs, source-pack ledgers, checker scaffolds, rich candidate templates, or validation reports. Do not use for KE landing, Serving Projection materialization, RAG context_bundle, DIFY workflow, CandidatePack instances, production readiness, or generation output.
---

# Diyu GKB Draft Intake

## Purpose

Produce and validate source-grounded rich draft intake artifacts for Diyu GeneralKnowledgeBase work.

This skill creates draft candidate inputs, contracts, ledgers, checks, and reports only. It never lands KE,
Serving, RAG, DIFY, CandidatePack instances, production assets, or generation output.

## Required Order

1. Read the active Execution Brief.
2. Verify the allowed write surface before editing.
3. Verify protected paths are outside the write surface.
4. Read the batch lockfile before any micro-batch generation.
5. Bind every candidate to source_pack refs or route it to source_gap.
6. Keep all readiness, production, release, and generation flags false.
7. Run the checker suite or report why a checker is unavailable.
8. Deliver changed files, checks, failures, and readiness flags.

## Resource Routing

- Read `references/intake_contract.md` before creating or validating candidate-shaped artifacts.
- Read `references/nine_pass_method.md` before planning or running a micro-batch.
- Read `references/failure_codes.md` before writing rejection, review, source_gap, or decision_packet reports.
- Read `references/scoring_rubric.md` before producing validation summaries.
- Read `references/release_integration.md` before creating gold_hook or serving spec candidates.
- Use `assets/*.template.yaml` only as scaffold templates; do not treat them as evidence or production data.

## Hard Boundaries

Reject or stop if the task requires:

- KE truth source, ABox, TBox, or Evidence writes.
- Serving Projection materialization.
- approved_passage_text, rendered_body, or passage_text generation.
- RAG context_bundle.
- DIFY workflow or output.
- CandidatePack instances.
- External runtime, credentials, package install, embedding, or LLM generation.
- Any readiness, production, release, or generation flag set to true.

## Delivery Minimum

Every delivery must report:

- Input brief and source-pack status.
- Files created or changed.
- Checks run and failures.
- Fixture selftest results when checkers are touched.
- Readiness flags, all false.
- Next safe action.

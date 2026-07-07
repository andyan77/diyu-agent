# Codex Rich Body Quality Standard v0.1

This standard defines the minimum quality bar for future Codex-generated GeneralKnowledgeBase draft candidates. It is a contract for generation outputs, not a knowledge draft.

## Minimum Body Requirements

- `min_body_chars`: 350
- The body must explain a reusable principle, not just repeat field names.
- The body must include a definition or core principle, applicable conditions, non-applicable conditions, output or execution implication, risk boundary, and evidence or source requirement.
- Every body section must reference at least one structured proposition from the semantic structure.
- Real instance facts and hard claims require source references or must route to source workorder / exclusion.

## Forbidden Body Content

The natural-language body must not contain semantic self-check field names as prose, YAML key dumps, generic adjective stacks, empty expert opinion, ungrounded real-instance claims, readiness claims, production-ready claims, CandidatePack claims, KE/RAG/DIFY claims, or control-plane route authority.

The following governance terms may appear only as structured fields, not as body prose: `candidate_kind`, `target_owner`, `layer_annotation`, `semantic_alignment`, `body_entailment`, `dedupe_fingerprint`, `readiness_flags`, and `state_machine_route`.

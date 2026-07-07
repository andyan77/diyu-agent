# GKB Intake Checkers

These checker scripts are local blocking gates for `knowledge_intake/gpt55_gkb_enrichment_v1`.

Gate set:

- `check_no_readiness_leak.py`: blocks readiness, production, release, and generation flags.
- `check_source_anchor_coverage.py`: blocks CandidatePack eligibility without source anchors.
- `check_declared_semantics_alignment.py`: checks declared semantics preservation and field / enum mapping.
- `check_hard_claim_and_brand_fact_leak.py`: local rule-based hard claim and concrete fact gate.
- `check_rich_body_structure_consistency.py`: checks required rich body blocks and generic boundary.
- `check_semantic_fingerprint_dedupe.py`: blocks missing or unresolved duplicate semantic fingerprints.
- `check_capability_routing_composability.py`: checks P0 capability refs and consumption hints.
- `check_serving_spec_no_passage_text.py`: blocks generated serving passage text.
- `check_gold_hooks_as_release_input.py`: keeps gold hooks as Step 20 / 21 input candidates only.

Run each checker with `--selftest` before using it on a real batch.

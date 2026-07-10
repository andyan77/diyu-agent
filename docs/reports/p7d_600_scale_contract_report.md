# P7D 600 Expression Diversity Contract Design Report

## Scope

This task defines one canonical, design-only contract for a possible future 600-item expression batch. It consumes the frozen Founder-reviewed Clean-120 reference corpus and materializes no assignment, sample ID, draft, generation record, runner, or checkpoint event.

## Contract

- Frozen corpus: `founder_reviewed_clean_120_reference_corpus.v1.0.jsonl`
- Frozen corpus SHA256: `b6f8fccdcc38407d4791e85631d4a6df7366861617eccca5c13de4d311bb8c91`
- Canonical contract SHA256: `966190c341b070d88fbc3a25540e9c8fddf69ad8f19b90fb29badbb1ffad52a9`
- Topology: 120 parent references x 5 variants = 600; 40 clusters x 15 items
- P0 allocation: P0-01 90, P0-02 105, P0-03 150, P0-04 135, P0-05 120
- Platform allocation: 120 per platform family
- Generation modes: creative prototype 240, fact-slot script 240, display solution 120, evidence-bound candidate 0
- Capture modes: daily native 488, lightly guided 90, campaign directed 22

## Guardrails

The contract keeps claim safety above diversity optimization, treats negation and sequence-word frequency as diagnostic only, separates professional and ordinary voice lanes without erasing role identity, and forbids unsupported real-event, credential, customer, or outcome claims. Sampling and risk strata are computed only from frozen pre-generation features; body text, scores, grades, pass/fail outcomes, preferences, and generated metrics are prohibited inputs.

Failed work items keep their IDs and cannot be replaced or redrawn. Machine checks cover deterministic structure and safety invariants; deep voice similarity, platform nativeness, and content quality remain human-review responsibilities.

## Decision

Status: `P7D_600_SCALE_CONTRACT_DESIGN_COMPLETE_HOLD_FOR_FOUNDER_SINGLE_CLUSTER_PROBE_AUTHORIZATION`.

This design does not authorize a 15-item probe or 600 generation. After Guardian review, the only possible next action is a separately Founder-authorized single-cluster dual-voice probe. Generation 600, expansion 3600, CandidatePack, KE, Serving, RAG, DIFY, production, and all readiness flags remain blocked or false.

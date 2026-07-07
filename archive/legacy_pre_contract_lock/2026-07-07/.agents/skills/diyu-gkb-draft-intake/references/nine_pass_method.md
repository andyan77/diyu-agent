# Nine-Pass Method

Use this sequence for micro-batches after the scaffold phase.

1. Batch Brief Lock: verify the batch lockfile and allowed outputs.
2. Source Binding: bind source packs and excerpt digests or declare source_gap routing.
3. GPT55 Draft Generation: create structured draft candidates only within the brief.
4. Rich Body Expansion: add bounded rich_body_blocks without passage text.
5. Declared Semantics Parse: preserve declared semantics and map fields.
6. Semantic Alignment Gate: validate field mapping, enum alignment, and write surface.
7. Risk, Dedupe, Routing: strip hard claims, dedupe fingerprints, and route unsafe items.
8. Capability Routing Composability: prove each item can be consumed by P0 capabilities.
9. CandidatePack Eligibility and Gold Hooks: emit eligibility reports and hook candidates only.

Do not skip source binding, readiness checks, or capability routing checks.

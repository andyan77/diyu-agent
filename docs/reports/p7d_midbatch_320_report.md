# P7D Conditional Midbatch 320 Report

## Outcome

`GKB-P7D-CONDITIONAL-MIDBATCH-320-GENERATION-AND-REVIEW-HANDOFF-001` completed the founder-authorized bounded generation:
320 Codex-native scoped drafts, 40 clusters, exactly 8 drafts per cluster. The machine result is
`MIDBATCH_320_EXECUTED_PENDING_GUARDIAN_AND_FOUNDER_REVIEW`.

This is not a 3600 release decision. `guardian_review=PENDING`, `founder_human_review=PENDING`,
`full_scale_3600=HOLD`, and `expand_to_3600_allowed=false`.

## Honest Scale Meaning

The 3600 source manifest is a planning/control manifest, not 3600 independent content seeds. This run bound the selected
work items to the 120 existing user-visible kernels within the same cluster. Each cluster used its three seeds for eight
drafts, producing a `3/3/2` reuse distribution and an average pressure of about `2.67x`.

Passing this task therefore tests bounded midbatch execution and kernel variation around `2.67x`. It does not prove that
the repository has enough independent seeds for 3600 drafts, nor that roughly `30x` reuse would remain stable.

## Deterministic Selection

- Source: `execution_scalability_001/scale_work_item_manifest.v0.1.jsonl`
- Sort key: `cluster_id`, `ordinal`, `work_item_id`
- Per-cluster zero-based breakpoints: `0, 11, 22, 33, 45, 56, 67, 78`
- Selection: `40 x 8 = 320`
- Selection digest: `a095efc9b59e7358ccfe51ceafc35e2650ece350ebc5cb5b72923f8a7071a58a`
- Mode distribution: creative prototype 96; fact-slot script 96; evidence-bound candidate 64; display solution 64
- P0 distribution: P0-01 48; P0-02 56; P0-03 80; P0-04 72; P0-05 64

## Machine Gates

- Every selected work item has exactly one accepted output; no 321st output was attempted.
- Every draft was compared with all 120 user-visible kernels; maximum normalized exact overlap was 10 characters
  against a ceiling of 17.
- Exact duplicates: 0; normalized duplicates: 0.
- Maximum within-cluster character 5-shingle Jaccard: `0.242857` against a fail threshold of `0.62`.
- Checkpoints: 40; bounded resume events: 1; missing or duplicate consumption IDs: 0.
- Failure ledger: 0 unresolved failures; retry count: 0.
- CandidatePack/KE/Serving/RAG/DIFY/production materialization: none; readiness remains false.

The deterministic fact-boundary gate covers slots, source binding, unsupported numeric claims, and readiness fields. It
cannot prove that a generic narrative contains no invented customer or life episode. Candidate specificity and narrative
fabrication therefore remain human-review questions, not machine-PASS claims.

## Review Handoff

- Guardian packet: all 320 drafts with binding, body, digest, overlap, and scope metadata.
- Founder packet: 40 readable drafts, exactly one per cluster, selected without quality-score cherry-picking.
- P0-05: 64 generated drafts; its scene prerequisite, customer task, product role, non-hard-sell, spoken conversion,
  overreach, and generic-praise dimensions require Guardian/founder review.

Only after Guardian review and founder review may a new decision choose remaining 3280, another bounded midbatch, or
repair. This report authorizes none of those actions.

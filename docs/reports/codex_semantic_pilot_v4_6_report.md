# CODEX Semantic Pilot V4.6 Report

Task: `CODEX-SEMANTIC-PILOT-V4_5-CLOSEOUT-TYPE-SPECIFIC-RICH-BODY-COMPILER-AND-V4_6-REWRITE-001`

V4.5 is closed as architecture conditional pass and Rich Body quality no-go. V4.6 adds type-specific Rich Body compiler assignments and rewrites eight one-to-one samples. This is not accepted domain knowledge and does not unlock wider generation.

## What Changed

- Added V4.5 closeout and semantic review digest with founder authorization.
- Added type-specific Rich Body compiler contract, independence policy, and sidecar leak prevention policy.
- Added `03_pilot/semantic_v4_6/**` with 8 one-to-one rewritten samples and a compiler assignment matrix.
- Added V4.6 fail-closed checker and 16 negative fixtures.
- Route-synced old pilot checkers to accept `CODEX-SEMANTIC-PILOT-V4_6-JUDGE-GO-NOGO-001` while continuing to reject `CODEX-GKB-DRAFT-GENERATION-BATCH-001`.
- Updated workspace status to route to V4.6 judge only.

## What Was Not Changed

- V4.5 original artifacts were not modified; sha256 verification is required and recorded.
- No batch generation, CandidatePack, KE, Serving, RAG, or DIFY assets were created or touched.
- No source repo or external service was accessed.

## Key Results

- V4.6 drafts: 8
- Distribution: {'content_method': 2, 'apparel_claim_boundary': 2, 'display_to_content': 2, 'control_plane_governance': 2}
- Compiler shape valid count: 8
- Complete Rich Body valid count: 8
- Exact section reuse count: 0
- Same-group max similarity: 0.183
- Cross-group max similarity: 0.197
- Similarity method: lowercase ASCII tokens plus CJK character bigrams; punctuation and whitespace removed for CJK comparison; Jaccard similarity over normalized unit sets
- Repeated downstream paragraph count: 0
- Sidecar leak into Rich Body count: 0
- Predicate version suffix count: 0
- Accepted domain knowledge count: 0
- Batch generation unlocked: false

## Checks

- V4.5 checker live: PASS
- V4.5 checker selftest: PASS
- V4.6 checker live: PASS
- V4.6 checker selftest: PASS
- `python -O` fail-closed: PASS, exit 2
- Contract lock checker: PASS
- Old route-sync checker live/selftest: PASS
- Parse checks: PASS
- Readiness false scan: PASS

## Route Sync Files

- `ci/checkers/check_codex_generation_cross_type_pilot.py`
- `ci/checkers/check_codex_semantic_pilot_regen.py`
- `ci/checkers/check_codex_semantic_pilot_v3.py`
- `ci/checkers/check_codex_semantic_pilot_v4.py`
- `ci/checkers/check_codex_semantic_pilot_v4_1.py`
- `ci/checkers/check_codex_semantic_pilot_v4_2.py`
- `ci/checkers/check_codex_semantic_pilot_v4_3.py`
- `ci/checkers/check_codex_semantic_pilot_v4_4.py`
- `ci/checkers/check_codex_semantic_pilot_v4_5.py`
- `ci/checkers/check_pilot_semantic_fail_closeout_and_brief_hardening.py`

## Next

Recommended next step: `CODEX-SEMANTIC-PILOT-V4_6-JUDGE-GO-NOGO-001`. Human decision is needed before any further widening; V4.6 must not be treated as batch-ready or CandidatePack-ready.

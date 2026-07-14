# P2 Targeted R6 Secondary Independent Review

## Verdict

- Packet item: P2R6-GENERATOR-CORE
- Reviewer identity: P2-SECONDARY-PROVENANCE-REVIEWER-B
- Decision: APPROVE
- Score: 97/100 (A)
- Defect severity: OBSERVATION
- Hard vetoes: none
- Distribution: APPROVE 1, REPAIR 0, REJECT 0

## Findings And Repairs

### P2R6-GENERATOR-CORE

No blocking repair remains.

1. Required-slot trust root closed. The committed 20-case matrix rejected 20/20 path-level slot substitutions. An independently different 60-case matrix added resolved but undeclared input, fact, and authorization bindings for every product; 60/60 rejected with E_COMPONENT_REQUIRED_SLOT_MISMATCH.
2. Operator program schema closed. For all 20 products and six axes, both an unknown field and a missing required field were inserted into a recomputed path and request. All 240/240 rejected with E_AXIS_PROGRAM_FIELD_SET.
3. Mechanism identity and bound-fact evidence closed. All 62/62 recomputed unreviewed ordinary-component mechanism identities were rejected with E_COMPONENT_IDENTITY. All 62/62 alternate fact-object bindings preserved the required slot and fact-value digest while changing the nonmetadata fact-role graph.
4. Observation, nonblocking. A value-only update under the same fact_id preserves the ordinary component reference-graph topology in 62/62 supplemental probes. The graph points to exact typed objects rather than embedding fact values. This did not create a truth bypass: all 40 request-level fact-value/material-digest mutations with recomputed request digests were rejected by the trusted path material contract. P3/P4 still owns value-level content quality.

## Methods

I read the sole packet line and actual review_subject from commit 6555c83c58c54e698ef50c3ff707e44a255d5d9b, then read the complete R6 core (260 lines), complete R6 harness (508 lines), and every byte and row of the four evidence files. Their subject hashes, file hashes, row counts, and all 384 row digests were recomputed. I inspected the delegated R5 validation and realization code because R6 calls it directly.

I rebuilt the component pool from committed candidate files, reconstructed all 20 synthetic typed materials from the frozen profiles, executed both lanes for every product, and invoked the R6 core directly. The committed evidence files were not treated as an oracle: independent attacks used separately constructed mutations and recomputed all affected binding, path, material, and request digests.

No primary or sibling review output was opened or used. The packet's own immutable R5 decision and digest fields were read only because they are part of the single required subject. The R6 packet builder was not executed because its build path reads imported prior-review records; this review instead exercised the committed core and evidence harness directly.

## Actual Replay

| Matrix | Executed | Passed or rejected as required |
|---|---:|---:|
| Positive author requests | 40 | 40 |
| A/B pairs | 20 | 20 |
| Axis body differences | 120 | 120 |
| Component pointers | 410 | 410 |
| Component ablations | 410 | 410 |
| Path substitutions | 120 | 120 |
| Trust-contract tampers | 180 | 180 |
| Required-slot trust-root tampers | 20 | 20 |
| Program-schema tampers | 240 | 240 |
| Mechanism-identity tampers | 62 | 62 |
| Bound-fact structural effects | 62 | 62 |
| Supplemental input/fact/auth slot attacks | 60 | 60 |
| Supplemental fact/source/auth/audience attacks | 160 | 160 |

The four R6 evidence files rebuilt byte-identically:

| Evidence | Rows | SHA-256 |
|---|---:|---|
| required-slot trust root | 20 | 4dc1a3e6cd2c1575d35833631bd508288b297faaee54ae4303572b5040cb0f09 |
| path-program schema | 240 | 779d29317c0cf2a0c12f36badcc5e196b9b48dca145c276cfaecf18480ed132b |
| mechanism identity | 62 | 03c9382618b078d9bffc26f1be6e2bf6c1b274e9883e17bdf9011abb6901e7e8 |
| bound-fact structural effect | 62 | 4830f3acc2230a0952165562344f7172b5d0f99c2ded7dfcda90e2f9a79877c2 |

## Provenance And Boundary Judgment

- All 2,060 component typed references resolved to the exact input, fact, or authorization object and slot; no component ID was used as a fact or authorization object.
- All 240 axis outputs carried the exact material, fact-set, authorization-set, and claim-boundary binding. All 20 A/B pairs shared byte-identical sources, facts, authorizations, and typed material while using distinct sessions.
- CP16's trigger binds exactly customer_task_truth, service_feedback_or_unfinished_state, customer_privacy_consent, service_capture_scope, and safe_next_step_policy; its component boundary disclaims fact, event, person, brand, outcome, and authorization authority.
- All 40 sound realizations used fact-bound cues plus synthetic, publication-denied authorization objects. Audience title/body/script outputs were empty, provider requests/responses were 0/0, and all material remained synthetic and excluded from the 300.
- The six operators contain no product, profile, lane, customer-task, brand, provider, or audience-body payload. Product-specific programs remain in the approved paths.
- ruff check --no-cache passed for the R6 core, harness, and packet builder.

## R5 Immutability And Core Numbers

The R5 revised components, additions, controls, 85 edges, supply matrix, 20 paths, R5 core, and R5 path semantics were byte-identical between 6f18ac14a15e7e17bfb3f45809c3b33d3b1c1d5a and 6555c83c58c54e698ef50c3ff707e44a255d5d9b.

Frozen counts remained intact: reference 120 SHA-256 d4798e9847f9e4800676f002c46bb431e03d2e4763b07c91685f7962f7525ed0; historical 86 SHA-256 de7bb3f3142a2076d88d92494ab512d31d125bb7b96b0ed232ac0122b354a601. The R6 checkpoint retains 300/120/86, p2_complete=false, p3_allowed=false, zero active components and edges, and every readiness flag false.

## Coverage Assertion

I actually read and traced the one packet item in packet order, its complete actual subject, complete R6 core, complete R6 harness, all four evidence files, delegated runtime code, exact R5 artifacts, and all 20 executable paths. I executed every requested case rather than inferring from counts or executor claims. Record order is identical to packet order. Reviewer repository writes, activation, readiness transitions, and primary or sibling review visibility were all zero.

## Repository Write Audit

HEAD remained 6555c83c58c54e698ef50c3ff707e44a255d5d9b and the modified-path set remained limited to the two pre-existing unrelated files. Their worktree diff content changed concurrently during this review: SHA-256 77159677458818708c85f33e4be45ec2b6f8baa57baaa565d254178c8db79581 became 69a946f80ae3c8d598912598b8259f15c48e87a14fa7c39ce2e2303946ebc978. I did not write, inspect for review evidence, or revert those changes. All R6 evidence was read from the exact commit or from relevant worktree files first verified byte-identical to it.

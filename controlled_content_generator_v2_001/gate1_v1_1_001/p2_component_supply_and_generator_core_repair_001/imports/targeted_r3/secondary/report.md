# P2 Targeted r3 Secondary Provenance / Fact / Authorization Review

## Binding

- Task: `GATE1_V11_COMPONENT_SUPPLY_AND_GENERATOR_CORE_REPAIR_001`
- Prompt revision: `r3`
- Role: `SECONDARY_PROVENANCE_FACT_AUTHORIZATION`
- Reviewer: `P2-SECONDARY-PROVENANCE-REVIEWER-B`
- Session: `019f5dce-9436-7e03-be80-220461f6107d`
- Run: `P2-SECONDARY-R3-RUN-20260713-E83C4A2`
- Reviewed commit: `e83c4a27259d64dd1a52d41d9ca0b9cc7237db61`
- Packet: `/home/diyu/笛语领域通用数据库/controlled_content_generator_v2_001/gate1_v1_1_001/p2_component_supply_and_generator_core_repair_001/review/targeted_repair_review_packet.r3.jsonl`
- Packet SHA-256: `e14bf95b40d87c83be48e45f2455d983c3c5e412f88ef41f5b034b9d2403883d`
- Frozen standard SHA-256: `022fc9b96919233e6f5268f5f9d0722b592914cc8919b5d1628dd3600a494542`

## Method

I read all 29 packet rows in order from the exact commit object and compared every review subject with its committed component, edge, path, profile, provenance, material, and generator source. I did not use item order, supply demand, or an approval target to choose verdicts.

For the seven component items, I recomputed component digests, verified profile digests and hard guards, distinguished `PROFILE_DERIVED_DOMAIN_DESIGN` from extracted evidence, reviewed necessity/nonduplication, and checked facts, authorization, compatibility, forbidden combinations, missing-input behavior, truth flags, and readiness flags. For the CP16 edge, I traced the exact component/profile/material/catalog bindings and reviewed product-semantic fit.

For the 20 A/B items, I traced 205 component uses across 68 unique components. The selected pool contains 22 source-derived components, 16 Founder-authorized design components, and 30 profile-derived design components. Source-derived uses resolve through 23 exact parent references and 32 exact spans (18 field spans plus 14 offset spans); parent canonical-row digests and span text/digests recompute. Historical source-candidate identities disclosed by three earlier repaired triggers were treated as identity observations only because their replacement direct-parent derivations are explicit and exact.

I loaded `p2_generator_core.py` directly from commit `e83c4a27259d64dd1a52d41d9ca0b9cc7237db61` into memory. I executed both lanes for every path (40 requests and 40 realizations), resolved every output pointer, and compared A/B facts and authorization byte-for-byte. I then ran the required mutation set on every CP plus additional closure probes.

## Counts

| Decision | Count |
|---|---:|
| APPROVE | 8 |
| REPAIR | 21 |
| REJECT | 0 |
| Total | 29 |

| Object type | APPROVE | REPAIR | Total |
|---|---:|---:|---:|
| REVISED_OR_NECESSARY_COMPONENT | 7 | 0 | 7 |
| REVISED_COMPONENT_CP_EDGE | 1 | 0 | 1 |
| REVISED_AB_STRUCTURAL_PATH_CAPABILITY | 0 | 20 | 20 |
| GENERATOR_CORE_CONTRACT_REPAIR | 0 | 1 | 1 |

Grades: A=8, B=21. Severities: NONE=8, MAJOR=21. No hard veto was assigned because the exact committed payload did not itself leak truth, authorization, audience content, or readiness; the unresolved defects are repairable fail-closed contract gaps.

## Verified Results

- Packet hash and count: exact, 29/29.
- Canonical subject digests: 7/7 changed components, 1/1 changed edge, 20/20 paths.
- Positive A/B execution: 20/20 pairs, 40/40 requests, 40/40 realizations.
- Six exact axis bindings in the committed paths: 120/120.
- Six A/B structural-effect differences: 20/20 paths.
- Byte-identical typed facts and authorization across A/B: 20/20.
- Typed-material revalidation mutation rejected: 20/20.
- Fact-value plus recomputed material/request digest mutation rejected: 20/20.
- Bad material digest plus recomputed request digest rejected: 20/20.
- Stripped non-axis fact/authorization binding rejected: 20/20.
- Unknown axis enum rejected: 20/20.
- Fact-set and authorization-set digest mutations rejected: 20/20 each.
- CP16 customer task, service state, privacy consent, and service scope removal rejected: 4/4.
- External provider dispatch: rejected before network start.
- Audience surface, real brand fact, activation, readiness transition, and 300 increment: none.

## Approved Items

| Packet item | Score | Grade |
|---|---:|---:|
| `P2R3-COMPONENT-G1V11-P2-AXIS-ENDING-BOUNDARY` | 94 | A |
| `P2R3-COMPONENT-G1V11-P2-AXIS-INFORMATION-ORDER` | 94 | A |
| `P2R3-COMPONENT-G1V11-P2-AXIS-NARRATIVE-MECHANISM` | 95 | A |
| `P2R3-COMPONENT-G1V11-P2-AXIS-RHYTHM` | 94 | A |
| `P2R3-COMPONENT-G1V11-P2-AXIS-SOUND-SUBJECT` | 94 | A |
| `P2R3-COMPONENT-G1V11-P2-AXIS-VISUAL-SUBJECT` | 94 | A |
| `P2R3-COMPONENT-G1V11-P2-TRIGGER-AUTHORIZED-SERVICE-NEED` | 93 | A |
| `P2R3-EDGE-CP16-trigger-01` | 93 | A |

## Blocking Repairs By Item

The following findings are shared but were independently reproduced for each listed path:

1. Removing one or two axis contracts and recomputing `request_digest` is accepted, yielding five- or four-axis realizations. The claimed six consumed operators are therefore not fail-closed.
2. A changed component `claim_boundary` is accepted after request re-digesting.
3. Changed `operator_component_binding.binding_digest`, `allowed_values_digest`, and `realization_target` are accepted. The core can emit a false operator-binding receipt or an unresolvable pointer.

| Packet item | Score | Required repair |
|---|---:|---|
| `P2R3-AB-CP01` | 88 / B | CP01 positive path passes, but shared core does not fail closed on all six axes or authoritative boundary/receipt fields. |
| `P2R3-AB-CP02` | 88 / B | CP02 positive path passes, but shared core does not fail closed on all six axes or authoritative boundary/receipt fields. |
| `P2R3-AB-CP03` | 88 / B | CP03 positive path passes, but shared core does not fail closed on all six axes or authoritative boundary/receipt fields. |
| `P2R3-AB-CP04` | 88 / B | CP04 positive path passes, but shared core does not fail closed on all six axes or authoritative boundary/receipt fields. |
| `P2R3-AB-CP05` | 88 / B | CP05 positive path passes, but shared core does not fail closed on all six axes or authoritative boundary/receipt fields. |
| `P2R3-AB-CP06` | 88 / B | CP06 positive path passes, but shared core does not fail closed on all six axes or authoritative boundary/receipt fields. |
| `P2R3-AB-CP07` | 88 / B | CP07 positive path passes, but shared core does not fail closed on all six axes or authoritative boundary/receipt fields. |
| `P2R3-AB-CP08` | 88 / B | CP08 positive path passes, but shared core does not fail closed on all six axes or authoritative boundary/receipt fields. |
| `P2R3-AB-CP09` | 88 / B | CP09 positive path passes, but shared core does not fail closed on all six axes or authoritative boundary/receipt fields. |
| `P2R3-AB-CP10` | 88 / B | CP10 positive path passes, but shared core does not fail closed on all six axes or authoritative boundary/receipt fields. |
| `P2R3-AB-CP11` | 88 / B | CP11 positive path passes, but shared core does not fail closed on all six axes or authoritative boundary/receipt fields. |
| `P2R3-AB-CP12` | 88 / B | CP12 positive path passes, but shared core does not fail closed on all six axes or authoritative boundary/receipt fields. |
| `P2R3-AB-CP13` | 88 / B | CP13 positive path passes, but shared core does not fail closed on all six axes or authoritative boundary/receipt fields. |
| `P2R3-AB-CP14` | 88 / B | CP14 positive path passes, but shared core does not fail closed on all six axes or authoritative boundary/receipt fields. |
| `P2R3-AB-CP15` | 88 / B | CP15 positive path passes, but shared core does not fail closed on all six axes or authoritative boundary/receipt fields. |
| `P2R3-AB-CP16` | 88 / B | CP16 positive path passes, but shared core does not fail closed on all six axes or authoritative boundary/receipt fields. |
| `P2R3-AB-CP17` | 88 / B | CP17 positive path passes, but shared core does not fail closed on all six axes or authoritative boundary/receipt fields. |
| `P2R3-AB-CP18` | 88 / B | CP18 positive path passes, but shared core does not fail closed on all six axes or authoritative boundary/receipt fields. |
| `P2R3-AB-CP19` | 88 / B | CP19 positive path passes, but shared core does not fail closed on all six axes or authoritative boundary/receipt fields. |
| `P2R3-AB-CP20` | 88 / B | CP20 positive path passes, but shared core does not fail closed on all six axes or authoritative boundary/receipt fields. |
| `P2R3-GENERATOR-CORE` | 86 / B | Core accepts 4/5-axis requests and altered claim-boundary, binding/enum digest, and realization-target receipts after request re-digesting. |

The core repair should require the axis and contract key sets to equal the six frozen axes; require one contract and one operator parameter per axis; compare binding claim boundaries to authoritative components; recompute and compare binding and allowed-value digests; require the exact axis realization target; and recompute emitted receipt digests rather than copying unvalidated fields. Add negative tests for each condition across all 20 paths.

## Coverage Assertion

I explicitly attest that every one of the 29 packet items was actually read, traced, scored, and decided in packet order. I reviewed the actual revised payload rather than counts or prior verdicts. I executed all 20 A/B paths and both lanes, manually checked profile-semantic fit, traced exact component-to-material bindings, and ran the required adversarial cases. No sibling reviewer output was opened, read, or used.

## Repository And State Audit

The repository HEAD remained `e83c4a27259d64dd1a52d41d9ca0b9cc7237db61`. I made zero repository writes. Two pre-existing worktree modifications were visible throughout: `ci/checkers/check_gate1_v1_1_current.py` and `controlled_content_generator_v2_001/gate1_v1_1_001/p2_component_supply_and_generator_core_repair_001/p2_final_materializer.py`; neither worktree version was opened or used as review evidence. All bound repository evidence came from `git show e83c4a27259d64dd1a52d41d9ca0b9cc7237db61:<path>`.

No component, edge, path, generator, readiness flag, provider, audience surface, or 300 baseline state was activated or changed. Only the three assigned external review artifacts were written.

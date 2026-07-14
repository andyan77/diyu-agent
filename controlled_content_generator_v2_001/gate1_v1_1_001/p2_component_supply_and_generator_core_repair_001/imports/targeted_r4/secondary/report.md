# P2 r4 Secondary Targeted Review

## Binding

- Task: GATE1_V11_COMPONENT_SUPPLY_AND_GENERATOR_CORE_REPAIR_001
- Prompt revision: r4
- Role: SECONDARY_PROVENANCE_FACT_AUTHORIZATION
- Reviewer identity: P2-SECONDARY-PROVENANCE-REVIEWER-B
- Reviewer session: 019f5dce-9436-7e03-be80-220461f6107d
- Review run: P2-SECONDARY-R4-RUN-20260713-87D3CA8
- Reviewed commit: 87d3ca89ba9cbb743ee82af105cf831bbd8e2dab
- Packet: /home/diyu/笛语领域通用数据库/controlled_content_generator_v2_001/gate1_v1_1_001/p2_component_supply_and_generator_core_repair_001/review/targeted_repair_review_packet.r4.jsonl
- Packet SHA-256: 95c2a44e8d473844ada77d242ede0299a6b4db63b2699dfc633af0704d2c7e72
- Frozen standard SHA-256: 022fc9b96919233e6f5268f5f9d0722b592914cc8919b5d1628dd3600a494542

## Verdict

- Records: 27/27 in packet order
- APPROVE: 6
- REPAIR: 21
- REJECT: 0
- Approved subjects: the six revised semantic axis components
- Blocking subjects: all 20 executable A/B path capabilities and the r4 generator core
- Activation/readiness transition: none

## Method

I read every actual review_subject in the 27-line committed packet and traced it from the commit object, not the working tree. I independently recomputed packet, component, path, profile, program, material, catalog, binding, structural-body, and source-parent digests. The six design components were checked against all 20 exact frozen profile digests and founder hard guards. The 68 components selected by the paths were traced as 30 profile-derived designs, 22 source-derived components, and 16 Founder-authorized design mechanisms; source parent ids/digests/fields/spans resolve to the committed parent objects, while design mechanisms remain explicitly non-factual and non-authorizing.

For the 20 paths I checked 205 exact component bindings, 829 typed objects, 120 axis contracts, and 40 lane executions. Required-role coverage is exact for every profile. Every selected fact reference resolves to the same exact typed material used by both lanes. All sound outputs include the exact material authorization ids/digest and USE_SILENCE_NOT_INVENTED_SOUND; no sound fact, voice, or event is invented.

I executed the closure matrix independently:

- 40/40 positive lane realizations passed.
- 240/240 known-but-wrong-lane substitutions, covering both directions for all six axes and 20 products, rejected.
- Exact-six-axis contract/value/parameter removal and unknown-axis additions rejected for all 40 lanes.
- Component and material claim-boundary, fact-value/material identity, operator binding digest, allowed-values digest, realization target, path digest, and path lane tampering rejected for all 40 lanes.
- 410/410 component-digest, 410/410 required-fact-binding, and 410/410 required-authorization-binding attacks rejected.
- Provider, publishable, runtime-consumable, and may_enter_300 flips rejected for all 40 lanes.
- Profile body, founder hard guards, path-profile metadata, lane session/visibility, controls, hard prohibitions, and expected audience-body permission were also attacked. Those attacks exposed the repairs below.

The new core imports no p2_generator_core_r3 or r3 authoring function. It reuses named typed-material and route utilities from the historical base core; the r4 authoring and realization functions are the committed r4 implementations.

## Approved Components

- P2R4-COMPONENT-G1V11-P2-AXIS-ENDING-BOUNDARY
- P2R4-COMPONENT-G1V11-P2-AXIS-INFORMATION-ORDER
- P2R4-COMPONENT-G1V11-P2-AXIS-NARRATIVE-MECHANISM
- P2R4-COMPONENT-G1V11-P2-AXIS-RHYTHM
- P2R4-COMPONENT-G1V11-P2-AXIS-SOUND-SUBJECT
- P2R4-COMPONENT-G1V11-P2-AXIS-VISUAL-SUBJECT

Each approved component is A-grade, has atomicity at least 13/15, composability at least 17/20, applicability/compatibility/missing-input boundary at least 13/15, type-specific quality at least 17/20, and no major, fatal, or veto finding.

## Repairs By Item

### P2R4-AB-CP01 (CP01)
- Positive trace: CP01 uses product-specific A=FORWARD_TASK_EVIDENCE_CHAIN and B=PARALLEL_STATUS_AND_BLOCKER_MAP; required-role component coverage is exact, the path/profile/material digests are valid, both lanes share byte-identical typed material, all six structural bodies differ, and all fact/sound bindings resolve.
- MAJOR: both CP01 lanes accept frozen profile-body and founder-hard-guard tampering while retaining the stale profile_digest and recomputing only request_digest. The runtime compares the stored digest value but does not recompute the profile object digest.
- MAJOR: both CP01 lanes accept approved_path_binding.content_product_type_id tampering and changes to session_id, session_policy, and other_lane_visible. The committed path fields are correct, but realization does not revalidate path-profile metadata or independent-session visibility.
- MAJOR: both CP01 lanes accept removal of all control_rule_bindings and changes to hard_prohibitions and expected_output_structure.audience_body_allowed. The executable path therefore is not closed to its claimed control, hard-guard, and no-audience request contract.
- Score/decision: 87 (B), REPAIR, MAJOR.

### P2R4-AB-CP02 (CP02)
- Positive trace: CP02 uses product-specific A=FIXED_CAMERA_TIME_CHRONICLE and B=FIXED_ANCHOR_TIME_SLICE_TRACE; required-role component coverage is exact, the path/profile/material digests are valid, both lanes share byte-identical typed material, all six structural bodies differ, and all fact/sound bindings resolve.
- MAJOR: both CP02 lanes accept frozen profile-body and founder-hard-guard tampering while retaining the stale profile_digest and recomputing only request_digest. The runtime compares the stored digest value but does not recompute the profile object digest.
- MAJOR: both CP02 lanes accept approved_path_binding.content_product_type_id tampering and changes to session_id, session_policy, and other_lane_visible. The committed path fields are correct, but realization does not revalidate path-profile metadata or independent-session visibility.
- MAJOR: both CP02 lanes accept removal of all control_rule_bindings and changes to hard_prohibitions and expected_output_structure.audience_body_allowed. The executable path therefore is not closed to its claimed control, hard-guard, and no-audience request contract.
- Score/decision: 87 (B), REPAIR, MAJOR.

### P2R4-AB-CP03 (CP03)
- Positive trace: CP03 uses product-specific A=FULL_VISIBLE_STEP_PROCESS and B=RESULT_TO_STEP_EVIDENCE_TRACE; required-role component coverage is exact, the path/profile/material digests are valid, both lanes share byte-identical typed material, all six structural bodies differ, and all fact/sound bindings resolve.
- MAJOR: both CP03 lanes accept frozen profile-body and founder-hard-guard tampering while retaining the stale profile_digest and recomputing only request_digest. The runtime compares the stored digest value but does not recompute the profile object digest.
- MAJOR: both CP03 lanes accept approved_path_binding.content_product_type_id tampering and changes to session_id, session_policy, and other_lane_visible. The committed path fields are correct, but realization does not revalidate path-profile metadata or independent-session visibility.
- MAJOR: both CP03 lanes accept removal of all control_rule_bindings and changes to hard_prohibitions and expected_output_structure.audience_body_allowed. The executable path therefore is not closed to its claimed control, hard-guard, and no-audience request contract.
- Score/decision: 87 (B), REPAIR, MAJOR.

### P2R4-AB-CP04 (CP04)
- Positive trace: CP04 uses product-specific A=ORDERED_ROLE_HANDOFF and B=PARALLEL_ROLE_STATE_READBACK; required-role component coverage is exact, the path/profile/material digests are valid, both lanes share byte-identical typed material, all six structural bodies differ, and all fact/sound bindings resolve.
- MAJOR: both CP04 lanes accept frozen profile-body and founder-hard-guard tampering while retaining the stale profile_digest and recomputing only request_digest. The runtime compares the stored digest value but does not recompute the profile object digest.
- MAJOR: both CP04 lanes accept approved_path_binding.content_product_type_id tampering and changes to session_id, session_policy, and other_lane_visible. The committed path fields are correct, but realization does not revalidate path-profile metadata or independent-session visibility.
- MAJOR: both CP04 lanes accept removal of all control_rule_bindings and changes to hard_prohibitions and expected_output_structure.audience_body_allowed. The executable path therefore is not closed to its claimed control, hard-guard, and no-audience request contract.
- Score/decision: 86 (B), REPAIR, MAJOR.

### P2R4-AB-CP05 (CP05)
- Positive trace: CP05 uses product-specific A=AUTHORIZED_CAREER_TIMELINE and B=EVIDENCE_LEDGER_STAGE_TRACE; required-role component coverage is exact, the path/profile/material digests are valid, both lanes share byte-identical typed material, all six structural bodies differ, and all fact/sound bindings resolve.
- MAJOR: both CP05 lanes accept frozen profile-body and founder-hard-guard tampering while retaining the stale profile_digest and recomputing only request_digest. The runtime compares the stored digest value but does not recompute the profile object digest.
- MAJOR: both CP05 lanes accept approved_path_binding.content_product_type_id tampering and changes to session_id, session_policy, and other_lane_visible. The committed path fields are correct, but realization does not revalidate path-profile metadata or independent-session visibility.
- MAJOR: both CP05 lanes accept removal of all control_rule_bindings and changes to hard_prohibitions and expected_output_structure.audience_body_allowed. The executable path therefore is not closed to its claimed control, hard-guard, and no-audience request contract.
- Score/decision: 86 (B), REPAIR, MAJOR.

### P2R4-AB-CP06 (CP06)
- Positive trace: CP06 uses product-specific A=OBSERVATION_TO_BOUNDED_JUDGMENT and B=CONCLUSION_TO_EVIDENCE_TRACE; required-role component coverage is exact, the path/profile/material digests are valid, both lanes share byte-identical typed material, all six structural bodies differ, and all fact/sound bindings resolve.
- MAJOR: both CP06 lanes accept frozen profile-body and founder-hard-guard tampering while retaining the stale profile_digest and recomputing only request_digest. The runtime compares the stored digest value but does not recompute the profile object digest.
- MAJOR: both CP06 lanes accept approved_path_binding.content_product_type_id tampering and changes to session_id, session_policy, and other_lane_visible. The committed path fields are correct, but realization does not revalidate path-profile metadata or independent-session visibility.
- MAJOR: both CP06 lanes accept removal of all control_rule_bindings and changes to hard_prohibitions and expected_output_structure.audience_body_allowed. The executable path therefore is not closed to its claimed control, hard-guard, and no-audience request contract.
- Score/decision: 87 (B), REPAIR, MAJOR.

### P2R4-AB-CP07 (CP07)
- Positive trace: CP07 uses product-specific A=CONDITION_DECISION_TREE and B=EXCLUSION_THEN_SUPPORTED_ALTERNATIVE; required-role component coverage is exact, the path/profile/material digests are valid, both lanes share byte-identical typed material, all six structural bodies differ, and all fact/sound bindings resolve.
- MAJOR: both CP07 lanes accept frozen profile-body and founder-hard-guard tampering while retaining the stale profile_digest and recomputing only request_digest. The runtime compares the stored digest value but does not recompute the profile object digest.
- MAJOR: both CP07 lanes accept approved_path_binding.content_product_type_id tampering and changes to session_id, session_policy, and other_lane_visible. The committed path fields are correct, but realization does not revalidate path-profile metadata or independent-session visibility.
- MAJOR: both CP07 lanes accept removal of all control_rule_bindings and changes to hard_prohibitions and expected_output_structure.audience_body_allowed. The executable path therefore is not closed to its claimed control, hard-guard, and no-audience request contract.
- Score/decision: 87 (B), REPAIR, MAJOR.

### P2R4-AB-CP08 (CP08)
- Positive trace: CP08 uses product-specific A=OUTER_TO_INNER_STRUCTURE_DECONSTRUCTION and B=EVIDENCE_RESULT_REVERSE_TRACE; required-role component coverage is exact, the path/profile/material digests are valid, both lanes share byte-identical typed material, all six structural bodies differ, and all fact/sound bindings resolve.
- MAJOR: both CP08 lanes accept frozen profile-body and founder-hard-guard tampering while retaining the stale profile_digest and recomputing only request_digest. The runtime compares the stored digest value but does not recompute the profile object digest.
- MAJOR: both CP08 lanes accept approved_path_binding.content_product_type_id tampering and changes to session_id, session_policy, and other_lane_visible. The committed path fields are correct, but realization does not revalidate path-profile metadata or independent-session visibility.
- MAJOR: both CP08 lanes accept removal of all control_rule_bindings and changes to hard_prohibitions and expected_output_structure.audience_body_allowed. The executable path therefore is not closed to its claimed control, hard-guard, and no-audience request contract.
- Score/decision: 87 (B), REPAIR, MAJOR.

### P2R4-AB-CP09 (CP09)
- Positive trace: CP09 uses product-specific A=FIT_THEN_NONFIT_COMPARISON and B=DISQUALIFIER_FIRST_TRACE; required-role component coverage is exact, the path/profile/material digests are valid, both lanes share byte-identical typed material, all six structural bodies differ, and all fact/sound bindings resolve.
- MAJOR: both CP09 lanes accept frozen profile-body and founder-hard-guard tampering while retaining the stale profile_digest and recomputing only request_digest. The runtime compares the stored digest value but does not recompute the profile object digest.
- MAJOR: both CP09 lanes accept approved_path_binding.content_product_type_id tampering and changes to session_id, session_policy, and other_lane_visible. The committed path fields are correct, but realization does not revalidate path-profile metadata or independent-session visibility.
- MAJOR: both CP09 lanes accept removal of all control_rule_bindings and changes to hard_prohibitions and expected_output_structure.audience_body_allowed. The executable path therefore is not closed to its claimed control, hard-guard, and no-audience request contract.
- Score/decision: 87 (B), REPAIR, MAJOR.

### P2R4-AB-CP10 (CP10)
- Positive trace: CP10 uses product-specific A=HYPOTHESIS_RECORD_RESULT_CHAIN and B=RESULT_TO_RECORD_TRACE; required-role component coverage is exact, the path/profile/material digests are valid, both lanes share byte-identical typed material, all six structural bodies differ, and all fact/sound bindings resolve.
- MAJOR: both CP10 lanes accept frozen profile-body and founder-hard-guard tampering while retaining the stale profile_digest and recomputing only request_digest. The runtime compares the stored digest value but does not recompute the profile object digest.
- MAJOR: both CP10 lanes accept approved_path_binding.content_product_type_id tampering and changes to session_id, session_policy, and other_lane_visible. The committed path fields are correct, but realization does not revalidate path-profile metadata or independent-session visibility.
- MAJOR: both CP10 lanes accept removal of all control_rule_bindings and changes to hard_prohibitions and expected_output_structure.audience_body_allowed. The executable path therefore is not closed to its claimed control, hard-guard, and no-audience request contract.
- Score/decision: 87 (B), REPAIR, MAJOR.

### P2R4-AB-CP11 (CP11)
- Positive trace: CP11 uses product-specific A=PROBLEM_OPTIONS_CHOICE and B=ABANDONED_OPTION_FIRST; required-role component coverage is exact, the path/profile/material digests are valid, both lanes share byte-identical typed material, all six structural bodies differ, and all fact/sound bindings resolve.
- MAJOR: both CP11 lanes accept frozen profile-body and founder-hard-guard tampering while retaining the stale profile_digest and recomputing only request_digest. The runtime compares the stored digest value but does not recompute the profile object digest.
- MAJOR: both CP11 lanes accept approved_path_binding.content_product_type_id tampering and changes to session_id, session_policy, and other_lane_visible. The committed path fields are correct, but realization does not revalidate path-profile metadata or independent-session visibility.
- MAJOR: both CP11 lanes accept removal of all control_rule_bindings and changes to hard_prohibitions and expected_output_structure.audience_body_allowed. The executable path therefore is not closed to its claimed control, hard-guard, and no-audience request contract.
- Score/decision: 87 (B), REPAIR, MAJOR.

### P2R4-AB-CP12 (CP12)
- Positive trace: CP12 uses product-specific A=VERSION_CHRONOLOGY and B=CURRENT_TO_PRIOR_TRACE; required-role component coverage is exact, the path/profile/material digests are valid, both lanes share byte-identical typed material, all six structural bodies differ, and all fact/sound bindings resolve.
- MAJOR: both CP12 lanes accept frozen profile-body and founder-hard-guard tampering while retaining the stale profile_digest and recomputing only request_digest. The runtime compares the stored digest value but does not recompute the profile object digest.
- MAJOR: both CP12 lanes accept approved_path_binding.content_product_type_id tampering and changes to session_id, session_policy, and other_lane_visible. The committed path fields are correct, but realization does not revalidate path-profile metadata or independent-session visibility.
- MAJOR: both CP12 lanes accept removal of all control_rule_bindings and changes to hard_prohibitions and expected_output_structure.audience_body_allowed. The executable path therefore is not closed to its claimed control, hard-guard, and no-audience request contract.
- Score/decision: 87 (B), REPAIR, MAJOR.

### P2R4-AB-CP13 (CP13)
- Positive trace: CP13 uses product-specific A=LIFE_CONTEXT_SEQUENCE and B=SAME_OBJECT_ROLE_MAP; required-role component coverage is exact, the path/profile/material digests are valid, both lanes share byte-identical typed material, all six structural bodies differ, and all fact/sound bindings resolve.
- MAJOR: both CP13 lanes accept frozen profile-body and founder-hard-guard tampering while retaining the stale profile_digest and recomputing only request_digest. The runtime compares the stored digest value but does not recompute the profile object digest.
- MAJOR: both CP13 lanes accept approved_path_binding.content_product_type_id tampering and changes to session_id, session_policy, and other_lane_visible. The committed path fields are correct, but realization does not revalidate path-profile metadata or independent-session visibility.
- MAJOR: both CP13 lanes accept removal of all control_rule_bindings and changes to hard_prohibitions and expected_output_structure.audience_body_allowed. The executable path therefore is not closed to its claimed control, hard-guard, and no-audience request contract.
- Score/decision: 87 (B), REPAIR, MAJOR.

### P2R4-AB-CP14 (CP14)
- Positive trace: CP14 uses product-specific A=SINGLE_PROPERTY_VISUAL_MOTIF and B=CONTACT_SOUND_PULSE; required-role component coverage is exact, the path/profile/material digests are valid, both lanes share byte-identical typed material, all six structural bodies differ, and all fact/sound bindings resolve.
- MAJOR: both CP14 lanes accept frozen profile-body and founder-hard-guard tampering while retaining the stale profile_digest and recomputing only request_digest. The runtime compares the stored digest value but does not recompute the profile object digest.
- MAJOR: both CP14 lanes accept approved_path_binding.content_product_type_id tampering and changes to session_id, session_policy, and other_lane_visible. The committed path fields are correct, but realization does not revalidate path-profile metadata or independent-session visibility.
- MAJOR: both CP14 lanes accept removal of all control_rule_bindings and changes to hard_prohibitions and expected_output_structure.audience_body_allowed. The executable path therefore is not closed to its claimed control, hard-guard, and no-audience request contract.
- Score/decision: 86 (B), REPAIR, MAJOR.

### P2R4-AB-CP15 (CP15)
- Positive trace: CP15 uses product-specific A=GOODS_LIFECYCLE and B=STATE_MAP_HANDOFF; required-role component coverage is exact, the path/profile/material digests are valid, both lanes share byte-identical typed material, all six structural bodies differ, and all fact/sound bindings resolve.
- MAJOR: both CP15 lanes accept frozen profile-body and founder-hard-guard tampering while retaining the stale profile_digest and recomputing only request_digest. The runtime compares the stored digest value but does not recompute the profile object digest.
- MAJOR: both CP15 lanes accept approved_path_binding.content_product_type_id tampering and changes to session_id, session_policy, and other_lane_visible. The committed path fields are correct, but realization does not revalidate path-profile metadata or independent-session visibility.
- MAJOR: both CP15 lanes accept removal of all control_rule_bindings and changes to hard_prohibitions and expected_output_structure.audience_body_allowed. The executable path therefore is not closed to its claimed control, hard-guard, and no-audience request contract.
- Score/decision: 87 (B), REPAIR, MAJOR.

### P2R4-AB-CP16 (CP16)
- Positive trace: CP16 uses product-specific A=NEED_JUDGMENT_OPTION_FEEDBACK and B=TASK_FRICTION_FIRST; required-role component coverage is exact, the path/profile/material digests are valid, both lanes share byte-identical typed material, all six structural bodies differ, and all fact/sound bindings resolve.
- MAJOR: both CP16 lanes accept frozen profile-body and founder-hard-guard tampering while retaining the stale profile_digest and recomputing only request_digest. The runtime compares the stored digest value but does not recompute the profile object digest.
- MAJOR: both CP16 lanes accept approved_path_binding.content_product_type_id tampering and changes to session_id, session_policy, and other_lane_visible. The committed path fields are correct, but realization does not revalidate path-profile metadata or independent-session visibility.
- MAJOR: both CP16 lanes accept removal of all control_rule_bindings and changes to hard_prohibitions and expected_output_structure.audience_body_allowed. The executable path therefore is not closed to its claimed control, hard-guard, and no-audience request contract.
- Score/decision: 86 (B), REPAIR, MAJOR.

### P2R4-AB-CP17 (CP17)
- Positive trace: CP17 uses product-specific A=HYPOTHESIS_ADJUST_COMPARE and B=RESULT_FIRST_SPATIAL_TRACE; required-role component coverage is exact, the path/profile/material digests are valid, both lanes share byte-identical typed material, all six structural bodies differ, and all fact/sound bindings resolve.
- MAJOR: both CP17 lanes accept frozen profile-body and founder-hard-guard tampering while retaining the stale profile_digest and recomputing only request_digest. The runtime compares the stored digest value but does not recompute the profile object digest.
- MAJOR: both CP17 lanes accept approved_path_binding.content_product_type_id tampering and changes to session_id, session_policy, and other_lane_visible. The committed path fields are correct, but realization does not revalidate path-profile metadata or independent-session visibility.
- MAJOR: both CP17 lanes accept removal of all control_rule_bindings and changes to hard_prohibitions and expected_output_structure.audience_body_allowed. The executable path therefore is not closed to its claimed control, hard-guard, and no-audience request contract.
- Score/decision: 87 (B), REPAIR, MAJOR.

### P2R4-AB-CP18 (CP18)
- Positive trace: CP18 uses product-specific A=AUTHORIZED_PLACE_TIME_CHRONICLE and B=SOUND_ANCHOR_TIME_SLICES; required-role component coverage is exact, the path/profile/material digests are valid, both lanes share byte-identical typed material, all six structural bodies differ, and all fact/sound bindings resolve.
- MAJOR: both CP18 lanes accept frozen profile-body and founder-hard-guard tampering while retaining the stale profile_digest and recomputing only request_digest. The runtime compares the stored digest value but does not recompute the profile object digest.
- MAJOR: both CP18 lanes accept approved_path_binding.content_product_type_id tampering and changes to session_id, session_policy, and other_lane_visible. The committed path fields are correct, but realization does not revalidate path-profile metadata or independent-session visibility.
- MAJOR: both CP18 lanes accept removal of all control_rule_bindings and changes to hard_prohibitions and expected_output_structure.audience_body_allowed. The executable path therefore is not closed to its claimed control, hard-guard, and no-audience request contract.
- Score/decision: 86 (B), REPAIR, MAJOR.

### P2R4-AB-CP19 (CP19)
- Positive trace: CP19 uses product-specific A=CONTEXT_OPTIONS_CHOICE_COST and B=COST_RESULT_REVERSE_TRACE; required-role component coverage is exact, the path/profile/material digests are valid, both lanes share byte-identical typed material, all six structural bodies differ, and all fact/sound bindings resolve.
- MAJOR: both CP19 lanes accept frozen profile-body and founder-hard-guard tampering while retaining the stale profile_digest and recomputing only request_digest. The runtime compares the stored digest value but does not recompute the profile object digest.
- MAJOR: both CP19 lanes accept approved_path_binding.content_product_type_id tampering and changes to session_id, session_policy, and other_lane_visible. The committed path fields are correct, but realization does not revalidate path-profile metadata or independent-session visibility.
- MAJOR: both CP19 lanes accept removal of all control_rule_bindings and changes to hard_prohibitions and expected_output_structure.audience_body_allowed. The executable path therefore is not closed to its claimed control, hard-guard, and no-audience request contract.
- Score/decision: 86 (B), REPAIR, MAJOR.

### P2R4-AB-CP20 (CP20)
- Positive trace: CP20 uses product-specific A=COMMITMENT_NODE_EVIDENCE and B=DEVIATION_EVIDENCE_FIRST; required-role component coverage is exact, the path/profile/material digests are valid, both lanes share byte-identical typed material, all six structural bodies differ, and all fact/sound bindings resolve.
- MAJOR: both CP20 lanes accept frozen profile-body and founder-hard-guard tampering while retaining the stale profile_digest and recomputing only request_digest. The runtime compares the stored digest value but does not recompute the profile object digest.
- MAJOR: both CP20 lanes accept approved_path_binding.content_product_type_id tampering and changes to session_id, session_policy, and other_lane_visible. The committed path fields are correct, but realization does not revalidate path-profile metadata or independent-session visibility.
- MAJOR: both CP20 lanes accept removal of all control_rule_bindings and changes to hard_prohibitions and expected_output_structure.audience_body_allowed. The executable path therefore is not closed to its claimed control, hard-guard, and no-audience request contract.
- Score/decision: 86 (B), REPAIR, MAJOR.

### P2R4-GENERATOR-CORE
- Verified the committed core, axis-semantics, and evidence-harness SHA-256 values. All 40 positive lane requests realize; 240 two-direction known-wrong-lane enum substitutions, exact-six-axis removals/additions, claim-boundary tampering, operator/allowed-value/target tampering, material identity tampering, and 1,230 component digest/fact/authorization binding attacks are rejected.
- Verified all 120 A/B axis pairs differ at structural_body_digest level; every selected fact slot exists in the exact typed material, sound cues carry the exact authorization set plus silence-on-missing-source policy, provider/publishable/runtime/300 flips reject, and the r4 core import graph does not call p2_generator_core_r3 or other r3 authoring logic.
- MAJOR: 40/40 lanes accept profile body and founder hard-guard deletion or replacement with a stale profile_digest after request_digest recomputation. validate_author_request must recompute the frozen profile digest and bind all profile projections/hard guards.
- MAJOR: 40/40 lanes accept path-binding profile-id tampering, shared/incorrect session identity and policy, other_lane_visible=true, removed controls, altered hard prohibitions, and expected audience-body permission. These request fields must be compared to the trusted path/profile/control contract before realization.
- Score/decision: 82 (B), REPAIR, MAJOR.

## Blocking Repair Themes

1. Recompute profile_digest from profile_contract and compare the full trusted profile projection, including founder hard guards, platforms, account identity, capture constraints, and hard prohibitions.
2. Bind and revalidate approved_path_binding.content_product_type_id, lane session id/policy, and other_lane_visible; enforce pairwise session separation.
3. Bind control-rule ids/digests and validate the no-audience expected-output contract instead of trusting mutable request fields.
4. Preserve the already-correct six-axis, typed-material, component-binding, sound authorization/silence, and provider/readiness rejection behavior.

## Coverage Assertion

I actually read and traced every one of the 27 packet items in packet order: six revised semantic axis components, twenty revised semantic A/B structural paths, and one semantic generator-core repair. I did not derive decisions from item order, desired supply, prior approval counts, or another reviewer's verdict. No primary or sibling review output content was read or used. No item was activated, no readiness flag was transitioned, and no repository file was written by this review.

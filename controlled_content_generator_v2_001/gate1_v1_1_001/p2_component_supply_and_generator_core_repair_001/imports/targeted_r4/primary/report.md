# Targeted r4 Primary Independent Review Report

## Binding

- Task: `GATE1_V11_COMPONENT_SUPPLY_AND_GENERATOR_CORE_REPAIR_001`
- Prompt revision: `r4`
- Review role: `PRIMARY_CONTENT_VALUE_COMPOSABILITY`
- Reviewer: `P2-PRIMARY-CONTENT-REVIEWER-A` / `019f5dce-25f9-74c3-85d6-c19280e9664a`
- Review run: `P2-PRIMARY-R4-RUN-20260713-87D3CA8`
- Reviewed commit: `87d3ca89ba9cbb743ee82af105cf831bbd8e2dab`
- Packet SHA-256: `95c2a44e8d473844ada77d242ede0299a6b4db63b2699dfc633af0704d2c7e72`
- Activation/readiness transitions: none

## Methods

I actually read every one of the 27 actual `review_subject` payloads in packet order: six revised semantic-axis components, 20 revised A/B structural paths, and one generator-core contract. I independently decided every item without using packet order, a target approval count, supply need, or any sibling/secondary review output.

I applied the frozen v1.1 80+20 component rubric directly to components and the closest enabled structural/content-product/generator logical view to paths and the core. Component approval still required grade A, atomicity at least 13/15, composability at least 17/20, applicability/boundary at least 13/15, type-specific quality at least 17/20, and no major/fatal defect.

The packet, job, core, semantic-program source, and evidence harness were verified against an isolated archive of the exact reviewed commit. This excluded pre-existing or concurrent working-tree drift. I used the prior same-identity r3 primary record only to preserve the established v0.1 field layout; no sibling review artifact was opened or used.

Executable review rebuilt the exact-commit r4 component pool and all 20 typed materials in memory, executed both lanes for every path, resolved every pointer, compared structural bodies, and ran adversarial mutation matrices for unknown and known enums, exact six-axis presence, component/material claim boundaries, component digests, path bindings, operator bindings, allowed-values receipts, target receipts, semantic-program receipts, and mechanism receipts. It also inspected each selected non-axis component's fact-role use and tested component pointers rather than accepting ablation counters at face value.

No audience content was requested or produced, and this review makes no audience-content or content-quality claim. Conclusions concern candidate component value, atomicity, composability, product fit, typed structural behavior, and implementation truth only.

## Verdict Counts

| Decision | Count |
|---|---:|
| APPROVE | 0 |
| REPAIR | 27 |
| REJECT | 0 |

| Object type | APPROVE | REPAIR | REJECT | Total |
|---|---:|---:|---:|---:|
| REVISED_SEMANTIC_AXIS_COMPONENT | 0 | 6 | 0 | 6 |
| REVISED_SEMANTIC_AB_STRUCTURAL_PATH_CAPABILITY | 0 | 20 | 0 | 20 |
| SEMANTIC_GENERATOR_CORE_CONTRACT_REPAIR | 0 | 1 | 0 | 1 |

Grades: A=0, B=17, C=10, D=0.

Defect severities: NONE=0, OBSERVATION=0, MINOR=0, MAJOR=27, FATAL=0.

## Executable Evidence

- Exact-commit r4 document validator: PASS.
- Lane requests realized: 40/40; same exact typed-material lane pairs: 20/20.
- Dedicated axis output contracts and pointer resolution: 240/240.
- A/B `structural_body_digest` differences: 120/120.
- Unknown enum values rejected: 240/240; opposite-lane known reviewed enums rejected: 240/240.
- Missing axis values, parameters, and contracts rejected: 240/240 for each class; extra axes rejected: 40/40.
- Operator binding, exact-binding recomputation, allowed-values receipt, target receipt, program receipt, and mechanism receipt tampering rejected: 240/240 for each class.
- Component/material claim-boundary and path-binding tampering rejected: 40/40 for each top-level class; every selected component boundary and digest tamper rejected: 410/410 for each class.
- Every selected-component ablation rejected or changed: 410/410, but all removals are rejected at authoritative-set validation and therefore do not prove an observable implementation effect.
- Generic selected-component implementation pointers resolved: 0/410. Dedicated axis pointers resolved: 240/240.
- Non-axis lane bindings with no fact-role reference in the structural bodies: 46/170.
- Axis program registry: 240 profile/lane programs, 232 distinct enum names; executable payloads are distinct in 239/240 instances after identity/receipt fields are removed.
- Cross-axis payload duplication: narrative order equals information order 40/40; flattened rhythm groups equal information order 40/40; narrative stop boundary equals ending boundary 40/40.
- Strict fact-role topology differences after removing labels, digests, modes, policies, and receipts: 117/120; CP05, CP12, and CP13 ending pairs remain identical.
- Audience title/body/spoken-script fields empty: 40/40.

## Blocking Themes

1. **Payload-sized operator libraries.** Each axis object contains 40 product/lane programs. Across the six components, 232/240 enum instances have distinct names and 239/240 executable payloads are one-off. This falls below the frozen composability minimum and makes reuse mostly nominal at the wrapper ID.
2. **Cross-axis duplication.** Narrative embeds all information ordering and ending stop data; rhythm embeds the full information order. These payloads should compose by typed references rather than be copied into neighboring components.
3. **False component-use evidence.** The core claims every selected component is realized, yet 0/410 generic contribution pointers resolve and 46/170 non-axis lane bindings have no structural fact-role use. Pre-realization set-membership rejection is not an effect-level ablation.
4. **Three policy-only ending differences.** CP05, CP12, and CP13 have the same ending facts and booleans; only closure/policy enum strings differ. Those lanes need explicit different closure action structures.
5. **Propagation to every path.** All 20 paths have product-semantic A/B axes and exact material binding, but each relies on the six unapproved registries and carries at least one non-axis lane binding without a fact-role contribution plus unresolved component pointers.

## Repairs By Item ID

### `P2R4-COMPONENT-G1V11-P2-AXIS-ENDING-BOUNDARY`

Decision: **REPAIR**; grade C (74/100); severity MAJOR.

- The actual packet payload was read in position 1. It is a profile-derived design component for only the ending axis, declares no fact or authorization authority, carries explicit compatibility and missing-input boundaries, and emits BOUNDARY_CLOSURE_MAP objects.
- Exact-commit replay produced 40/40 ending outputs at resolvable dedicated axis pointers. All 20 A/B body digests differed, 40/40 unknown values rejected, 40/40 opposite-lane known values rejected, and the axis's 40 ablations rejected.
- The r4 code removes hash/token-derived selection and validates the authoritative profile, lane, value, exact material, operator binding, allowed-values receipt, target receipt, and program receipt.
- Composability remains below the v1.1 approval minimum: this one component embeds 40 profile-by-lane programs with 39 enum names and 40 distinct executable payloads. Across all six components, 232 of 240 enum instances have distinct names; the objects function as payload-sized path template registries, not independently reusable axis components.
- Its boundary_fact_slots duplicate the narrative stop_boundary_slots in 40/40 profile-lane programs, so closure payload and narrative-stop data are not independently owned.
- For CP05, CP12, and CP13, A and B use identical boundary fact references and identical booleans; only closure_mode and next_step_policy enum strings change. Removing those policy labels leaves 17/20 ending pairs with a different fact-role topology, not 20/20.
- Move profile/lane closure data to reviewed path contracts or reusable closure primitives, and emit explicit closure/next-step action nodes for CP05, CP12, and CP13 rather than policy labels alone.

Scored under the closest enabled structural narrative or visual-audio component view. The r4 execution and boundary controls are real improvements, but parameterization/composability is below 17/20 and the component carries an unresolved major template-registry defect. It therefore cannot be approved under the frozen component minima.

### `P2R4-COMPONENT-G1V11-P2-AXIS-INFORMATION-ORDER`

Decision: **REPAIR**; grade C (78/100); severity MAJOR.

- The actual packet payload was read in position 2. It is a profile-derived design component for only the information_order axis, declares no fact or authorization authority, carries explicit compatibility and missing-input boundaries, and emits INFORMATION_NODE_SEQUENCE objects.
- Exact-commit replay produced 40/40 information_order outputs at resolvable dedicated axis pointers. All 20 A/B body digests differed, 40/40 unknown values rejected, 40/40 opposite-lane known values rejected, and the axis's 40 ablations rejected.
- The r4 code removes hash/token-derived selection and validates the authoritative profile, lane, value, exact material, operator binding, allowed-values receipt, target receipt, and program receipt.
- Composability remains below the v1.1 approval minimum: this one component embeds 40 profile-by-lane programs with 40 enum names and 40 distinct executable payloads. Across all six components, 232 of 240 enum instances have distinct names; the objects function as payload-sized path template registries, not independently reusable axis components.
- The explicit ordered fact-role sequences are product-grounded and replace r3's SHA/token ordering.
- All 40 enum names and all 40 executable sequence payloads are one-off profile/lane entries; no parameter value is reused across products, so the object is a registry of path instances rather than a broadly composable ordering component.
- Keep a small reusable ordering-operator vocabulary in the component and place product-specific typed role sequences in the authoritative path binding.

Scored under the closest enabled structural narrative or visual-audio component view. The r4 execution and boundary controls are real improvements, but parameterization/composability is below 17/20 and the component carries an unresolved major template-registry defect. It therefore cannot be approved under the frozen component minima.

### `P2R4-COMPONENT-G1V11-P2-AXIS-NARRATIVE-MECHANISM`

Decision: **REPAIR**; grade C (71/100); severity MAJOR.

- The actual packet payload was read in position 3. It is a profile-derived design component for only the narrative_mechanism axis, declares no fact or authorization authority, carries explicit compatibility and missing-input boundaries, and emits NARRATIVE_SEGMENT_GRAPH objects.
- Exact-commit replay produced 40/40 narrative_mechanism outputs at resolvable dedicated axis pointers. All 20 A/B body digests differed, 40/40 unknown values rejected, 40/40 opposite-lane known values rejected, and the axis's 40 ablations rejected.
- The r4 code removes hash/token-derived selection and validates the authoritative profile, lane, value, exact material, operator binding, allowed-values receipt, target receipt, and program receipt.
- Composability remains below the v1.1 approval minimum: this one component embeds 40 profile-by-lane programs with 40 enum names and 40 distinct executable payloads. Across all six components, 232 of 240 enum instances have distinct names; the objects function as payload-sized path template registries, not independently reusable axis components.
- The explicit relation_mode and fact-role graph replace r3's hash/token-derived graph selection.
- The narrative ordered_fact_slots are byte-for-byte the information-order slots in 40/40 programs, and narrative stop_boundary_slots are the ending boundary slots in 40/40 programs. That duplicates two neighboring axis payloads and weakens semantic atomicity.
- Make narrative own only reusable relation/segment mechanics, reference an information-order output and an ending boundary by typed pointer, and move the 40 path-specific programs out of the component object.

Scored under the closest enabled structural narrative or visual-audio component view. The r4 execution and boundary controls are real improvements, but parameterization/composability is below 17/20 and the component carries an unresolved major template-registry defect. It therefore cannot be approved under the frozen component minima.

### `P2R4-COMPONENT-G1V11-P2-AXIS-RHYTHM`

Decision: **REPAIR**; grade C (71/100); severity MAJOR.

- The actual packet payload was read in position 4. It is a profile-derived design component for only the rhythm axis, declares no fact or authorization authority, carries explicit compatibility and missing-input boundaries, and emits STRUCTURAL_BEAT_MAP objects.
- Exact-commit replay produced 40/40 rhythm outputs at resolvable dedicated axis pointers. All 20 A/B body digests differed, 40/40 unknown values rejected, 40/40 opposite-lane known values rejected, and the axis's 40 ablations rejected.
- The r4 code removes hash/token-derived selection and validates the authoritative profile, lane, value, exact material, operator binding, allowed-values receipt, target receipt, and program receipt.
- Composability remains below the v1.1 approval minimum: this one component embeds 40 profile-by-lane programs with 40 enum names and 40 distinct executable payloads. Across all six components, 232 of 240 enum instances have distinct names; the objects function as payload-sized path template registries, not independently reusable axis components.
- The explicit beat groups and cadence modes replace r3's SHA rotation and token-based group sizing.
- Flattening beat_fact_slot_groups reproduces the full information-order sequence in 40/40 programs. The rhythm component therefore embeds the neighboring ordering payload rather than composing over it.
- Express reusable cadence/grouping rules over an authoritative information-order output, and keep profile/lane role sequences in the path contract instead of duplicating them in the rhythm component.

Scored under the closest enabled structural narrative or visual-audio component view. The r4 execution and boundary controls are real improvements, but parameterization/composability is below 17/20 and the component carries an unresolved major template-registry defect. It therefore cannot be approved under the frozen component minima.

### `P2R4-COMPONENT-G1V11-P2-AXIS-SOUND-SUBJECT`

Decision: **REPAIR**; grade C (79/100); severity MAJOR.

- The actual packet payload was read in position 5. It is a profile-derived design component for only the sound_subject axis, declares no fact or authorization authority, carries explicit compatibility and missing-input boundaries, and emits SOUND_CUE_MAP objects.
- Exact-commit replay produced 40/40 sound_subject outputs at resolvable dedicated axis pointers. All 20 A/B body digests differed, 40/40 unknown values rejected, 40/40 opposite-lane known values rejected, and the axis's 40 ablations rejected.
- The r4 code removes hash/token-derived selection and validates the authoritative profile, lane, value, exact material, operator binding, allowed-values receipt, target receipt, and program receipt.
- Composability remains below the v1.1 approval minimum: this one component embeds 40 profile-by-lane programs with 34 enum names and 39 distinct executable payloads. Across all six components, 232 of 240 enum instances have distinct names; the objects function as payload-sized path template registries, not independently reusable axis components.
- The explicit cue slots, source class, missing-source behavior, and authorization IDs are materially stronger than r3's arbitrary fact rotation.
- The component still contains 40 profile/lane programs: 34 enum names and 39 distinct executable cue payloads. Reuse is mostly at the wrapper ID, not at the semantic parameter/program level.
- Separate reusable sound-source/cue-selection primitives from profile-specific typed cue bindings, with the latter carried by reviewed path contracts.

Scored under the closest enabled structural narrative or visual-audio component view. The r4 execution and boundary controls are real improvements, but parameterization/composability is below 17/20 and the component carries an unresolved major template-registry defect. It therefore cannot be approved under the frozen component minima.

### `P2R4-COMPONENT-G1V11-P2-AXIS-VISUAL-SUBJECT`

Decision: **REPAIR**; grade C (79/100); severity MAJOR.

- The actual packet payload was read in position 6. It is a profile-derived design component for only the visual_subject axis, declares no fact or authorization authority, carries explicit compatibility and missing-input boundaries, and emits VISUAL_FOCUS_MAP objects.
- Exact-commit replay produced 40/40 visual_subject outputs at resolvable dedicated axis pointers. All 20 A/B body digests differed, 40/40 unknown values rejected, 40/40 opposite-lane known values rejected, and the axis's 40 ablations rejected.
- The r4 code removes hash/token-derived selection and validates the authoritative profile, lane, value, exact material, operator binding, allowed-values receipt, target receipt, and program receipt.
- Composability remains below the v1.1 approval minimum: this one component embeds 40 profile-by-lane programs with 39 enum names and 40 distinct executable payloads. Across all six components, 232 of 240 enum instances have distinct names; the objects function as payload-sized path template registries, not independently reusable axis components.
- The explicit lead/support fact-role selection and focus mode replace r3's digest-rotated first-fact choice.
- The component holds 40 profile/lane programs, 39 enum names, and 40 distinct executable visual payloads. The parameter does not define a portable visual operation independent of a single reviewed path lane.
- Define reusable focus/subject operators and move exact product-specific lead/support fact-role bindings into the authoritative path contract.

Scored under the closest enabled structural narrative or visual-audio component view. The r4 execution and boundary controls are real improvements, but parameterization/composability is below 17/20 and the component carries an unresolved major template-registry defect. It therefore cannot be approved under the frozen component minima.

### `P2R4-AB-CP01`

Decision: **REPAIR**; grade B (84/100); severity MAJOR.

- The actual CP01 path payload was read in packet position 7. Task chronology versus a parallel state/blocker map is product-semantic for a real task microdocumentary. Its reviewed lane program is: narrative_mechanism task_chronology -> parallel_status_map; information_order context_action_boundary -> state_blocker_trace; visual_subject actor_task -> task_object_state; sound_subject ambient_task_sound -> evidence_cue; rhythm steady_observation -> status_pulse; ending current_boundary -> next_check.
- Exact-commit replay realized both lanes over byte-identical typed material in independent sessions. All 12 dedicated axis pointers resolved, all 12 packet structural-output contracts matched, and all six A/B structural_body digests differed.
- Per-path adversarial replay rejected all 12 unknown-enum substitutions, all 12 opposite-lane known-enum substitutions, missing/extra-axis mutations, component/material claim-boundary tampering, and every operator-binding, allowed-values, program, mechanism, and target-receipt mutation.
- The selected-component use claim is false as emitted: 0/20 generic component_contributions pointers for this path resolve because the core points to /structural_realization/lane_{id}/{role}/{index}, while the emitted object contains only lane_{id}/axes. The path still reports every selected component as realized and reports zero unrealized components.
- In addition, 2/8 non-axis lane bindings for CP01 contribute no fact-role reference to that lane's structural bodies. The ablation harness rejects removal at exact-set validation, so its changed/rejected result proves membership integrity, not an observable component-specific implementation effect required by execution brief section 7.3.
- The path also depends on six profile/lane template registries whose component-level composability remains below the frozen 17/20 threshold. Move product-specific programs into the path contract, emit resolvable component-specific structural objects or mark components honestly unrealized, and demonstrate an effect-level ablation after validation.

Scored under the closest enabled content-product and structural-composition path view. The A/B axes are product-specific, same-material binding is exact, and r3's enum-authority defects are closed. However, every path carries unresolved fake-use evidence for selected components and depends on noncomposable profile/lane registries. That major defect invokes repair rather than approval; no activation is authorized.

### `P2R4-AB-CP02`

Decision: **REPAIR**; grade B (84/100); severity MAJOR.

- The actual CP02 path payload was read in packet position 8. Fixed-camera chronology versus fixed-anchor time slices preserves the ordinary store-period observational product. Its reviewed lane program is: narrative_mechanism fixed_camera_chronicle -> fixed_anchor_time_slice; information_order time_then_change -> state_then_time_trace; visual_subject whole_space_anchor -> same_anchor_detail; sound_subject continuous_ambience -> time_marker_sound; rhythm natural_duration -> interval_pulse; ending ordinary_close -> open_next_slice.
- Exact-commit replay realized both lanes over byte-identical typed material in independent sessions. All 12 dedicated axis pointers resolved, all 12 packet structural-output contracts matched, and all six A/B structural_body digests differed.
- Per-path adversarial replay rejected all 12 unknown-enum substitutions, all 12 opposite-lane known-enum substitutions, missing/extra-axis mutations, component/material claim-boundary tampering, and every operator-binding, allowed-values, program, mechanism, and target-receipt mutation.
- The selected-component use claim is false as emitted: 0/20 generic component_contributions pointers for this path resolve because the core points to /structural_realization/lane_{id}/{role}/{index}, while the emitted object contains only lane_{id}/axes. The path still reports every selected component as realized and reports zero unrealized components.
- In addition, 2/8 non-axis lane bindings for CP02 contribute no fact-role reference to that lane's structural bodies. The ablation harness rejects removal at exact-set validation, so its changed/rejected result proves membership integrity, not an observable component-specific implementation effect required by execution brief section 7.3.
- The path also depends on six profile/lane template registries whose component-level composability remains below the frozen 17/20 threshold. Move product-specific programs into the path contract, emit resolvable component-specific structural objects or mark components honestly unrealized, and demonstrate an effect-level ablation after validation.

Scored under the closest enabled content-product and structural-composition path view. The A/B axes are product-specific, same-material binding is exact, and r3's enum-authority defects are closed. However, every path carries unresolved fake-use evidence for selected components and depends on noncomposable profile/lane registries. That major defect invokes repair rather than approval; no activation is authorized.

### `P2R4-AB-CP03`

Decision: **REPAIR**; grade B (84/100); severity MAJOR.

- The actual CP03 path payload was read in packet position 9. Full causal-step process versus result-to-step evidence trace fits a complete craft process without inventing steps. Its reviewed lane program is: narrative_mechanism full_step_process -> result_to_step_trace; information_order input_step_judgment_result -> result_judgment_step_input; visual_subject hand_and_tool -> result_detail_then_hand; sound_subject contact_source_sound -> key_action_sound; rhythm causal_step_rhythm -> evidence_backtrack; ending visible_step_state -> unfinished_or_verified.
- Exact-commit replay realized both lanes over byte-identical typed material in independent sessions. All 12 dedicated axis pointers resolved, all 12 packet structural-output contracts matched, and all six A/B structural_body digests differed.
- Per-path adversarial replay rejected all 12 unknown-enum substitutions, all 12 opposite-lane known-enum substitutions, missing/extra-axis mutations, component/material claim-boundary tampering, and every operator-binding, allowed-values, program, mechanism, and target-receipt mutation.
- The selected-component use claim is false as emitted: 0/22 generic component_contributions pointers for this path resolve because the core points to /structural_realization/lane_{id}/{role}/{index}, while the emitted object contains only lane_{id}/axes. The path still reports every selected component as realized and reports zero unrealized components.
- In addition, 2/10 non-axis lane bindings for CP03 contribute no fact-role reference to that lane's structural bodies. The ablation harness rejects removal at exact-set validation, so its changed/rejected result proves membership integrity, not an observable component-specific implementation effect required by execution brief section 7.3.
- The path also depends on six profile/lane template registries whose component-level composability remains below the frozen 17/20 threshold. Move product-specific programs into the path contract, emit resolvable component-specific structural objects or mark components honestly unrealized, and demonstrate an effect-level ablation after validation.

Scored under the closest enabled content-product and structural-composition path view. The A/B axes are product-specific, same-material binding is exact, and r3's enum-authority defects are closed. However, every path carries unresolved fake-use evidence for selected components and depends on noncomposable profile/lane registries. That major defect invokes repair rather than approval; no activation is authorized.

### `P2R4-AB-CP04`

Decision: **REPAIR**; grade B (84/100); severity MAJOR.

- The actual CP04 path payload was read in packet position 10. Role handoff versus parallel role readback fits real multi-role collaboration and authority separation. Its reviewed lane program is: narrative_mechanism role_handoff -> parallel_role_readback; information_order role_sequence -> result_then_role_evidence; visual_subject actor_and_shared_object -> shared_object_multi_view; sound_subject role_source_sound -> separate_role_cues; rhythm handoff_rhythm -> parallel_state_pulse; ending shared_state -> authority_boundary.
- Exact-commit replay realized both lanes over byte-identical typed material in independent sessions. All 12 dedicated axis pointers resolved, all 12 packet structural-output contracts matched, and all six A/B structural_body digests differed.
- Per-path adversarial replay rejected all 12 unknown-enum substitutions, all 12 opposite-lane known-enum substitutions, missing/extra-axis mutations, component/material claim-boundary tampering, and every operator-binding, allowed-values, program, mechanism, and target-receipt mutation.
- The selected-component use claim is false as emitted: 0/22 generic component_contributions pointers for this path resolve because the core points to /structural_realization/lane_{id}/{role}/{index}, while the emitted object contains only lane_{id}/axes. The path still reports every selected component as realized and reports zero unrealized components.
- In addition, 2/10 non-axis lane bindings for CP04 contribute no fact-role reference to that lane's structural bodies. The ablation harness rejects removal at exact-set validation, so its changed/rejected result proves membership integrity, not an observable component-specific implementation effect required by execution brief section 7.3.
- The path also depends on six profile/lane template registries whose component-level composability remains below the frozen 17/20 threshold. Move product-specific programs into the path contract, emit resolvable component-specific structural objects or mark components honestly unrealized, and demonstrate an effect-level ablation after validation.

Scored under the closest enabled content-product and structural-composition path view. The A/B axes are product-specific, same-material binding is exact, and r3's enum-authority defects are closed. However, every path carries unresolved fake-use evidence for selected components and depends on noncomposable profile/lane registries. That major defect invokes repair rather than approval; no activation is authorized.

### `P2R4-AB-CP05`

Decision: **REPAIR**; grade B (81/100); severity MAJOR.

- The actual CP05 path payload was read in packet position 11. Career timeline versus an evidence-led stage ledger fits documented professional history. Its reviewed lane program is: narrative_mechanism career_timeline -> evidence_ledger_stages; information_order stage_then_change -> artifact_then_stage_trace; visual_subject authorized_stage_artifact -> field_and_object; sound_subject recorded_voice_or_silence -> dated_record_cue; rhythm longitudinal_pacing -> archive_pulse; ending current_stage -> open_history_gap.
- Exact-commit replay realized both lanes over byte-identical typed material in independent sessions. All 12 dedicated axis pointers resolved, all 12 packet structural-output contracts matched, and all six A/B structural_body digests differed.
- Per-path adversarial replay rejected all 12 unknown-enum substitutions, all 12 opposite-lane known-enum substitutions, missing/extra-axis mutations, component/material claim-boundary tampering, and every operator-binding, allowed-values, program, mechanism, and target-receipt mutation.
- The selected-component use claim is false as emitted: 0/22 generic component_contributions pointers for this path resolve because the core points to /structural_realization/lane_{id}/{role}/{index}, while the emitted object contains only lane_{id}/axes. The path still reports every selected component as realized and reports zero unrealized components.
- In addition, 2/10 non-axis lane bindings for CP05 contribute no fact-role reference to that lane's structural bodies. The ablation harness rejects removal at exact-set validation, so its changed/rejected result proves membership integrity, not an observable component-specific implementation effect required by execution brief section 7.3.
- The path also depends on six profile/lane template registries whose component-level composability remains below the frozen 17/20 threshold. Move product-specific programs into the path contract, emit resolvable component-specific structural objects or mark components honestly unrealized, and demonstrate an effect-level ablation after validation.
- Additional CP05 ending defect: current_stage versus open_history_gap uses the same boundary fact references and booleans; only closure_mode and next_step_policy strings differ, so removing policy labels eliminates the ending transformation.

Scored under the closest enabled content-product and structural-composition path view. The A/B axes are product-specific, same-material binding is exact, and r3's enum-authority defects are closed. However, every path carries unresolved fake-use evidence for selected components and depends on noncomposable profile/lane registries. That major defect invokes repair rather than approval; no activation is authorized.

### `P2R4-AB-CP06`

Decision: **REPAIR**; grade C (77/100); severity MAJOR.

- The actual CP06 path payload was read in packet position 12. Observation-to-judgment versus conclusion-to-evidence fits bounded professional judgment. Its reviewed lane program is: narrative_mechanism observation_to_judgment -> conclusion_to_evidence; information_order detail_basis_limit -> limit_basis_detail; visual_subject detail_path -> evidence_map; sound_subject operation_sound -> source_cue; rhythm analytic_pause -> reverse_evidence_pulse; ending bounded_conclusion -> unproven_boundary.
- Exact-commit replay realized both lanes over byte-identical typed material in independent sessions. All 12 dedicated axis pointers resolved, all 12 packet structural-output contracts matched, and all six A/B structural_body digests differed.
- Per-path adversarial replay rejected all 12 unknown-enum substitutions, all 12 opposite-lane known-enum substitutions, missing/extra-axis mutations, component/material claim-boundary tampering, and every operator-binding, allowed-values, program, mechanism, and target-receipt mutation.
- The selected-component use claim is false as emitted: 0/20 generic component_contributions pointers for this path resolve because the core points to /structural_realization/lane_{id}/{role}/{index}, while the emitted object contains only lane_{id}/axes. The path still reports every selected component as realized and reports zero unrealized components.
- In addition, 6/8 non-axis lane bindings for CP06 contribute no fact-role reference to that lane's structural bodies. The ablation harness rejects removal at exact-set validation, so its changed/rejected result proves membership integrity, not an observable component-specific implementation effect required by execution brief section 7.3.
- The path also depends on six profile/lane template registries whose component-level composability remains below the frozen 17/20 threshold. Move product-specific programs into the path contract, emit resolvable component-specific structural objects or mark components honestly unrealized, and demonstrate an effect-level ablation after validation.

Scored under the closest enabled content-product and structural-composition path view. The A/B axes are product-specific, same-material binding is exact, and r3's enum-authority defects are closed. However, every path carries unresolved fake-use evidence for selected components and depends on noncomposable profile/lane registries. That major defect invokes repair rather than approval; no activation is authorized.

### `P2R4-AB-CP07`

Decision: **REPAIR**; grade B (84/100); severity MAJOR.

- The actual CP07 path payload was read in packet position 13. Condition decision tree versus exclusion/alternative reasoning fits a real-question response. Its reviewed lane program is: narrative_mechanism condition_decision_tree -> exclusion_then_alternative; information_order question_condition_option -> not_fit_reason_alternative; visual_subject specific_task -> counter_condition; sound_subject direct_role_voice -> patient_explanation; rhythm decision_steps -> elimination_steps; ending bounded_option -> request_missing_condition.
- Exact-commit replay realized both lanes over byte-identical typed material in independent sessions. All 12 dedicated axis pointers resolved, all 12 packet structural-output contracts matched, and all six A/B structural_body digests differed.
- Per-path adversarial replay rejected all 12 unknown-enum substitutions, all 12 opposite-lane known-enum substitutions, missing/extra-axis mutations, component/material claim-boundary tampering, and every operator-binding, allowed-values, program, mechanism, and target-receipt mutation.
- The selected-component use claim is false as emitted: 0/20 generic component_contributions pointers for this path resolve because the core points to /structural_realization/lane_{id}/{role}/{index}, while the emitted object contains only lane_{id}/axes. The path still reports every selected component as realized and reports zero unrealized components.
- In addition, 1/8 non-axis lane bindings for CP07 contribute no fact-role reference to that lane's structural bodies. The ablation harness rejects removal at exact-set validation, so its changed/rejected result proves membership integrity, not an observable component-specific implementation effect required by execution brief section 7.3.
- The path also depends on six profile/lane template registries whose component-level composability remains below the frozen 17/20 threshold. Move product-specific programs into the path contract, emit resolvable component-specific structural objects or mark components honestly unrealized, and demonstrate an effect-level ablation after validation.

Scored under the closest enabled content-product and structural-composition path view. The A/B axes are product-specific, same-material binding is exact, and r3's enum-authority defects are closed. However, every path carries unresolved fake-use evidence for selected components and depends on noncomposable profile/lane registries. That major defect invokes repair rather than approval; no activation is authorized.

### `P2R4-AB-CP08`

Decision: **REPAIR**; grade C (78/100); severity MAJOR.

- The actual CP08 path payload was read in packet position 14. Outer-to-inner deconstruction versus evidence-result reverse trace fits material and construction explanation. Its reviewed lane program is: narrative_mechanism outer_to_inner_deconstruction -> evidence_result_reverse; information_order surface_structure_limit -> limit_structure_surface; visual_subject construction_detail -> detail_relation_map; sound_subject operation_sync -> source_cue; rhythm micro_to_structure -> structure_pulse; ending evidence_boundary -> no_performance_inference.
- Exact-commit replay realized both lanes over byte-identical typed material in independent sessions. All 12 dedicated axis pointers resolved, all 12 packet structural-output contracts matched, and all six A/B structural_body digests differed.
- Per-path adversarial replay rejected all 12 unknown-enum substitutions, all 12 opposite-lane known-enum substitutions, missing/extra-axis mutations, component/material claim-boundary tampering, and every operator-binding, allowed-values, program, mechanism, and target-receipt mutation.
- The selected-component use claim is false as emitted: 0/20 generic component_contributions pointers for this path resolve because the core points to /structural_realization/lane_{id}/{role}/{index}, while the emitted object contains only lane_{id}/axes. The path still reports every selected component as realized and reports zero unrealized components.
- In addition, 5/8 non-axis lane bindings for CP08 contribute no fact-role reference to that lane's structural bodies. The ablation harness rejects removal at exact-set validation, so its changed/rejected result proves membership integrity, not an observable component-specific implementation effect required by execution brief section 7.3.
- The path also depends on six profile/lane template registries whose component-level composability remains below the frozen 17/20 threshold. Move product-specific programs into the path contract, emit resolvable component-specific structural objects or mark components honestly unrealized, and demonstrate an effect-level ablation after validation.

Scored under the closest enabled content-product and structural-composition path view. The A/B axes are product-specific, same-material binding is exact, and r3's enum-authority defects are closed. However, every path carries unresolved fake-use evidence for selected components and depends on noncomposable profile/lane registries. That major defect invokes repair rather than approval; no activation is authorized.

### `P2R4-AB-CP09`

Decision: **REPAIR**; grade B (84/100); severity MAJOR.

- The actual CP09 path payload was read in packet position 15. Fit/nonfit conditions versus disqualifier-first reasoning fits nonjudgmental applicability guidance. Its reviewed lane program is: narrative_mechanism fit_then_nonfit -> disqualifier_first; information_order condition_applicable_excluded -> excluded_reason_fit; visual_subject condition_table -> counterexample; sound_subject direct_boundary_voice -> nonjudgmental_voice; rhythm condition_steps -> reverse_decision; ending alternative -> ask_for_condition.
- Exact-commit replay realized both lanes over byte-identical typed material in independent sessions. All 12 dedicated axis pointers resolved, all 12 packet structural-output contracts matched, and all six A/B structural_body digests differed.
- Per-path adversarial replay rejected all 12 unknown-enum substitutions, all 12 opposite-lane known-enum substitutions, missing/extra-axis mutations, component/material claim-boundary tampering, and every operator-binding, allowed-values, program, mechanism, and target-receipt mutation.
- The selected-component use claim is false as emitted: 0/20 generic component_contributions pointers for this path resolve because the core points to /structural_realization/lane_{id}/{role}/{index}, while the emitted object contains only lane_{id}/axes. The path still reports every selected component as realized and reports zero unrealized components.
- In addition, 2/8 non-axis lane bindings for CP09 contribute no fact-role reference to that lane's structural bodies. The ablation harness rejects removal at exact-set validation, so its changed/rejected result proves membership integrity, not an observable component-specific implementation effect required by execution brief section 7.3.
- The path also depends on six profile/lane template registries whose component-level composability remains below the frozen 17/20 threshold. Move product-specific programs into the path contract, emit resolvable component-specific structural objects or mark components honestly unrealized, and demonstrate an effect-level ablation after validation.

Scored under the closest enabled content-product and structural-composition path view. The A/B axes are product-specific, same-material binding is exact, and r3's enum-authority defects are closed. However, every path carries unresolved fake-use evidence for selected components and depends on noncomposable profile/lane registries. That major defect invokes repair rather than approval; no activation is authorized.

### `P2R4-AB-CP10`

Decision: **REPAIR**; grade B (84/100); severity MAJOR.

- The actual CP10 path payload was read in packet position 16. Hypothesis-record-result versus result-to-record trace fits tracked observation rather than universal claims. Its reviewed lane program is: narrative_mechanism hypothesis_record_result -> result_to_record_trace; information_order time_record_limit -> result_record_hypothesis; visual_subject matched_frame -> evidence_ledger; sound_subject dated_cue -> record_marker; rhythm log_interval -> reverse_log; ending limited_result -> next_review.
- Exact-commit replay realized both lanes over byte-identical typed material in independent sessions. All 12 dedicated axis pointers resolved, all 12 packet structural-output contracts matched, and all six A/B structural_body digests differed.
- Per-path adversarial replay rejected all 12 unknown-enum substitutions, all 12 opposite-lane known-enum substitutions, missing/extra-axis mutations, component/material claim-boundary tampering, and every operator-binding, allowed-values, program, mechanism, and target-receipt mutation.
- The selected-component use claim is false as emitted: 0/20 generic component_contributions pointers for this path resolve because the core points to /structural_realization/lane_{id}/{role}/{index}, while the emitted object contains only lane_{id}/axes. The path still reports every selected component as realized and reports zero unrealized components.
- In addition, 2/8 non-axis lane bindings for CP10 contribute no fact-role reference to that lane's structural bodies. The ablation harness rejects removal at exact-set validation, so its changed/rejected result proves membership integrity, not an observable component-specific implementation effect required by execution brief section 7.3.
- The path also depends on six profile/lane template registries whose component-level composability remains below the frozen 17/20 threshold. Move product-specific programs into the path contract, emit resolvable component-specific structural objects or mark components honestly unrealized, and demonstrate an effect-level ablation after validation.

Scored under the closest enabled content-product and structural-composition path view. The A/B axes are product-specific, same-material binding is exact, and r3's enum-authority defects are closed. However, every path carries unresolved fake-use evidence for selected components and depends on noncomposable profile/lane registries. That major defect invokes repair rather than approval; no activation is authorized.

### `P2R4-AB-CP11`

Decision: **REPAIR**; grade B (81/100); severity MAJOR.

- The actual CP11 path payload was read in packet position 17. Problem-options-choice versus abandoned-option-first makes actual tradeoffs visible. Its reviewed lane program is: narrative_mechanism problem_options_choice -> abandoned_option_first; information_order problem_option_choice_cost -> cost_abandonment_choice; visual_subject option_artifacts -> discarded_option_trace; sound_subject document_cue -> field_marker; rhythm decision_sequence -> tradeoff_pulse; ending recorded_tradeoff -> open_constraint.
- Exact-commit replay realized both lanes over byte-identical typed material in independent sessions. All 12 dedicated axis pointers resolved, all 12 packet structural-output contracts matched, and all six A/B structural_body digests differed.
- Per-path adversarial replay rejected all 12 unknown-enum substitutions, all 12 opposite-lane known-enum substitutions, missing/extra-axis mutations, component/material claim-boundary tampering, and every operator-binding, allowed-values, program, mechanism, and target-receipt mutation.
- The selected-component use claim is false as emitted: 0/22 generic component_contributions pointers for this path resolve because the core points to /structural_realization/lane_{id}/{role}/{index}, while the emitted object contains only lane_{id}/axes. The path still reports every selected component as realized and reports zero unrealized components.
- In addition, 3/10 non-axis lane bindings for CP11 contribute no fact-role reference to that lane's structural bodies. The ablation harness rejects removal at exact-set validation, so its changed/rejected result proves membership integrity, not an observable component-specific implementation effect required by execution brief section 7.3.
- The path also depends on six profile/lane template registries whose component-level composability remains below the frozen 17/20 threshold. Move product-specific programs into the path contract, emit resolvable component-specific structural objects or mark components honestly unrealized, and demonstrate an effect-level ablation after validation.

Scored under the closest enabled content-product and structural-composition path view. The A/B axes are product-specific, same-material binding is exact, and r3's enum-authority defects are closed. However, every path carries unresolved fake-use evidence for selected components and depends on noncomposable profile/lane registries. That major defect invokes repair rather than approval; no activation is authorized.

### `P2R4-AB-CP12`

Decision: **REPAIR**; grade B (81/100); severity MAJOR.

- The actual CP12 path payload was read in packet position 18. Version chronology versus current-to-prior trace fits authenticated version comparison. Its reviewed lane program is: narrative_mechanism version_chronology -> current_to_prior_trace; information_order prior_change_current_pending -> current_difference_prior_cause; visual_subject matched_version_action -> difference_first; sound_subject version_marker -> record_cue; rhythm comparison_steps -> reverse_version_pulse; ending pending_validation -> unverified_result.
- Exact-commit replay realized both lanes over byte-identical typed material in independent sessions. All 12 dedicated axis pointers resolved, all 12 packet structural-output contracts matched, and all six A/B structural_body digests differed.
- Per-path adversarial replay rejected all 12 unknown-enum substitutions, all 12 opposite-lane known-enum substitutions, missing/extra-axis mutations, component/material claim-boundary tampering, and every operator-binding, allowed-values, program, mechanism, and target-receipt mutation.
- The selected-component use claim is false as emitted: 0/20 generic component_contributions pointers for this path resolve because the core points to /structural_realization/lane_{id}/{role}/{index}, while the emitted object contains only lane_{id}/axes. The path still reports every selected component as realized and reports zero unrealized components.
- In addition, 1/8 non-axis lane bindings for CP12 contribute no fact-role reference to that lane's structural bodies. The ablation harness rejects removal at exact-set validation, so its changed/rejected result proves membership integrity, not an observable component-specific implementation effect required by execution brief section 7.3.
- The path also depends on six profile/lane template registries whose component-level composability remains below the frozen 17/20 threshold. Move product-specific programs into the path contract, emit resolvable component-specific structural objects or mark components honestly unrealized, and demonstrate an effect-level ablation after validation.
- Additional CP12 ending defect: pending_validation versus unverified_result uses the same boundary fact references and booleans; only closure_mode and next_step_policy strings differ, so removing policy labels eliminates the ending transformation.

Scored under the closest enabled content-product and structural-composition path view. The A/B axes are product-specific, same-material binding is exact, and r3's enum-authority defects are closed. However, every path carries unresolved fake-use evidence for selected components and depends on noncomposable profile/lane registries. That major defect invokes repair rather than approval; no activation is authorized.

### `P2R4-AB-CP13`

Decision: **REPAIR**; grade B (81/100); severity MAJOR.

- The actual CP13 path payload was read in packet position 19. Life-context sequence versus same-object role map fits context-based observation without body judgment. Its reviewed lane program is: narrative_mechanism life_context_sequence -> same_object_role_map; information_order context_role_relation -> role_condition_context; visual_subject same_item_context -> fixed_object_compare; sound_subject context_source_cue -> condition_marker; rhythm context_steps -> role_map_pulse; ending bounded_role -> not_body_judgment.
- Exact-commit replay realized both lanes over byte-identical typed material in independent sessions. All 12 dedicated axis pointers resolved, all 12 packet structural-output contracts matched, and all six A/B structural_body digests differed.
- Per-path adversarial replay rejected all 12 unknown-enum substitutions, all 12 opposite-lane known-enum substitutions, missing/extra-axis mutations, component/material claim-boundary tampering, and every operator-binding, allowed-values, program, mechanism, and target-receipt mutation.
- The selected-component use claim is false as emitted: 0/20 generic component_contributions pointers for this path resolve because the core points to /structural_realization/lane_{id}/{role}/{index}, while the emitted object contains only lane_{id}/axes. The path still reports every selected component as realized and reports zero unrealized components.
- In addition, 2/8 non-axis lane bindings for CP13 contribute no fact-role reference to that lane's structural bodies. The ablation harness rejects removal at exact-set validation, so its changed/rejected result proves membership integrity, not an observable component-specific implementation effect required by execution brief section 7.3.
- The path also depends on six profile/lane template registries whose component-level composability remains below the frozen 17/20 threshold. Move product-specific programs into the path contract, emit resolvable component-specific structural objects or mark components honestly unrealized, and demonstrate an effect-level ablation after validation.
- Additional CP13 ending defect: bounded_role versus not_body_judgment uses the same boundary fact references and booleans; only closure_mode and next_step_policy strings differ, so removing policy labels eliminates the ending transformation.

Scored under the closest enabled content-product and structural-composition path view. The A/B axes are product-specific, same-material binding is exact, and r3's enum-authority defects are closed. However, every path carries unresolved fake-use evidence for selected components and depends on noncomposable profile/lane registries. That major defect invokes repair rather than approval; no activation is authorized.

### `P2R4-AB-CP14`

Decision: **REPAIR**; grade B (84/100); severity MAJOR.

- The actual CP14 path payload was read in packet position 20. A property visual motif versus contact-sound pulse fits an object-centered sensory material study. Its reviewed lane program is: narrative_mechanism single_property_visual_motif -> contact_sound_pulse; information_order surface_contact_detail -> sound_contact_pause; visual_subject material_contact -> same_property_detail; sound_subject environment_source_sound -> contact_anchor; rhythm slow_contact -> silent_evidence_pulse; ending visible_property_only -> sensory_limit.
- Exact-commit replay realized both lanes over byte-identical typed material in independent sessions. All 12 dedicated axis pointers resolved, all 12 packet structural-output contracts matched, and all six A/B structural_body digests differed.
- Per-path adversarial replay rejected all 12 unknown-enum substitutions, all 12 opposite-lane known-enum substitutions, missing/extra-axis mutations, component/material claim-boundary tampering, and every operator-binding, allowed-values, program, mechanism, and target-receipt mutation.
- The selected-component use claim is false as emitted: 0/20 generic component_contributions pointers for this path resolve because the core points to /structural_realization/lane_{id}/{role}/{index}, while the emitted object contains only lane_{id}/axes. The path still reports every selected component as realized and reports zero unrealized components.
- In addition, 1/8 non-axis lane bindings for CP14 contribute no fact-role reference to that lane's structural bodies. The ablation harness rejects removal at exact-set validation, so its changed/rejected result proves membership integrity, not an observable component-specific implementation effect required by execution brief section 7.3.
- The path also depends on six profile/lane template registries whose component-level composability remains below the frozen 17/20 threshold. Move product-specific programs into the path contract, emit resolvable component-specific structural objects or mark components honestly unrealized, and demonstrate an effect-level ablation after validation.

Scored under the closest enabled content-product and structural-composition path view. The A/B axes are product-specific, same-material binding is exact, and r3's enum-authority defects are closed. However, every path carries unresolved fake-use evidence for selected components and depends on noncomposable profile/lane registries. That major defect invokes repair rather than approval; no activation is authorized.

### `P2R4-AB-CP15`

Decision: **REPAIR**; grade B (81/100); severity MAJOR.

- The actual CP15 path payload was read in packet position 21. Goods lifecycle versus state-map handoff fits goods-status operations. Its reviewed lane program is: narrative_mechanism goods_lifecycle -> state_map_handoff; information_order arrival_action_handoff -> state_blocker_next; visual_subject goods_and_actor -> status_map; sound_subject operation_sound -> time_anchor; rhythm stage_sequence -> state_pulse; ending current_stage -> pending_handoff.
- Exact-commit replay realized both lanes over byte-identical typed material in independent sessions. All 12 dedicated axis pointers resolved, all 12 packet structural-output contracts matched, and all six A/B structural_body digests differed.
- Per-path adversarial replay rejected all 12 unknown-enum substitutions, all 12 opposite-lane known-enum substitutions, missing/extra-axis mutations, component/material claim-boundary tampering, and every operator-binding, allowed-values, program, mechanism, and target-receipt mutation.
- The selected-component use claim is false as emitted: 0/20 generic component_contributions pointers for this path resolve because the core points to /structural_realization/lane_{id}/{role}/{index}, while the emitted object contains only lane_{id}/axes. The path still reports every selected component as realized and reports zero unrealized components.
- In addition, 3/8 non-axis lane bindings for CP15 contribute no fact-role reference to that lane's structural bodies. The ablation harness rejects removal at exact-set validation, so its changed/rejected result proves membership integrity, not an observable component-specific implementation effect required by execution brief section 7.3.
- The path also depends on six profile/lane template registries whose component-level composability remains below the frozen 17/20 threshold. Move product-specific programs into the path contract, emit resolvable component-specific structural objects or mark components honestly unrealized, and demonstrate an effect-level ablation after validation.

Scored under the closest enabled content-product and structural-composition path view. The A/B axes are product-specific, same-material binding is exact, and r3's enum-authority defects are closed. However, every path carries unresolved fake-use evidence for selected components and depends on noncomposable profile/lane registries. That major defect invokes repair rather than approval; no activation is authorized.

### `P2R4-AB-CP16`

Decision: **REPAIR**; grade B (84/100); severity MAJOR.

- The actual CP16 path payload was read in packet position 22. Need-judgment-option-feedback versus task-friction-first fits authorized service-need review and avoids heroization. Its reviewed lane program is: narrative_mechanism need_judgment_option_feedback -> task_friction_first; information_order need_option_action_feedback -> friction_evidence_option; visual_subject service_action -> shared_object; sound_subject role_dialogue -> separate_role_cues; rhythm service_steps -> evidence_pulse; ending feedback_boundary -> no_hero_claim.
- Exact-commit replay realized both lanes over byte-identical typed material in independent sessions. All 12 dedicated axis pointers resolved, all 12 packet structural-output contracts matched, and all six A/B structural_body digests differed.
- Per-path adversarial replay rejected all 12 unknown-enum substitutions, all 12 opposite-lane known-enum substitutions, missing/extra-axis mutations, component/material claim-boundary tampering, and every operator-binding, allowed-values, program, mechanism, and target-receipt mutation.
- The selected-component use claim is false as emitted: 0/20 generic component_contributions pointers for this path resolve because the core points to /structural_realization/lane_{id}/{role}/{index}, while the emitted object contains only lane_{id}/axes. The path still reports every selected component as realized and reports zero unrealized components.
- In addition, 1/8 non-axis lane bindings for CP16 contribute no fact-role reference to that lane's structural bodies. The ablation harness rejects removal at exact-set validation, so its changed/rejected result proves membership integrity, not an observable component-specific implementation effect required by execution brief section 7.3.
- The path also depends on six profile/lane template registries whose component-level composability remains below the frozen 17/20 threshold. Move product-specific programs into the path contract, emit resolvable component-specific structural objects or mark components honestly unrealized, and demonstrate an effect-level ablation after validation.

Scored under the closest enabled content-product and structural-composition path view. The A/B axes are product-specific, same-material binding is exact, and r3's enum-authority defects are closed. However, every path carries unresolved fake-use evidence for selected components and depends on noncomposable profile/lane registries. That major defect invokes repair rather than approval; no activation is authorized.

### `P2R4-AB-CP17`

Decision: **REPAIR**; grade B (84/100); severity MAJOR.

- The actual CP17 path payload was read in packet position 23. Hypothesis-adjust-compare versus result-first spatial trace fits a bounded store experiment. Its reviewed lane program is: narrative_mechanism hypothesis_adjust_compare -> result_first_spatial_trace; information_order hypothesis_action_before_after -> result_change_hypothesis; visual_subject fixed_space -> state_map_detail; sound_subject operation_sound -> time_marker; rhythm experiment_steps -> comparison_pulse; ending review_state -> no_causal_overclaim.
- Exact-commit replay realized both lanes over byte-identical typed material in independent sessions. All 12 dedicated axis pointers resolved, all 12 packet structural-output contracts matched, and all six A/B structural_body digests differed.
- Per-path adversarial replay rejected all 12 unknown-enum substitutions, all 12 opposite-lane known-enum substitutions, missing/extra-axis mutations, component/material claim-boundary tampering, and every operator-binding, allowed-values, program, mechanism, and target-receipt mutation.
- The selected-component use claim is false as emitted: 0/22 generic component_contributions pointers for this path resolve because the core points to /structural_realization/lane_{id}/{role}/{index}, while the emitted object contains only lane_{id}/axes. The path still reports every selected component as realized and reports zero unrealized components.
- In addition, 1/10 non-axis lane bindings for CP17 contribute no fact-role reference to that lane's structural bodies. The ablation harness rejects removal at exact-set validation, so its changed/rejected result proves membership integrity, not an observable component-specific implementation effect required by execution brief section 7.3.
- The path also depends on six profile/lane template registries whose component-level composability remains below the frozen 17/20 threshold. Move product-specific programs into the path contract, emit resolvable component-specific structural objects or mark components honestly unrealized, and demonstrate an effect-level ablation after validation.

Scored under the closest enabled content-product and structural-composition path view. The A/B axes are product-specific, same-material binding is exact, and r3's enum-authority defects are closed. However, every path carries unresolved fake-use evidence for selected components and depends on noncomposable profile/lane registries. That major defect invokes repair rather than approval; no activation is authorized.

### `P2R4-AB-CP18`

Decision: **REPAIR**; grade B (84/100); severity MAJOR.

- The actual CP18 path payload was read in packet position 24. Authorized place-time chronicle versus sound-anchored time slices fits local store life without invented locality. Its reviewed lane program is: narrative_mechanism authorized_place_time_chronicle -> sound_anchor_time_slices; information_order place_time_task -> sound_state_time; visual_subject local_store_anchor -> same_place_detail; sound_subject authorized_soundscape -> time_sound_anchor; rhythm daily_duration -> seasonal_pulse; ending local_boundary -> no_locality_invention.
- Exact-commit replay realized both lanes over byte-identical typed material in independent sessions. All 12 dedicated axis pointers resolved, all 12 packet structural-output contracts matched, and all six A/B structural_body digests differed.
- Per-path adversarial replay rejected all 12 unknown-enum substitutions, all 12 opposite-lane known-enum substitutions, missing/extra-axis mutations, component/material claim-boundary tampering, and every operator-binding, allowed-values, program, mechanism, and target-receipt mutation.
- The selected-component use claim is false as emitted: 0/20 generic component_contributions pointers for this path resolve because the core points to /structural_realization/lane_{id}/{role}/{index}, while the emitted object contains only lane_{id}/axes. The path still reports every selected component as realized and reports zero unrealized components.
- In addition, 1/8 non-axis lane bindings for CP18 contribute no fact-role reference to that lane's structural bodies. The ablation harness rejects removal at exact-set validation, so its changed/rejected result proves membership integrity, not an observable component-specific implementation effect required by execution brief section 7.3.
- The path also depends on six profile/lane template registries whose component-level composability remains below the frozen 17/20 threshold. Move product-specific programs into the path contract, emit resolvable component-specific structural objects or mark components honestly unrealized, and demonstrate an effect-level ablation after validation.

Scored under the closest enabled content-product and structural-composition path view. The A/B axes are product-specific, same-material binding is exact, and r3's enum-authority defects are closed. However, every path carries unresolved fake-use evidence for selected components and depends on noncomposable profile/lane registries. That major defect invokes repair rather than approval; no activation is authorized.

### `P2R4-AB-CP19`

Decision: **REPAIR**; grade B (84/100); severity MAJOR.

- The actual CP19 path payload was read in packet position 25. Context-options-choice-cost versus cost-result reverse fits real decision tradeoffs. Its reviewed lane program is: narrative_mechanism context_options_choice_cost -> cost_result_reverse; information_order context_option_abandonment_result -> cost_abandonment_choice_context; visual_subject decision_record -> evidence_ledger; sound_subject authorized_role_voice -> record_cue; rhythm tradeoff_sequence -> reverse_tradeoff; ending bounded_result -> open_cost.
- Exact-commit replay realized both lanes over byte-identical typed material in independent sessions. All 12 dedicated axis pointers resolved, all 12 packet structural-output contracts matched, and all six A/B structural_body digests differed.
- Per-path adversarial replay rejected all 12 unknown-enum substitutions, all 12 opposite-lane known-enum substitutions, missing/extra-axis mutations, component/material claim-boundary tampering, and every operator-binding, allowed-values, program, mechanism, and target-receipt mutation.
- The selected-component use claim is false as emitted: 0/20 generic component_contributions pointers for this path resolve because the core points to /structural_realization/lane_{id}/{role}/{index}, while the emitted object contains only lane_{id}/axes. The path still reports every selected component as realized and reports zero unrealized components.
- In addition, 2/8 non-axis lane bindings for CP19 contribute no fact-role reference to that lane's structural bodies. The ablation harness rejects removal at exact-set validation, so its changed/rejected result proves membership integrity, not an observable component-specific implementation effect required by execution brief section 7.3.
- The path also depends on six profile/lane template registries whose component-level composability remains below the frozen 17/20 threshold. Move product-specific programs into the path contract, emit resolvable component-specific structural objects or mark components honestly unrealized, and demonstrate an effect-level ablation after validation.

Scored under the closest enabled content-product and structural-composition path view. The A/B axes are product-specific, same-material binding is exact, and r3's enum-authority defects are closed. However, every path carries unresolved fake-use evidence for selected components and depends on noncomposable profile/lane registries. That major defect invokes repair rather than approval; no activation is authorized.

### `P2R4-AB-CP20`

Decision: **REPAIR**; grade C (77/100); severity MAJOR.

- The actual CP20 path payload was read in packet position 26. Commitment-node evidence versus deviation-first audit fits evidence-based commitment tracking. Its reviewed lane program is: narrative_mechanism commitment_node_evidence -> deviation_evidence_first; information_order commitment_node_result_next -> deviation_evidence_commitment; visual_subject commitment_record -> evidence_gap; sound_subject dated_record_cue -> exception_marker; rhythm review_sequence -> audit_pulse; ending next_node -> no_emotional_substitute.
- Exact-commit replay realized both lanes over byte-identical typed material in independent sessions. All 12 dedicated axis pointers resolved, all 12 packet structural-output contracts matched, and all six A/B structural_body digests differed.
- Per-path adversarial replay rejected all 12 unknown-enum substitutions, all 12 opposite-lane known-enum substitutions, missing/extra-axis mutations, component/material claim-boundary tampering, and every operator-binding, allowed-values, program, mechanism, and target-receipt mutation.
- The selected-component use claim is false as emitted: 0/20 generic component_contributions pointers for this path resolve because the core points to /structural_realization/lane_{id}/{role}/{index}, while the emitted object contains only lane_{id}/axes. The path still reports every selected component as realized and reports zero unrealized components.
- In addition, 5/8 non-axis lane bindings for CP20 contribute no fact-role reference to that lane's structural bodies. The ablation harness rejects removal at exact-set validation, so its changed/rejected result proves membership integrity, not an observable component-specific implementation effect required by execution brief section 7.3.
- The path also depends on six profile/lane template registries whose component-level composability remains below the frozen 17/20 threshold. Move product-specific programs into the path contract, emit resolvable component-specific structural objects or mark components honestly unrealized, and demonstrate an effect-level ablation after validation.

Scored under the closest enabled content-product and structural-composition path view. The A/B axes are product-specific, same-material binding is exact, and r3's enum-authority defects are closed. However, every path carries unresolved fake-use evidence for selected components and depends on noncomposable profile/lane registries. That major defect invokes repair rather than approval; no activation is authorized.

### `P2R4-GENERATOR-CORE`

Decision: **REPAIR**; grade C (77/100); severity MAJOR.

- The actual core contract payload and its committed controlled_content_generator_v2_001/gate1_v1_1_001/p2_component_supply_and_generator_core_repair_001/p2_generator_core_r4.py and axis-semantics source were read in packet position 27; their SHA-256 values match the packet and reviewed commit.
- Static and executable checks confirm no hash/token-derived semantic selection in the active r4 core. It performs exact profile/value program lookup, requires the exact six-axis set, binds the authoritative path/lane, and rejects unknown or opposite-lane reviewed values.
- All 40 author requests realized; 20/20 A/B pairs preserved identical typed material; 240/240 dedicated axis pointers resolved; all 120 body digests differed; and 40/40 audience fields remained empty. Independent tamper matrices rejected every tested component/material boundary, axis-set, operator binding, allowed-values receipt, target receipt, program receipt, and mechanism receipt mutation.
- The core nevertheless fabricates selected-component realization evidence. It appends component_contributions with pointers under /structural_realization/lane_{id}/{role}/{index}, but the realization contains only /structural_realization/lane_{id}/axes. Exactly 0/410 claimed contribution pointers resolve while realized_component_count equals selected_component_count and unrealized_component_count is zero.
- Of 170 non-axis lane bindings, 46 have no fact-role reference in the emitted structural bodies. The 410/410 ablation result is produced by rejecting a request that no longer equals the authoritative component set, not by observing the corresponding component's implementation change. This violates execution brief sections 7.3 and 12's prohibition on counting metadata-only selected components as realized.
- The six consumed operators embed 240 profile/lane programs with 232 distinct enum names and almost entirely one-off executable payloads. Narrative duplicates information order and ending boundary in 40/40 programs; rhythm duplicates information order in 40/40 programs.
- A stricter label-free check finds only 117/120 fact-role topologies differ: CP05, CP12, and CP13 endings retain identical fact references and booleans and differ only in closure/policy enum strings.
- Repair requires resolvable component-specific implementation objects (or honest unrealized status), effect-level ablation after successful validation, reusable atomic axis operators separated from product/lane program data, and explicit closure action structures for the three policy-only ending pairs.

Scored under the closest enabled generator and content-composition-plan view. The r4 validator closes the prior hash/token, enum-authority, six-axis, and receipt-tamper defects, but it still makes a materially false component-realization claim and consumes payload-sized program registries. These are major, repairable defects, so the core is not approved.

## Coverage And Independence Assertion

I explicitly attest that I actually read and independently decided every one of the 27 packet items in packet order against its actual committed payload and executable behavior. The records file contains exactly one canonical-digest-bound record per item in that same order.

I did not read or use any sibling, secondary, or other-reviewer output. I wrote no repository file, activated nothing, changed no readiness flag, and made no audience-content or quality claim. The review is bound only to commit `87d3ca89ba9cbb743ee82af105cf831bbd8e2dab` and packet SHA-256 `95c2a44e8d473844ada77d242ede0299a6b4db63b2699dfc633af0704d2c7e72`.

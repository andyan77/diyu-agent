# Semantic Pilot V4.3 Judge Protocol

Task: `CODEX-SEMANTIC-PILOT-V4_2-NOGO-CLOSEOUT-PREDICATE-REGISTRY-AND-V4_3-TARGETED-REPAIR-001`

V4.3 is a targeted repair set, not accepted domain knowledge. Judge review must decide whether the eight drafts are semantically useful enough to become future exemplars. The default remains no batch generation.

Required judge checks:

- Confirm `claim_boundary` and `asset_binding_policy_candidate` appear only as profile/body-shape concepts, never as strict `owner_model.artifact_kind` values.
- Confirm claim-boundary cards have source workorder hints and do not use display or camera predicates.
- Confirm display cards have ordered steps, completion conditions, stop conditions, and authorization/privacy boundaries.
- Confirm control-plane route target is `founder_review` where W7 requires founder review.
- Confirm control-plane 002 is resliced to `asset_binding_policy_candidate` profile with strict artifact kind `governance_outbox_candidate` and storage target `GovernanceOutbox`.
- Keep `accepted_domain_knowledge_count: 0`, `batch_generation_unlocked: false`, and all readiness flags false until judge/human approval.

Recommended next step after this package: `CODEX-SEMANTIC-PILOT-V4_3-JUDGE-GO-NOGO-001`.

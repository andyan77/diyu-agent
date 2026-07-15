# AGENTS.md

## Project role

This repository is the single business repository for the Diyu content agent.
The current product route is declared by:

- `project-infra/current_product_status.v1.yaml`
- `project-infra/product_workspace_manifest.v1.yaml`
- `11_product_foundation/public_foundation_001/`

Older knowledge-engineering manifests remain historical evidence. They must not
be used to infer the current product phase or silently rewritten.

## Authority boundaries

- Server-confirmed tenant, organization, store, login user, and content-account
  scope is authoritative. User or Dify input cannot widen it.
- Login identity and outward-facing content account are separate objects. Real
  people never share credentials. A simulation exception must be explicit and
  non-publishable.
- Narrative retrieval is supporting evidence. It cannot grant authorization or
  override a newer exact fact for SKU, specification, price, stock, time,
  authorization, or revocation.
- Expression components, rules, edges, and A/B paths are referenced expression
  assets. They are not brand facts, permissions, stock records, or source text.
- A confirmed requirement version may have one canonical composition plan.
  The expression `prepare` operation owns that plan; Dify, retrieval, and the
  generator may not create competing canonical plans.
- No evidence or authorization means no publishable output. Missing inputs must
  produce an action card, degradation, or stop decision.

## Historical and forbidden default writes

Unless an execution brief explicitly authorizes them, do not modify:

- `KE/**`
- `serving_projection/**`
- `rag/**`
- `dify/**`
- `candidatepack_etl/candidatepack_instances/**`
- P1-P4 evidence, gold answers, first failures, or frozen expression assets
- runtime or production files
- secret files or external service configuration

Never write raw Markdown or model output directly into ABox, TBox, Evidence,
brand facts, or another truth source. User feedback cannot directly write those
truth sources.

## Readiness flags

Unless a task explicitly authorizes a transition, all of these remain false:

- candidatepack_ready
- KE_ready
- RAG_ready
- DIFY_ready
- production_servable
- generation_eligible
- generation_allowed
- generator_qualified
- retrieval_ready
- runtime_ready
- release_ready
- production_ready

## Execution discipline

- Read the current execution brief and nearest `AGENTS.md` before writing.
- Verify the expected HEAD, branch, worktree, and allowed write surface.
- Work with unrelated user changes; never delete or revert them.
- Stop before production, external runtime, secrets, paid services, or a truth
  transition that lacks explicit authorization.
- Prefer the repository's current contracts and checkers over parallel models.
- Run the task's delta checks and report changed files, failures, remote checks,
  and every readiness transition.

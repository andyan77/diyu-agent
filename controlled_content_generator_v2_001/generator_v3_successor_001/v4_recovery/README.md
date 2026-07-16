# Gate1 v4 recovery

`v4_recovery` is an isolated, qualification-only recovery candidate. It does
not modify or reinterpret any historical G3, P7, or R1-R5 artifact, and it is
not a production generator.

## Non-negotiable invariants

1. There is one `gate1_test_assignment` per sealed scenario. It is a test
   allocation record, **not** the formal content-composition plan defined by
   later V1.1 gates.
2. `batch_id` identifies an execution only. It never participates in test
   assignment allocation.
3. CP01, CP02, and CP03 use explicit, frozen profile overrides for their
   already-verified task/time-window/process structures. CP04-CP20 use their
   family default divergence strategies; an override can never silently fall
   back to the family pool.
4. Every material fact cites one or more exact UTF-8 source spans. A source ID
   alone is never factual support. Material has three audience-surface policies:
   `MUST_SURFACE`, `MAY_SURFACE`, and `CONTROL_ONLY`. Control-only facts remain
   visible to the author and verifier as constraints but may not be bound to an
   audience surface.
5. Material, assignment, policy, request, output, gate, metric, and telemetry
   objects are digest-closed. A downstream object carries and validates its
   upstream digests.
6. Qualification mode accepts exactly the first attempt. No feedback-driven
   retry, replacement candidate, or denominator deletion is allowed.
7. Whole-batch hard veto zero is a real conjunctive gate. A veto in a rejected
   candidate still fails the batch.
8. Machine semantic or similarity signals may queue review, but do not become
   factuality or formulaic verdicts merely by crossing a threshold.
9. Missing provider call receipts, usage, or cost data are recorded as
   `unavailable` with a
   reason. It is never represented by a fabricated zero.
10. Profile capacity counts only independently assessed, material-bound legal
    assignments. Semantic material diversity and assignment-DNA diversity are
    separate gates: renamed clones do not increase capacity. Each CP needs 12;
    15 is only a buffer target. Without material coverage for all 20 CPs the
    status is `NOT_EVALUATED`, and a shortfall is `REQUEST_CURATION`.

## Modules

- `contract.py`: schemas, canonical serialization, digests, fail-closed helpers.
- `material_policy.py`: exact source-span evidence validation and three-way
  surface policy.
- `test_allocator.py`: stable family-aware Gate1 test assignments and the
  observed-capacity audit plus the read-only R5 90/120 mismatch diagnostic.
- `request_builder.py`: request construction with material/assignment closure.
- `author_contract.py`: first-attempt author output contract and serialization.
- `deterministic_claims.py` and `registry/deterministic_claim_registry.v1.json`:
  a preregistered, deliberately incomplete known-risk gate for fiber,
  composition, construction, durability, and performance claims. A registered
  term is authorized only when it appears in both the bound fact value and an
  independently reverified source quote; unregistered semantics still require
  fact review.
- `deterministic_gates.py`: deterministic safety/contract gates only; its
  report binds the known-risk registry digest.
- `metrics.py`: sealed-batch metrics and true whole-batch conjunctive verdict.
- `telemetry.py`: per-event telemetry plus the V1.1 run-manifest contract.
  Author-generation events must join the exact request/output digests and carry
  a non-empty provider call receipt for complete telemetry. Qualification also
  requires exact author, deterministic-gate, content-review, fact-review, and
  metrics event coverage; unknown or missing events fail closed. Run-manifest
  input/output/model bindings are recomputed from the sealed batch, and the
  telemetry summary binds the exact `event_id`/`event_digest` manifest rather
  than only aggregate totals.

The v4 event is the detailed B-side record. `to_eval_spine_cost_event()` maps it
to `eval-spine-cost-event-v1`. The caller must supply the approved
`budget_category`; the adapted record also carries the v4 event digest and maps
`SUCCESS / FAILED / ABORTED` to the cost contract's outcome status. The audit
spine accepts it only when the category matches the preregistered classification
manifest and the exact source-telemetry manifest covers every successful, failed,
aborted, and human-review event. The adapter includes explicit unavailable reasons, so the
evaluation audit spine can consume costs without treating the two schemas as
identical. Token usage is normalized so cached input is a subset of input,
reasoning is a subset of output, and `total_tokens = input + output`; subset
fields are never added twice.
- `runner.py`: qualification-batch construction/evaluation and diagnostic CLI.

## Run tests

From the repository root:

```bash
python3 -m unittest discover \
  controlled_content_generator_v2_001/generator_v3_successor_001/v4_recovery/tests \
  -p 'test_*.py' -v
```

Run the historical mismatch diagnostic without writing any file:

```bash
python3 -m controlled_content_generator_v2_001.generator_v3_successor_001.v4_recovery.runner diagnose-r5
```

## Status boundary

Passing these deterministic tests proves only that the recovery contracts are
enforced. It does not qualify the factuality evaluator, the formulaic rubric,
the generator, or a 300-item baseline. Those require separately frozen gold
calibration, cross-review, feasibility, and cost gates.

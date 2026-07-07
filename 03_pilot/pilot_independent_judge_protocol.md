# Pilot Independent Judge Protocol

This protocol reviews the 44 cross-type pilot drafts before any batch generation is allowed.

Required judge checks:

1. Confirm the body text is supported by the structured propositions.
2. Confirm hard claims and named-instance facts are absent.
3. Confirm control-plane samples do not land as general knowledge.
4. Confirm readiness, production, and downstream materialization flags remain false.
5. Confirm any uncertain item routes to source work, decision review, or backlog.

Outcome policy:

- PASS may set `ready_for_pilot_review` complete in a later review task only.
- This pilot does not set `ready_for_first_batch_generation` to true.
- First batch generation remains blocked until judge or human review explicitly issues go/no-go.

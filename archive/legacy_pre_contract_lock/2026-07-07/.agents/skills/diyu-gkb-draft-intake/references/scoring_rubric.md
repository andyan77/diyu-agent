# Scoring Rubric

## Blocking

Fail the batch if any blocking condition appears:

- Readiness flag is true.
- CandidatePack eligibility lacks source anchor.
- Hard claim or concrete brand fact leaks.
- Serving passage text, RAG context bundle, or DIFY output is generated.
- Capability routing is missing.
- Required rich_body_blocks are incomplete.
- Negative checker fixture does not fail.

## Report-Only

Report, but do not treat as passing:

- Keyword-based claim scan maturity.
- Empty source pack registry during scaffold-only mode.
- Missing real batch lockfile during scaffold-only mode.
- Unverified Codex recognition of repo-scoped skill path.

## Health Metrics

After real micro-batches begin, track aligned rate, reject rate, source_gap rate, duplicate rate,
hard-claim leak count, brand-fact leak count, and capability coverage distribution every 10 micro-batches.

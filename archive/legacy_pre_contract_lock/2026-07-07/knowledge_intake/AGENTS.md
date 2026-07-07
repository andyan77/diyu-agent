# knowledge_intake/AGENTS.md

## Scope

This directory is for knowledge intake, draft alignment, CandidatePack preparation, source_gap, decision_packet, and review ledger artifacts.

## Intake rules

- Treat structured drafts as declared semantics.
- Do not reclassify declared Rule / L2 / L3 / Governance / TBox / ABox labels unless there is a contract conflict or risk evidence.
- Every candidate must preserve source trace or route to source_gap.
- GPT-generated text is not source evidence.
- A candidate without source_pack_refs and excerpt digest must not be marked candidatepack_eligible.
- Brand facts, concrete products, stores, cities, people, campaigns, customer feedback, and authorization facts must not enter GeneralKB candidates.
- Hard claims must be stripped, blocked, or routed to source_gap unless evidence policy is satisfied.

## Required ledgers

Any failed or unsafe item must be routed to one of:

- source_gap_ledger
- failure_ledger
- decision_packet_ledger
- review_queue
- excluded_candidates

Do not silently drop items.

## Output rules

Knowledge intake may output:

- draft candidate cards
- rich_body_blocks
- relation edge candidates
- semantic fingerprints
- source_gap candidates
- decision_packet candidates
- serving passage spec candidates
- gold hook candidates
- validation reports

Knowledge intake must not output:

- KE truth records
- approved passage text
- rendered_body
- RAG context_bundle
- DIFY output
- production-ready content
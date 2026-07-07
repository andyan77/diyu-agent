# GKB Intake Tools

This directory contains repository-local gate tools for the GKB intake workspace.

The tools intentionally avoid package installation, external services, LLM generation, embeddings, database writes,
Serving materialization, RAG context bundle creation, and DIFY calls.

Use:

- `run_gates.py`: runs the complete local checker suite and writes machine-readable gate reports.
- `run_batch.py`: deterministic batch gate runner that requires a batch lockfile and refuses generation.
- `validate_batch.py`: parses YAML / JSON / CSV, checks required files, CSV headers, contracts, forbidden roots, readiness flags, and optional content presence.
- `audit_pilot_readiness.py`: reports source-pack content status, Batch 000/001 lockfile status, non-git policy, and whether real candidate generation is blocked.
- `build_reports.py`: builds a manifest, protected hash summary, and optional gate summary bundle.

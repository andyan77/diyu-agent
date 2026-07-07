# GKB Intake Real Local Tools Upgrade Report

Task: replace scaffold tools with executable local gate tools.

Workspace: `/home/diyu/笛语领域通用数据库`

Mode: non-git workspace manifest/hash audit.

## What Changed

The previous scaffold-level tools were upgraded into a local gate suite:

- `tools/gkb_intake/run_gates.py` runs all 9 local gates and writes per-gate JSON reports.
- `tools/gkb_intake/run_batch.py` validates a batch lockfile, runs workspace validation, runs gates, and refuses generation.
- `tools/gkb_intake/validate_batch.py` now parses YAML / JSON / CSV, validates required files, CSV headers, contracts, forbidden roots, readiness flags, and optional content presence.
- `tools/gkb_intake/build_reports.py` now includes gate summary data and protected-file hash evidence.
- `ci/checkers/gkb_intake_common.py` centralizes structured parsing, finding records, report emission, candidate discovery, source-anchor checks, and readiness helpers.

The checker set now matches the workspace AGENTS requirement:

- `check_no_readiness_leak.py`
- `check_source_anchor_coverage.py`
- `check_declared_semantics_alignment.py`
- `check_hard_claim_and_brand_fact_leak.py`
- `check_rich_body_structure_consistency.py`
- `check_semantic_fingerprint_dedupe.py`
- `check_capability_routing_composability.py`
- `check_serving_spec_no_passage_text.py`
- `check_gold_hooks_as_release_input.py`

## Fixture Coverage

Added positive fixtures for declared semantics, fingerprint registry, serving spec, and batch lockfile.

Added negative fixtures for declared semantics mismatch and independent gold system.

All 9 negative fixtures were run directly against their checker and failed as expected.

## Checks Run

- `python3 tools/gkb_intake/run_gates.py --workspace knowledge_intake/gpt55_gkb_enrichment_v1 --selftest --summary-json knowledge_intake/gpt55_gkb_enrichment_v1/11_reports/gkb_intake_gate_summary.json`: PASS
- `python3 tools/gkb_intake/validate_batch.py --workspace knowledge_intake/gpt55_gkb_enrichment_v1 --scaffold-only --run-gates --report-json knowledge_intake/gpt55_gkb_enrichment_v1/11_reports/gkb_intake_validation_report.json`: PASS
- `python3 tools/gkb_intake/run_batch.py --workspace knowledge_intake/gpt55_gkb_enrichment_v1 --lockfile fixtures/gkb_intake/positive/valid_batch_lockfile.yaml --gate-only --report-json knowledge_intake/gpt55_gkb_enrichment_v1/11_reports/gkb_intake_runner_report.json`: PASS
- `python3 tools/gkb_intake/build_reports.py --root . --workspace knowledge_intake/gpt55_gkb_enrichment_v1 --gate-summary knowledge_intake/gpt55_gkb_enrichment_v1/11_reports/gkb_intake_gate_summary.json --output-json knowledge_intake/gpt55_gkb_enrichment_v1/11_reports/gkb_intake_real_tools_manifest.json`: PASS
- `python3 -m py_compile ci/checkers/*.py tools/gkb_intake/*.py`: PASS, then generated `__pycache__` files were removed.
- YAML / JSON / CSV parse scan: PASS
- Forbidden protected path existence scan: PASS, protected runtime and production paths absent.
- Protected file hash check: unchanged for existing AGENTS files, legacy SKILL, `tools.txt`, and `落盘总方案.txt`.

## Boundary Result

No knowledge generation was executed.

No CandidatePack instance, KE truth source, Serving Projection, RAG context bundle, DIFY workflow, runtime file,
secret file, or external service configuration was created.

`run_batch.py` reported `generation_executed: false`.

The only text-scan positive readiness flag occurrence remains inside the required negative readiness fixture.

## Readiness Flags

```yaml
candidatepack_ready: false
KE_ready: false
RAG_ready: false
DIFY_ready: false
production_servable: false
generation_eligible: false
generation_allowed: false
release_ready: false
production_ready: false
```

## Remaining Limits

The hard-claim / brand-fact gate is now a real local rule-based gate, but it is not a statistical or LLM classifier.
Before large-scale production intake, it should receive a maintained pattern catalog and possibly a separate offline
classifier, subject to explicit authorization.

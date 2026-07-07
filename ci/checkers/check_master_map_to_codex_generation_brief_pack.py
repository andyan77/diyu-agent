#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

import yaml

EXPECTED_BATCH_IDS = [f'batch_{i:03d}' for i in range(1, 15)]
EXPECTED_ASSIGNMENTS = [f'GA-{i:03d}' for i in range(1, 15)]
EXPECTED_BUDGETS = {
    'batch_001': 100, 'batch_002': 200, 'batch_003': 280,
    'batch_004': 240, 'batch_005': 240, 'batch_006': 240, 'batch_007': 240,
    'batch_008': 240, 'batch_009': 240, 'batch_010': 240,
    'batch_011': 360, 'batch_012': 360, 'batch_013': 380, 'batch_014': 240,
}
NEGATIVE_FIXTURES = [
    'negative_missing_batch.yaml', 'negative_total_budget_wrong.yaml', 'negative_budget_as_kpi.yaml',
    'negative_missing_cluster_assignment.yaml', 'negative_unknown_generation_assignment.yaml',
    'negative_missing_contract_ref.yaml', 'negative_readiness_true.yaml', 'negative_generated_knowledge_present.yaml',
    'negative_candidatepack_claim.yaml', 'negative_source_repo_dependency_true.yaml',
    'negative_pilot_missing_entailment_review.yaml',
]

class CheckError(Exception):
    pass

def fail(message: str) -> None:
    raise CheckError(message)

def load_yaml(path: Path) -> Any:
    if not path.exists():
        fail(f'missing yaml: {path}')
    return yaml.safe_load(path.read_text(encoding='utf-8'))

def load_json(path: Path) -> Any:
    if not path.exists():
        fail(f'missing json: {path}')
    return json.loads(path.read_text(encoding='utf-8'))

def validate_fixture_model(fixture: dict[str, Any]) -> list[str]:
    data = fixture.get('brief_pack_fixture', {})
    errors: list[str] = []
    if data.get('macro_batch_count') != 14:
        errors.append('macro_batch_count must be 14')
    if data.get('total_budget') != 3600:
        errors.append('total_budget must be 3600')
    if data.get('budget_not_kpi') is not True:
        errors.append('budget_not_kpi must be true')
    if data.get('canonical_cluster_count') != 46 or len(set(data.get('cluster_refs', []))) != 46:
        errors.append('canonical cluster coverage must be 46')
    if data.get('generation_assignment_count') != 14:
        errors.append('generation_assignment_count must be 14')
    if sorted(data.get('batch_ids', [])) != EXPECTED_BATCH_IDS:
        errors.append('batch ids must be batch_001..batch_014')
    if sorted(data.get('assignment_refs', [])) != EXPECTED_ASSIGNMENTS:
        errors.append('assignments must be GA-001..GA-014 exactly once')
    if data.get('contract_refs_present') is not True:
        errors.append('contract refs must be present')
    if data.get('readiness_all_false') is not True:
        errors.append('readiness_all_false must be true')
    if data.get('generated_knowledge_count') != 0:
        errors.append('generated_knowledge_count must be 0')
    if data.get('candidatepack_created') is not False:
        errors.append('candidatepack_created must be false')
    if data.get('source_repo_live_dependency') is not False or data.get('source_repo_live_accessed') is not False:
        errors.append('source repo live access/dependency must be false')
    if data.get('pilot_entailment_review_carry_forward') is not True:
        errors.append('pilot entailment review carry-forward is required')
    counts = data.get('microbatch_target_counts', [])
    if any(c < 20 or c > 40 for c in counts):
        errors.append('microbatch target counts must be 20..40')
    totals = data.get('microbatch_batch_totals', {})
    if totals and totals != EXPECTED_BUDGETS:
        errors.append('microbatch batch totals must match budget matrix')
    if sum(counts) != 3600:
        errors.append('microbatch target total must be 3600')
    rule = data.get('shared_assignment_rule', {})
    if rule.get('generation_assignment_refs_must_be_exactly_once') is not True:
        errors.append('shared assignment rule must require exactly-once assignment refs')
    return errors

def validate_live(workspace: Path, brief_root: Path, contracts_root: Path, fixtures_root: Path, report_out: Path | None) -> dict[str, Any]:
    baseline = load_yaml(contracts_root/'w7_generation_baseline_lock.v0.1.yaml')['w7_generation_baseline_lock']
    w7_digest = baseline['w7_map']['digest']
    founder_digest = baseline['founder_overlay']['digest']
    required_contracts = [
        'w7_generation_baseline_lock.v0.1.yaml', 'codex_generation_output_contract.v0.1.schema.json',
        'codex_candidate_kind_target_owner_policy.v0.1.yaml', 'codex_source_type_boundary_policy.v0.1.yaml',
        'codex_layer_annotation_policy.v0.1.yaml', 'codex_rich_body_quality_standard.v0.1.md',
        'codex_body_entailment_policy.v0.1.yaml', 'codex_dedupe_fingerprint_policy.v0.1.yaml',
        'codex_expert_synthesis_source_policy.v0.1.yaml', 'codex_microbatch_execution_policy.v0.1.yaml',
        'codex_state_machine_mapping_policy.v0.1.yaml',
    ]
    for name in required_contracts:
        if not (contracts_root/name).exists():
            fail(f'missing contract ref: {name}')
    shared = load_yaml(brief_root/'00_shared_generation_rules.yaml')['shared_generation_rules']
    if shared.get('source_repo_live_dependency') is not False or shared.get('source_repo_live_accessed') is not False:
        fail('shared rules source repo dependency/access must be false')
    if shared.get('W7_baseline_digest') != w7_digest or shared.get('founder_overlay_digest') != founder_digest:
        fail('baseline digest mismatch')
    baseline_lock = load_yaml(brief_root/'00_generation_baseline_lock.yaml')['generation_baseline_lock']
    for key, expected in [('W7_baseline_digest', w7_digest), ('founder_overlay_digest', founder_digest), ('canonical_cluster_count', 46), ('generation_assignment_count', 14), ('total_budget', 3600)]:
        if baseline_lock.get(key) != expected:
            fail(f'generation baseline lock mismatch: {key}')
    for key in ['source_repo_live_dependency', 'source_repo_live_accessed', 'candidatepack_created']:
        if baseline_lock.get(key) is not False:
            fail(f'{key} must be false')
    if baseline_lock.get('generated_knowledge_count') != 0 or baseline_lock.get('readiness_all_false') is not True:
        fail('baseline assertions failed')
    allocation = load_yaml(brief_root/'00_batch_allocation_matrix.yaml')['batch_allocation_matrix']
    if allocation.get('macro_batch_count') != 14 or allocation.get('total_budget') != 3600 or allocation.get('budget_not_kpi') is not True:
        fail('allocation matrix budget/count invalid')
    batches = allocation.get('batches', [])
    if sorted(b['batch_id'] for b in batches) != EXPECTED_BATCH_IDS:
        fail('allocation matrix must contain 14 batches')
    if sum(int(b['target_count_budget']) for b in batches) != 3600:
        fail('allocation budget sum must be 3600')
    registry = load_yaml(workspace/'00_source_inputs/W7_master_map/shared_knowledge_cluster_registry.yaml')
    known_clusters = {c['canonical_cluster_id'] for c in registry['clusters']}
    assignments = load_yaml(workspace/'00_source_inputs/generation_assignments/generation_assignment_plan.yaml')['assignments']
    known_assignments = {a['assignment_id'] for a in assignments}
    brief_cluster_refs: set[str] = set()
    brief_assignment_refs: list[str] = []
    for bid in EXPECTED_BATCH_IDS:
        path = brief_root/bid/f'{bid}_generation_brief.yaml'
        data = load_yaml(path)['batch_generation_brief']
        if data.get('batch_id') != bid:
            fail(f'batch brief id mismatch: {bid}')
        if data.get('target_count_budget') != EXPECTED_BUDGETS[bid] or data.get('budget_not_kpi') is not True:
            fail(f'batch budget invalid: {bid}')
        trace = data['W7_trace']
        if trace['W7_baseline_digest'] != w7_digest or trace['founder_overlay_digest'] != founder_digest:
            fail(f'batch digest mismatch: {bid}')
        refs = set(trace['canonical_cluster_refs'])
        if refs - known_clusters:
            fail(f'unknown canonical cluster refs in {bid}: {sorted(refs-known_clusters)}')
        brief_cluster_refs.update(refs)
        brief_assignment_refs.extend(trace['generation_assignment_refs'])
        if data['risk_controls'].get('readiness_all_false') is not True:
            fail(f'readiness control missing in {bid}')
    if brief_cluster_refs != known_clusters or len(brief_cluster_refs) != 46:
        fail(f'canonical cluster coverage invalid: {len(brief_cluster_refs)}')
    if sorted(brief_assignment_refs) != sorted(known_assignments) or len(brief_assignment_refs) != 14:
        fail('generation assignment refs must cover GA-001..GA-014 exactly once')
    if len(brief_assignment_refs) != len(set(brief_assignment_refs)):
        fail('generation assignment refs are duplicated without exactly-once compliance')
    pilot = load_yaml(brief_root/'00_pilot_sampling_plan.yaml')['pilot_sampling_plan']
    carry = pilot.get('pilot_review_carry_forward', {})
    if carry.get('body_entailment_requires_human_or_independent_judge_review') is not True or carry.get('structural_checker_is_not_true_semantic_proof') is not True:
        fail('pilot entailment review carry-forward missing')
    manifest = load_yaml(brief_root/'00_brief_pack_manifest.yaml')['brief_pack_manifest']
    if manifest.get('source_repo_live_dependency') is not False or manifest.get('source_repo_live_accessed') is not False:
        fail('manifest source repo dependency/access must be false')
    if manifest['assertions'].get('no_generated_knowledge') is not True or manifest['assertions'].get('no_candidatepack_created') is not True:
        fail('manifest no-generation assertions missing')
    with (brief_root/'00_microbatch_plan.csv').open(encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    if not rows:
        fail('microbatch plan empty')
    batch_totals = {bid: 0 for bid in EXPECTED_BATCH_IDS}
    for row in rows:
        bid = row['batch_id']
        count = int(row['target_count'])
        if bid not in batch_totals:
            fail(f'unknown microbatch batch id: {bid}')
        if count < 20 or count > 40:
            fail(f'microbatch target count out of range: {row["microbatch_id"]}')
        if row.get('budget_not_kpi') != 'true':
            fail('microbatch budget_not_kpi must be true')
        batch_totals[bid] += count
    if batch_totals != EXPECTED_BUDGETS:
        fail(f'microbatch batch totals mismatch: {batch_totals}')
    if sum(batch_totals.values()) != 3600:
        fail('microbatch total must be 3600')
    for bid in EXPECTED_BATCH_IDS:
        mm = load_yaml(brief_root/'microbatch_manifest'/f'{bid}_microbatch_manifest.yaml')['microbatch_manifest']
        if mm['batch_target_count_budget'] != EXPECTED_BUDGETS[bid] or mm['microbatch_target_total'] != EXPECTED_BUDGETS[bid]:
            fail(f'microbatch manifest total mismatch: {bid}')
        if any(mb['target_count'] < 20 or mb['target_count'] > 40 for mb in mm['microbatches']):
            fail(f'microbatch manifest count out of range: {bid}')
    status = load_yaml(workspace/'project-infra/current_workspace_status.yaml')
    bad = {k:v for k,v in status.get('readiness', {}).items() if v is True or str(v).lower() == 'true'}
    if bad:
        fail(f'readiness true flags: {bad}')
    positive = load_yaml(fixtures_root/'positive_valid_brief_pack_minimal.yaml')
    positive_errors = validate_fixture_model(positive)
    if positive_errors:
        fail(f'positive fixture failed: {positive_errors}')
    negative_results = {}
    for name in NEGATIVE_FIXTURES:
        errors = validate_fixture_model(load_yaml(fixtures_root/name))
        negative_results[name] = errors
        if not errors:
            fail(f'negative fixture unexpectedly passed: {name}')
    report = {
        'status': 'PASS',
        'macro_batch_count': 14,
        'microbatch_manifest_count': 14,
        'microbatch_row_count': len(rows),
        'total_budget': 3600,
        'budget_not_kpi': True,
        'canonical_cluster_coverage_count': len(brief_cluster_refs),
        'generation_assignment_coverage_count': len(set(brief_assignment_refs)),
        'negative_fixture_count': len(NEGATIVE_FIXTURES),
        'positive_fixture_count': 1,
        'negative_fixtures_fail_closed': True,
        'positive_fixture_passed': True,
        'source_repo_live_accessed_reported': False,
        'generated_knowledge_count': 0,
        'candidatepack_created': False,
        'readiness_false_preserved': True,
        'negative_results': negative_results,
    }
    if report_out:
        report_out.parent.mkdir(parents=True, exist_ok=True)
        report_out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return report

def main() -> int:
    if not __debug__:
        print('FAIL-CLOSED: python -O disables debug semantics; checker refuses optimized execution.', file=sys.stderr)
        return 2
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace-root', default='.')
    parser.add_argument('--brief-pack-root', default='02_generation_brief_pack')
    parser.add_argument('--contracts-root', default='01_generation_contracts')
    parser.add_argument('--fixtures-root', default='ci/fixtures/master_map_to_brief_pack')
    parser.add_argument('--report-out')
    parser.add_argument('--selftest', action='store_true')
    args = parser.parse_args()
    workspace = Path(args.workspace_root).resolve()
    brief_root = (workspace/args.brief_pack_root).resolve() if not Path(args.brief_pack_root).is_absolute() else Path(args.brief_pack_root)
    contracts_root = (workspace/args.contracts_root).resolve() if not Path(args.contracts_root).is_absolute() else Path(args.contracts_root)
    fixtures_root = (workspace/args.fixtures_root).resolve() if not Path(args.fixtures_root).is_absolute() else Path(args.fixtures_root)
    report_out = Path(args.report_out) if args.report_out else None
    if report_out and not report_out.is_absolute():
        report_out = workspace/report_out
    try:
        report = validate_live(workspace, brief_root, contracts_root, fixtures_root, report_out)
        if args.selftest:
            print(json.dumps({'selftest': 'PASS', 'negative_fixture_count': report['negative_fixture_count'], 'positive_fixture_count': 1}, ensure_ascii=False))
        else:
            print(json.dumps({'brief_pack_check': 'PASS'}, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(f'FAIL-CLOSED: {exc}', file=sys.stderr)
        return 1

if __name__ == '__main__':
    raise SystemExit(main())

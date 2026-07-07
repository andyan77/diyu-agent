#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

EXPECTED_COUNTS = {
    'canonical_cluster_count': 46,
    'source_cluster_count': 58,
    'generation_assignment_count': 14,
    'unresolved_decision_count': 12,
    'source_gap_seed_count': 16,
    'readiness_true_count': 0,
}
REQUIRED_CONTRACTS = [
    'w7_generation_baseline_lock.v0.1.yaml',
    'codex_generation_output_contract.v0.1.schema.json',
    'codex_candidate_kind_target_owner_policy.v0.1.yaml',
    'codex_source_type_boundary_policy.v0.1.yaml',
    'codex_layer_annotation_policy.v0.1.yaml',
    'codex_rich_body_quality_standard.v0.1.md',
    'codex_body_entailment_policy.v0.1.yaml',
    'codex_dedupe_fingerprint_policy.v0.1.yaml',
    'codex_expert_synthesis_source_policy.v0.1.yaml',
    'codex_microbatch_execution_policy.v0.1.yaml',
    'codex_state_machine_mapping_policy.v0.1.yaml',
    'codex_provenance_safety_policy.v0.1.yaml',
]
NEGATIVE_FIXTURES = [
    'negative_readiness_true.yaml',
    'negative_missing_candidate_kind.yaml',
    'negative_invalid_enum.yaml',
    'negative_source_type_decides_layer.yaml',
    'negative_empty_rich_body.yaml',
    'negative_selfcheck_leaked_into_body.yaml',
    'negative_body_not_entailed.yaml',
    'negative_hard_claim_expert_synthesis.yaml',
    'negative_real_instance_fact_leak.yaml',
    'negative_p0_00_general_kb_leak.yaml',
    'negative_candidatepack_claim.yaml',
    'negative_KE_RAG_DIFY_claim.yaml',
    'negative_provenance_true_flag_treated_as_active.yaml',
    'negative_provenance_true_flag_misread.yaml',
]
SELF_CHECK_TERMS = ['candidate_kind', 'target_owner', 'layer_annotation', 'semantic_alignment', 'body_entailment', 'dedupe_fingerprint', 'readiness_flags', 'state_machine_route']
FORBIDDEN_OWNER_MARKERS = ['P0_00_control_plane_operation', 'route_authority', 'readiness_transition_rule']

class ContractError(Exception):
    pass

def fail(message: str) -> None:
    raise ContractError(message)

def load_yaml(path: Path) -> Any:
    if not path.exists():
        fail(f'missing file: {path}')
    return yaml.safe_load(path.read_text(encoding='utf-8'))

def load_json(path: Path) -> Any:
    if not path.exists():
        fail(f'missing file: {path}')
    return json.loads(path.read_text(encoding='utf-8'))

def ensure_strict_schema(schema: dict[str, Any]) -> None:
    if schema.get('type') != 'object' or schema.get('additionalProperties') is not False:
        fail('schema root must be strict object with additionalProperties false')
    required = schema.get('required')
    if not isinstance(required, list) or len(required) < 10:
        fail('schema required fields are incomplete')
    def walk(node: Any, path: str) -> None:
        if isinstance(node, dict):
            if node.get('type') == 'object' and node.get('additionalProperties') is not False:
                fail(f'object schema missing additionalProperties false at {path}')
            for child_key, child in node.items():
                walk(child, f'{path}.{child_key}')
        elif isinstance(node, list):
            for idx, child in enumerate(node):
                walk(child, f'{path}[{idx}]')
    walk(schema, '$')
    readiness = schema['properties']['readiness_flags']['properties']
    for key, spec in readiness.items():
        if spec.get('const') is not False:
            fail(f'readiness schema is not const false for {key}')
    for location in [
        schema['properties']['ownership']['properties']['candidate_kind'],
        schema['properties']['ownership']['properties']['proposed_target_owner'],
        schema['properties']['source_policy']['properties']['source_type'],
    ]:
        if 'enum' not in location:
            fail('schema enum missing')

def validate_schema_shape(candidate: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    def check(node: Any, spec: dict[str, Any], path: str) -> None:
        expected_type = spec.get('type')
        if expected_type == 'object':
            if not isinstance(node, dict):
                errors.append(f'{path}: expected object')
                return
            allowed = set(spec.get('properties', {}).keys())
            for key in spec.get('required', []):
                if key not in node:
                    errors.append(f'{path}.{key}: missing required')
            if spec.get('additionalProperties') is False:
                for key in node:
                    if key not in allowed:
                        errors.append(f'{path}.{key}: additional property')
            for key, child_spec in spec.get('properties', {}).items():
                if key in node:
                    check(node[key], child_spec, f'{path}.{key}')
        elif expected_type == 'array':
            if not isinstance(node, list):
                errors.append(f'{path}: expected array')
                return
            if len(node) < spec.get('minItems', 0):
                errors.append(f'{path}: too few items')
            item_spec = spec.get('items')
            if item_spec:
                for idx, item in enumerate(node):
                    check(item, item_spec, f'{path}[{idx}]')
        elif expected_type == 'string':
            if not isinstance(node, str):
                errors.append(f'{path}: expected string')
                return
            if len(node) < spec.get('minLength', 0):
                errors.append(f'{path}: string too short')
        elif expected_type == 'boolean':
            if not isinstance(node, bool):
                errors.append(f'{path}: expected boolean')
        elif expected_type == 'number':
            if not isinstance(node, (int, float)) or isinstance(node, bool):
                errors.append(f'{path}: expected number')
                return
            if 'minimum' in spec and node < spec['minimum']:
                errors.append(f'{path}: below minimum')
            if 'maximum' in spec and node > spec['maximum']:
                errors.append(f'{path}: above maximum')
        if 'const' in spec and node != spec['const']:
            errors.append(f'{path}: expected const {spec["const"]!r}')
        if 'enum' in spec and node not in spec['enum']:
            errors.append(f'{path}: invalid enum {node!r}')
    check(candidate, schema, '$')
    return errors

def validate_candidate(candidate: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    fixture_meta_keys = {
        'source_type_decides_final_layer',
        'claim_profile',
        'content_markers',
        'candidatepack_instance_created',
        'downstream_claims',
        'provenance_only_text',
        'checker_behavior',
    }
    schema_candidate = {key: value for key, value in candidate.items() if key not in fixture_meta_keys}
    errors = validate_schema_shape(schema_candidate, schema)
    if errors:
        return errors
    flags = schema_candidate['readiness_flags']
    for key, value in flags.items():
        if value is not False:
            errors.append(f'readiness flag must be false: {key}')
    ownership = schema_candidate['ownership']
    if ownership['candidate_kind'] == 'general_knowledge_candidate':
        if ownership['proposed_target_owner'] != 'GeneralKnowledgeBase':
            errors.append('general_knowledge_candidate must target GeneralKnowledgeBase')
        markers = candidate.get('content_markers', [])
        if any(marker in markers for marker in FORBIDDEN_OWNER_MARKERS):
            errors.append('P0-00/control-plane marker cannot target GeneralKnowledgeBase')
    if ownership['candidate_kind'] == 'control_plane_candidate' and ownership['proposed_target_owner'] == 'GeneralKnowledgeBase':
        errors.append('control_plane_candidate cannot target GeneralKnowledgeBase')
    if candidate.get('source_type_decides_final_layer') is True:
        errors.append('source_type must not decide final layer')
    body_text = schema_candidate['rich_body']['body_text']
    if any(term in body_text for term in SELF_CHECK_TERMS):
        errors.append('semantic self-check term leaked into body text')
    for section in schema_candidate['rich_body']['body_sections']:
        if not section.get('proposition_refs'):
            errors.append('body section lacks proposition refs')
    claim_profile = candidate.get('claim_profile', {})
    if claim_profile.get('hard_claim') and not claim_profile.get('source_ref_present'):
        if schema_candidate['source_policy'].get('expert_synthesis_allowed'):
            errors.append('hard claim cannot be filled by expert synthesis')
    if claim_profile.get('real_instance_fact') and not claim_profile.get('source_ref_present'):
        errors.append('real instance fact leak')
    if candidate.get('candidatepack_instance_created') is True:
        errors.append('CandidatePack instance claim is forbidden')
    if schema_candidate['state_machine']['current_state'] != 'gpt_generated_structured_draft':
        errors.append('current_state must remain gpt_generated_structured_draft')
    downstream = candidate.get('downstream_claims', {})
    if any(downstream.get(key) is True for key in ['KE_ready', 'RAG_ready', 'DIFY_ready']):
        errors.append('KE/RAG/DIFY readiness claim forbidden')
    behavior = candidate.get('checker_behavior', {})
    if behavior.get('treat_provenance_as_active_readiness') is True:
        errors.append('provenance true flag examples must not be treated as active readiness')
    return errors

def run_live(workspace_root: Path, contracts_root: Path, fixtures_root: Path, report_out: Path | None) -> dict[str, Any]:
    contract_paths = {name: contracts_root / name for name in REQUIRED_CONTRACTS}
    for path in contract_paths.values():
        if not path.exists():
            fail(f'missing required contract: {path}')
    baseline = load_yaml(contract_paths['w7_generation_baseline_lock.v0.1.yaml'])['w7_generation_baseline_lock']
    counts = baseline['w7_map']
    actual_counts = {
        'canonical_cluster_count': counts['canonical_cluster_count'],
        'source_cluster_count': counts['source_cluster_count'],
        'generation_assignment_count': counts['generation_assignment_count'],
        'unresolved_decision_count': counts['unresolved_decision_count'],
        'source_gap_seed_count': counts['source_gap_seed_count'],
        'readiness_true_count': counts['readiness_true_count'],
    }
    if actual_counts != EXPECTED_COUNTS:
        fail(f'W7 counts mismatch: {actual_counts}')
    if baseline['source_inputs_authority'].get('source_repo_live_dependency') is not False:
        fail('source repo live dependency must be false')
    schema = load_json(contract_paths['codex_generation_output_contract.v0.1.schema.json'])
    ensure_strict_schema(schema)
    load_yaml(contract_paths['codex_candidate_kind_target_owner_policy.v0.1.yaml'])
    source_policy = load_yaml(contract_paths['codex_source_type_boundary_policy.v0.1.yaml'])['source_type_boundary']
    if source_policy.get('source_type_decides_final_layer') is not False:
        fail('source_type_decides_final_layer must be false')
    load_yaml(contract_paths['codex_layer_annotation_policy.v0.1.yaml'])
    load_yaml(contract_paths['codex_body_entailment_policy.v0.1.yaml'])
    load_yaml(contract_paths['codex_dedupe_fingerprint_policy.v0.1.yaml'])
    expert = load_yaml(contract_paths['codex_expert_synthesis_source_policy.v0.1.yaml'])['expert_synthesis_source_policy']
    if 'hard_claim' not in expert['forbidden_for'] or 'real_brand_fact' not in expert['forbidden_for']:
        fail('expert synthesis forbidden list is incomplete')
    load_yaml(contract_paths['codex_microbatch_execution_policy.v0.1.yaml'])
    load_yaml(contract_paths['codex_state_machine_mapping_policy.v0.1.yaml'])
    provenance = load_yaml(contract_paths['codex_provenance_safety_policy.v0.1.yaml'])['provenance_safety_rule']
    if provenance.get('checker_must_not_treat_provenance_examples_as_active_flags') is not True:
        fail('provenance safety rule missing')
    status = load_yaml(workspace_root / 'project-infra/current_workspace_status.yaml')
    bad = {k: v for k, v in status.get('readiness', {}).items() if v is True or str(v).lower() == 'true'}
    if bad:
        fail(f'workspace readiness true flags found: {bad}')
    positive = load_yaml(fixtures_root / 'positive_minimal_valid_candidate.yaml')
    positive_errors = validate_candidate(positive, schema)
    negative_results = {}
    if positive_errors:
        fail(f'positive fixture failed: {positive_errors}')
    for name in NEGATIVE_FIXTURES:
        fixture = load_yaml(fixtures_root / name)
        errs = validate_candidate(fixture, schema)
        negative_results[name] = errs
        if not errs:
            fail(f'negative fixture unexpectedly passed: {name}')
    report = {
        'checker': 'check_codex_generation_contract_lock.py',
        'status': 'PASS',
        'w7_counts': actual_counts,
        'schema_strict': True,
        'positive_fixture_passed': True,
        'negative_fixture_count': len(NEGATIVE_FIXTURES),
        'negative_fixtures_fail_closed': True,
        'negative_results': negative_results,
        'provenance_safety_verified': True,
        'source_repo_live_dependency': False,
        'readiness_false_preserved': True,
    }
    if report_out:
        report_out.parent.mkdir(parents=True, exist_ok=True)
        report_out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return report

def main() -> int:
    if not __debug__:
        print('FAIL-CLOSED: python -O disables debug assertions; checker refuses optimized execution.', file=sys.stderr)
        return 2
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace-root', default='.')
    parser.add_argument('--contracts-root', default='01_generation_contracts')
    parser.add_argument('--fixtures-root', default='ci/fixtures/codex_generation_contract_lock')
    parser.add_argument('--report-out')
    parser.add_argument('--selftest', action='store_true')
    args = parser.parse_args()
    workspace = Path(args.workspace_root).resolve()
    contracts = (workspace / args.contracts_root).resolve() if not Path(args.contracts_root).is_absolute() else Path(args.contracts_root)
    fixtures = (workspace / args.fixtures_root).resolve() if not Path(args.fixtures_root).is_absolute() else Path(args.fixtures_root)
    report_out = Path(args.report_out) if args.report_out else None
    if report_out and not report_out.is_absolute():
        report_out = workspace / report_out
    try:
        report = run_live(workspace, contracts, fixtures, report_out)
        if args.selftest:
            print(json.dumps({'selftest': 'PASS', 'negative_fixture_count': report['negative_fixture_count'], 'positive_fixture_passed': True}, ensure_ascii=False))
        else:
            print(json.dumps({'contract_lock_check': 'PASS'}, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(f'FAIL-CLOSED: {exc}', file=sys.stderr)
        return 1

if __name__ == '__main__':
    raise SystemExit(main())

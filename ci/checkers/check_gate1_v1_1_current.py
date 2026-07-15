#!/usr/bin/env python3
"""Fail-closed current checker for the Gate 1 v1.1 P1A review packet."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Callable

import yaml


if not __debug__:
    print("check_gate1_v1_1_current refuses python -O", file=sys.stderr)
    raise SystemExit(2)


ROOT = Path(__file__).resolve().parents[2]
TASK_ID = "GATE1_V11_STANDARD_BASELINE_REVIEW_PACKET_AND_GOVERNANCE_PREFLIGHT_001"
P1B_TASK_ID = "GATE1_V11_SIGNED_REVIEW_CLOSEOUT_AND_BASELINE_FREEZE_001"
P2_TASK_ID = "GATE1_V11_COMPONENT_SUPPLY_AND_GENERATOR_CORE_REPAIR_001"
P3_TASK_ID = "GATE1_V11_OPEN_PROBE40_001"
P4_TASK_ID = "GATE1_V11_SEALED_HIDDEN_PROBE40_001"
BASELINE_COMMIT = "473a8664bdab37246db1b75785f765e62c80ed86"
V1_REPAIR_BASELINE_COMMIT = "69235a23d62d6c92683fadf572f7b8c291771dd6"
TASK_ROOT = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/"
    "p1a_standard_baseline_review_packet_and_governance_preflight_001"
)
P1B_TASK_ROOT = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/"
    "p1b_signed_review_closeout_and_baseline_freeze_001"
)
P2_TASK_ROOT = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/"
    "p2_component_supply_and_generator_core_repair_001"
)
P3_TASK_ROOT = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/"
    "p3_open_probe40_001"
)
P4_TASK_ROOT = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/"
    "p4_sealed_hidden_probe40_001"
)
P3_RECOVERY_TASK_ID = (
    "GATE1_V11_P3_ROUTE_INPUT_COMPILER_RECOVERY_AND_P4_RESEALED_PROBE40_001"
)
P3_RECOVERY_TASK_ROOT = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/"
    "p3_route_input_compiler_recovery_001"
)
P4_RESEALED_TASK_ROOT = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/"
    "p4_resealed_hidden_probe40_001"
)
P4_AUTHOR_RECOVERY_TASK_ID = (
    "GATE1_V11_P5_PREREQUISITE_P4_AUTHOR_OUTPUT_RECOVERY_001"
)
P4_AUTHOR_RECOVERY_TASK_ROOT = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/"
    "p4_author_output_contract_recovery_001"
)
P4_THIRD_TASK_ROOT = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/"
    "p4_third_sealed_hidden_probe40_001"
)
P4_BASELINE_COMMIT = "44609ef9d87594019b444d5bbfa229493f9ef566"
P4_CONDITIONAL_COMPAT_PATHS = frozenset(
    {
        P3_TASK_ROOT / "p3_current_guard.py",
        P3_TASK_ROOT / "p3_final_r1.py",
    }
)
PUBLIC_FOUNDATION_ROOT = Path("11_product_foundation/public_foundation_001")
PUBLIC_FOUNDATION_EXACT_PATHS = frozenset(
    {
        Path(".github/workflows/ci.yml"),
        Path("AGENTS.md"),
        Path("README.md"),
        PUBLIC_FOUNDATION_ROOT / "contract/public_foundation_contract.v1.yaml",
        PUBLIC_FOUNDATION_ROOT / "identity/simulation_tenant.v1.yaml",
        PUBLIC_FOUNDATION_ROOT / "taxonomy/topic_product_mapping.v1.yaml",
        PUBLIC_FOUNDATION_ROOT / "fixtures/contract_cases.v1.jsonl",
        PUBLIC_FOUNDATION_ROOT / "result/public_foundation_result.v1.yaml",
        PUBLIC_FOUNDATION_ROOT
        / "review/architecture_consumability_review.v1.yaml",
        PUBLIC_FOUNDATION_ROOT / "review/trust_fact_safety_review.v1.yaml",
        PUBLIC_FOUNDATION_ROOT / "review/coordinator_decision.v1.yaml",
        Path("ci/checkers/check_product_foundation.py"),
        Path("project-infra/current_product_status.v1.yaml"),
        Path("project-infra/product_workspace_manifest.v1.yaml"),
    }
)
PUBLIC_FOUNDATION_CHECKER_PATH = Path("ci/checkers/check_product_foundation.py")
PUBLIC_FOUNDATION_RESULT_PATH = (
    PUBLIC_FOUNDATION_ROOT / "result/public_foundation_result.v1.yaml"
)
P4_THIRD_TOOL_FREEZE_PATH = (
    P4_THIRD_TASK_ROOT / "freeze/tool_freeze.v1.0.yaml"
)
PUBLIC_FOUNDATION_LEGACY_CHECKER_AS_BUILT_SHA256 = (
    "1fae78276fe8d3e69da4a1cda369b792cd091bbca96094c8a76880c9859a75a8"
)
PUBLIC_FOUNDATION_SUCCESSOR_CHECKER_SHA256 = (
    "ed1fc96a20cf86d08a80418caa927ff13734e1cd4d5a4bc0e0ed915ef61be823"
)
PUBLIC_FOUNDATION_WORKFLOW_REQUIRED_ACTIVE_LINES = (
    "python3 ci/checkers/check_product_foundation.py",
    "python3 ci/checkers/check_product_foundation.py --selftest",
    '"ci/checkers/check_product_foundation.py" \\',
    '"ci/checkers/check_product_foundation.py --selftest" \\',
)
DOWNSTREAM_SUCCESSOR_DELEGATIONS = (
    (
        Path("12_expression_service/expression_runtime_adapter_001"),
        Path(
            "12_expression_service/expression_runtime_adapter_001/"
            "check_light_expression_service.py"
        ),
    ),
    (
        Path("13_brand_data/brand_data_import_001"),
        Path("13_brand_data/brand_data_import_001/check_brand_data_import.py"),
    ),
    (
        Path("14_dify_shell/dify_content_shell_001"),
        Path("14_dify_shell/dify_content_shell_001/check_dify_content_shell.py"),
    ),
)
DOWNSTREAM_NORMAL_WORKFLOW_STEP = "Run reserved downstream package checks"
DOWNSTREAM_OPTIMIZED_WORKFLOW_STEP = (
    "Verify reserved downstream package fail-closed optimized mode"
)
P2_BASELINE_COMMIT = "81ddfe975a11b3dc9533d6828ac6418328b0f254"
CURRENT_OWNER_PATH = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/current_gate1_owner.v0.1.yaml"
)
CURRENT_CHECKER_PATH = Path("ci/checkers/check_gate1_v1_1_current.py")
REPORT_PATH = Path(
    "docs/reports/gate1_v1_1_generator_gkb_retrospective_and_recovery_plan_20260713.md"
)
STANDARD_SNAPSHOT_PATH = (
    TASK_ROOT / "standard/diyu_content_composition_standard.v1.1.md"
)
STANDARD_CONTRACT_PATH = TASK_ROOT / "standard/v1_1_standard_contract.v0.1.yaml"
BASELINE_MANIFEST_PATH = TASK_ROOT / "baseline/gate1_input_baseline_manifest.v0.1.yaml"
REVIEW_PACKET_PATH = TASK_ROOT / "review/unified_gate1_review_packet.v0.1.jsonl"
REVIEW_CONTRACT_PATH = TASK_ROOT / "review/independent_review_contract.v0.1.yaml"
REVIEW_RECORD_TEMPLATE_PATH = (
    TASK_ROOT / "review/unified_independent_review_record_template.v0.1.yaml"
)
LEGACY_EDGE_MANIFEST_PATH = (
    TASK_ROOT
    / "component/legacy_component_applicability_historical_manifest.v0.1.jsonl"
)
COMPAT_RECEIPT_PATH = (
    TASK_ROOT / "compatibility/governance_compatibility_repair_receipt.v0.1.yaml"
)
RESULT_PATH = TASK_ROOT / "result/p1a_standard_baseline_preflight_result.v0.1.yaml"
MATERIALIZER_PATH = TASK_ROOT / "run_p1a_standard_baseline_review_packet_freezer.py"
P1B_MATERIALIZER_PATH = P1B_TASK_ROOT / "run_p1b_signed_review_closeout_freezer.py"
P1B_IMPORT_MANIFEST_PATH = (
    P1B_TASK_ROOT / "imports/signed_review_import_manifest.v0.1.yaml"
)
P1B_CONTRACT_PATH = (
    P1B_TASK_ROOT / "contract/p1b_signed_review_closeout_contract.v0.1.yaml"
)
P1B_NORMALIZED_PATH = P1B_TASK_ROOT / "normalized/signed_review_records.v0.1.jsonl"
P1B_CONTENT_PATH = P1B_TASK_ROOT / "content/reference_120_final_dispositions.v0.1.jsonl"
P1B_CONTENT_GAPS_PATH = (
    P1B_TASK_ROOT / "content/reference_120_content_product_gap_matrix.v0.1.yaml"
)
P1B_ROUTE_GOLD_PATH = P1B_TASK_ROOT / "route/route_60_gold_answers.v0.1.jsonl"
P1B_ROUTE_FREEZE_PATH = P1B_TASK_ROOT / "route/route_60_gold_freeze_manifest.v0.1.yaml"
P1B_ROUTE_COMPARISON_PATH = (
    P1B_TASK_ROOT / "route/route_60_current_actual_comparison.v0.1.jsonl"
)
P1B_COMPONENT_PATH = (
    P1B_TASK_ROOT / "component/component_86_final_dispositions.v0.1.jsonl"
)
P1B_ACTIVE_COMPONENTS_PATH = (
    P1B_TASK_ROOT / "component/active_gate1_development_components.v0.1.jsonl"
)
P1B_ACTIVE_EDGES_PATH = (
    P1B_TASK_ROOT / "component/active_gate1_development_edges.v0.1.jsonl"
)
P1B_COMPONENT_GAPS_PATH = (
    P1B_TASK_ROOT / "component/component_supply_gap_matrix.v0.1.yaml"
)
P1B_TEST_INPUTS_PATH = (
    P1B_TASK_ROOT / "test_inputs/gate1_development_test_input_manifest.v0.1.yaml"
)
P1B_COMPAT_RECEIPT_PATH = (
    P1B_TASK_ROOT / "compatibility/p1b_historical_identity_repair_receipt.v0.1.yaml"
)
P1B_RESULT_PATH = P1B_TASK_ROOT / "result/p1b_signed_review_closeout_result.v0.1.yaml"
P2_MATERIALIZER_PATH = (
    P2_TASK_ROOT / "run_p2_component_supply_and_generator_core_repair.py"
)
P2_MODEL_PATH = P2_TASK_ROOT / "p2_component_model.py"
P2_DOCUMENTS_PATH = P2_TASK_ROOT / "p2_checkpoint_documents.py"
P2_SUCCESSOR_PATH = (
    P2_TASK_ROOT / "component/historical_86_successor_dispositions.v0.1.jsonl"
)
P2_COMPONENTS_PATH = (
    P2_TASK_ROOT / "component/successor_component_candidates.v0.1.jsonl"
)
P2_RULES_PATH = P2_TASK_ROOT / "component/control_rule_candidates.v0.1.jsonl"
P2_EDGES_PATH = P2_TASK_ROOT / "component/proposed_component_cp_edges.v0.1.jsonl"
P2_SUPPLY_PATH = P2_TASK_ROOT / "component/candidate_supply_matrix.v0.1.yaml"
P2_ADDITION_PATH = P2_TASK_ROOT / "component/necessary_addition_assessment.v0.1.yaml"
P2_AB_PATH = P2_TASK_ROOT / "ab/ab_structural_path_candidates.v0.1.jsonl"
P2_REVIEW_PACKET_PATH = (
    P2_TASK_ROOT / "review/independent_component_review_packet.v0.1.jsonl"
)
P2_REVIEW_JOB_PATH = P2_TASK_ROOT / "review/independent_component_review_job.v0.1.yaml"
P2_COMPAT_PATH = (
    P2_TASK_ROOT / "compatibility/p1b_successor_compatibility_receipt.v0.1.yaml"
)
P2_RESULT_PATH = P2_TASK_ROOT / "result/p2_component_review_checkpoint_result.v0.1.yaml"
P2_TARGET_REVISED_COMPONENTS_PATH = (
    P2_TASK_ROOT / "component/revised_component_candidates.r1.jsonl"
)
P2_TARGET_ADDITIONS_PATH = (
    P2_TASK_ROOT / "component/necessary_addition_candidates.r1.jsonl"
)
P2_TARGET_RULES_PATH = P2_TASK_ROOT / "component/revised_control_rules.r1.jsonl"
P2_TARGET_EDGES_PATH = P2_TASK_ROOT / "component/final_edge_candidates.r1.jsonl"
P2_TARGET_AB_PATH = P2_TASK_ROOT / "ab/revised_ab_path_candidates.r1.jsonl"
P2_TARGET_REVIEW_PACKET_PATH = (
    P2_TASK_ROOT / "review/targeted_repair_review_packet.r1.jsonl"
)
P2_TARGET_R2_REVISED_COMPONENTS_PATH = (
    P2_TASK_ROOT / "component/revised_component_candidates.r2.jsonl"
)
P2_TARGET_R2_ADDITIONS_PATH = (
    P2_TASK_ROOT / "component/necessary_addition_candidates.r2.jsonl"
)
P2_TARGET_R2_RULES_PATH = P2_TASK_ROOT / "component/revised_control_rules.r2.jsonl"
P2_TARGET_R2_EDGES_PATH = P2_TASK_ROOT / "component/final_edge_candidates.r2.jsonl"
P2_TARGET_R2_AB_PATH = P2_TASK_ROOT / "ab/revised_ab_path_candidates.r2.jsonl"
P2_TARGET_R2_REVIEW_PACKET_PATH = (
    P2_TASK_ROOT / "review/targeted_repair_review_packet.r2.jsonl"
)
P2_TARGET_R3_REVISED_COMPONENTS_PATH = (
    P2_TASK_ROOT / "component/revised_component_candidates.r3.jsonl"
)
P2_TARGET_R3_ADDITIONS_PATH = (
    P2_TASK_ROOT / "component/necessary_addition_candidates.r3.jsonl"
)
P2_TARGET_R3_RULES_PATH = P2_TASK_ROOT / "component/revised_control_rules.r3.jsonl"
P2_TARGET_R3_EDGES_PATH = P2_TASK_ROOT / "component/final_edge_candidates.r3.jsonl"
P2_TARGET_R3_AB_PATH = P2_TASK_ROOT / "ab/revised_ab_path_candidates.r3.jsonl"
P2_TARGET_R3_REVIEW_PACKET_PATH = (
    P2_TASK_ROOT / "review/targeted_repair_review_packet.r3.jsonl"
)
P2_TARGET_R4_REVISED_COMPONENTS_PATH = (
    P2_TASK_ROOT / "component/revised_component_candidates.r4.jsonl"
)
P2_TARGET_R4_ADDITIONS_PATH = (
    P2_TASK_ROOT / "component/necessary_addition_candidates.r4.jsonl"
)
P2_TARGET_R4_RULES_PATH = P2_TASK_ROOT / "component/revised_control_rules.r4.jsonl"
P2_TARGET_R4_EDGES_PATH = P2_TASK_ROOT / "component/final_edge_candidates.r4.jsonl"
P2_TARGET_R4_AB_PATH = P2_TASK_ROOT / "ab/revised_ab_path_candidates.r4.jsonl"
P2_TARGET_R4_REVIEW_PACKET_PATH = (
    P2_TASK_ROOT / "review/targeted_repair_review_packet.r4.jsonl"
)
P2_TARGET_R5_REVISED_COMPONENTS_PATH = (
    P2_TASK_ROOT / "component/revised_component_candidates.r5.jsonl"
)
P2_TARGET_R5_ADDITIONS_PATH = (
    P2_TASK_ROOT / "component/necessary_addition_candidates.r5.jsonl"
)
P2_TARGET_R5_RULES_PATH = P2_TASK_ROOT / "component/revised_control_rules.r5.jsonl"
P2_TARGET_R5_EDGES_PATH = P2_TASK_ROOT / "component/final_edge_candidates.r5.jsonl"
P2_TARGET_R5_AB_PATH = P2_TASK_ROOT / "ab/revised_ab_path_candidates.r5.jsonl"
P2_TARGET_R5_REVIEW_PACKET_PATH = (
    P2_TASK_ROOT / "review/targeted_repair_review_packet.r5.jsonl"
)
P2_TARGET_R6_REVIEW_PACKET_PATH = (
    P2_TASK_ROOT / "review/targeted_repair_review_packet.r6.jsonl"
)
P2_INITIAL_PRIMARY_DIR = P2_TASK_ROOT / "imports/initial_review/primary"
P2_INITIAL_SECONDARY_DIR = P2_TASK_ROOT / "imports/initial_review/secondary"
P2_INITIAL_ADJUDICATION_DIR = P2_TASK_ROOT / "imports/initial_review/adjudication"
P2_TARGET_PRIMARY_DIR = P2_TASK_ROOT / "imports/targeted_r1/primary"
P2_TARGET_SECONDARY_DIR = P2_TASK_ROOT / "imports/targeted_r1/secondary"
P2_TARGET_R2_PRIMARY_DIR = P2_TASK_ROOT / "imports/targeted_r2/primary"
P2_TARGET_R2_SECONDARY_DIR = P2_TASK_ROOT / "imports/targeted_r2/secondary"
P2_TARGET_R3_PRIMARY_DIR = P2_TASK_ROOT / "imports/targeted_r3/primary"
P2_TARGET_R3_SECONDARY_DIR = P2_TASK_ROOT / "imports/targeted_r3/secondary"
P2_TARGET_R4_PRIMARY_DIR = P2_TASK_ROOT / "imports/targeted_r4/primary"
P2_TARGET_R4_SECONDARY_DIR = P2_TASK_ROOT / "imports/targeted_r4/secondary"
P2_TARGET_R5_PRIMARY_DIR = P2_TASK_ROOT / "imports/targeted_r5/primary"
P2_TARGET_R5_SECONDARY_DIR = P2_TASK_ROOT / "imports/targeted_r5/secondary"
P2_TARGET_R6_PRIMARY_DIR = P2_TASK_ROOT / "imports/targeted_r6/primary"
P2_TARGET_R6_SECONDARY_DIR = P2_TASK_ROOT / "imports/targeted_r6/secondary"
P2_IMPORT_MANIFEST_PATH = (
    P2_TASK_ROOT / "imports/independent_review_import_manifest.v0.1.yaml"
)
P2_INITIAL_COMBINED_PATH = P2_TASK_ROOT / "review/combined_review_records.v0.1.jsonl"
P2_TARGET_COMBINED_PATH = (
    P2_TASK_ROOT / "review/targeted_r1_combined_review_records.v0.1.jsonl"
)
P2_TARGET_R2_COMBINED_PATH = (
    P2_TASK_ROOT / "review/targeted_r2_combined_review_records.v0.1.jsonl"
)
P2_TARGET_R3_COMBINED_PATH = (
    P2_TASK_ROOT / "review/targeted_r3_combined_review_records.v0.1.jsonl"
)
P2_TARGET_R4_COMBINED_PATH = (
    P2_TASK_ROOT / "review/targeted_r4_combined_review_records.v0.1.jsonl"
)
P2_TARGET_R5_COMBINED_PATH = (
    P2_TASK_ROOT / "review/targeted_r5_combined_review_records.v0.1.jsonl"
)
P2_TARGET_R6_COMBINED_PATH = (
    P2_TASK_ROOT / "review/targeted_r6_combined_review_records.v0.1.jsonl"
)
P2_REVIEW_CLOSEOUT_PATH = (
    P2_TASK_ROOT / "review/independent_component_review_closeout.v0.1.yaml"
)
P2_ACTIVE_COMPONENTS_PATH = (
    P2_TASK_ROOT / "component/active_gate1_components.v0.1.jsonl"
)
P2_ACTIVE_RULES_PATH = P2_TASK_ROOT / "component/active_control_rules.v0.1.jsonl"
P2_ACTIVE_EDGES_PATH = P2_TASK_ROOT / "component/active_gate1_edges.v0.1.jsonl"
P2_APPROVED_SUPPLY_PATH = (
    P2_TASK_ROOT / "component/approved_component_supply_matrix.v0.1.yaml"
)
P2_ACTIVE_AB_PATH = P2_TASK_ROOT / "ab/active_ab_structural_paths.v0.1.jsonl"
P2_GENERATOR_CONTRACT_PATH = (
    P2_TASK_ROOT / "generator/gate1_generator_contract.v0.1.yaml"
)
P2_GENERATOR_REGISTRY_PATH = (
    P2_TASK_ROOT / "generator/active_gate1_generator_registry.v0.1.yaml"
)
P2_AUTHOR_REQUESTS_PATH = P2_TASK_ROOT / "generator/typed_author_requests.v0.1.jsonl"
P2_REALIZATIONS_PATH = (
    P2_TASK_ROOT / "generator/component_realization_results.v0.1.jsonl"
)
P2_PAIR_RESULTS_PATH = P2_TASK_ROOT / "generator/ab_pair_results.v0.1.jsonl"
P2_AXIS_BODY_PAIR_RESULTS_PATH = (
    P2_TASK_ROOT / "generator/axis_body_pair_results.v0.1.jsonl"
)
P2_PATH_PROGRAM_TAMPER_RESULTS_PATH = (
    P2_TASK_ROOT / "generator/path_program_tamper_results.v0.1.jsonl"
)
P2_TRUST_CONTRACT_TAMPER_RESULTS_PATH = (
    P2_TASK_ROOT / "generator/trust_contract_tamper_results.v0.1.jsonl"
)
P2_COMPONENT_POINTER_RESULTS_PATH = (
    P2_TASK_ROOT / "generator/component_pointer_results.v0.1.jsonl"
)
P2_OBSERVABLE_EFFECT_TAMPER_RESULTS_PATH = (
    P2_TASK_ROOT / "generator/observable_effect_tamper_results.v0.1.jsonl"
)
P2_BOUND_FACT_EFFECT_RESULTS_PATH = (
    P2_TASK_ROOT / "generator/bound_fact_structural_effect_results.v0.1.jsonl"
)
P2_REQUIRED_SLOT_TAMPER_RESULTS_PATH = (
    P2_TASK_ROOT / "generator/required_slot_trust_root_tamper_results.v0.1.jsonl"
)
P2_PROGRAM_SCHEMA_TAMPER_RESULTS_PATH = (
    P2_TASK_ROOT / "generator/path_program_schema_tamper_results.v0.1.jsonl"
)
P2_ABLATION_RESULTS_PATH = (
    P2_TASK_ROOT / "generator/component_ablation_results.v0.1.jsonl"
)
P2_ROUTE_ACTUALS_PATH = P2_TASK_ROOT / "generator/route_actuals.v0.1.jsonl"
P2_ROUTE_COMPARISONS_PATH = (
    P2_TASK_ROOT / "generator/route_comparisons.v0.1.jsonl"
)
P2_PROVIDER_AUDIT_PATH = (
    P2_TASK_ROOT / "generator/external_provider_exit_audit.v0.1.yaml"
)
P2_FINAL_COMPAT_PATH = (
    P2_TASK_ROOT / "compatibility/p2_final_current_checker_receipt.v0.1.yaml"
)
P2_FINAL_RESULT_PATH = P2_TASK_ROOT / "result/p2_final_result.v0.1.yaml"
P2_TARGET_REVIEWED_COMMIT = "6d7aa877a12867ee9a73e50a8e292ef4a631d7a9"
P2_INITIAL_REVIEW_PACKET_SHA256 = (
    "67751ab60e6ee8e227c4aaff3dccd4c7f3c5d027ceda2f910f4ea1a600231095"
)
P2_TARGET_REVIEW_PACKET_SHA256 = (
    "5d32c3dd1140013978f42df887ec98462b723317bf58daaf8eaa040d608bea50"
)
P2_TARGET_R2_REVIEWED_COMMIT = "211b9b241d7660dfa688d3b8db4716ce4e871d27"
P2_TARGET_R2_REVIEW_PACKET_SHA256 = (
    "6eaa8e8f365888ea887a13e3065e9cb711f8f518460f61d4865f3e24852986ef"
)
P2_TARGET_R3_REVIEWED_COMMIT = "e83c4a27259d64dd1a52d41d9ca0b9cc7237db61"
P2_TARGET_R3_REVIEW_PACKET_SHA256 = (
    "e14bf95b40d87c83be48e45f2455d983c3c5e412f88ef41f5b034b9d2403883d"
)
P2_TARGET_R4_REVIEWED_COMMIT = "87d3ca89ba9cbb743ee82af105cf831bbd8e2dab"
P2_TARGET_R4_REVIEW_PACKET_SHA256 = (
    "95c2a44e8d473844ada77d242ede0299a6b4db63b2699dfc633af0704d2c7e72"
)
P2_TARGET_R5_REVIEWED_COMMIT = "6f18ac14a15e7e17bfb3f45809c3b33d3b1c1d5a"
P2_TARGET_R5_REVIEW_PACKET_SHA256 = (
    "de59316fd7d88237e00cc84bd8802959d194995ddf5aef703477bd4921adc245"
)
P2_TARGET_R6_REVIEWED_COMMIT = "6555c83c58c54e698ef50c3ff707e44a255d5d9b"
P2_TARGET_R6_REVIEW_PACKET_SHA256 = (
    "2da6b6eaebd03feea33094e6606730e357d07ae57e38119414685a96332f52a8"
)
P2_CHECKPOINT_CURRENT_CHECKER_SHA256 = (
    "2aec6f38dd6d64118506ad998c504e950eeaae34fc97b718ab285e49edc035bd"
)

CLEAN_120_PATH = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/"
    "clean_120_reference_corpus_freeze_001/"
    "founder_reviewed_clean_120_reference_corpus.v1.0.jsonl"
)
ROUTE_INPUT_PATH = Path(
    "controlled_content_generator_v2_001/creative_authoring_route_oracle_convergence_001/"
    "route/route_inputs.v0.1.jsonl"
)
ROUTE_ACTUAL_PATH = Path(
    "controlled_content_generator_v2_001/"
    "b_channel_component_consumption_and_claim_closure_dev_gate_001/"
    "route/route_regression_actuals.v0.1.jsonl"
)
COMPONENT_SOURCE_PATH = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/"
    "controlled_composition_v2_001/b_channel_component_review_and_handoff_001/"
    "reviewed_reusable_component_registry.v0.4.jsonl"
)
CANDIDATE_SOURCE_PATH = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/"
    "controlled_composition_v2_001/component_candidate_manifest.v0.1.jsonl"
)
PROFILE_PATH = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/"
    "controlled_composition_v2_001/content_product_profile_20_completion_001/"
    "content_product_profiles.v0.2.yaml"
)
AB_CONTRACT_PATH = Path(
    "controlled_content_generator_v2_001/"
    "b_channel_component_consumption_and_claim_closure_dev_gate_001/"
    "contracts/orch_ab_divergence_contract.v0.1.json"
)
B24_CHECKER_PATH = Path("ci/checkers/check_gkb_v2_b_channel_24_component_review.py")
SUCCESSOR_CHECKER_PATH = Path(
    "ci/checkers/check_orch_generator_v2_b_channel_component_consumption_dev_gate.py"
)
CI_WORKFLOW_PATH = Path(".github/workflows/ci.yml")

STANDARD_SHA256 = "022fc9b96919233e6f5268f5f9d0722b592914cc8919b5d1628dd3600a494542"
CLEAN_120_SHA256 = "b6f8fccdcc38407d4791e85631d4a6df7366861617eccca5c13de4d311bb8c91"
ROUTE_INPUT_SHA256 = "68bc65bff904652f1e565097117c7e8dfccdcc6ef00d2e3a0e93a082a4d72f12"
ROUTE_ACTUAL_SHA256 = "bb7d68686761b7be092f191a0f46cb7493a3947f98959703c3ccaa69a86de3ad"
COMPONENT_SOURCE_SHA256 = (
    "de7bb3f3142a2076d88d92494ab512d31d125bb7b96b0ed232ac0122b354a601"
)
CANDIDATE_SOURCE_SHA256 = (
    "70ce2f7ebae3699fba6be0a0fff5d4a0a8e1023bbd32ae5a4f7340b3c4f43f7d"
)
PROFILE_SHA256 = "d38c7139d5eb5b88745b20adc37f6e4c97e42dff3076aca5d2822d78be5c1056"
AB_CONTRACT_SHA256 = "6862166cffb84dfb45ad8d98c82d5ae1faed18739df5e502d43a5d21d384a221"
P2_FROZEN_HASHES = {
    STANDARD_SNAPSHOT_PATH: STANDARD_SHA256,
    P1B_RESULT_PATH: "d4738a12b846d4c7fa5ca231de6d9e884e32733c01b9add6e81fad8d56601f72",
    P1B_CONTENT_PATH: "d4798e9847f9e4800676f002c46bb431e03d2e4763b07c91685f7962f7525ed0",
    P1B_ROUTE_GOLD_PATH: "f87d984d1780423e7ace0d78c54ba40e97ab5b48c39950f691c7ffca6652e054",
    P1B_ROUTE_FREEZE_PATH: "59490dc0260d9b05e28891136906744a2f383a15dc6f90d1e4754f353f769f3e",
    P1B_COMPONENT_PATH: "554f97ff23c913bc85722305f6002a91876bbd3848cc399e1fb6dd46001fc4e0",
    P1B_COMPONENT_GAPS_PATH: "a5cf34ec23b95649bc23f8e400268c432cb8f2e017fc56d2ea3120a5730f666e",
    COMPONENT_SOURCE_PATH: COMPONENT_SOURCE_SHA256,
    CANDIDATE_SOURCE_PATH: CANDIDATE_SOURCE_SHA256,
    PROFILE_PATH: PROFILE_SHA256,
    AB_CONTRACT_PATH: AB_CONTRACT_SHA256,
}
REPORT_AFTER_POLICY_SHA256 = (
    "b89dd9f29bc084c9df69595efc6e3145372ade05210c0ecfe7df76f5aba6f02d"
)
B24_CHECKER_BEFORE_SHA256 = (
    "ff4060e02f387e92b9ec1613df31b5b855cbd04a1155d92f5ca03dacf3191394"
)
SUCCESSOR_CHECKER_BEFORE_SHA256 = (
    "95fcf3e6716e86f01a210c64dbe4685705962583ff9b2c560182389ba66df71c"
)
CURRENT_GATE1_CHECKER_V1_BEFORE_SHA256 = (
    "679343b9187ad12c3af077ab4041a3c706bcef56b915c6ef0234af54319ee716"
)
P1A_CURRENT_GATE1_CHECKER_AS_BUILT_SHA256 = (
    "29a872dd08b13c02a776ca4b4074a419320667a97b6c16125ab03432626d3806"
)
P1B_CURRENT_GATE1_CHECKER_AS_BUILT_SHA256 = (
    "6474966c8ea5d0fdb2c5d40cc5888969f5fc8ebb63f8006d61504a4aaae8e231"
)
P1B_BASELINE_COMMIT = "01da326e4195b47e9b769b025bdf962936f10419"
P1B_IMPORT_HASHES = {
    "independent_reviews/review_job.v0.yaml": "511e203a464b7e57fdf2661abc7254f168c0da59c1631f618a861f3cf8f9192a",
    "independent_reviews/review_job_blindness_amendment.v0.yaml": "fa10da85ac4b380d426fc3ac896d56e832b2ff877001ff0d6767793f1f1861c1",
    "independent_reviews/review_session_invalidations.v0.yaml": "5cb3c049ef8c99a4f89400a1c76b4383ae407f78d0d918603fff04d187583fcb",
    "independent_reviews/adjudication_assignment.v0.yaml": "1cf4c1987af6a803baa741877bb51462e789b46341c9550040e8936e13a9a98b",
    "independent_reviews/primary/records.jsonl": "fdaaff1355e3365fa51ecc26cac8d342f2c736b69cd2022ecf921ce339778a51",
    "independent_reviews/primary/report.md": "149bab88fdfca4203781ddb8aaee76897364bdca9ccd72ce2789f32ad3b7fe5c",
    "independent_reviews/primary/run_manifest.yaml": "801916ecf79b01023c2eec8b2d5e969565be6afe3f7c29e77dd61a7e5660a4c9",
    "independent_reviews/secondary/records.jsonl": "61586c7fce34baa59db1c179eeeae7214b6afebb3daa2282221e68e91f7e6b61",
    "independent_reviews/secondary/report.md": "38ce8105b9e747eb0f26ceca15e8173da56143e99078a485414dcebd64f7a76c",
    "independent_reviews/secondary/run_manifest.yaml": "07283675742cf0fd9900d6a5edc7b664071e4f4b603cb0a54786bd6ddf107bcb",
    "independent_reviews/adjudication/records.jsonl": "47b88fd579f7fce70ed20f4a9ad43000f013019b5cbcf7e1338c04137e7c973c",
    "independent_reviews/adjudication/report.md": "940742b85805a8abe6cf495cb34a2095081507e863bd4bc8abe165b91084959a",
    "independent_reviews/adjudication/run_manifest.yaml": "c52eb752b9fd0ab38732e2504142c895da3e1c20b830d20f7650e1f8fb543d0b",
    "independent_reviews/coordinator_review_checkpoint_closeout.v0.md": "5d68c5e2510e633bd25a6c076352727cdcd169bd2c1f452ae0acbd80454c72e2",
    "coordinator_expert_review.v1.md": "6f1485cbbef84c52c546f171e7b1a49c5b87e2163d51a35e4a359e5b804bf6aa",
}

ALLOWED_EXACT_PATHS = frozenset(
    {
        CURRENT_OWNER_PATH,
        REPORT_PATH,
        Path("ci/checkers/check_gate1_v1_1_current.py"),
    }
)
TASK_MANAGED_PATHS = frozenset(
    {
        STANDARD_SNAPSHOT_PATH,
        STANDARD_CONTRACT_PATH,
        BASELINE_MANIFEST_PATH,
        REVIEW_PACKET_PATH,
        REVIEW_CONTRACT_PATH,
        REVIEW_RECORD_TEMPLATE_PATH,
        LEGACY_EDGE_MANIFEST_PATH,
        COMPAT_RECEIPT_PATH,
        RESULT_PATH,
        MATERIALIZER_PATH,
    }
)
READY_KEYS = frozenset(
    {
        "candidatepack_ready",
        "KE_ready",
        "RAG_ready",
        "DIFY_ready",
        "Serving_ready",
        "production_servable",
        "generation_eligible",
        "generation_allowed",
        "release_ready",
        "production_ready",
        "generator_qualified",
        "runtime_ingest_ready",
        "runtime_provider_adapter_qualified",
    }
)
P2_AXIS_OPERATOR_ROLE_BY_AXIS = {
    "narrative_mechanism": "narrative_mechanism_operator",
    "information_order": "information_order_operator",
    "visual_subject": "visual_subject_operator",
    "sound_subject": "sound_subject_operator",
    "rhythm": "rhythm_operator",
    "ending": "ending_operator",
}
P2_AXIS_OUTPUT_KIND_BY_AXIS = {
    "narrative_mechanism": "NARRATIVE_SEGMENT_GRAPH",
    "information_order": "INFORMATION_NODE_SEQUENCE",
    "visual_subject": "VISUAL_FOCUS_MAP",
    "sound_subject": "SOUND_CUE_MAP",
    "rhythm": "STRUCTURAL_BEAT_MAP",
    "ending": "BOUNDARY_CLOSURE_MAP",
}


class UniqueKeyLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects duplicate mapping keys."""


def construct_unique_mapping(
    loader: UniqueKeyLoader,
    node: yaml.nodes.MappingNode,
    deep: bool = False,
) -> dict[Any, Any]:
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise ValueError(f"duplicate YAML key: {key}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    construct_unique_mapping,
)


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def object_digest(value: dict[str, Any], digest_key: str) -> str:
    payload = {key: child for key, child in value.items() if key != digest_key}
    return sha256_bytes(canonical_json(payload).encode("utf-8"))


def add_error(errors: list[dict[str, str]], code: str, detail: str) -> None:
    errors.append({"code": code, "detail": detail})


def load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.load(path.read_text(encoding="utf-8"), Loader=UniqueKeyLoader)
    if not isinstance(value, dict):
        raise TypeError(f"YAML root is not a mapping: {path}")
    return value


def write_yaml(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        yaml.safe_dump(value, allow_unicode=True, sort_keys=False, width=120),
        encoding="utf-8",
    )


def read_jsonl(path: Path) -> list[tuple[dict[str, Any], str]]:
    rows: list[tuple[dict[str, Any], str]] = []
    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not raw_line:
            continue
        value = json.loads(raw_line)
        if not isinstance(value, dict):
            raise TypeError(f"{path}:{line_number} is not a JSON object")
        rows.append((value, raw_line))
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "\n".join(canonical_json(row) for row in rows) + "\n",
        encoding="utf-8",
    )


def recursively_find_true(value: Any, keys: frozenset[str]) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in keys and child is True:
                found.append(key)
            found.extend(recursively_find_true(child, keys))
    elif isinstance(value, list):
        for child in value:
            found.extend(recursively_find_true(child, keys))
    return found


def recursively_find_strings(value: Any) -> list[str]:
    """Return all mapping keys and scalar strings for narrow leakage checks."""

    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            found.append(str(key))
            found.extend(recursively_find_strings(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(recursively_find_strings(child))
    elif isinstance(value, str):
        found.append(value)
    return found


def git(root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def is_public_foundation_write_path(path: Path) -> bool:
    """Delegate only the fixed product-foundation surface to its current checker."""

    return path in PUBLIC_FOUNDATION_EXACT_PATHS


def public_foundation_successor_registration_is_valid(root: Path) -> bool:
    """Pin the delegated checker and every required workflow invocation."""

    checker = root / PUBLIC_FOUNDATION_CHECKER_PATH
    workflow = root / CI_WORKFLOW_PATH
    if not checker.is_file() or not workflow.is_file():
        return False
    document = yaml.safe_load(workflow.read_text(encoding="utf-8"))
    if not isinstance(document, dict) or not isinstance(document.get("jobs"), dict):
        return False
    job = document["jobs"].get("checker-compatibility")
    if not isinstance(job, dict) or not isinstance(job.get("steps"), list):
        return False
    active_lines = tuple(
        stripped
        for step in job["steps"]
        if isinstance(step, dict) and isinstance(step.get("run"), str)
        for line in step["run"].splitlines()
        if (stripped := line.strip()) and not stripped.startswith("#")
    )
    checker_pin_line = (
        'test "$(sha256sum ci/checkers/check_product_foundation.py '
        "| cut -d ' ' -f 1)\" = \""
        f"{PUBLIC_FOUNDATION_SUCCESSOR_CHECKER_SHA256}\""
    )
    return (
        sha256_file(checker) == PUBLIC_FOUNDATION_SUCCESSOR_CHECKER_SHA256
        and active_lines.count(checker_pin_line) == 1
        and all(
            active_lines.count(required_line) == 1
            for required_line in PUBLIC_FOUNDATION_WORKFLOW_REQUIRED_ACTIVE_LINES
        )
    )


def downstream_workflow_step_lines(root: Path, step_name: str) -> tuple[str, ...]:
    """Return the exact nonblank lines for one named checker workflow step."""

    workflow = root / CI_WORKFLOW_PATH
    if not workflow.is_file():
        return ()
    document = yaml.safe_load(workflow.read_text(encoding="utf-8"))
    if not isinstance(document, dict) or not isinstance(document.get("jobs"), dict):
        return ()
    job = document["jobs"].get("checker-compatibility")
    if not isinstance(job, dict) or not isinstance(job.get("steps"), list):
        return ()
    matching = [
        step
        for step in job["steps"]
        if isinstance(step, dict) and step.get("name") == step_name
    ]
    if len(matching) != 1 or not isinstance(matching[0].get("run"), str):
        return ()
    return tuple(
        line.strip() for line in matching[0]["run"].splitlines() if line.strip()
    )


def downstream_successor_workflow_registration_is_valid(root: Path) -> bool:
    """Require one fail-closed remote runner for each reserved package root."""

    normal_lines = (
        "set -euo pipefail",
        "run_downstream_package_checker() {",
        'package_root="$1"',
        'checker="$2"',
        'if [ ! -e "$package_root" ]; then',
        "return 0",
        "fi",
        'test -d "$package_root"',
        'test -f "$checker"',
        'python3 "$checker"',
        'python3 "$checker" --selftest',
        "}",
        *(
            f'run_downstream_package_checker "{package_root.as_posix()}" '
            f'"{checker_path.as_posix()}"'
            for package_root, checker_path in DOWNSTREAM_SUCCESSOR_DELEGATIONS
        ),
    )
    optimized_lines = (
        "set -euo pipefail",
        "run_downstream_package_checker_optimized() {",
        'package_root="$1"',
        'checker="$2"',
        'if [ ! -e "$package_root" ]; then',
        "return 0",
        "fi",
        'test -d "$package_root"',
        'test -f "$checker"',
        "set +e",
        'python3 -O "$checker"',
        "code=$?",
        "set -e",
        'test "$code" -eq 2',
        "set +e",
        'python3 -O "$checker" --selftest',
        "code=$?",
        "set -e",
        'test "$code" -eq 2',
        "}",
        *(
            f'run_downstream_package_checker_optimized "{package_root.as_posix()}" '
            f'"{checker_path.as_posix()}"'
            for package_root, checker_path in DOWNSTREAM_SUCCESSOR_DELEGATIONS
        ),
    )
    return (
        downstream_workflow_step_lines(root, DOWNSTREAM_NORMAL_WORKFLOW_STEP)
        == normal_lines
        and downstream_workflow_step_lines(root, DOWNSTREAM_OPTIMIZED_WORKFLOW_STEP)
        == optimized_lines
    )


def is_registered_downstream_successor_write_path(root: Path, path: Path) -> bool:
    """Delegate only an existing reserved root with its registered package checker."""

    for package_root, checker_path in DOWNSTREAM_SUCCESSOR_DELEGATIONS:
        if not path.is_relative_to(package_root):
            continue
        package = root / package_root
        checker = root / checker_path
        return (
            package.is_dir()
            and not package.is_symlink()
            and checker.is_file()
            and not checker.is_symlink()
            and downstream_successor_workflow_registration_is_valid(root)
        )
    return False


def public_foundation_checker_handoff_is_valid(root: Path) -> bool:
    """Validate the frozen predecessor identity before delegating its successor."""

    try:
        freeze = load_yaml(root / P4_THIRD_TOOL_FREEZE_PATH).get(
            "third_p4_tool_freeze"
        )
        result = load_yaml(root / PUBLIC_FOUNDATION_RESULT_PATH).get(
            "public_foundation_result"
        )
        if not isinstance(freeze, dict) or not isinstance(result, dict):
            return False
        tool_files = freeze.get("tool_file_sha256")
        return (
            freeze.get("tool_freeze_digest")
            == object_digest(freeze, "tool_freeze_digest")
            and isinstance(tool_files, dict)
            and tool_files.get(CURRENT_CHECKER_PATH.as_posix())
            == PUBLIC_FOUNDATION_LEGACY_CHECKER_AS_BUILT_SHA256
            and result.get("task_id")
            == "DIYU_ENGINEERING_ENTRY_AND_PUBLIC_FOUNDATION_FREEZE_001"
            and public_foundation_successor_registration_is_valid(root)
        )
    except (OSError, TypeError, ValueError, yaml.YAMLError):
        return False


def filter_public_foundation_checker_handoff(
    root: Path, errors: list[dict[str, str]]
) -> list[dict[str, str]]:
    """Suppress only the predecessor's expected self-drift after a valid handoff."""

    if not public_foundation_checker_handoff_is_valid(root):
        return errors
    return [
        error
        for error in errors
        if not (
            error.get("code") == "E_T3_TOOL_FILE_DRIFT"
            and error.get("detail") == CURRENT_CHECKER_PATH.as_posix()
        )
    ]


def install_public_foundation_recovery_handoff(recovery_guard: Any) -> None:
    """Wrap the frozen P4 validator without changing its on-disk implementation."""

    if getattr(recovery_guard, "_public_foundation_handoff_installed", False):
        return
    frozen_loader = recovery_guard._load_third_guard

    def compatible_loader(root: Path) -> Any:
        third_guard = frozen_loader(root)
        frozen_validate_tool_freeze = third_guard._validate_tool_freeze

        def compatible_validate_tool_freeze(
            candidate_root: Path, errors: list[dict[str, str]]
        ) -> None:
            frozen_errors: list[dict[str, str]] = []
            frozen_validate_tool_freeze(candidate_root, frozen_errors)
            errors.extend(
                filter_public_foundation_checker_handoff(
                    candidate_root, frozen_errors
                )
            )

        third_guard._validate_tool_freeze = compatible_validate_tool_freeze
        return third_guard

    recovery_guard._load_third_guard = compatible_loader
    recovery_guard._public_foundation_handoff_installed = True


def unexpected_write_paths(root: Path, paths: set[Path]) -> list[str]:
    unexpected: list[str] = []
    for path in paths:
        if (
            path.is_relative_to(P2_TASK_ROOT)
            or path.is_relative_to(P3_TASK_ROOT)
            or path.is_relative_to(P4_TASK_ROOT)
            or path.is_relative_to(P3_RECOVERY_TASK_ROOT)
            or path.is_relative_to(P4_RESEALED_TASK_ROOT)
            or path.is_relative_to(P4_AUTHOR_RECOVERY_TASK_ROOT)
            or path.is_relative_to(P4_THIRD_TASK_ROOT)
        ):
            continue
        if is_public_foundation_write_path(path):
            continue
        if is_registered_downstream_successor_write_path(root, path):
            continue
        if path not in {
            CURRENT_OWNER_PATH,
            CURRENT_CHECKER_PATH,
            P1B_MATERIALIZER_PATH,
        }:
            unexpected.append(path.as_posix())
    return sorted(unexpected)


def validate_p3_successor(root: Path, errors: list[dict[str, str]]) -> None:
    """Load the P3 guard as a library, never as a nested checker process."""

    if (root / P4_AUTHOR_RECOVERY_TASK_ROOT).exists():
        return

    module_root = ROOT / P3_TASK_ROOT
    if str(module_root) not in sys.path:
        sys.path.insert(0, str(module_root))
    try:
        from p3_current_guard import validate_p3_current

        legacy_errors = validate_p3_current(root)
        recovery_valid = False
        if (root / P3_RECOVERY_TASK_ROOT).exists():
            if (root / P4_RESEALED_TASK_ROOT).exists():
                successor_root = root / P4_RESEALED_TASK_ROOT
                if str(successor_root) not in sys.path:
                    sys.path.insert(0, str(successor_root))
                from p3_recovery_guard_current import validate_p3_recovery_current

                recovery_valid = not validate_p3_recovery_current(root)
            else:
                recovery_root = root / P3_RECOVERY_TASK_ROOT
                if str(recovery_root) not in sys.path:
                    sys.path.insert(0, str(recovery_root))
                from p3_recovery_guard import validate_p3_recovery

                recovery_valid = not validate_p3_recovery(root)
        for item in legacy_errors:
            if (
                recovery_valid
                and item.get("code") == "E_P3_OWNER"
                and item.get("detail")
                in {
                    "GATE1_V11_P3_ROUTE_COMPILER_RECOVERY_OWNER",
                    "GATE1_V11_P4_RESEALED_PENDING_OWNER",
                }
            ):
                continue
            errors.append(item)
    except (ImportError, OSError, TypeError, ValueError) as exc:
        add_error(errors, "E_P3_GUARD_IMPORT", str(exc))


def validate_p4_successor(root: Path, errors: list[dict[str, str]]) -> None:
    """Load the P4 guard as a library, never as a nested checker process."""

    if (root / P4_AUTHOR_RECOVERY_TASK_ROOT).exists():
        return

    module_root = ROOT / P4_TASK_ROOT
    if str(module_root) not in sys.path:
        sys.path.insert(0, str(module_root))
    try:
        import p4_guard_current

        if (root / P3_RECOVERY_TASK_ROOT).exists():
            if (root / P4_RESEALED_TASK_ROOT).exists():
                successor_root = root / P4_RESEALED_TASK_ROOT
                if str(successor_root) not in sys.path:
                    sys.path.insert(0, str(successor_root))
                from p3_recovery_guard_current import validate_p3_recovery_current

                recovery_errors = validate_p3_recovery_current(root)
                freeze = load_yaml(
                    successor_root / "freeze/p4_resealed_tool_freeze.v1.0.yaml"
                ).get("p4_resealed_tool_freeze")
                expected_checker_sha = (
                    freeze.get("tool_files", {}).get(CURRENT_CHECKER_PATH.as_posix())
                    if isinstance(freeze, dict)
                    else None
                )
            else:
                recovery_root = root / P3_RECOVERY_TASK_ROOT
                if str(recovery_root) not in sys.path:
                    sys.path.insert(0, str(recovery_root))
                from p3_recovery_guard import validate_p3_recovery

                recovery_errors = validate_p3_recovery(root)
                freeze = load_yaml(
                    recovery_root / "freeze/p3_route_compiler_recovery_freeze.v1.0.yaml"
                )
                expected_checker_sha = freeze.get("current_checker_sha256")
            if recovery_errors:
                errors.extend(recovery_errors)
                return
            if (
                not isinstance(expected_checker_sha, str)
                or sha256_file(root / CURRENT_CHECKER_PATH) != expected_checker_sha
            ):
                add_error(errors, "E_P3R_CURRENT_CHECKER_BINDING", "P4 compatibility")
                return
            p4_guard_current.CURRENT_CHECKER_COMPAT_SHA256 = expected_checker_sha

        for item in p4_guard_current.validate_p4_current(root):
            if (
                (root / P3_RECOVERY_TASK_ROOT).exists()
                and item.get("code") == "E_P4_OWNER_EARLY_ADVANCE"
                and item.get("detail")
                in {
                    "GATE1_V11_P3_ROUTE_COMPILER_RECOVERY_OWNER",
                    "GATE1_V11_P4_RESEALED_PENDING_OWNER",
                }
            ):
                continue
            errors.append(item)
    except (ImportError, OSError, TypeError, ValueError) as exc:
        add_error(errors, "E_P4_GUARD_IMPORT", str(exc))


def validate_p4_write_surface(root: Path, errors: list[dict[str, str]]) -> None:
    """Keep the P4 delta inside the exact execution-brief write surface."""

    if not (root / ".git").exists() or not (root / P4_TASK_ROOT).exists():
        return
    ancestor = git(root, ["merge-base", "--is-ancestor", P4_BASELINE_COMMIT, "HEAD"])
    if ancestor.returncode != 0:
        add_error(errors, "E_P4_BASELINE", "P4 baseline is not an ancestor")
        return
    results = (
        git(root, ["diff", "--name-only", f"{P4_BASELINE_COMMIT}..HEAD"]),
        git(root, ["diff", "--name-only", "HEAD"]),
        git(root, ["ls-files", "--others", "--exclude-standard"]),
    )
    if any(result.returncode != 0 for result in results):
        add_error(errors, "E_P4_WRITE_SURFACE", "unable to inspect git paths")
        return
    paths = {
        Path(line)
        for result in results
        for line in result.stdout.splitlines()
        if line
    }
    allowed_exact = {
        CURRENT_CHECKER_PATH,
        CURRENT_OWNER_PATH,
        *P4_CONDITIONAL_COMPAT_PATHS,
    }
    unexpected = sorted(
        path.as_posix()
        for path in paths
        if not path.is_relative_to(P4_TASK_ROOT)
        and not path.is_relative_to(P3_RECOVERY_TASK_ROOT)
        and not path.is_relative_to(P4_RESEALED_TASK_ROOT)
        and not path.is_relative_to(P4_AUTHOR_RECOVERY_TASK_ROOT)
        and not path.is_relative_to(P4_THIRD_TASK_ROOT)
        and not is_public_foundation_write_path(path)
        and not is_registered_downstream_successor_write_path(root, path)
        and path not in allowed_exact
    )
    if unexpected:
        add_error(errors, "E_P4_WRITE_SURFACE", str(unexpected))


def validate_write_surface(root: Path, errors: list[dict[str, str]]) -> None:
    if not (root / ".git").exists():
        return
    ancestor = git(root, ["merge-base", "--is-ancestor", P2_BASELINE_COMMIT, "HEAD"])
    if ancestor.returncode != 0:
        add_error(errors, "E_BASELINE", "baseline commit is not an ancestor of HEAD")
        return
    changed = git(root, ["diff", "--name-only", f"{P2_BASELINE_COMMIT}..HEAD"])
    unstaged = git(root, ["diff", "--name-only", "HEAD"])
    untracked = git(root, ["ls-files", "--others", "--exclude-standard"])
    if any(result.returncode != 0 for result in (changed, unstaged, untracked)):
        add_error(errors, "E_WRITE_SURFACE", "unable to inspect git paths")
        return
    paths = {
        Path(line)
        for result in (changed, unstaged, untracked)
        for line in result.stdout.splitlines()
        if line
    }
    unexpected = unexpected_write_paths(root, paths)
    if unexpected:
        add_error(errors, "E_WRITE_SURFACE", str(unexpected))


def source_maps(root: Path, errors: list[dict[str, str]]) -> dict[str, Any] | None:
    expected_hashes = {
        CLEAN_120_PATH: CLEAN_120_SHA256,
        ROUTE_INPUT_PATH: ROUTE_INPUT_SHA256,
        ROUTE_ACTUAL_PATH: ROUTE_ACTUAL_SHA256,
        COMPONENT_SOURCE_PATH: COMPONENT_SOURCE_SHA256,
    }
    for relative_path, expected_hash in expected_hashes.items():
        path = root / relative_path
        if not path.exists() or sha256_file(path) != expected_hash:
            add_error(errors, "E_SOURCE_DRIFT", relative_path.as_posix())
    if errors:
        return None
    try:
        clean_rows = read_jsonl(root / CLEAN_120_PATH)
        route_input_rows = read_jsonl(root / ROUTE_INPUT_PATH)
        route_actual_rows = read_jsonl(root / ROUTE_ACTUAL_PATH)
        component_rows = read_jsonl(root / COMPONENT_SOURCE_PATH)
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        add_error(errors, "E_SOURCE_PARSE", str(exc))
        return None
    if (
        len(clean_rows) != 120
        or len(route_input_rows) != 60
        or len(route_actual_rows) != 60
    ):
        add_error(errors, "E_SOURCE_COUNT", "expected 120/60/60")
    if len(component_rows) != 86:
        add_error(errors, "E_SOURCE_COUNT", "expected 86 components")

    def as_map(
        rows: list[tuple[dict[str, Any], str]], key: str, label: str
    ) -> dict[str, str]:
        output: dict[str, str] = {}
        for row, raw_line in rows:
            value = row.get(key)
            if not isinstance(value, str) or not value or value in output:
                add_error(errors, "E_SOURCE_IDS", label)
                continue
            output[value] = sha256_bytes(raw_line.encode("utf-8"))
        return output

    clean_by_id = as_map(clean_rows, "asset_id", "clean_120")
    route_input_by_id = as_map(route_input_rows, "case_id", "route_input")
    route_actual_by_id = as_map(route_actual_rows, "case_id", "route_actual")
    component_by_id = as_map(component_rows, "component_id", "components")
    if set(route_input_by_id) != set(route_actual_by_id):
        add_error(errors, "E_SOURCE_ROUTE_PAIRING", "route input/actual ids differ")
    edge_set: set[tuple[str, str]] = set()
    for row, _ in component_rows:
        component_id = row.get("component_id")
        cp_ids = row.get("applicable_content_product_type_ids")
        if not isinstance(component_id, str) or not isinstance(cp_ids, list):
            add_error(errors, "E_SOURCE_COMPONENT_SCHEMA", str(component_id))
            continue
        for cp_id in cp_ids:
            if not isinstance(cp_id, str) or (component_id, cp_id) in edge_set:
                add_error(errors, "E_SOURCE_COMPONENT_EDGE", str(component_id))
                continue
            edge_set.add((component_id, cp_id))
    if len(edge_set) != 543:
        add_error(errors, "E_SOURCE_EDGE_COUNT", str(len(edge_set)))
    return {
        "clean_by_id": clean_by_id,
        "route_input_by_id": route_input_by_id,
        "route_actual_by_id": route_actual_by_id,
        "component_by_id": component_by_id,
        "edge_set": edge_set,
    }


def validate_standard(root: Path, errors: list[dict[str, str]]) -> None:
    snapshot = root / STANDARD_SNAPSHOT_PATH
    contract_path = root / STANDARD_CONTRACT_PATH
    if not snapshot.exists() or sha256_file(snapshot) != STANDARD_SHA256:
        add_error(errors, "E_STANDARD_SNAPSHOT", STANDARD_SNAPSHOT_PATH.as_posix())
    try:
        contract = load_yaml(contract_path).get("gate1_v1_1_standard_contract")
    except (OSError, TypeError, ValueError, yaml.YAMLError) as exc:
        add_error(errors, "E_STANDARD_CONTRACT", str(exc))
        return
    if not isinstance(contract, dict):
        add_error(errors, "E_STANDARD_CONTRACT", "root missing")
        return
    expected = {
        "standard_version": "v1.1",
        "source_sha256": STANDARD_SHA256,
        "snapshot_path": STANDARD_SNAPSHOT_PATH.as_posix(),
    }
    for key, value in expected.items():
        if contract.get(key) != value:
            add_error(errors, "E_STANDARD_CONTRACT", f"{key}={contract.get(key)}")
    targets = contract.get("first_gate_targets")
    if targets != {
        "positive_parent_content_target": 240,
        "route_case_target": 60,
        "total_case_target": 300,
        "content_product_count": 20,
    }:
        add_error(errors, "E_STANDARD_TARGETS", str(targets))
    if contract.get("contract_digest") != object_digest(contract, "contract_digest"):
        add_error(errors, "E_STANDARD_CONTRACT_DIGEST", "mismatch")


def validate_baseline_manifest(root: Path, errors: list[dict[str, str]]) -> None:
    try:
        manifest = load_yaml(root / BASELINE_MANIFEST_PATH).get(
            "gate1_input_baseline_manifest"
        )
    except (OSError, TypeError, ValueError, yaml.YAMLError) as exc:
        add_error(errors, "E_BASELINE_MANIFEST", str(exc))
        return
    if not isinstance(manifest, dict):
        add_error(errors, "E_BASELINE_MANIFEST", "root missing")
        return
    if (
        manifest.get("task_id") != TASK_ID
        or manifest.get("baseline_commit") != BASELINE_COMMIT
    ):
        add_error(errors, "E_BASELINE_MANIFEST", "task or commit mismatch")
    anchor = manifest.get("anchor_report")
    if (
        not isinstance(anchor, dict)
        or anchor.get("after_p1a_policy_correction_sha256")
        != REPORT_AFTER_POLICY_SHA256
    ):
        add_error(errors, "E_BASELINE_REPORT", str(anchor))
    inputs = manifest.get("review_inputs")
    expected = {
        "legacy_reference_content": (CLEAN_120_PATH.as_posix(), CLEAN_120_SHA256, 120),
        "route_input_cases": (ROUTE_INPUT_PATH.as_posix(), ROUTE_INPUT_SHA256, 60),
        "route_actual_records": (ROUTE_ACTUAL_PATH.as_posix(), ROUTE_ACTUAL_SHA256, 60),
        "component_candidates": (
            COMPONENT_SOURCE_PATH.as_posix(),
            COMPONENT_SOURCE_SHA256,
            86,
        ),
    }
    if not isinstance(inputs, dict):
        add_error(errors, "E_BASELINE_INPUTS", "missing")
    else:
        for key, (path, digest, count) in expected.items():
            item = inputs.get(key)
            if not isinstance(item, dict) or (
                item.get("path"),
                item.get("sha256"),
                item.get("count"),
            ) != (path, digest, count):
                add_error(errors, "E_BASELINE_INPUTS", key)
        route_actual = inputs.get("route_actual_records")
        if (
            not isinstance(route_actual, dict)
            or route_actual.get("excluded_from_blind_review_packet") is not True
            or route_actual.get(
                "comparison_allowed_only_after_signed_independent_determination"
            )
            is not True
        ):
            add_error(
                errors, "E_ROUTE_BLINDNESS", "baseline route actual release policy"
            )
    boundary = manifest.get("p1a_boundary")
    if not isinstance(boundary, dict) or any(
        boundary.get(key) not in (False, "NOT_FROZEN")
        for key in (
            "review_decisions_created",
            "counted_positive_parent_count",
            "component_dispositions_created",
            "route_gold_answers_created",
        )
    ):
        add_error(errors, "E_REVIEW_DECISION", "baseline manifest boundary")
    if manifest.get("manifest_digest") != object_digest(manifest, "manifest_digest"):
        add_error(errors, "E_BASELINE_MANIFEST_DIGEST", "mismatch")


def validate_review_packet(
    root: Path, source: dict[str, Any], errors: list[dict[str, str]]
) -> None:
    try:
        rows = [row for row, _ in read_jsonl(root / REVIEW_PACKET_PATH)]
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        add_error(errors, "E_REVIEW_PACKET", str(exc))
        return
    if len(rows) != 266:
        add_error(errors, "E_REVIEW_PACKET_COUNT", str(len(rows)))
        return
    packet_ids = [row.get("packet_item_id") for row in rows]
    if len(set(packet_ids)) != 266 or any(
        not isinstance(item, str) for item in packet_ids
    ):
        add_error(errors, "E_REVIEW_PACKET_IDS", "duplicate or missing")
    by_type = Counter(row.get("object_type") for row in rows)
    if by_type != Counter(
        {
            "LEGACY_REFERENCE_CONTENT": 120,
            "ROUTE_CASE": 60,
            "COMPONENT_CANDIDATE": 86,
        }
    ):
        add_error(errors, "E_REVIEW_PACKET_TYPES", str(dict(by_type)))
    clean_seen: set[str] = set()
    route_seen: set[str] = set()
    component_seen: set[str] = set()
    for row in rows:
        packet_strings = recursively_find_strings(row)
        forbidden_route_leakage = {
            "observed_implementation_record",
            "current_implementation_record",
            "actual_decision",
            "implementation_result",
            ROUTE_ACTUAL_PATH.as_posix(),
            ROUTE_ACTUAL_SHA256,
        }
        if forbidden_route_leakage.intersection(packet_strings):
            add_error(errors, "E_ROUTE_BLINDNESS", str(row.get("packet_item_id")))
        review_state = row.get("review_state")
        if review_state != "PENDING_INDEPENDENT_REVIEW":
            add_error(errors, "E_REVIEW_DECISION", str(row.get("packet_item_id")))
        object_type = row.get("object_type")
        object_id = row.get("object_id")
        if not isinstance(object_id, str):
            add_error(errors, "E_REVIEW_PACKET_SCHEMA", str(row.get("packet_item_id")))
            continue
        if object_type == "LEGACY_REFERENCE_CONTENT":
            record = row.get("source")
            expected = source["clean_by_id"].get(object_id)
            if (
                not isinstance(record, dict)
                or record.get("path") != CLEAN_120_PATH.as_posix()
                or record.get("locator") != f"{CLEAN_120_PATH}#{object_id}"
                or record.get("record_sha256") != expected
                or row.get("may_count_toward_positive_240_before_p1b") is not False
            ):
                add_error(errors, "E_REVIEW_PACKET_SOURCE", object_id)
            clean_seen.add(object_id)
        elif object_type == "ROUTE_CASE":
            input_record = row.get("input_source")
            if (
                not isinstance(input_record, dict)
                or input_record.get("path") != ROUTE_INPUT_PATH.as_posix()
                or input_record.get("locator") != f"{ROUTE_INPUT_PATH}#{object_id}"
                or input_record.get("record_sha256")
                != source["route_input_by_id"].get(object_id)
            ):
                add_error(errors, "E_REVIEW_PACKET_ROUTE", object_id)
            route_seen.add(object_id)
        elif object_type == "COMPONENT_CANDIDATE":
            record = row.get("source")
            if (
                not isinstance(record, dict)
                or record.get("path") != COMPONENT_SOURCE_PATH.as_posix()
                or record.get("locator") != f"{COMPONENT_SOURCE_PATH}#{object_id}"
                or record.get("record_sha256")
                != source["component_by_id"].get(object_id)
                or row.get("may_be_consumed_by_new_generator") is not False
            ):
                add_error(errors, "E_REVIEW_PACKET_SOURCE", object_id)
            component_seen.add(object_id)
    if clean_seen != set(source["clean_by_id"]):
        add_error(errors, "E_REVIEW_PACKET_COVERAGE", "legacy content")
    if route_seen != set(source["route_input_by_id"]):
        add_error(errors, "E_REVIEW_PACKET_COVERAGE", "route cases")
    if component_seen != set(source["component_by_id"]):
        add_error(errors, "E_REVIEW_PACKET_COVERAGE", "components")


def validate_review_identity_set(
    reviewer_records: dict[str, dict[str, Any]],
    errors: list[dict[str, str]],
) -> None:
    """Validate the identity separation P1B must apply to a review record set."""

    primary = reviewer_records.get("PRIMARY_CONTENT_VALUE")
    secondary = reviewer_records.get("SECONDARY_FACT_AUTHORIZATION")
    if not isinstance(primary, dict) or not isinstance(secondary, dict):
        add_error(
            errors, "E_REVIEWER_IDENTITY_COLLISION", "primary or secondary missing"
        )
        return
    distinct_fields = (
        "reviewer_identity_id",
        "reviewer_instance_or_session_id",
        "review_run_id",
        "append_only_signature_or_attestation",
    )
    for field in distinct_fields:
        primary_value = primary.get(field)
        secondary_value = secondary.get(field)
        if (
            not isinstance(primary_value, str)
            or not isinstance(secondary_value, str)
            or primary_value == secondary_value
        ):
            add_error(
                errors, "E_REVIEWER_IDENTITY_COLLISION", f"primary/secondary:{field}"
            )
    adjudicator = reviewer_records.get("INDEPENDENT_ADJUDICATION")
    if adjudicator is not None:
        if not isinstance(adjudicator, dict):
            add_error(errors, "E_REVIEWER_IDENTITY_COLLISION", "adjudicator schema")
            return
        for field in distinct_fields:
            adjudicator_value = adjudicator.get(field)
            if not isinstance(adjudicator_value, str) or adjudicator_value in {
                primary.get(field),
                secondary.get(field),
            }:
                add_error(
                    errors, "E_REVIEWER_IDENTITY_COLLISION", f"adjudicator:{field}"
                )


def validate_scoring_contract_binding(value: Any, errors: list[dict[str, str]]) -> None:
    if not isinstance(value, dict):
        add_error(errors, "E_SCORING_CONTRACT", "missing")
        return
    expected = {
        "positive_content": ("formula", "70_PLUS_30_EQUALS_100"),
        "component_candidate": ("formula", "80_PLUS_20_EQUALS_100"),
        "route_case": ("formula", "HARD_PRIMARY_ACTION_AND_REASON_CODE"),
    }
    for key, (field, expected_value) in expected.items():
        item = value.get(key)
        if not isinstance(item, dict) or item.get(field) != expected_value:
            add_error(errors, "E_SCORING_CONTRACT", key)
    route = value.get("route_case")
    summary = value.get("review_delivery_summary")
    if (
        not isinstance(route, dict)
        or route.get("per_record_percentage_forbidden") is not True
        or not isinstance(summary, dict)
        or summary.get("independent_coordinator_score_out_of") != 100
        or summary.get("is_not_a_substitute_for_object_level_decision") is not True
        or value.get("high_score_may_not_override_hard_veto") is not True
        or not isinstance(value.get("separation_required"), list)
        or set(value["separation_required"])
        != {
            "total_score",
            "hard_gate",
            "veto",
            "grade",
            "disposition",
            "lifecycle_status",
        }
    ):
        add_error(errors, "E_SCORING_CONTRACT", "decision separation")


def validate_review_contract(root: Path, errors: list[dict[str, str]]) -> None:
    try:
        contract = load_yaml(root / REVIEW_CONTRACT_PATH).get(
            "independent_review_contract"
        )
    except (OSError, TypeError, ValueError, yaml.YAMLError) as exc:
        add_error(errors, "E_REVIEW_CONTRACT", str(exc))
        return
    if not isinstance(contract, dict):
        add_error(errors, "E_REVIEW_CONTRACT", "root missing")
        return
    policy = contract.get("reviewer_identity_policy")
    required_policy = {
        "reviewer_may_be_ai_or_human": True,
        "distinct_reviewer_identity_id_required": True,
        "isolated_instance_or_session_required": True,
        "independent_run_and_signature_record_required": True,
        "blind_to_other_review_before_own_conclusion": True,
        "primary_and_secondary_pairwise_distinct_required": True,
        "adjudicator_pairwise_distinct_from_primary_and_secondary_when_triggered": True,
        "may_not_equal_content_author": True,
        "may_not_equal_p1a_packet_builder": True,
        "may_not_equal_p1b_freezer": True,
    }
    if not isinstance(policy, dict) or any(
        policy.get(key) != value for key, value in required_policy.items()
    ):
        add_error(errors, "E_REVIEW_IDENTITY_POLICY", str(policy))
    if not isinstance(policy, dict) or policy.get(
        "pairwise_distinct_record_fields"
    ) != [
        "reviewer_identity_id",
        "reviewer_instance_or_session_id",
        "review_run_id",
        "append_only_signature_or_attestation",
    ]:
        add_error(errors, "E_REVIEW_IDENTITY_POLICY", "pairwise record fields")
    roles = contract.get("roles")
    if not isinstance(roles, dict):
        add_error(errors, "E_REVIEW_ROLES", "missing")
    else:
        primary = roles.get("PRIMARY_CONTENT_VALUE")
        if (
            not isinstance(primary, dict)
            or primary.get("coverage")
            != "APPLICABLE_POSITIVE_FIRST_OUTPUTS_100_PERCENT"
        ):
            add_error(errors, "E_REVIEW_COVERAGE", str(primary))
        secondary = roles.get("SECONDARY_FACT_AUTHORIZATION")
        if (
            not isinstance(secondary, dict)
            or secondary.get("minimum_review_count") != 48
            or secondary.get("minimum_per_content_product") != 2
        ):
            add_error(errors, "E_REVIEW_COVERAGE", str(secondary))
        adjudicator = roles.get("INDEPENDENT_ADJUDICATION")
        if (
            not isinstance(adjudicator, dict)
            or adjudicator.get("required_when")
            != "PRIMARY_AND_SECONDARY_CONCLUSIONS_CONFLICT"
            or adjudicator.get("may_not_be_p1a_builder_or_p1b_freezer") is not True
        ):
            add_error(errors, "E_REVIEW_ROLES", str(adjudicator))
    standard_binding = contract.get("repository_standard_binding")
    if not isinstance(standard_binding, dict) or standard_binding != {
        "snapshot_path": STANDARD_SNAPSHOT_PATH.as_posix(),
        "snapshot_sha256": STANDARD_SHA256,
        "positive_content_scoring": "70_PLUS_30_EQUALS_100",
        "component_scoring": "80_PLUS_20_EQUALS_100",
        "route_scoring": "HARD_PRIMARY_ACTION_AND_REASON_CODE_NO_PER_RECORD_PERCENTAGE",
    }:
        add_error(errors, "E_SCORING_CONTRACT", "repository standard binding")
    validate_scoring_contract_binding(
        contract.get("scoring_and_decision_contract"), errors
    )
    route_sequence = contract.get("route_blind_review_sequence")
    expected_route_actual = {
        "path": ROUTE_ACTUAL_PATH.as_posix(),
        "sha256": ROUTE_ACTUAL_SHA256,
        "p1b_only_after_signed_determination": True,
    }
    if (
        not isinstance(route_sequence, dict)
        or route_sequence.get(
            "blind_packet_may_not_contain_current_implementation_locator_or_digest"
        )
        is not True
        or route_sequence.get("first_submission_required_before_actual_comparison")
        is not True
        or route_sequence.get("current_actual_source") != expected_route_actual
        or route_sequence.get("required_signed_determination_fields")
        != [
            "primary_action",
            "reason_code",
            "evidence_refs",
            "append_only_record_digest",
        ]
    ):
        add_error(errors, "E_ROUTE_BLINDNESS", str(route_sequence))
    disagreement = contract.get("disagreement_policy")
    expected_disagreement = {
        "original_conclusions_and_evidence_append_only": True,
        "independent_adjudication_required_on_conflict": True,
        "silent_intersection_forbidden": True,
        "average_forbidden": True,
        "overwrite_forbidden": True,
    }
    if disagreement != expected_disagreement:
        add_error(errors, "E_DISAGREEMENT_POLICY", str(disagreement))
    channel_boundary = contract.get("creative_channel_boundary")
    expected_channel_boundary = {
        "review_roles": [
            "PRIMARY_CONTENT_VALUE",
            "SECONDARY_FACT_AUTHORIZATION",
            "INDEPENDENT_ADJUDICATION",
        ],
        "review_role_may_not_be_mapped_to_generation_lane": True,
        "historical_b_channel_is_not_generation_lane_evidence": True,
        "source_generation_lane_or_pair_ref_only_if_source_carries_it": True,
        "source_generation_lane_or_pair_ref_fabrication_forbidden": True,
        "optional_lane_applicability_nonblocking": True,
        "optional_lane_applicability_not_approval_evidence": True,
        "default_lane_applicability_without_source_evidence": "NOT_APPLICABLE",
        "p1a_may_not_assert_dual_channel_qualified": True,
        "p2_to_p6_must_preserve_dual_channel_requirement": True,
    }
    if channel_boundary != expected_channel_boundary:
        add_error(errors, "E_LANE_BOUNDARY", str(channel_boundary))
    prohibitions = contract.get("p1a_prohibitions")
    if not isinstance(prohibitions, dict) or any(
        value is not False for value in prohibitions.values()
    ):
        add_error(errors, "E_REVIEW_DECISION", "contract p1a boundary")
    if contract.get("contract_digest") != object_digest(contract, "contract_digest"):
        add_error(errors, "E_REVIEW_CONTRACT_DIGEST", "mismatch")


def validate_review_record_template(root: Path, errors: list[dict[str, str]]) -> None:
    try:
        template = load_yaml(root / REVIEW_RECORD_TEMPLATE_PATH).get(
            "unified_independent_review_record_template"
        )
    except (OSError, TypeError, ValueError, yaml.YAMLError) as exc:
        add_error(errors, "E_REVIEW_TEMPLATE", str(exc))
        return
    if not isinstance(template, dict):
        add_error(errors, "E_REVIEW_TEMPLATE", "root missing")
        return
    standard = template.get("standard_binding")
    if not isinstance(standard, dict) or standard != {
        "snapshot_path": STANDARD_SNAPSHOT_PATH.as_posix(),
        "snapshot_sha256": STANDARD_SHA256,
        "content_formula": "70_PLUS_30_EQUALS_100",
        "component_formula": "80_PLUS_20_EQUALS_100",
        "route_formula": "HARD_PRIMARY_ACTION_AND_REASON_CODE_NO_PER_RECORD_PERCENTAGE",
    }:
        add_error(errors, "E_SCORING_CONTRACT", "template standard binding")
    object_record = template.get("object")
    reviewer = template.get("reviewer")
    evaluation = template.get("evidence_and_evaluation")
    disagreement = template.get("disagreement")
    required_top_level = {
        "schema_version": "v0.1",
        "template_status": "BLANK_TEMPLATE_NO_REVIEW_DECISION",
        "task_id": TASK_ID,
        "contract_path": REVIEW_CONTRACT_PATH.as_posix(),
    }
    if any(template.get(key) != value for key, value in required_top_level.items()):
        add_error(errors, "E_REVIEW_TEMPLATE", "top level")
    if (
        not isinstance(object_record, dict)
        or object_record.get("source_generation_lane_or_pair_ref") is not None
        or object_record.get("optional_lane_applicability") is not None
        or not isinstance(reviewer, dict)
        or any(value is not None for value in reviewer.values())
        or not isinstance(evaluation, dict)
        or evaluation.get("conclusion") is not None
        or evaluation.get("disposition") is not None
        or not isinstance(disagreement, dict)
        or disagreement.get("adjudication_conclusion") is not None
        or disagreement.get("final_disposition") is not None
    ):
        add_error(errors, "E_REVIEW_TEMPLATE", "must remain blank")
    if template.get("template_digest") != object_digest(template, "template_digest"):
        add_error(errors, "E_REVIEW_TEMPLATE_DIGEST", "mismatch")


def validate_legacy_edges(
    root: Path, source: dict[str, Any], errors: list[dict[str, str]]
) -> None:
    try:
        rows = [row for row, _ in read_jsonl(root / LEGACY_EDGE_MANIFEST_PATH)]
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        add_error(errors, "E_LEGACY_EDGE_MANIFEST", str(exc))
        return
    if len(rows) != 543:
        add_error(errors, "E_LEGACY_EDGE_COUNT", str(len(rows)))
        return
    seen: set[tuple[str, str]] = set()
    for row in rows:
        component_id = row.get("component_id")
        cp_id = row.get("content_product_type_id")
        edge = (component_id, cp_id)
        if (
            not isinstance(component_id, str)
            or not isinstance(cp_id, str)
            or edge in seen
        ):
            add_error(errors, "E_LEGACY_EDGE_SCHEMA", str(edge))
            continue
        seen.add(edge)
        if (
            row.get("relationship_lifecycle") != "HISTORICAL_UNREVIEWED_NON_ACTIVE"
            or row.get("review_state") != "PENDING_INDEPENDENT_REVIEW"
            or row.get("new_generator_consumable") is not False
            or row.get("active_edge_claimed") is not False
        ):
            add_error(errors, "E_LEGACY_EDGE_ACTIVE", str(edge))
        record = row.get("source")
        if (
            not isinstance(record, dict)
            or record.get("path") != COMPONENT_SOURCE_PATH.as_posix()
            or record.get("locator") != f"{COMPONENT_SOURCE_PATH}#{component_id}"
            or record.get("record_sha256")
            != source["component_by_id"].get(component_id)
        ):
            add_error(errors, "E_LEGACY_EDGE_SOURCE", str(edge))
    if seen != source["edge_set"]:
        add_error(errors, "E_LEGACY_EDGE_COVERAGE", str(len(seen)))


def validate_result(root: Path, errors: list[dict[str, str]]) -> None:
    try:
        result = load_yaml(root / RESULT_PATH).get(
            "p1a_standard_baseline_preflight_result"
        )
    except (OSError, TypeError, ValueError, yaml.YAMLError) as exc:
        add_error(errors, "E_RESULT", str(exc))
        return
    if not isinstance(result, dict):
        add_error(errors, "E_RESULT", "root missing")
        return
    if result.get("execution_status") != "PASS_PENDING_INDEPENDENT_REVIEWS":
        add_error(errors, "E_RESULT", str(result.get("execution_status")))
    boundary = result.get("review_decision_boundary")
    if (
        not isinstance(boundary, dict)
        or boundary.get("review_decisions_created") is not False
        or boundary.get("counted_positive_parent_count") != "NOT_FROZEN"
    ):
        add_error(errors, "E_REVIEW_DECISION", "result boundary")
    readiness = result.get("readiness")
    if not isinstance(readiness, dict) or recursively_find_true(readiness, READY_KEYS):
        add_error(errors, "E_READINESS", str(readiness))
    impact = result.get("core_number_impact")
    if impact != {
        "target_total": 300,
        "legacy_reference_content": 120,
        "component_candidates": 86,
        "all_unchanged": True,
    }:
        add_error(errors, "E_CORE_NUMBERS", str(impact))
    if result.get("result_digest") != object_digest(result, "result_digest"):
        add_error(errors, "E_RESULT_DIGEST", "mismatch")


def validate_owner(root: Path, errors: list[dict[str, str]]) -> None:
    try:
        owner = load_yaml(root / CURRENT_OWNER_PATH).get("current_gate1_owner")
    except (OSError, TypeError, ValueError, yaml.YAMLError) as exc:
        add_error(errors, "E_OWNER_POLICY", str(exc))
        return
    if not isinstance(owner, dict):
        add_error(errors, "E_OWNER_POLICY", "root missing")
        return
    if owner.get("task_id") == P4_AUTHOR_RECOVERY_TASK_ID:
        # The successor guard validates the complete owner/lifecycle binding.
        return
    if (
        owner.get("task_id") == P3_RECOVERY_TASK_ID
        and owner.get("owner_id") == "GATE1_V11_P4_RESEALED_PENDING_OWNER"
    ):
        if (
            owner.get("current_task_root") != P4_RESEALED_TASK_ROOT.as_posix()
            or owner.get("current_checker") != CURRENT_CHECKER_PATH.as_posix()
            or owner.get("result_state")
            != "PASS_PENDING_FOUNDER_QUALIFICATION_DECISION"
            or owner.get("p3_complete") is not True
            or owner.get("p4_resealed_technical_gate_pass") is not True
            or owner.get("coordinator_decision_required") is not True
            or owner.get("generator_qualified") is not False
            or owner.get("p5_allowed") is not False
            or owner.get("owner_digest") != object_digest(owner, "owner_digest")
        ):
            add_error(errors, "E_OWNER_POLICY", "p4 resealed pending binding")
        predecessor = owner.get("predecessor")
        if (
            not isinstance(predecessor, dict)
            or predecessor.get("owner_id")
            != "GATE1_V11_P3_ROUTE_COMPILER_RECOVERY_OWNER"
            or predecessor.get("task_id") != P3_RECOVERY_TASK_ID
        ):
            add_error(errors, "E_OWNER_POLICY", "p4 resealed predecessor")
        generator = owner.get("current_generator")
        if (
            not isinstance(generator, dict)
            or generator.get("entrypoint")
            != (P4_RESEALED_TASK_ROOT / "p4_resealed.py").as_posix()
            or generator.get("route_contract")
            != (P3_RECOVERY_TASK_ROOT / "route_contract.py").as_posix()
            or generator.get("active_component_count") != 68
            or generator.get("active_edge_count") != 85
            or generator.get("active_control_rule_count") != 8
            or generator.get("generator_core_changed") is not False
            or generator.get("author_instruction_or_model_changed") is not False
        ):
            add_error(errors, "E_OWNER_POLICY", "p4 resealed generator")
        if owner.get("core_numbers") != {
            "target_total": 300,
            "reference_inventory": 120,
            "historical_component_inventory": 86,
            "all_unchanged": True,
        }:
            add_error(errors, "E_OWNER_POLICY", "p4 resealed core numbers")
        if recursively_find_true(owner.get("readiness"), READY_KEYS):
            add_error(errors, "E_READINESS", "p4 resealed owner")
        return
    if owner.get("task_id") == P3_RECOVERY_TASK_ID:
        if (
            owner.get("owner_id") != "GATE1_V11_P3_ROUTE_COMPILER_RECOVERY_OWNER"
            or owner.get("current_task_root") != P3_RECOVERY_TASK_ROOT.as_posix()
            or owner.get("current_checker") != CURRENT_CHECKER_PATH.as_posix()
            or owner.get("result_state") != "PASS_TO_P4_RESEALED_PROBE"
            or owner.get("p3_complete") is not True
            or owner.get("p4_resealed_allowed") is not True
            or owner.get("owner_digest") != object_digest(owner, "owner_digest")
        ):
            add_error(errors, "E_OWNER_POLICY", "p3 recovery task binding")
        predecessor = owner.get("predecessor")
        if (
            not isinstance(predecessor, dict)
            or predecessor.get("owner_id") != "GATE1_V11_P3_OPEN_PROBE_FINAL_OWNER"
            or predecessor.get("owner_digest")
            != "d63daca011eb2eb12ff585a1ccf5081b54d69781548000cdf265adbc40e2fd8a"
            or predecessor.get("task_id") != P3_TASK_ID
        ):
            add_error(errors, "E_OWNER_POLICY", "p3 recovery predecessor")
        generator = owner.get("current_generator")
        if (
            not isinstance(generator, dict)
            or generator.get("entrypoint")
            != (P3_RECOVERY_TASK_ROOT / "run_p3_route_recovery.py").as_posix()
            or generator.get("route_contract")
            != (P3_RECOVERY_TASK_ROOT / "route_contract.py").as_posix()
            or generator.get("active_component_count") != 68
            or generator.get("active_edge_count") != 85
            or generator.get("active_control_rule_count") != 8
            or generator.get("generator_core_changed") is not False
            or generator.get("author_instruction_or_model_changed") is not False
        ):
            add_error(errors, "E_OWNER_POLICY", "p3 recovery generator")
        if owner.get("core_numbers") != {
            "target_total": 300,
            "reference_inventory": 120,
            "historical_component_inventory": 86,
            "all_unchanged": True,
        }:
            add_error(errors, "E_OWNER_POLICY", "p3 recovery core numbers")
        if recursively_find_true(owner.get("readiness"), READY_KEYS):
            add_error(errors, "E_READINESS", "p3 recovery owner")
        return
    if owner.get("task_id") == P3_TASK_ID:
        if (
            owner.get("owner_id") != "GATE1_V11_P3_OPEN_PROBE_FINAL_OWNER"
            or owner.get("current_task_root") != P3_TASK_ROOT.as_posix()
            or owner.get("current_checker") != CURRENT_CHECKER_PATH.as_posix()
            or owner.get("result_state") != "PASS_TO_P4_SEALED_HIDDEN_PROBE"
            or owner.get("p3_complete") is not True
            or owner.get("p4_allowed") is not True
            or owner.get("owner_digest") != object_digest(owner, "owner_digest")
        ):
            add_error(errors, "E_OWNER_POLICY", "p3 task binding")
        predecessor = owner.get("predecessor")
        if (
            not isinstance(predecessor, dict)
            or predecessor.get("owner_id") != "GATE1_V11_P2_FINAL_OWNER"
            or predecessor.get("owner_digest")
            != "ac4fe6c1ccdf8af787eb51d04f085883c27660690ccee6dfb996a90d89d4f7a7"
            or predecessor.get("p2_result_sha256")
            != "076bd9eb6c8ab67c0023bb454f6a82f16acecb284e896dc9029ef97582db5c3b"
        ):
            add_error(errors, "E_OWNER_POLICY", "p3 predecessor")
        generator = owner.get("current_generator")
        if (
            not isinstance(generator, dict)
            or generator.get("entrypoint")
            != (P3_TASK_ROOT / "run_p3_open_probe_r1.py").as_posix()
            or generator.get("active_component_count") != 68
            or generator.get("active_edge_count") != 85
            or generator.get("active_control_rule_count") != 8
            or generator.get("p3_component_addition_count") != 0
            or generator.get("historical_generator_entrypoints_consumed") != []
        ):
            add_error(errors, "E_OWNER_POLICY", "p3 generator")
        if owner.get("core_numbers") != {
            "target_total": 300,
            "reference_inventory": 120,
            "historical_component_inventory": 86,
            "all_unchanged": True,
        }:
            add_error(errors, "E_OWNER_POLICY", "p3 core numbers")
        if recursively_find_true(owner.get("readiness"), READY_KEYS):
            add_error(errors, "E_READINESS", "p3 owner")
        return
    if owner.get("task_id") == P2_TASK_ID:
        if owner.get("owner_id") == "GATE1_V11_P2_FINAL_OWNER":
            if (
                owner.get("current_task_root") != P2_TASK_ROOT.as_posix()
                or owner.get("current_checker") != CURRENT_CHECKER_PATH.as_posix()
                or owner.get("result_state") != "PASS_TO_P3_OPEN_PROBE"
                or owner.get("p2_complete") is not True
                or owner.get("p3_allowed") is not True
                or owner.get("owner_digest") != object_digest(owner, "owner_digest")
            ):
                add_error(errors, "E_OWNER_POLICY", "p2 final task binding")
            predecessor = owner.get("predecessor")
            if (
                not isinstance(predecessor, dict)
                or predecessor.get("owner_id")
                != "GATE1_V11_P2_COMPONENT_REVIEW_CHECKPOINT_OWNER"
                or predecessor.get("final_targeted_review", {}).get(
                    "reviewed_checkpoint_commit"
                )
                != P2_TARGET_R6_REVIEWED_COMMIT
                or predecessor.get("final_targeted_review", {}).get(
                    "review_packet_sha256"
                )
                != P2_TARGET_R6_REVIEW_PACKET_SHA256
            ):
                add_error(errors, "E_OWNER_POLICY", "p2 final predecessor")
            generator = owner.get("current_generator")
            if (
                not isinstance(generator, dict)
                or generator.get("entrypoint") != P2_MATERIALIZER_PATH.as_posix()
                or generator.get("active_component_count") != 68
                or generator.get("active_edge_count") != 85
                or generator.get("active_control_rule_count") != 8
                or generator.get("historical_generator_entrypoints_consumed") != []
            ):
                add_error(errors, "E_OWNER_POLICY", "p2 final generator")
            if owner.get("core_numbers") != {
                "target_total": 300,
                "reference_inventory": 120,
                "historical_component_inventory": 86,
                "all_unchanged": True,
            }:
                add_error(errors, "E_OWNER_POLICY", "p2 final core numbers")
            if recursively_find_true(owner.get("readiness"), READY_KEYS):
                add_error(errors, "E_READINESS", "p2 final owner")
            return
        expected = {
            "owner_id": "GATE1_V11_P2_COMPONENT_REVIEW_CHECKPOINT_OWNER",
            "baseline_commit": P2_BASELINE_COMMIT,
            "current_task_root": P2_TASK_ROOT.as_posix(),
            "current_checker": CURRENT_CHECKER_PATH.as_posix(),
        }
        if any(owner.get(key) != value for key, value in expected.items()):
            add_error(errors, "E_OWNER_POLICY", "p2 task binding")
        predecessor = owner.get("predecessor")
        if (
            not isinstance(predecessor, dict)
            or predecessor.get("task_id") != P1B_TASK_ID
            or predecessor.get("result_state") != "STOPPED_COMPONENT_SUPPLY_GAP"
            or predecessor.get("p2_allowed_by_p1b") is not False
            or predecessor.get("historical_owner_sha256")
            != "541443a9c5c34047fb5c9a4652412cc019218abd60d29528b57dbc1d771d637a"
            or predecessor.get("historical_checker_sha256")
            != "6474966c8ea5d0fdb2c5d40cc5888969f5fc8ebb63f8006d61504a4aaae8e231"
        ):
            add_error(errors, "E_OWNER_POLICY", "p1b predecessor binding")
        checkpoint = owner.get("checkpoint")
        if (
            not isinstance(checkpoint, dict)
            or checkpoint.get("state") != "PENDING_INDEPENDENT_COMPONENT_REVIEW"
            or checkpoint.get("p2_final_complete") is not False
            or checkpoint.get("proposed_component_count") != 54
            or checkpoint.get("proposed_edge_count") != 162
            or checkpoint.get("active_component_count") != 0
            or checkpoint.get("active_edge_count") != 0
            or checkpoint.get("self_approval_count") != 0
            or checkpoint.get("p3_allowed") is not False
        ):
            add_error(errors, "E_OWNER_POLICY", "p2 checkpoint")
        numbers = owner.get("core_numbers")
        if numbers != {
            "target_total": 300,
            "reference_inventory": 120,
            "historical_component_inventory": 86,
        }:
            add_error(errors, "E_OWNER_POLICY", "p2 core numbers")
        authority = owner.get("current_ledger_authority")
        if (
            not isinstance(authority, dict)
            or authority.get("shared_horizon_modified") is not False
            or authority.get("terminal_derivation") != "delegated_to_existing_owner"
        ):
            add_error(errors, "E_OWNER_POLICY", "p2 ledger authority")
        if recursively_find_true(owner.get("readiness"), READY_KEYS):
            add_error(errors, "E_READINESS", "p2 owner")
        return
    p1b_owner = owner.get("task_id") == P1B_TASK_ID
    expected = (
        {
            "task_id": P1B_TASK_ID,
            "baseline_commit": P1B_BASELINE_COMMIT,
            "current_task_root": P1B_TASK_ROOT.as_posix(),
            "current_checker": "ci/checkers/check_gate1_v1_1_current.py",
        }
        if p1b_owner
        else {
            "task_id": TASK_ID,
            "baseline_commit": BASELINE_COMMIT,
            "current_task_root": TASK_ROOT.as_posix(),
            "current_checker": "ci/checkers/check_gate1_v1_1_current.py",
        }
    )
    if any(owner.get(key) != value for key, value in expected.items()):
        add_error(errors, "E_OWNER_POLICY", "task binding")
    protected_inputs = owner.get("protected_inputs")
    expected_inputs = {
        "clean_120_source": CLEAN_120_PATH.as_posix(),
        "route_input_source": ROUTE_INPUT_PATH.as_posix(),
        "route_actual_source": ROUTE_ACTUAL_PATH.as_posix(),
        "component_source": COMPONENT_SOURCE_PATH.as_posix(),
    }
    if not isinstance(protected_inputs, dict) or any(
        protected_inputs.get(key) != value for key, value in expected_inputs.items()
    ):
        add_error(errors, "E_OWNER_POLICY", "protected inputs")
    if p1b_owner:
        p1a_protection = owner.get("p1a_as_built_protection")
        closeout = owner.get("p1b_closeout")
        if (
            not isinstance(p1a_protection, dict)
            or p1a_protection.get("p1a_current_checker_as_built_sha256")
            != P1A_CURRENT_GATE1_CHECKER_AS_BUILT_SHA256
            or p1a_protection.get("p1a_generated_outputs_must_remain_byte_identical")
            is not True
            or not isinstance(closeout, dict)
            or closeout.get("result_state") != "STOPPED_COMPONENT_SUPPLY_GAP"
            or closeout.get("counted_positive_parent_count") != 29
            or closeout.get("active_component_count") != 0
            or closeout.get("p2_allowed_by_p1b") is not False
        ):
            add_error(errors, "E_OWNER_POLICY", "p1b closeout binding")
    authority = owner.get("current_ledger_authority")
    if (
        not isinstance(authority, dict)
        or authority.get("shared_horizon_modified") is not False
        or authority.get("terminal_derivation") != "delegated_to_existing_owner"
    ):
        add_error(errors, "E_OWNER_POLICY", "ledger authority")
    if recursively_find_true(owner.get("readiness"), READY_KEYS):
        add_error(errors, "E_READINESS", "owner")


def validate_compatibility_receipt(root: Path, errors: list[dict[str, str]]) -> None:
    try:
        receipt = load_yaml(root / COMPAT_RECEIPT_PATH).get(
            "governance_compatibility_repair_receipt"
        )
    except (OSError, TypeError, ValueError, yaml.YAMLError) as exc:
        add_error(errors, "E_COMPAT_RECEIPT", str(exc))
        return
    if not isinstance(receipt, dict):
        add_error(errors, "E_COMPAT_RECEIPT", "root missing")
        return
    checkers = receipt.get("modified_live_checkers")
    expected_before = {
        B24_CHECKER_PATH.as_posix(): B24_CHECKER_BEFORE_SHA256,
        SUCCESSOR_CHECKER_PATH.as_posix(): SUCCESSOR_CHECKER_BEFORE_SHA256,
    }
    if (
        receipt.get("modified_live_checker_count") != 2
        or not isinstance(checkers, list)
        or len(checkers) != 2
    ):
        add_error(errors, "E_COMPAT_RECEIPT", "modified checker count")
    else:
        seen: set[str] = set()
        for item in checkers:
            if not isinstance(item, dict):
                add_error(errors, "E_COMPAT_RECEIPT", "checker item")
                continue
            path_value = item.get("path")
            if not isinstance(path_value, str):
                add_error(errors, "E_COMPAT_RECEIPT", "checker path")
                continue
            seen.add(path_value)
            relative = Path(path_value)
            if (
                item.get("sha256_before") != expected_before.get(path_value)
                or not (root / relative).exists()
                or item.get("sha256_after") != sha256_file(root / relative)
                or not isinstance(item.get("negative_injection_proof"), dict)
            ):
                add_error(errors, "E_COMPAT_RECEIPT", path_value)
        if seen != set(expected_before):
            add_error(errors, "E_COMPAT_RECEIPT", "modified checker paths")
    current = receipt.get("new_current_checker")
    if (
        not isinstance(current, dict)
        or current.get("path") != "ci/checkers/check_gate1_v1_1_current.py"
        or current.get("sha256") != P1A_CURRENT_GATE1_CHECKER_AS_BUILT_SHA256
    ):
        add_error(errors, "E_COMPAT_RECEIPT", "new checker")
    v1_repair = receipt.get("v1_current_checker_repair")
    expected_v1_repair_proof = {
        "command": "python3 ci/checkers/check_gate1_v1_1_current.py --selftest",
        "must_reject": [
            "route actual leakage into blind packet",
            "same reviewer identity or session/run/signature",
            "missing scoring contract",
            "review role mapped to generation lane",
        ],
    }
    if (
        not isinstance(v1_repair, dict)
        or v1_repair.get("path") != "ci/checkers/check_gate1_v1_1_current.py"
        or v1_repair.get("sha256_before") != CURRENT_GATE1_CHECKER_V1_BEFORE_SHA256
        or v1_repair.get("sha256_after") != P1A_CURRENT_GATE1_CHECKER_AS_BUILT_SHA256
        or v1_repair.get("negative_injection_proof") != expected_v1_repair_proof
    ):
        add_error(errors, "E_COMPAT_RECEIPT", "v1 current checker repair")
    if (
        receipt.get("shared_ledger_or_horizon_modified") is not False
        or receipt.get("historical_allowlist_expanded") is not False
    ):
        add_error(errors, "E_COMPAT_RECEIPT", "shared authority boundary")
    if receipt.get("receipt_digest") != object_digest(receipt, "receipt_digest"):
        add_error(errors, "E_COMPAT_RECEIPT_DIGEST", "mismatch")


def validate_repair_shape(root: Path, errors: list[dict[str, str]]) -> None:
    b24_text = (root / B24_CHECKER_PATH).read_text(encoding="utf-8")
    successor_text = (root / SUCCESSOR_CHECKER_PATH).read_text(encoding="utf-8")
    if (
        "validate_current_write_surface" in b24_text
        or "CURRENT_ALLOWED_EXACT_PATHS" in b24_text
    ):
        add_error(errors, "E_REPAIR_SCOPE", "B24 still owns current write surface")
    if (
        "CURRENT_LEDGER_OWNER_CHECKER" not in successor_text
        or "CURRENT_B_CHANNEL_CHECKER" in successor_text
    ):
        add_error(errors, "E_REPAIR_SCOPE", "successor has not delegated current owner")
    if (
        "HISTORICAL_ROUTE_DIGESTS_19_33" not in successor_text
        or '"E_ROUTE34"' in successor_text
    ):
        add_error(errors, "E_REPAIR_SCOPE", "successor historical scope missing")


def validate_report(root: Path, errors: list[dict[str, str]]) -> None:
    path = root / REPORT_PATH
    if not path.exists() or sha256_file(path) != REPORT_AFTER_POLICY_SHA256:
        add_error(errors, "E_REPORT_ANCHOR", REPORT_PATH.as_posix())
        return
    report = path.read_text(encoding="utf-8")
    required_phrases = (
        "AI 审查可以计入正式审查",
        "身份隔离审查",
        "第二专家至少 48 条且每个 CP 至少 2 条",
        "八份实际执行指令",
        "全部旧关系标 historical/non-active",
        "甲／乙是后续创作与资格测试的质量要求，不是两份审查职责",
        "P2 至 P6 必须继续承接",
    )
    if any(phrase not in report for phrase in required_phrases):
        add_error(errors, "E_REPORT_POLICY", "required policy phrase missing")
    forbidden_phrases = (
        "543 条",
        "654 个槽位",
        "68 个 authorization-like",
        "887 个案例",
        "七份执行 Prompt",
        "3_to_6",
        "3 至 6",
        "预计3..6",
    )
    if any(phrase in report for phrase in forbidden_phrases):
        add_error(errors, "E_REPORT_POLICY", "obsolete process metric retained")


def p1b_document(
    root: Path, relative_path: Path, key: str, errors: list[dict[str, str]]
) -> dict[str, Any] | None:
    try:
        value = load_yaml(root / relative_path).get(key)
    except (OSError, TypeError, ValueError, yaml.YAMLError) as exc:
        add_error(errors, "E_P1B_SCHEMA", f"{relative_path}:{exc}")
        return None
    if not isinstance(value, dict):
        add_error(errors, "E_P1B_SCHEMA", relative_path.as_posix())
        return None
    return value


def validate_p1b(
    root: Path, source: dict[str, Any] | None, errors: list[dict[str, str]]
) -> None:
    """Independently verify P1B's externally signed inputs and mechanical closeout."""

    required = (
        P1B_MATERIALIZER_PATH,
        P1B_IMPORT_MANIFEST_PATH,
        P1B_CONTRACT_PATH,
        P1B_NORMALIZED_PATH,
        P1B_CONTENT_PATH,
        P1B_CONTENT_GAPS_PATH,
        P1B_ROUTE_GOLD_PATH,
        P1B_ROUTE_FREEZE_PATH,
        P1B_ROUTE_COMPARISON_PATH,
        P1B_COMPONENT_PATH,
        P1B_ACTIVE_COMPONENTS_PATH,
        P1B_ACTIVE_EDGES_PATH,
        P1B_COMPONENT_GAPS_PATH,
        P1B_TEST_INPUTS_PATH,
        P1B_COMPAT_RECEIPT_PATH,
        P1B_RESULT_PATH,
    )
    for relative_path in required:
        if not (root / relative_path).exists():
            add_error(errors, "E_P1B_REQUIRED_FILE", relative_path.as_posix())
    if any(error["code"] == "E_P1B_REQUIRED_FILE" for error in errors):
        return

    for import_path, expected_hash in P1B_IMPORT_HASHES.items():
        path = root / P1B_TASK_ROOT / "imports" / import_path
        if not path.exists() or sha256_file(path) != expected_hash:
            add_error(errors, "E_P1B_IMPORT_HASH", import_path)

    import_manifest = p1b_document(
        root, P1B_IMPORT_MANIFEST_PATH, "signed_review_import_manifest", errors
    )
    contract = p1b_document(
        root, P1B_CONTRACT_PATH, "p1b_signed_review_closeout_contract", errors
    )
    content_gaps = p1b_document(
        root, P1B_CONTENT_GAPS_PATH, "reference_120_content_product_gap_matrix", errors
    )
    route_freeze = p1b_document(
        root, P1B_ROUTE_FREEZE_PATH, "route_60_gold_freeze_manifest", errors
    )
    component_gaps = p1b_document(
        root, P1B_COMPONENT_GAPS_PATH, "component_supply_gap_matrix", errors
    )
    test_inputs = p1b_document(
        root, P1B_TEST_INPUTS_PATH, "gate1_development_test_input_manifest", errors
    )
    compatibility = p1b_document(
        root, P1B_COMPAT_RECEIPT_PATH, "p1b_historical_identity_repair_receipt", errors
    )
    result = p1b_document(
        root, P1B_RESULT_PATH, "p1b_signed_review_closeout_result", errors
    )
    documents = (
        (import_manifest, "manifest_digest"),
        (contract, "contract_digest"),
        (content_gaps, "matrix_digest"),
        (route_freeze, "freeze_manifest_digest"),
        (component_gaps, "matrix_digest"),
        (test_inputs, "manifest_digest"),
        (compatibility, "receipt_digest"),
        (result, "result_digest"),
    )
    for document, digest_key in documents:
        if document is not None and document.get(digest_key) != object_digest(
            document, digest_key
        ):
            add_error(errors, "E_P1B_DOCUMENT_DIGEST", digest_key)
    if any(value is None for value, _ in documents):
        return
    if any(
        value is None
        for value in (
            import_manifest,
            contract,
            content_gaps,
            route_freeze,
            component_gaps,
            test_inputs,
            compatibility,
            result,
        )
    ):
        return

    entries = import_manifest.get("entries")
    if (
        import_manifest.get("task_id") != P1B_TASK_ID
        or import_manifest.get("external_review_count") != len(P1B_IMPORT_HASHES)
        or not isinstance(entries, list)
        or {
            entry.get("import_path"): entry.get("sha256")
            for entry in entries
            if isinstance(entry, dict)
        }
        != {f"imports/{path}": digest for path, digest in P1B_IMPORT_HASHES.items()}
    ):
        add_error(errors, "E_P1B_IMPORT_MANIFEST", "signed input set")
    if (
        contract.get("task_id") != P1B_TASK_ID
        or contract.get("fourth_review_forbidden") is not True
        or contract.get("input_model") != "THREE_SIGNED_REVIEW_STRUCTURES_ONLY"
        or recursively_find_true(contract.get("readiness"), READY_KEYS)
    ):
        add_error(errors, "E_P1B_CONTRACT", "closeout boundary")

    try:
        normalized_rows = read_jsonl(root / P1B_NORMALIZED_PATH)
        content_rows = read_jsonl(root / P1B_CONTENT_PATH)
        gold_rows = read_jsonl(root / P1B_ROUTE_GOLD_PATH)
        comparison_rows = read_jsonl(root / P1B_ROUTE_COMPARISON_PATH)
        component_rows = read_jsonl(root / P1B_COMPONENT_PATH)
        active_components = read_jsonl(root / P1B_ACTIVE_COMPONENTS_PATH)
        active_edges = read_jsonl(root / P1B_ACTIVE_EDGES_PATH)
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        add_error(errors, "E_P1B_PARSE", str(exc))
        return
    normalized = [row for row, _ in normalized_rows]
    content = [row for row, _ in content_rows]
    gold = [row for row, _ in gold_rows]
    comparison = [row for row, _ in comparison_rows]
    components = [row for row, _ in component_rows]
    if (
        len(normalized) != 503
        or len({row.get("normalized_record_id") for row in normalized}) != 503
        or any(
            row.get("source_generation_lane_or_pair_ref") is not None
            or row.get("optional_lane_applicability") is not None
            for row in normalized
        )
    ):
        add_error(
            errors, "E_P1B_REVIEW_NORMALIZATION", "count, identity, or lane evidence"
        )
    if source is not None:
        content_ids = {row.get("asset_id") for row in content}
        counted_content = [
            row
            for row in content
            if row.get("final_disposition") == "COUNT_TOWARD_FINAL_300_POSITIVE"
        ]
        if (
            len(content) != 120
            or content_ids != set(source["clean_by_id"])
            or any(
                row.get("source_record_sha256")
                != source["clean_by_id"].get(row.get("asset_id"))
                for row in content
            )
            or len(counted_content) != 29
        ):
            add_error(errors, "E_P1B_CONTENT_CLOSEOUT", "120 disposition derivation")
        actual_rows = {
            row.get("case_id"): row
            for row, _ in read_jsonl(root / ROUTE_ACTUAL_PATH)
            if isinstance(row.get("case_id"), str)
        }
        if (
            len(gold) != 60
            or len({row.get("case_id") for row in gold}) != 60
            or len(comparison) != 60
            or len({row.get("case_id") for row in comparison}) != 60
            or set(row.get("case_id") for row in gold)
            != set(source["route_input_by_id"])
            or any(
                row.get("current_actual_record_sha256")
                != source["route_actual_by_id"].get(row.get("case_id"))
                for row in comparison
            )
            or any(
                not isinstance(actual_rows.get(row.get("case_id")), dict)
                or row.get("current_primary_action")
                != actual_rows[row["case_id"]]
                .get("actual_decision", {})
                .get("actual_primary_action")
                or row.get("current_primary_reason_code")
                != actual_rows[row["case_id"]]
                .get("actual_decision", {})
                .get("actual_primary_reason_code")
                or row.get("primary_action_matches_gold")
                != (row.get("gold_primary_action") == row.get("current_primary_action"))
                or row.get("primary_reason_matches_gold")
                != (
                    row.get("gold_reason_code")
                    == row.get("current_primary_reason_code")
                )
                for row in comparison
            )
        ):
            add_error(errors, "E_P1B_ROUTE_COMPARISON", "60 signed gold answers")
        if (
            len(components) != 86
            or {row.get("component_id") for row in components}
            != set(source["component_by_id"])
            or any(
                row.get("source_record_sha256")
                != source["component_by_id"].get(row.get("component_id"))
                for row in components
            )
            or any(
                row.get("final_disposition") == "KEEP_ACTIVE_FOR_GATE1_DEVELOPMENT_TEST"
                for row in components
            )
            or active_components
            or active_edges
        ):
            add_error(errors, "E_P1B_COMPONENT_CLOSEOUT", "86 candidate disposition")
    golden_text = (root / P1B_ROUTE_GOLD_PATH).read_text(encoding="utf-8")
    freeze_text = (root / P1B_ROUTE_FREEZE_PATH).read_text(encoding="utf-8")
    if (
        ROUTE_ACTUAL_PATH.as_posix() in golden_text
        or ROUTE_ACTUAL_SHA256 in golden_text
        or ROUTE_ACTUAL_PATH.as_posix() in freeze_text
        or ROUTE_ACTUAL_SHA256 in freeze_text
        or route_freeze.get("gold_answers_sha256")
        != sha256_file(root / P1B_ROUTE_GOLD_PATH)
    ):
        add_error(
            errors, "E_P1B_ROUTE_BLINDNESS", "actual implementation leaked into gold"
        )
    if (
        content_gaps.get("counted_positive_parent_count") != 29
        or content_gaps.get("legacy_inventory_count") != 120
        or not isinstance(content_gaps.get("entries"), list)
        or len(content_gaps["entries"]) != 20
        or component_gaps.get("active_component_count") != 0
        or component_gaps.get("active_edge_count") != 0
        or component_gaps.get("complete_profile_count") != 0
        or component_gaps.get("incomplete_profile_count") != 20
        or not isinstance(component_gaps.get("entries"), list)
        or len(component_gaps["entries"]) != 20
    ):
        add_error(errors, "E_P1B_GAP_MATRIX", "content or component gap")
    if (
        test_inputs.get("component_count") != 0
        or test_inputs.get("edge_count") != 0
        or test_inputs.get("p2_input_eligible") is not False
        or recursively_find_true(test_inputs, READY_KEYS)
    ):
        add_error(errors, "E_P1B_TEST_INPUTS", "supply must remain unavailable")
    current_successor = compatibility.get("current_gate1_checker_successor")
    p1a_protection = compatibility.get("p1a_materializer_reference_safe_change")
    if (
        compatibility.get("modified_live_checker_count") != 1
        or compatibility.get("historical_assets_rewritten") is not False
        or not isinstance(current_successor, dict)
        or current_successor.get("sha256_after")
        != P1B_CURRENT_GATE1_CHECKER_AS_BUILT_SHA256
        or not isinstance(p1a_protection, dict)
        or p1a_protection.get("historical_current_checker_sha256")
        != P1A_CURRENT_GATE1_CHECKER_AS_BUILT_SHA256
        or p1a_protection.get("p1a_generated_output_bytes_changed") is not False
    ):
        add_error(errors, "E_P1B_COMPATIBILITY", "historical identity protection")
    impact = result.get("core_number_impact")
    if (
        result.get("task_id") != P1B_TASK_ID
        or result.get("result_state") != "STOPPED_COMPONENT_SUPPLY_GAP"
        or result.get("p2_allowed") is not False
        or not isinstance(impact, dict)
        or impact.get("target_total") != 300
        or impact.get("legacy_reference_inventory") != 120
        or impact.get("counted_positive_parent_count") != 29
        or impact.get("component_candidate_inventory") != 86
        or impact.get("active_component_count") != 0
        or result.get("component_supply_incomplete_profile_count") != 20
        or recursively_find_true(result.get("readiness"), READY_KEYS)
    ):
        add_error(errors, "E_P1B_RESULT", "honest stop state")

    if root == ROOT:
        materializer = subprocess.run(
            [sys.executable, str(root / P1B_MATERIALIZER_PATH), "--check"],
            cwd=root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if materializer.returncode != 0:
            add_error(
                errors, "E_P1B_MATERIALIZER", materializer.stderr or materializer.stdout
            )


def p2_yaml_document(
    root: Path,
    relative_path: Path,
    key: str,
    errors: list[dict[str, str]],
) -> dict[str, Any] | None:
    try:
        value = load_yaml(root / relative_path).get(key)
    except (OSError, TypeError, ValueError, yaml.YAMLError) as exc:
        add_error(errors, "E_P2_SCHEMA", f"{relative_path}:{exc}")
        return None
    if not isinstance(value, dict):
        add_error(errors, "E_P2_SCHEMA", relative_path.as_posix())
        return None
    return value


def expected_p2_mechanism(source: dict[str, Any]) -> dict[str, Any]:
    abstract = source.get("abstract_payload")
    if isinstance(abstract, dict):
        return abstract
    return {
        "function": source.get("function"),
        "reusable_mechanism": source.get("reusable_mechanism"),
        "abstraction_invariants": source.get("abstraction_invariants", []),
        "surface_policy": {
            "generate_new_surface": True,
            "parent_verbatim_allowed": False,
            "source_sentence_template_allowed": False,
        },
    }


def expected_p2_provenance(
    source: dict[str, Any],
    candidate_by_id: dict[Any, dict[str, Any]],
) -> dict[str, Any] | None:
    component_id = str(source.get("component_id", ""))
    if component_id.startswith("RCV2-004-"):
        design_basis = source.get("provenance")
        if not isinstance(design_basis, dict):
            return None
        return {
            "source_type": "FOUNDER_AUTHORIZED_DESIGN_COMPONENT",
            "design_basis": design_basis,
            "source_text_span_required": False,
            "evidence_boundary": "DESIGN_MECHANISM_ONLY_NO_FACT_AUTHORITY",
        }
    if component_id.startswith("RCV2-003-"):
        parent_ids = source.get("parent_asset_ids")
        parent_digests = source.get("parent_digests")
        evidence_spans = source.get("evidence_spans")
        if (
            not isinstance(parent_ids, list)
            or not parent_ids
            or not isinstance(parent_digests, dict)
            or not isinstance(evidence_spans, list)
            or not evidence_spans
            or any(parent_id not in parent_digests for parent_id in parent_ids)
        ):
            return None
        return {
            "source_type": "SOURCE_DERIVED",
            "parent_assets": [
                {
                    "parent_asset_id": parent_id,
                    "parent_digest": parent_digests[parent_id],
                }
                for parent_id in parent_ids
            ],
            "evidence_spans": evidence_spans,
            "evidence_boundary": "ABSTRACTED_MECHANISM_NOT_PARENT_SURFACE",
        }
    lineage = source.get("lineage")
    source_refs = (
        lineage.get("source_candidate_refs") if isinstance(lineage, dict) else None
    )
    if not isinstance(source_refs, list) or not source_refs:
        return None
    parent_assets: list[dict[str, Any]] = []
    for source_ref in source_refs:
        candidate_id = (
            source_ref.get("candidate_id") if isinstance(source_ref, dict) else None
        )
        candidate = candidate_by_id.get(candidate_id)
        parent_refs = (
            candidate.get("parent_refs") if isinstance(candidate, dict) else None
        )
        if not isinstance(parent_refs, list) or not parent_refs:
            return None
        for parent_ref in parent_refs:
            if not isinstance(parent_ref, dict):
                return None
            parent_assets.append({"source_candidate_id": candidate_id, **parent_ref})
    return {
        "source_type": "SOURCE_DERIVED",
        "parent_assets": parent_assets,
        "evidence_boundary": "ABSTRACTED_MECHANISM_NOT_PARENT_SURFACE",
    }


def validate_p2(root: Path, errors: list[dict[str, str]]) -> None:
    """Validate the P2 review checkpoint without treating candidates as approved."""

    for relative_path, expected_hash in P2_FROZEN_HASHES.items():
        path = root / relative_path
        if not path.is_file() or sha256_file(path) != expected_hash:
            add_error(errors, "E_P2_FROZEN_INPUT", relative_path.as_posix())
    try:
        successors = [row for row, _ in read_jsonl(root / P2_SUCCESSOR_PATH)]
        components = [row for row, _ in read_jsonl(root / P2_COMPONENTS_PATH)]
        rules = [row for row, _ in read_jsonl(root / P2_RULES_PATH)]
        edges = [row for row, _ in read_jsonl(root / P2_EDGES_PATH)]
        ab_paths = [row for row, _ in read_jsonl(root / P2_AB_PATH)]
        packet = [row for row, _ in read_jsonl(root / P2_REVIEW_PACKET_PATH)]
        source_component_records = read_jsonl(root / COMPONENT_SOURCE_PATH)
        source_components = [row for row, _ in source_component_records]
        candidate_rows = [row for row, _ in read_jsonl(root / CANDIDATE_SOURCE_PATH)]
        p1b_dispositions = [row for row, _ in read_jsonl(root / P1B_COMPONENT_PATH)]
        profiles_root = load_yaml(root / PROFILE_PATH).get(
            "content_product_profile_registry"
        )
    except (
        OSError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
        yaml.YAMLError,
    ) as exc:
        add_error(errors, "E_P2_PARSE", str(exc))
        return
    if not isinstance(profiles_root, dict) or not isinstance(
        profiles_root.get("profiles"), list
    ):
        add_error(errors, "E_P2_PROFILE", "profile registry")
        return
    profiles = profiles_root["profiles"]
    source_by_id = {row.get("component_id"): row for row in source_components}
    source_record_hash_by_id = {
        row.get("component_id"): sha256_bytes(raw.encode("utf-8"))
        for row, raw in source_component_records
    }
    candidate_by_id = {row.get("component_id"): row for row in candidate_rows}
    p1b_by_id = {row.get("component_id"): row for row in p1b_dispositions}
    if (
        len(successors) != 86
        or len(p1b_by_id) != 86
        or len({row.get("historical_component_id") for row in successors}) != 86
        or set(row.get("historical_component_id") for row in successors)
        != set(source_by_id)
        or any(
            row.get("historical_component_digest")
            != source_by_id.get(row.get("historical_component_id"), {}).get(
                "component_digest"
            )
            or row.get("p1b_final_disposition")
            != p1b_by_id.get(row.get("historical_component_id"), {}).get(
                "final_disposition"
            )
            or row.get("historical_inventory_counted_once") is not True
            or row.get("historical_source_unchanged") is not True
            or row.get("active") is not False
            or row.get("independent_review_state") != "PENDING_TWO_REVIEWS"
            or row.get("mapping_digest") != object_digest(row, "mapping_digest")
            for row in successors
        )
    ):
        add_error(errors, "E_P2_SUCCESSOR_MAP", "86 historical successors")

    component_by_id = {row.get("component_id"): row for row in components}
    if len(components) != 78 or len(component_by_id) != 78:
        add_error(errors, "E_P2_COMPONENT_COUNT", str(len(components)))
    for component in components:
        component_id = component.get("component_id")
        provenance = component.get("provenance")
        source = source_by_id.get(component_id)
        disposition = p1b_by_id.get(component_id)
        expected_provenance = (
            expected_p2_provenance(source, candidate_by_id)
            if isinstance(source, dict)
            else None
        )
        if (
            component.get("component_digest")
            != object_digest(component, "component_digest")
            or component.get("new_generator_consumable") is not False
            or component.get("independent_review_state") != "PENDING_TWO_REVIEWS"
            or recursively_find_true(component.get("readiness"), READY_KEYS)
            or not isinstance(provenance, dict)
        ):
            add_error(errors, "E_P2_COMPONENT_SCHEMA", str(component_id))
        if (
            not isinstance(source, dict)
            or not isinstance(disposition, dict)
            or expected_provenance is None
            or canonical_json(provenance) != canonical_json(expected_provenance)
            or component.get("supersedes_component_digest")
            != source.get("component_digest")
            or component.get("historical_source_sha256")
            != source_record_hash_by_id.get(component_id)
            or component.get("historical_source_sha256")
            != disposition.get("source_record_sha256")
            or component.get("component_role")
            != (source.get("source_component_role") or source.get("component_role"))
            or component.get("composition_asset_class")
            != source.get("composition_asset_class")
            or canonical_json(component.get("mechanism"))
            != canonical_json(expected_p2_mechanism(source))
            or component.get("required_input_slots")
            != (
                source.get("required_input_slots")
                or source.get("input_slot_contract", {}).get("required", [])
            )
            or component.get("required_fact_slots")
            != source.get("required_fact_slots", [])
            or component.get("required_authorization_slots")
            != source.get("required_authorization_slots", [])
            or component.get("truth_boundary") != source.get("truth_boundary", {})
            or component.get("historical_applicability_only")
            != source.get("applicable_content_product_type_ids", [])
        ):
            add_error(errors, "E_P2_COMPONENT_PROVENANCE", str(component_id))

    control_source_ids = {
        row.get("supersedes_misclassified_component_id") for row in rules
    }
    rule_by_source = {
        row.get("supersedes_misclassified_component_id"): row for row in rules
    }
    if (
        len(rules) != 8
        or len(control_source_ids) != 8
        or any(
            row.get("control_rule_digest") != object_digest(row, "control_rule_digest")
            or row.get("supersedes_component_digest")
            != source_by_id.get(
                row.get("supersedes_misclassified_component_id"), {}
            ).get("component_digest")
            or row.get("applicability_boundary")
            != source_by_id.get(
                row.get("supersedes_misclassified_component_id"), {}
            ).get("applicable_content_product_type_ids", [])
            or canonical_json(row.get("source_mechanism"))
            != canonical_json(
                expected_p2_mechanism(
                    source_by_id.get(
                        row.get("supersedes_misclassified_component_id"), {}
                    )
                )
            )
            or row.get("contributes_component_supply") is not False
            or row.get("may_write_audience_surface") is not False
            or row.get("active") is not False
            or row.get("independent_review_state") != "PENDING_TWO_REVIEWS"
            for row in rules
        )
    ):
        add_error(errors, "E_P2_CONTROL_RULES", "8 separate control rules")

    selected_ids = {
        row.get("component_id")
        for row in components
        if str(row.get("activation_proposal", "")).startswith("PROPOSED")
    }
    for successor in successors:
        source_id = successor.get("historical_component_id")
        rule = rule_by_source.get(source_id)
        component = component_by_id.get(source_id)
        if rule is not None:
            expected_id = rule.get("control_rule_id")
            expected_digest = rule.get("control_rule_digest")
            expected_disposition = "RECLASSIFIED_AS_CONTROL_RULE_CANDIDATE"
        elif component is not None:
            expected_id = source_id
            expected_digest = component.get("component_digest")
            expected_disposition = (
                "REVISED_COMPONENT_PROPOSED_FOR_ACTIVATION"
                if source_id in selected_ids
                else "REVISED_COMPONENT_DEFERRED_NOT_REQUIRED_FOR_P2"
            )
        else:
            expected_id = None
            expected_digest = None
            expected_disposition = None
        if (
            successor.get("successor_id") != expected_id
            or successor.get("successor_digest") != expected_digest
            or successor.get("p2_successor_disposition") != expected_disposition
        ):
            add_error(errors, "E_P2_SUCCESSOR_MAP", str(source_id))
    profile_by_id = {row.get("content_product_type_id"): row for row in profiles}
    demand_cells = {
        (row.get("content_product_type_id"), requirement.get("role"))
        for row in profiles
        for requirement in row.get("required_component_roles", [])
    }
    edge_cells: Counter[tuple[Any, Any]] = Counter()
    edge_ranks: dict[tuple[Any, Any], set[str]] = {}
    edge_by_id: dict[Any, dict[str, Any]] = {}
    for edge in edges:
        edge_id = edge.get("edge_id")
        component = component_by_id.get(edge.get("component_id"))
        profile = profile_by_id.get(edge.get("content_product_type_id"))
        cell = (
            edge.get("content_product_type_id"),
            edge.get("required_component_role"),
        )
        rank = str(edge_id).rsplit("-", 1)[-1]
        edge_by_id[edge_id] = edge
        edge_cells[cell] += 1
        edge_ranks.setdefault(cell, set()).add(rank)
        mechanism = component.get("mechanism") if isinstance(component, dict) else {}
        function = (
            mechanism.get("function") or mechanism.get("reusable_mechanism")
            if isinstance(mechanism, dict)
            else None
        )
        input_requirements = (
            profile.get("input_requirements", {}) if isinstance(profile, dict) else {}
        )
        expected_fit_basis = {
            "profile_requires_exact_role": cell[1],
            "component_mechanism": function,
            "business_purpose": (
                profile.get("business_purpose") if isinstance(profile, dict) else None
            ),
            "profile_specific_hard_guards": (
                profile.get("founder_hard_guards", [])
                if isinstance(profile, dict)
                else []
            ),
            "fact_set_must_be_runtime_supplied": True,
        }
        expected_bindings = {
            "profile": {
                "source": list(input_requirements.get("required_source_slots", [])),
                "fact": list(input_requirements.get("required_fact_slots", [])),
                "authorization": list(
                    input_requirements.get("required_authorization_slots", [])
                ),
            },
            "component_input_slots": (
                component.get("required_input_slots", [])
                if isinstance(component, dict)
                else []
            ),
            "component_fact_slots": (
                component.get("required_fact_slots", [])
                if isinstance(component, dict)
                else []
            ),
            "component_authorization_slots": (
                component.get("required_authorization_slots", [])
                if isinstance(component, dict)
                else []
            ),
        }
        if (
            edge.get("edge_digest") != object_digest(edge, "edge_digest")
            or edge_id != f"P2-EDGE-{cell[0]}-{cell[1]}-{rank}"
            or rank not in {"01", "02"}
            or edge.get("selection_purpose")
            != ("MINIMUM_SUPPLY" if rank == "01" else "AB_STRUCTURAL_ALTERNATIVE")
            or edge.get("active") is not False
            or edge.get("historical_edge_reactivated") is not False
            or edge.get("proposed_new_edge") is not True
            or edge.get("independent_review_state") != "PENDING_TWO_REVIEWS"
            or component is None
            or edge.get("component_id") not in selected_ids
            or edge.get("component_digest") != component.get("component_digest")
            or component.get("component_role") != cell[1]
            or cell not in demand_cells
            or profile is None
            or canonical_json(edge.get("fit_basis"))
            != canonical_json(expected_fit_basis)
            or canonical_json(edge.get("required_bindings"))
            != canonical_json(expected_bindings)
            or edge.get("forbidden_combinations")
            != component.get("forbidden_combinations")
            or edge.get("missing_input_behavior")
            != component.get("missing_input_behavior")
        ):
            add_error(errors, "E_P2_EDGE", str(edge_id))
    if (
        len(edges) != 162
        or len(edge_by_id) != 162
        or set(edge_cells) != demand_cells
        or any(count < 1 or count > 2 for count in edge_cells.values())
        or any(
            ranks != ({"01"} if edge_cells[cell] == 1 else {"01", "02"})
            for cell, ranks in edge_ranks.items()
        )
        or len(selected_ids) != 54
    ):
        add_error(errors, "E_P2_EDGE_COVERAGE", "need-driven 20CP role coverage")

    supply = p2_yaml_document(root, P2_SUPPLY_PATH, "candidate_supply_matrix", errors)
    addition = p2_yaml_document(
        root, P2_ADDITION_PATH, "necessary_addition_assessment", errors
    )
    if supply is not None and (
        supply.get("matrix_digest") != object_digest(supply, "matrix_digest")
        or supply.get("candidate_complete_profile_count") != 20
        or supply.get("approved_complete_profile_count") != 0
        or supply.get("components_active") is not False
        or not isinstance(supply.get("entries"), list)
        or len(supply["entries"]) != 20
        or any(
            row.get("candidate_supply_complete") is not True
            or row.get("approved_supply_complete") is not False
            or any(
                role.get("candidate_count", 0) < role.get("minimum", 1)
                or role.get("approved_count") != 0
                for role in row.get("required_roles", [])
            )
            for row in supply["entries"]
        )
    ):
        add_error(errors, "E_P2_SUPPLY", "candidate is not approved supply")
    if addition is not None and (
        addition.get("assessment_digest")
        != object_digest(addition, "assessment_digest")
        or addition.get("historical_starting_inventory") != 86
        or addition.get("necessary_addition_count") != 0
        or addition.get("necessary_additions") != []
        or addition.get("number_target_used") is not False
        or addition.get("future_addition_policy")
        != "ALLOW_ONLY_AFTER_INDEPENDENT_REVIEW_CONFIRMS_A_REAL_ROLE_OR_AB_GAP"
    ):
        add_error(errors, "E_P2_ADDITION_POLICY", "number-driven or unsupported")

    ab_by_cp = {row.get("content_product_type_id"): row for row in ab_paths}
    if len(ab_paths) != 20 or set(ab_by_cp) != set(profile_by_id):
        add_error(errors, "E_P2_AB_PATH", "20CP coverage")
    for cp_id, path in ab_by_cp.items():
        lane_a = path.get("lane_a")
        lane_b = path.get("lane_b")
        axes = path.get("observable_difference_axes")
        differing_axes = (
            [axis for axis in axes if lane_a.get(axis) != lane_b.get(axis)]
            if isinstance(lane_a, dict)
            and isinstance(lane_b, dict)
            and isinstance(axes, list)
            else []
        )
        if (
            path.get("path_digest") != object_digest(path, "path_digest")
            or path.get("same_fact_source_authorization_and_boundary_required")
            is not True
            or not isinstance(axes, list)
            or len(axes) != len(set(axes))
            or len(differing_axes) != len(axes)
            or path.get("observable_difference_axis_count") != len(differing_axes)
            or len(differing_axes) < 4
            or path.get("content_quality_proven") is not False
            or path.get("structural_candidate_only") is not True
            or path.get("independent_review_state") != "PENDING_TWO_REVIEWS"
            or path.get("active") is not False
            or not isinstance(lane_a, dict)
            or not isinstance(lane_b, dict)
            or lane_a.get("session_policy") == lane_b.get("session_policy")
            or not set(lane_a.get("component_ids", [])).issubset(selected_ids)
            or not set(lane_b.get("component_ids", [])).issubset(selected_ids)
        ):
            add_error(errors, "E_P2_AB_PATH", str(cp_id))

    object_counts = Counter(row.get("object_type") for row in packet)
    packet_subjects = {
        f"P2-COMPONENT-{row['component_id']}": row
        for row in components
        if row.get("component_id") in selected_ids
    }
    packet_subjects.update(
        {f"P2-CONTROL-{row['control_rule_id']}": row for row in rules}
    )
    packet_subjects.update({f"P2-{row['edge_id']}": row for row in edges})
    packet_subjects.update(
        {f"P2-AB-{row['content_product_type_id']}": row for row in ab_paths}
    )
    if (
        len(packet) != len(packet_subjects)
        or object_counts
        != Counter(
            {
                "PROPOSED_ACTIVE_COMPONENT": 54,
                "CONTROL_RULE_SEPARATION": 8,
                "PROPOSED_COMPONENT_CP_EDGE": 162,
                "AB_STRUCTURAL_PATH_CAPABILITY": 20,
            }
        )
        or any(
            row.get("prefilled_score") is not None
            or row.get("prefilled_decision") is not None
            or canonical_json(row.get("review_subject"))
            != canonical_json(packet_subjects.get(row.get("packet_item_id")))
            for row in packet
        )
    ):
        add_error(errors, "E_P2_REVIEW_PACKET", "self-contained blank review packet")

    review_job = p2_yaml_document(
        root, P2_REVIEW_JOB_PATH, "independent_component_review_job", errors
    )
    if review_job is not None:
        identity = review_job.get("review_identity_policy")
        if (
            review_job.get("review_job_digest")
            != object_digest(review_job, "review_job_digest")
            or review_job.get("review_packet_sha256")
            != sha256_file(root / P2_REVIEW_PACKET_PATH)
            or review_job.get("self_approval_allowed") is not False
            or review_job.get("component_activation_allowed_before_closeout")
            is not False
            or not isinstance(identity, dict)
            or identity.get("reviewer_count") != 2
            or identity.get("reviewers_must_be_different_instances_or_sessions")
            is not True
            or identity.get(
                "reviewers_must_differ_from_component_author_and_p2_executor"
            )
            is not True
            or identity.get("reviewers_must_differ_from_final_activator") is not True
        ):
            add_error(errors, "E_P2_REVIEW_JOB", "identity or packet binding")

    compatibility = p2_yaml_document(
        root, P2_COMPAT_PATH, "p1b_successor_compatibility_receipt", errors
    )
    if compatibility is not None:
        p1b_materializer = compatibility.get("p1b_materializer")
        current_checker = compatibility.get("current_checker")
        if (
            compatibility.get("receipt_digest")
            != object_digest(compatibility, "receipt_digest")
            or not isinstance(p1b_materializer, dict)
            or p1b_materializer.get("sha256_before")
            != "b82cfcedd747f8ac43748f57405c5760f5637e604403a8f5ed8893e504fba11f"
            or p1b_materializer.get("sha256_after")
            != sha256_file(root / P1B_MATERIALIZER_PATH)
            or p1b_materializer.get("historical_task_outputs_changed") is not False
            or p1b_materializer.get("global_owner_managed_by_p1b_after_successor")
            is not False
            or not isinstance(current_checker, dict)
            or current_checker.get("sha256_before")
            != P1B_CURRENT_GATE1_CHECKER_AS_BUILT_SHA256
            or current_checker.get("sha256_after")
            != P2_CHECKPOINT_CURRENT_CHECKER_SHA256
            or current_checker.get("recursive_checker_chain") is not False
            or compatibility.get("shared_ledger_modified") is not False
            or compatibility.get("readiness_changed") is not False
        ):
            add_error(errors, "E_P2_COMPATIBILITY", "reference-safe successor")
    materializer_text = (root / P1B_MATERIALIZER_PATH).read_text(encoding="utf-8")
    if (
        P1B_CURRENT_GATE1_CHECKER_AS_BUILT_SHA256 not in materializer_text
        or "541443a9c5c34047fb5c9a4652412cc019218abd60d29528b57dbc1d771d637a"
        not in materializer_text
        or "CURRENT_OWNER_PATH: yaml_bytes(owner)" in materializer_text
    ):
        add_error(
            errors, "E_P2_P1B_PIN", "P1B can overwrite or forget as-built identity"
        )

    result = p2_yaml_document(
        root, P2_RESULT_PATH, "p2_component_review_checkpoint_result", errors
    )
    if result is not None and (
        result.get("result_digest") != object_digest(result, "result_digest")
        or result.get("checkpoint_state") != "PENDING_INDEPENDENT_COMPONENT_REVIEW"
        or result.get("p2_final_complete") is not False
        or result.get("components_active") is not False
        or result.get("active_component_count") != 0
        or result.get("active_edge_count") != 0
        or result.get("self_approval_count") != 0
        or result.get("approved_supply_complete_profile_count") != 0
        or result.get("p3_allowed") is not False
        or result.get("core_number_impact")
        != {
            "target_total": 300,
            "reference_inventory": 120,
            "historical_component_inventory": 86,
            "all_unchanged": True,
        }
        or recursively_find_true(result.get("readiness"), READY_KEYS)
    ):
        add_error(errors, "E_P2_RESULT", "checkpoint must remain closed")


def p2_signed_review(
    root: Path,
    review_dir: Path,
    packet: list[dict[str, Any]],
    role: str,
    reviewed_commit: str,
    packet_sha256: str,
    prompt_revision: str,
    errors: list[dict[str, str]],
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    records_path = review_dir / "records.jsonl"
    report_path = review_dir / "report.md"
    manifest_path = review_dir / "run_manifest.yaml"
    try:
        records = [row for row, _ in read_jsonl(root / records_path)]
        report = (root / report_path).read_text(encoding="utf-8")
        manifest = load_yaml(root / manifest_path)
    except (OSError, TypeError, ValueError, json.JSONDecodeError, yaml.YAMLError) as exc:
        add_error(errors, "E_P2_SIGNED_REVIEW", f"{review_dir}:{exc}")
        return [], {}
    identities: set[str] = set()
    sessions: set[str] = set()
    runs: set[str] = set()
    score_maxima = {
        "source_parent_evidence_15": 15,
        "semantic_atomicity_15": 15,
        "parameterization_composability_20": 20,
        "applicability_compatibility_missing_boundary_15": 15,
        "cross_product_reuse_5": 5,
        "nonduplicate_information_gain_10": 10,
        "type_specific_quality_20": 20,
    }
    if len(records) != len(packet):
        add_error(errors, "E_P2_SIGNED_REVIEW_COUNT", review_dir.as_posix())
    for record, packet_item in zip(records, packet, strict=False):
        item_id = str(packet_item.get("packet_item_id"))
        breakdown = record.get("score_breakdown")
        score_valid = isinstance(breakdown, dict) and all(
            isinstance(breakdown.get(key), int)
            and 0 <= breakdown[key] <= maximum
            for key, maximum in score_maxima.items()
        )
        total = (
            sum(int(breakdown[key]) for key in score_maxima) if score_valid else -1
        )
        common = (
            sum(
                int(breakdown[key])
                for key in score_maxima
                if key != "type_specific_quality_20"
            )
            if score_valid
            else -1
        )
        type_score = int(breakdown["type_specific_quality_20"]) if score_valid else -1
        grade = "A" if total >= 90 else "B" if total >= 80 else "C" if total >= 70 else "D"
        decision = record.get("decision")
        vetoes = record.get("hard_veto_ids")
        severity = record.get("defect_severity")
        decision_valid = (
            decision in {"APPROVE", "REPAIR", "REJECT"}
            and isinstance(vetoes, list)
            and severity in {"NONE", "OBSERVATION", "MINOR", "MAJOR", "FATAL"}
            and (not vetoes or decision == "REJECT")
            and (severity not in {"MAJOR", "FATAL"} or decision != "APPROVE")
            and (decision != "APPROVE" or total >= 90)
            and (grade != "B" or decision == "REPAIR")
        )
        if decision == "APPROVE" and record.get("object_type") in {
            "PROPOSED_ACTIVE_COMPONENT",
            "REVISED_OR_NECESSARY_COMPONENT",
        }:
            decision_valid &= (
                breakdown["semantic_atomicity_15"] >= 13
                and breakdown["parameterization_composability_20"] >= 17
                and breakdown["applicability_compatibility_missing_boundary_15"]
                >= 13
                and type_score >= 17
            )
        if (
            record.get("schema_version") != "v0.1"
            or record.get("task_id") != P2_TASK_ID
            or record.get("prompt_revision") != prompt_revision
            or record.get("review_role") != role
            or record.get("reviewed_commit") != reviewed_commit
            or record.get("review_packet_sha256") != packet_sha256
            or record.get("packet_item_id") != item_id
            or record.get("object_type") != packet_item.get("object_type")
            or record.get("record_digest") != object_digest(record, "record_digest")
            or not score_valid
            or record.get("common_score_80") != common
            or record.get("type_score_20") != type_score
            or record.get("total_score_100") != total
            or record.get("grade") != grade
            or not decision_valid
            or not isinstance(record.get("findings"), list)
            or not isinstance(record.get("rationale"), str)
        ):
            add_error(errors, "E_P2_SIGNED_REVIEW_RECORD", item_id)
        identities.add(str(record.get("reviewer_identity_id")))
        sessions.add(str(record.get("reviewer_instance_or_session_id")))
        runs.add(str(record.get("review_run_id")))
    if len(identities) != 1 or len(sessions) != 1 or len(runs) != 1:
        add_error(errors, "E_P2_SIGNED_REVIEW_IDENTITY", review_dir.as_posix())
        return records, {}
    identity = next(iter(identities))
    session = next(iter(sessions))
    run = next(iter(runs))
    manifest_text = canonical_json(manifest)
    if not report.strip() or any(
        value not in manifest_text
        for value in (identity, session, run, reviewed_commit, packet_sha256)
    ):
        add_error(errors, "E_P2_SIGNED_REVIEW_ARTIFACT", review_dir.as_posix())
    return records, {
        "identity": identity,
        "session": session,
        "run": run,
        "records_sha256": sha256_file(root / records_path),
        "report_sha256": sha256_file(root / report_path),
        "manifest_sha256": sha256_file(root / manifest_path),
    }


def p2_independent_route(
    route_input: dict[str, Any], profile: dict[str, Any]
) -> tuple[str, str]:
    payload = route_input.get("actual_input_payload")
    if not isinstance(payload, dict):
        raise ValueError("route payload missing")
    requirements = profile.get("input_requirements")
    if not isinstance(requirements, dict):
        raise ValueError("profile requirements missing")
    present = {
        "source": set(map(str, payload.get("present_source_slots", []))),
        "fact": set(map(str, payload.get("present_fact_slots", []))),
        "authorization": set(
            map(str, payload.get("present_authorization_slots", []))
        ),
    }
    missing = {
        key: set(map(str, requirements.get(f"required_{key}_slots", [])))
        .difference(present[key])
        for key in ("source", "fact", "authorization")
    }
    risks = set(map(str, payload.get("risk_points", [])))
    guards = set(map(str, payload.get("hard_guard_hits", [])))
    if guards or any(value.startswith("AGR_") or value.startswith("hard_guard:AGR_") for value in risks):
        return "BLOCK", "输入冲突"
    if risks.intersection(
        {"PRIVACY_AUTHORIZATION_FAILURE", "ROLE_AUTHORITY_EXPANSION", "UNAUTHORIZED_BRAND_CLAIM"}
    ):
        return "BLOCK", "授权缺失"
    if risks.intersection(
        {"FABRICATED_EVENT", "FABRICATED_PERSON_EXPERIENCE", "UNSUPPORTED_NUMERIC_OR_PERFORMANCE_CLAIM"}
    ):
        return "BLOCK", "事实缺失"
    missing_classes = [
        key for key in ("authorization", "fact", "source") if missing[key]
    ]
    if not missing_classes:
        raise ValueError("unexpected route allow")
    slot_class = missing_classes[0]
    category = "授权缺失" if slot_class == "authorization" else "事实缺失"
    route_id = f"required_{slot_class}_missing"
    routes = {
        row.get("route_id"): row
        for row in profile.get("input_sufficiency_routes", [])
        if isinstance(row, dict)
    }
    route = routes.get(route_id)
    if not isinstance(route, dict):
        raise ValueError(f"missing route {route_id}")
    partial = payload.get("partial_artifact_payload")
    requested = str(payload.get("requested_degraded_output", ""))
    if (
        payload.get("partial_safe") is True
        and route.get("audience_facing_body_allowed") is False
        and requested in set(map(str, route.get("allowed_outputs", [])))
        and isinstance(partial, dict)
        and bool(partial)
    ):
        return "DEGRADE", category
    return "REQUEST_INPUT", category


def validate_p2_final(root: Path, errors: list[dict[str, str]]) -> None:
    """Independently validate signed P2 activation and generator evidence."""

    try:
        initial_packet = [row for row, _ in read_jsonl(root / P2_REVIEW_PACKET_PATH)]
        targeted_r1_packet = [
            row for row, _ in read_jsonl(root / P2_TARGET_REVIEW_PACKET_PATH)
        ]
        targeted_r2_packet = [
            row for row, _ in read_jsonl(root / P2_TARGET_R2_REVIEW_PACKET_PATH)
        ]
        targeted_r3_packet = [
            row for row, _ in read_jsonl(root / P2_TARGET_R3_REVIEW_PACKET_PATH)
        ]
        targeted_r4_packet = [
            row for row, _ in read_jsonl(root / P2_TARGET_R4_REVIEW_PACKET_PATH)
        ]
        targeted_r5_packet = [
            row for row, _ in read_jsonl(root / P2_TARGET_R5_REVIEW_PACKET_PATH)
        ]
        targeted_r6_packet = [
            row for row, _ in read_jsonl(root / P2_TARGET_R6_REVIEW_PACKET_PATH)
        ]
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        add_error(errors, "E_P2_FINAL_PACKET", str(exc))
        return
    if sha256_file(root / P2_REVIEW_PACKET_PATH) != P2_INITIAL_REVIEW_PACKET_SHA256:
        add_error(errors, "E_P2_FINAL_PACKET", "initial packet drift")
    if sha256_file(root / P2_TARGET_REVIEW_PACKET_PATH) != P2_TARGET_REVIEW_PACKET_SHA256:
        add_error(errors, "E_P2_FINAL_PACKET", "targeted r1 packet drift")
    if (
        sha256_file(root / P2_TARGET_R2_REVIEW_PACKET_PATH)
        != P2_TARGET_R2_REVIEW_PACKET_SHA256
    ):
        add_error(errors, "E_P2_FINAL_PACKET", "targeted r2 packet drift")
    if (
        sha256_file(root / P2_TARGET_R3_REVIEW_PACKET_PATH)
        != P2_TARGET_R3_REVIEW_PACKET_SHA256
    ):
        add_error(errors, "E_P2_FINAL_PACKET", "targeted r3 packet drift")
    if (
        sha256_file(root / P2_TARGET_R4_REVIEW_PACKET_PATH)
        != P2_TARGET_R4_REVIEW_PACKET_SHA256
    ):
        add_error(errors, "E_P2_FINAL_PACKET", "targeted r4 packet drift")
    if (
        sha256_file(root / P2_TARGET_R5_REVIEW_PACKET_PATH)
        != P2_TARGET_R5_REVIEW_PACKET_SHA256
    ):
        add_error(errors, "E_P2_FINAL_PACKET", "targeted r5 packet drift")
    if (
        sha256_file(root / P2_TARGET_R6_REVIEW_PACKET_PATH)
        != P2_TARGET_R6_REVIEW_PACKET_SHA256
    ):
        add_error(errors, "E_P2_FINAL_PACKET", "targeted r6 packet drift")
    initial_primary, initial_primary_meta = p2_signed_review(
        root,
        P2_INITIAL_PRIMARY_DIR,
        initial_packet,
        "PRIMARY_CONTENT_VALUE_COMPOSABILITY",
        "c37a894930025aac99db18a055d5a79294fa89dc",
        P2_INITIAL_REVIEW_PACKET_SHA256,
        "r0",
        errors,
    )
    initial_secondary, initial_secondary_meta = p2_signed_review(
        root,
        P2_INITIAL_SECONDARY_DIR,
        initial_packet,
        "SECONDARY_PROVENANCE_FACT_AUTHORIZATION",
        "c37a894930025aac99db18a055d5a79294fa89dc",
        P2_INITIAL_REVIEW_PACKET_SHA256,
        "r0",
        errors,
    )
    targeted_r1_primary, targeted_r1_primary_meta = p2_signed_review(
        root,
        P2_TARGET_PRIMARY_DIR,
        targeted_r1_packet,
        "PRIMARY_CONTENT_VALUE_COMPOSABILITY",
        P2_TARGET_REVIEWED_COMMIT,
        P2_TARGET_REVIEW_PACKET_SHA256,
        "r1",
        errors,
    )
    targeted_r1_secondary, targeted_r1_secondary_meta = p2_signed_review(
        root,
        P2_TARGET_SECONDARY_DIR,
        targeted_r1_packet,
        "SECONDARY_PROVENANCE_FACT_AUTHORIZATION",
        P2_TARGET_REVIEWED_COMMIT,
        P2_TARGET_REVIEW_PACKET_SHA256,
        "r1",
        errors,
    )
    targeted_r2_primary, targeted_r2_primary_meta = p2_signed_review(
        root,
        P2_TARGET_R2_PRIMARY_DIR,
        targeted_r2_packet,
        "PRIMARY_CONTENT_VALUE_COMPOSABILITY",
        P2_TARGET_R2_REVIEWED_COMMIT,
        P2_TARGET_R2_REVIEW_PACKET_SHA256,
        "r2",
        errors,
    )
    targeted_r2_secondary, targeted_r2_secondary_meta = p2_signed_review(
        root,
        P2_TARGET_R2_SECONDARY_DIR,
        targeted_r2_packet,
        "SECONDARY_PROVENANCE_FACT_AUTHORIZATION",
        P2_TARGET_R2_REVIEWED_COMMIT,
        P2_TARGET_R2_REVIEW_PACKET_SHA256,
        "r2",
        errors,
    )
    targeted_r3_primary, targeted_r3_primary_meta = p2_signed_review(
        root,
        P2_TARGET_R3_PRIMARY_DIR,
        targeted_r3_packet,
        "PRIMARY_CONTENT_VALUE_COMPOSABILITY",
        P2_TARGET_R3_REVIEWED_COMMIT,
        P2_TARGET_R3_REVIEW_PACKET_SHA256,
        "r3",
        errors,
    )
    targeted_r3_secondary, targeted_r3_secondary_meta = p2_signed_review(
        root,
        P2_TARGET_R3_SECONDARY_DIR,
        targeted_r3_packet,
        "SECONDARY_PROVENANCE_FACT_AUTHORIZATION",
        P2_TARGET_R3_REVIEWED_COMMIT,
        P2_TARGET_R3_REVIEW_PACKET_SHA256,
        "r3",
        errors,
    )
    targeted_r4_primary, targeted_r4_primary_meta = p2_signed_review(
        root,
        P2_TARGET_R4_PRIMARY_DIR,
        targeted_r4_packet,
        "PRIMARY_CONTENT_VALUE_COMPOSABILITY",
        P2_TARGET_R4_REVIEWED_COMMIT,
        P2_TARGET_R4_REVIEW_PACKET_SHA256,
        "r4",
        errors,
    )
    targeted_r4_secondary, targeted_r4_secondary_meta = p2_signed_review(
        root,
        P2_TARGET_R4_SECONDARY_DIR,
        targeted_r4_packet,
        "SECONDARY_PROVENANCE_FACT_AUTHORIZATION",
        P2_TARGET_R4_REVIEWED_COMMIT,
        P2_TARGET_R4_REVIEW_PACKET_SHA256,
        "r4",
        errors,
    )
    targeted_r5_primary, targeted_r5_primary_meta = p2_signed_review(
        root,
        P2_TARGET_R5_PRIMARY_DIR,
        targeted_r5_packet,
        "PRIMARY_CONTENT_VALUE_COMPOSABILITY",
        P2_TARGET_R5_REVIEWED_COMMIT,
        P2_TARGET_R5_REVIEW_PACKET_SHA256,
        "r5",
        errors,
    )
    targeted_r5_secondary, targeted_r5_secondary_meta = p2_signed_review(
        root,
        P2_TARGET_R5_SECONDARY_DIR,
        targeted_r5_packet,
        "SECONDARY_PROVENANCE_FACT_AUTHORIZATION",
        P2_TARGET_R5_REVIEWED_COMMIT,
        P2_TARGET_R5_REVIEW_PACKET_SHA256,
        "r5",
        errors,
    )
    targeted_r6_primary, targeted_r6_primary_meta = p2_signed_review(
        root,
        P2_TARGET_R6_PRIMARY_DIR,
        targeted_r6_packet,
        "PRIMARY_CONTENT_VALUE_COMPOSABILITY",
        P2_TARGET_R6_REVIEWED_COMMIT,
        P2_TARGET_R6_REVIEW_PACKET_SHA256,
        "r6",
        errors,
    )
    targeted_r6_secondary, targeted_r6_secondary_meta = p2_signed_review(
        root,
        P2_TARGET_R6_SECONDARY_DIR,
        targeted_r6_packet,
        "SECONDARY_PROVENANCE_FACT_AUTHORIZATION",
        P2_TARGET_R6_REVIEWED_COMMIT,
        P2_TARGET_R6_REVIEW_PACKET_SHA256,
        "r6",
        errors,
    )
    if any(
        not meta
        for meta in (
            initial_primary_meta,
            initial_secondary_meta,
            targeted_r1_primary_meta,
            targeted_r1_secondary_meta,
            targeted_r2_primary_meta,
            targeted_r2_secondary_meta,
            targeted_r3_primary_meta,
            targeted_r3_secondary_meta,
            targeted_r4_primary_meta,
            targeted_r4_secondary_meta,
            targeted_r5_primary_meta,
            targeted_r5_secondary_meta,
            targeted_r6_primary_meta,
            targeted_r6_secondary_meta,
        )
    ):
        return
    if (
        initial_primary_meta["identity"] == initial_secondary_meta["identity"]
        or initial_primary_meta["session"] == initial_secondary_meta["session"]
        or initial_primary_meta["run"] == initial_secondary_meta["run"]
        or targeted_r1_primary_meta["identity"]
        == targeted_r1_secondary_meta["identity"]
        or targeted_r1_primary_meta["session"]
        == targeted_r1_secondary_meta["session"]
        or targeted_r1_primary_meta["run"] == targeted_r1_secondary_meta["run"]
        or targeted_r2_primary_meta["identity"]
        != targeted_r1_primary_meta["identity"]
        or targeted_r2_secondary_meta["identity"]
        != targeted_r1_secondary_meta["identity"]
        or targeted_r2_primary_meta["identity"]
        == targeted_r2_secondary_meta["identity"]
        or targeted_r2_primary_meta["session"]
        == targeted_r2_secondary_meta["session"]
        or targeted_r2_primary_meta["run"] == targeted_r2_secondary_meta["run"]
        or targeted_r2_primary_meta["run"] == targeted_r1_primary_meta["run"]
        or targeted_r2_secondary_meta["run"] == targeted_r1_secondary_meta["run"]
        or targeted_r3_primary_meta["identity"]
        != targeted_r2_primary_meta["identity"]
        or targeted_r3_secondary_meta["identity"]
        != targeted_r2_secondary_meta["identity"]
        or targeted_r3_primary_meta["identity"]
        == targeted_r3_secondary_meta["identity"]
        or targeted_r3_primary_meta["session"]
        == targeted_r3_secondary_meta["session"]
        or targeted_r3_primary_meta["run"] == targeted_r3_secondary_meta["run"]
        or targeted_r3_primary_meta["run"] == targeted_r2_primary_meta["run"]
        or targeted_r3_secondary_meta["run"] == targeted_r2_secondary_meta["run"]
        or targeted_r4_primary_meta["identity"]
        != targeted_r3_primary_meta["identity"]
        or targeted_r4_secondary_meta["identity"]
        != targeted_r3_secondary_meta["identity"]
        or targeted_r4_primary_meta["identity"]
        == targeted_r4_secondary_meta["identity"]
        or targeted_r4_primary_meta["session"]
        == targeted_r4_secondary_meta["session"]
        or targeted_r4_primary_meta["run"] == targeted_r4_secondary_meta["run"]
        or targeted_r4_primary_meta["run"] == targeted_r3_primary_meta["run"]
        or targeted_r4_secondary_meta["run"] == targeted_r3_secondary_meta["run"]
        or targeted_r5_primary_meta["identity"]
        != targeted_r4_primary_meta["identity"]
        or targeted_r5_secondary_meta["identity"]
        != targeted_r4_secondary_meta["identity"]
        or targeted_r5_primary_meta["identity"]
        == targeted_r5_secondary_meta["identity"]
        or targeted_r5_primary_meta["session"]
        == targeted_r5_secondary_meta["session"]
        or targeted_r5_primary_meta["run"] == targeted_r5_secondary_meta["run"]
        or targeted_r5_primary_meta["run"] == targeted_r4_primary_meta["run"]
        or targeted_r5_secondary_meta["run"] == targeted_r4_secondary_meta["run"]
        or targeted_r6_primary_meta["identity"]
        != targeted_r5_primary_meta["identity"]
        or targeted_r6_secondary_meta["identity"]
        != targeted_r5_secondary_meta["identity"]
        or targeted_r6_primary_meta["identity"]
        == targeted_r6_secondary_meta["identity"]
        or targeted_r6_primary_meta["session"]
        == targeted_r6_secondary_meta["session"]
        or targeted_r6_primary_meta["run"] == targeted_r6_secondary_meta["run"]
        or targeted_r6_primary_meta["run"] == targeted_r5_primary_meta["run"]
        or targeted_r6_secondary_meta["run"] == targeted_r5_secondary_meta["run"]
    ):
        add_error(errors, "E_P2_FINAL_REVIEW_IDENTITY", "primary/secondary collision")

    initial_disagreements: list[tuple[dict[str, Any], dict[str, Any], dict[str, Any]]] = []
    expected_initial: dict[str, dict[str, Any]] = {}
    for packet_item, primary, secondary in zip(
        initial_packet, initial_primary, initial_secondary, strict=False
    ):
        item_id = str(packet_item["packet_item_id"])
        if primary["decision"] == secondary["decision"]:
            final_disposition = primary["decision"]
        else:
            final_disposition = "PENDING_ADJUDICATION"
            initial_disagreements.append((packet_item, primary, secondary))
        expected_initial[item_id] = {
            "primary": primary,
            "secondary": secondary,
            "final_disposition": final_disposition,
        }
    try:
        adjudication_records = [
            row
            for row, _ in read_jsonl(
                root / P2_INITIAL_ADJUDICATION_DIR / "records.jsonl"
            )
        ]
        adjudication_report = (
            root / P2_INITIAL_ADJUDICATION_DIR / "report.md"
        ).read_text(encoding="utf-8")
        adjudication_manifest = load_yaml(
            root / P2_INITIAL_ADJUDICATION_DIR / "run_manifest.yaml"
        )
    except (OSError, TypeError, ValueError, json.JSONDecodeError, yaml.YAMLError) as exc:
        add_error(errors, "E_P2_FINAL_ADJUDICATION", str(exc))
        return
    adjudicator_identities: set[str] = set()
    adjudicator_sessions: set[str] = set()
    adjudicator_runs: set[str] = set()
    if len(initial_disagreements) != len(adjudication_records) or len(adjudication_records) != 92:
        add_error(errors, "E_P2_FINAL_ADJUDICATION_COUNT", str(len(adjudication_records)))
    for record, (packet_item, primary, secondary) in zip(
        adjudication_records, initial_disagreements, strict=False
    ):
        item_id = str(packet_item["packet_item_id"])
        if (
            record.get("schema_version") != "v0.1"
            or record.get("task_id") != P2_TASK_ID
            or record.get("prompt_revision") != "r0"
            or record.get("review_role") != "TARGETED_THIRD_ADJUDICATION"
            or record.get("reviewed_commit")
            != "c37a894930025aac99db18a055d5a79294fa89dc"
            or record.get("review_packet_sha256")
            != P2_INITIAL_REVIEW_PACKET_SHA256
            or record.get("packet_item_id") != item_id
            or record.get("object_type") != packet_item.get("object_type")
            or record.get("primary_record_digest") != primary.get("record_digest")
            or record.get("secondary_record_digest")
            != secondary.get("record_digest")
            or record.get("primary_decision") != primary.get("decision")
            or record.get("secondary_decision") != secondary.get("decision")
            or record.get("adjudicated_decision")
            not in {"APPROVE", "REPAIR", "REJECT"}
            or record.get("record_digest") != object_digest(record, "record_digest")
        ):
            add_error(errors, "E_P2_FINAL_ADJUDICATION_RECORD", item_id)
        expected_initial[item_id]["final_disposition"] = record.get(
            "adjudicated_decision"
        )
        expected_initial[item_id]["adjudication_digest"] = record.get(
            "record_digest"
        )
        adjudicator_identities.add(str(record.get("reviewer_identity_id")))
        adjudicator_sessions.add(str(record.get("reviewer_instance_or_session_id")))
        adjudicator_runs.add(str(record.get("review_run_id")))
    if (
        len(adjudicator_identities) != 1
        or len(adjudicator_sessions) != 1
        or len(adjudicator_runs) != 1
        or next(iter(adjudicator_identities), "")
        in {initial_primary_meta["identity"], initial_secondary_meta["identity"]}
    ):
        add_error(errors, "E_P2_FINAL_ADJUDICATION_IDENTITY", "collision")
    adjudication_manifest_text = canonical_json(adjudication_manifest)
    if not adjudication_report.strip() or any(
        value not in adjudication_manifest_text
        for value in (
            next(iter(adjudicator_identities), ""),
            next(iter(adjudicator_sessions), ""),
            next(iter(adjudicator_runs), ""),
            P2_INITIAL_REVIEW_PACKET_SHA256,
        )
    ):
        add_error(errors, "E_P2_FINAL_ADJUDICATION_ARTIFACT", "binding")

    target_r1_decisions = {
        str(packet_item["packet_item_id"]): (
            primary["decision"],
            secondary["decision"],
        )
        for packet_item, primary, secondary in zip(
            targeted_r1_packet,
            targeted_r1_primary,
            targeted_r1_secondary,
            strict=False,
        )
    }
    target_r1_counts = Counter(target_r1_decisions.values())
    if target_r1_counts != Counter(
        {
            ("APPROVE", "APPROVE"): 27,
            ("REPAIR", "REPAIR"): 32,
            ("APPROVE", "REPAIR"): 2,
            ("REPAIR", "APPROVE"): 80,
        }
    ):
        add_error(errors, "E_P2_FINAL_TARGET_R1_REVIEW", str(target_r1_counts))

    target_r2_decisions = {
        str(packet_item["packet_item_id"]): (
            primary["decision"],
            secondary["decision"],
        )
        for packet_item, primary, secondary in zip(
            targeted_r2_packet,
            targeted_r2_primary,
            targeted_r2_secondary,
            strict=False,
        )
    }
    target_r2_counts = Counter(target_r2_decisions.values())
    if target_r2_counts != Counter(
        {
            ("APPROVE", "APPROVE"): 107,
            ("REPAIR", "REPAIR"): 20,
            ("REPAIR", "APPROVE"): 7,
        }
    ):
        add_error(errors, "E_P2_FINAL_TARGET_R2_REVIEW", str(target_r2_counts))

    target_r3_decisions = {
        str(packet_item["packet_item_id"]): (
            primary["decision"],
            secondary["decision"],
        )
        for packet_item, primary, secondary in zip(
            targeted_r3_packet,
            targeted_r3_primary,
            targeted_r3_secondary,
            strict=False,
        )
    }
    target_r3_counts = Counter(target_r3_decisions.values())
    if target_r3_counts != Counter(
        {
            ("APPROVE", "APPROVE"): 2,
            ("REPAIR", "REPAIR"): 21,
            ("REPAIR", "APPROVE"): 6,
        }
    ):
        add_error(errors, "E_P2_FINAL_TARGET_R3_REVIEW", str(target_r3_counts))

    target_r4_decisions = {
        str(packet_item["packet_item_id"]): (
            primary["decision"],
            secondary["decision"],
        )
        for packet_item, primary, secondary in zip(
            targeted_r4_packet,
            targeted_r4_primary,
            targeted_r4_secondary,
            strict=False,
        )
    }
    target_r4_counts = Counter(target_r4_decisions.values())
    if target_r4_counts != Counter(
        {
            ("REPAIR", "REPAIR"): 21,
            ("REPAIR", "APPROVE"): 6,
        }
    ):
        add_error(errors, "E_P2_FINAL_TARGET_R4_REVIEW", str(target_r4_counts))
    target_r4_subjects = {
        str(row.get("packet_item_id")): row.get("review_subject")
        for row in targeted_r4_packet
    }

    target_r5_decisions = {
        str(packet_item["packet_item_id"]): (
            primary["decision"],
            secondary["decision"],
        )
        for packet_item, primary, secondary in zip(
            targeted_r5_packet,
            targeted_r5_primary,
            targeted_r5_secondary,
            strict=False,
        )
    }
    target_r5_counts = Counter(target_r5_decisions.values())
    if target_r5_counts != Counter(
        {("APPROVE", "APPROVE"): 26, ("REPAIR", "APPROVE"): 1}
    ):
        add_error(errors, "E_P2_FINAL_TARGET_R5_REVIEW", str(target_r5_counts))
    target_r5_subjects = {
        str(row.get("packet_item_id")): row.get("review_subject")
        for row in targeted_r5_packet
    }
    r5_core_subject = target_r5_subjects.get("P2R5-GENERATOR-CORE")
    if (
        not isinstance(r5_core_subject, dict)
        or r5_core_subject.get("sha256")
        != sha256_file(root / P2_TASK_ROOT / "p2_generator_core_r5.py")
        or r5_core_subject.get("path_semantics_source", {}).get("sha256")
        != sha256_file(root / P2_TASK_ROOT / "p2_path_semantics_r5.py")
        or r5_core_subject.get("evidence_harness", {}).get("sha256")
        != sha256_file(root / P2_TASK_ROOT / "p2_final_documents_r5.py")
        or r5_core_subject.get("external_provider_allowed") is not False
        or r5_core_subject.get("audience_content_allowed") is not False
        or r5_core_subject.get("readiness_transition_allowed") is not False
    ):
        add_error(errors, "E_P2_FINAL_R5_CORE_REVIEW_BINDING", "subject drift")

    target_r6_decisions = {
        str(packet_item["packet_item_id"]): (
            primary["decision"],
            secondary["decision"],
        )
        for packet_item, primary, secondary in zip(
            targeted_r6_packet,
            targeted_r6_primary,
            targeted_r6_secondary,
            strict=False,
        )
    }
    if target_r6_decisions != {"P2R6-GENERATOR-CORE": ("APPROVE", "APPROVE")}:
        add_error(errors, "E_P2_FINAL_TARGET_R6_REVIEW", str(target_r6_decisions))
    target_r6_subjects = {
        str(row.get("packet_item_id")): row.get("review_subject")
        for row in targeted_r6_packet
    }
    r6_core_subject = target_r6_subjects.get("P2R6-GENERATOR-CORE")
    expected_r6_evidence = {
        "generator/required_slot_trust_root_tamper_results.r6.jsonl": 20,
        "generator/path_program_schema_tamper_results.r6.jsonl": 240,
        "generator/mechanism_identity_tamper_results.r6.jsonl": 62,
        "generator/bound_fact_structural_effect_results.r6.jsonl": 62,
    }
    r6_evidence_rows = (
        r6_core_subject.get("evidence_documents", [])
        if isinstance(r6_core_subject, dict)
        else []
    )
    r6_evidence_by_suffix = {
        str(row.get("path")).split("p2_component_supply_and_generator_core_repair_001/", 1)[-1]: row
        for row in r6_evidence_rows
        if isinstance(row, dict)
    }
    r5_primary_core = next(
        (
            row
            for row in targeted_r5_primary
            if row.get("packet_item_id") == "P2R5-GENERATOR-CORE"
        ),
        {},
    )
    r5_secondary_core = next(
        (
            row
            for row in targeted_r5_secondary
            if row.get("packet_item_id") == "P2R5-GENERATOR-CORE"
        ),
        {},
    )
    expected_r5_failure = {
        "review_packet_sha256": P2_TARGET_R5_REVIEW_PACKET_SHA256,
        "primary_decision": "REPAIR",
        "primary_record_digest": r5_primary_core.get("record_digest"),
        "secondary_decision": "APPROVE",
        "secondary_record_digest": r5_secondary_core.get("record_digest"),
    }
    if (
        not isinstance(r6_core_subject, dict)
        or r6_core_subject.get("sha256")
        != sha256_file(root / P2_TASK_ROOT / "p2_generator_core_r6.py")
        or r6_core_subject.get("evidence_harness", {}).get("sha256")
        != sha256_file(root / P2_TASK_ROOT / "p2_final_documents_r6.py")
        or r6_core_subject.get("external_provider_allowed") is not False
        or r6_core_subject.get("audience_content_allowed") is not False
        or r6_core_subject.get("readiness_transition_allowed") is not False
        or r6_core_subject.get("approved_r5_components_and_paths_modified") is not False
        or canonical_json(r6_core_subject.get("r5_failure_evidence"))
        != canonical_json(expected_r5_failure)
        or set(r6_evidence_by_suffix) != set(expected_r6_evidence)
        or any(
            row.get("case_count") != expected_r6_evidence[suffix]
            or row.get("sha256") != sha256_file(root / P2_TASK_ROOT / suffix)
            for suffix, row in r6_evidence_by_suffix.items()
        )
    ):
        add_error(errors, "E_P2_FINAL_R6_CORE_REVIEW_BINDING", "subject drift")

    try:
        initial_combined = [
            row for row, _ in read_jsonl(root / P2_INITIAL_COMBINED_PATH)
        ]
        targeted_r1_combined = [
            row for row, _ in read_jsonl(root / P2_TARGET_COMBINED_PATH)
        ]
        targeted_r2_combined = [
            row for row, _ in read_jsonl(root / P2_TARGET_R2_COMBINED_PATH)
        ]
        targeted_r3_combined = [
            row for row, _ in read_jsonl(root / P2_TARGET_R3_COMBINED_PATH)
        ]
        targeted_r4_combined = [
            row for row, _ in read_jsonl(root / P2_TARGET_R4_COMBINED_PATH)
        ]
        targeted_r5_combined = [
            row for row, _ in read_jsonl(root / P2_TARGET_R5_COMBINED_PATH)
        ]
        targeted_r6_combined = [
            row for row, _ in read_jsonl(root / P2_TARGET_R6_COMBINED_PATH)
        ]
        active_components = [
            row for row, _ in read_jsonl(root / P2_ACTIVE_COMPONENTS_PATH)
        ]
        active_rules = [row for row, _ in read_jsonl(root / P2_ACTIVE_RULES_PATH)]
        active_edges = [row for row, _ in read_jsonl(root / P2_ACTIVE_EDGES_PATH)]
        active_paths = [row for row, _ in read_jsonl(root / P2_ACTIVE_AB_PATH)]
        requests = [row for row, _ in read_jsonl(root / P2_AUTHOR_REQUESTS_PATH)]
        realizations = [row for row, _ in read_jsonl(root / P2_REALIZATIONS_PATH)]
        pair_results = [row for row, _ in read_jsonl(root / P2_PAIR_RESULTS_PATH)]
        axis_body_pairs = [
            row for row, _ in read_jsonl(root / P2_AXIS_BODY_PAIR_RESULTS_PATH)
        ]
        path_program_tampers = [
            row for row, _ in read_jsonl(root / P2_PATH_PROGRAM_TAMPER_RESULTS_PATH)
        ]
        trust_contract_tampers = [
            row for row, _ in read_jsonl(root / P2_TRUST_CONTRACT_TAMPER_RESULTS_PATH)
        ]
        component_pointer_results = [
            row for row, _ in read_jsonl(root / P2_COMPONENT_POINTER_RESULTS_PATH)
        ]
        observable_effect_tampers = [
            row
            for row, _ in read_jsonl(
                root / P2_OBSERVABLE_EFFECT_TAMPER_RESULTS_PATH
            )
        ]
        bound_fact_effects = [
            row
            for row, _ in read_jsonl(root / P2_BOUND_FACT_EFFECT_RESULTS_PATH)
        ]
        required_slot_tampers = [
            row
            for row, _ in read_jsonl(root / P2_REQUIRED_SLOT_TAMPER_RESULTS_PATH)
        ]
        program_schema_tampers = [
            row
            for row, _ in read_jsonl(root / P2_PROGRAM_SCHEMA_TAMPER_RESULTS_PATH)
        ]
        ablations = [row for row, _ in read_jsonl(root / P2_ABLATION_RESULTS_PATH)]
        route_actuals = [row for row, _ in read_jsonl(root / P2_ROUTE_ACTUALS_PATH)]
        route_comparisons = [
            row for row, _ in read_jsonl(root / P2_ROUTE_COMPARISONS_PATH)
        ]
        profiles_root = load_yaml(root / PROFILE_PATH)["content_product_profile_registry"]
        approved_supply = load_yaml(root / P2_APPROVED_SUPPLY_PATH)[
            "approved_component_supply_matrix"
        ]
        import_manifest = load_yaml(root / P2_IMPORT_MANIFEST_PATH)[
            "independent_review_import_manifest"
        ]
        review_closeout = load_yaml(root / P2_REVIEW_CLOSEOUT_PATH)[
            "independent_component_review_closeout"
        ]
        generator_contract = load_yaml(root / P2_GENERATOR_CONTRACT_PATH)[
            "gate1_generator_contract"
        ]
        generator_registry = load_yaml(root / P2_GENERATOR_REGISTRY_PATH)[
            "active_gate1_generator_registry"
        ]
        provider_audit = load_yaml(root / P2_PROVIDER_AUDIT_PATH)[
            "external_provider_exit_audit"
        ]
        final_compat = load_yaml(root / P2_FINAL_COMPAT_PATH)[
            "p2_final_current_checker_compatibility_receipt"
        ]
        final_result = load_yaml(root / P2_FINAL_RESULT_PATH)["p2_final_result"]
    except (
        OSError,
        KeyError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
        yaml.YAMLError,
    ) as exc:
        add_error(errors, "E_P2_FINAL_PARSE", str(exc))
        return

    def preserves_candidate_payload(
        active: dict[str, Any],
        candidate: dict[str, Any],
        lifecycle_keys: set[str],
    ) -> bool:
        return all(
            key in lifecycle_keys
            or canonical_json(active.get(key)) == canonical_json(value)
            for key, value in candidate.items()
        )

    def digest_value(value: Any) -> str:
        return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()

    def shared_material_binding(material: dict[str, Any]) -> dict[str, Any]:
        facts = [
            {
                "fact_id": str(row.get("fact_id")),
                "slot_id": str(row.get("slot_id")),
                "fact_value_digest": str(row.get("fact_value_digest")),
                "claim_boundary": str(row.get("claim_boundary")),
            }
            for row in material.get("facts", [])
            if isinstance(row, dict)
        ]
        authorizations = [
            {
                "authorization_id": str(row.get("authorization_id")),
                "slot_id": str(row.get("slot_id")),
                "subject_id": str(row.get("subject_id")),
                "purpose": str(row.get("purpose")),
                "scope": row.get("scope"),
                "validity_condition": str(row.get("validity_condition")),
            }
            for row in material.get("authorizations", [])
            if isinstance(row, dict)
        ]
        binding = {
            "material_id": str(material.get("material_id")),
            "material_digest": str(material.get("material_digest")),
            "fact_object_ids": [row["fact_id"] for row in facts],
            "fact_set_digest": digest_value(facts),
            "authorization_object_ids": [
                row["authorization_id"] for row in authorizations
            ],
            "authorization_set_digest": digest_value(authorizations),
            "claim_boundary_digest": digest_value(material.get("claim_boundary")),
        }
        binding["binding_digest"] = digest_value(binding)
        return binding

    def resolve_pointer(document: dict[str, Any], pointer: str) -> Any:
        node: Any = document
        for token in pointer.removeprefix("/").split("/"):
            if not isinstance(node, dict) or token not in node:
                return None
            node = node[token]
        return node

    def expected_active_binding(
        binding: dict[str, Any], component: dict[str, Any]
    ) -> dict[str, Any]:
        expected = copy.deepcopy(binding)
        expected["reviewed_candidate_component_digest"] = expected[
            "component_digest"
        ]
        expected["component_digest"] = component["component_digest"]
        expected["component_role"] = component["component_role"]
        expected["binding_digest"] = digest_value(
            expected["exact_typed_object_bindings"]
        )
        return expected

    def expected_axis_body(
        axis: str,
        program: dict[str, Any],
        material_contract: dict[str, Any],
    ) -> dict[str, Any]:
        catalog = material_contract.get("typed_object_catalog", {})
        fact_by_slot = {
            str(row.get("slot_id")): str(row.get("object_id"))
            for row in catalog.get("fact", [])
            if isinstance(row, dict)
        }

        def fact_ref(slot_id: str) -> dict[str, str]:
            if slot_id not in fact_by_slot:
                raise ValueError(f"missing fact slot {slot_id}")
            return {
                "fact_object_id": fact_by_slot[slot_id],
                "fact_slot_id": slot_id,
            }

        if axis == "narrative_mechanism":
            relation_mode = str(program.get("relation_mode"))
            ordered_slots = list(map(str, program.get("ordered_fact_slots", [])))
            stop_slots = list(map(str, program.get("stop_boundary_slots", [])))
            return {
                "relation_mode": relation_mode,
                "segments": [
                    {
                        "segment_index": index,
                        **fact_ref(slot_id),
                        "relation_to_next": relation_mode,
                    }
                    for index, slot_id in enumerate(ordered_slots)
                ],
                "stop_boundary_fact_refs": [
                    fact_ref(slot_id) for slot_id in stop_slots
                ],
            }
        if axis == "information_order":
            ordered_slots = list(map(str, program.get("ordered_fact_slots", [])))
            return {
                "ordering_is_authoritative": program.get(
                    "ordering_is_authoritative"
                ),
                "ordered_nodes": [
                    {"position": index, **fact_ref(slot_id)}
                    for index, slot_id in enumerate(ordered_slots)
                ],
            }
        if axis == "visual_subject":
            return {
                "focus_mode": str(program.get("focus_mode")),
                "lead_fact_ref": fact_ref(str(program.get("lead_fact_slot"))),
                "supporting_fact_refs": [
                    fact_ref(slot_id)
                    for slot_id in map(
                        str, program.get("supporting_fact_slots", [])
                    )
                ],
                "all_facts_remain_available": True,
            }
        if axis == "sound_subject":
            authorization_ids = [
                str(row.get("object_id"))
                for row in catalog.get("authorization", [])
                if isinstance(row, dict)
            ]
            return {
                "cue_source_class": str(program.get("cue_source_class")),
                "cues": [
                    {
                        "cue_index": index,
                        **fact_ref(slot_id),
                        "source_policy": str(
                            program.get("missing_source_behavior")
                        ),
                    }
                    for index, slot_id in enumerate(
                        map(str, program.get("cue_fact_slots", []))
                    )
                ],
                "authorization_object_ids": authorization_ids,
                "authorization_set_digest": material_contract.get(
                    "shared_material_binding", {}
                ).get("authorization_set_digest"),
            }
        if axis == "rhythm":
            return {
                "cadence_mode": str(program.get("cadence_mode")),
                "chronology_policy": str(program.get("chronology_policy")),
                "beat_groups": [
                    {
                        "beat_index": index,
                        "fact_refs": [
                            fact_ref(slot_id) for slot_id in map(str, group)
                        ],
                    }
                    for index, group in enumerate(
                        program.get("beat_fact_slot_groups", [])
                    )
                    if isinstance(group, list)
                ],
            }
        return {
            "closure_mode": str(program.get("closure_mode")),
            "boundary_fact_refs": [
                fact_ref(slot_id)
                for slot_id in map(str, program.get("boundary_fact_slots", []))
            ],
            "next_step_policy": str(program.get("next_step_policy")),
            "claims_resolved": program.get("claims_resolved"),
            "may_add_commitment": program.get("may_add_commitment"),
        }

    if len(initial_combined) != 244:
        add_error(errors, "E_P2_FINAL_COMBINED", "initial count")
    for row in initial_combined:
        item_id = str(row.get("packet_item_id"))
        expected = expected_initial.get(item_id)
        if (
            expected is None
            or row.get("primary_record_digest")
            != expected["primary"].get("record_digest")
            or row.get("secondary_record_digest")
            != expected["secondary"].get("record_digest")
            or row.get("final_disposition") != expected["final_disposition"]
            or row.get("adjudication_record_digest")
            != expected.get("adjudication_digest")
            or row.get("combined_digest") != object_digest(row, "combined_digest")
        ):
            add_error(errors, "E_P2_FINAL_COMBINED", item_id)
    targeted_r1_combined_counts = Counter(
        (
            row.get("combined_disposition"),
            row.get("requires_targeted_adjudication"),
        )
        for row in targeted_r1_combined
    )
    if len(targeted_r1_combined) != 141 or targeted_r1_combined_counts != Counter(
        {
            ("APPROVE", False): 27,
            ("REPAIR", False): 32,
            ("DISAGREEMENT_REQUIRES_ADJUDICATION", True): 82,
        }
    ) or any(
        row.get("combined_digest") != object_digest(row, "combined_digest")
        for row in targeted_r1_combined
    ):
        add_error(errors, "E_P2_FINAL_TARGET_R1_COMBINED", "failure evidence drift")
    targeted_r2_combined_counts = Counter(
        (
            row.get("combined_disposition"),
            row.get("requires_targeted_adjudication"),
        )
        for row in targeted_r2_combined
    )
    if len(targeted_r2_combined) != 134 or targeted_r2_combined_counts != Counter(
        {
            ("APPROVE", False): 107,
            ("REPAIR", False): 20,
            ("DISAGREEMENT_REQUIRES_ADJUDICATION", True): 7,
        }
    ) or any(
        row.get("combined_digest") != object_digest(row, "combined_digest")
        for row in targeted_r2_combined
    ):
        add_error(errors, "E_P2_FINAL_TARGET_R2_COMBINED", "failure evidence drift")
    targeted_r3_combined_counts = Counter(
        (
            row.get("combined_disposition"),
            row.get("requires_targeted_adjudication"),
        )
        for row in targeted_r3_combined
    )
    if len(targeted_r3_combined) != 29 or targeted_r3_combined_counts != Counter(
        {
            ("APPROVE", False): 2,
            ("REPAIR", False): 21,
            ("DISAGREEMENT_REQUIRES_ADJUDICATION", True): 6,
        }
    ) or any(
        row.get("combined_digest") != object_digest(row, "combined_digest")
        for row in targeted_r3_combined
    ):
        add_error(errors, "E_P2_FINAL_TARGET_R3_COMBINED", "failure evidence drift")
    targeted_r4_combined_counts = Counter(
        (
            row.get("combined_disposition"),
            row.get("requires_targeted_adjudication"),
        )
        for row in targeted_r4_combined
    )
    if len(targeted_r4_combined) != 27 or targeted_r4_combined_counts != Counter(
        {
            ("REPAIR", False): 21,
            ("DISAGREEMENT_REQUIRES_ADJUDICATION", True): 6,
        }
    ) or any(
        row.get("combined_digest") != object_digest(row, "combined_digest")
        for row in targeted_r4_combined
    ):
        add_error(errors, "E_P2_FINAL_TARGET_R4_COMBINED", "failure evidence drift")
    targeted_r5_combined_counts = Counter(
        (
            row.get("combined_disposition"),
            row.get("requires_targeted_adjudication"),
        )
        for row in targeted_r5_combined
    )
    if len(targeted_r5_combined) != 27 or targeted_r5_combined_counts != Counter(
        {
            ("APPROVE", False): 26,
            ("DISAGREEMENT_REQUIRES_ADJUDICATION", True): 1,
        }
    ) or any(
        row.get("combined_digest") != object_digest(row, "combined_digest")
        for row in targeted_r5_combined
    ):
        add_error(errors, "E_P2_FINAL_TARGET_R5_COMBINED", "failure evidence drift")
    if len(targeted_r6_combined) != 1 or any(
        row.get("combined_disposition") != "APPROVE"
        or row.get("requires_targeted_adjudication") is not False
        or row.get("combined_digest") != object_digest(row, "combined_digest")
        for row in targeted_r6_combined
    ):
        add_error(errors, "E_P2_FINAL_TARGET_R6_COMBINED", "r6 closeout")

    manifest_files = import_manifest.get("files")
    if (
        import_manifest.get("manifest_digest")
        != object_digest(import_manifest, "manifest_digest")
        or import_manifest.get("imported_file_count") != 45
        or not isinstance(manifest_files, list)
        or len(manifest_files) != 45
        or any(
            not isinstance(row, dict)
            or row.get("byte_imported_without_rewrite") is not True
            or not (root / str(row.get("path"))).is_file()
            or row.get("sha256") != sha256_file(root / str(row.get("path")))
            for row in (manifest_files or [])
        )
    ):
        add_error(errors, "E_P2_FINAL_IMPORT_MANIFEST", "raw import mismatch")
    if (
        review_closeout.get("review_closeout_digest")
        != object_digest(review_closeout, "review_closeout_digest")
        or review_closeout.get("initial_real_disagreement_count") != 92
        or review_closeout.get("initial_adjudication_record_count") != 92
        or review_closeout.get("targeted_r1_combined_record_count") != 141
        or review_closeout.get("targeted_r1_matching_approval_count") != 27
        or review_closeout.get("targeted_r1_failure_or_open_count") != 114
        or review_closeout.get("targeted_r2_combined_record_count") != 134
        or review_closeout.get("targeted_r2_matching_approval_count") != 107
        or review_closeout.get("targeted_r2_matching_repair_count") != 20
        or review_closeout.get("targeted_r2_unresolved_disagreement_count") != 7
        or review_closeout.get("targeted_r2_failure_evidence_preserved") is not True
        or review_closeout.get("targeted_r3_combined_record_count") != 29
        or review_closeout.get("targeted_r3_matching_approval_count") != 2
        or review_closeout.get("targeted_r3_matching_repair_count") != 21
        or review_closeout.get("targeted_r3_unresolved_disagreement_count") != 6
        or review_closeout.get("targeted_r3_failure_evidence_preserved") is not True
        or review_closeout.get("targeted_r4_combined_record_count") != 27
        or review_closeout.get("targeted_r4_matching_approval_count") != 0
        or review_closeout.get("targeted_r4_matching_repair_count") != 21
        or review_closeout.get("targeted_r4_unresolved_disagreement_count") != 6
        or review_closeout.get("targeted_r4_failure_evidence_preserved") is not True
        or review_closeout.get("targeted_r5_combined_record_count") != 27
        or review_closeout.get("targeted_r5_matching_approval_count") != 26
        or review_closeout.get("targeted_r5_unresolved_disagreement_count") != 1
        or review_closeout.get("targeted_r5_failure_evidence_preserved") is not True
        or review_closeout.get("targeted_r6_combined_record_count") != 1
        or review_closeout.get("targeted_r6_matching_approval_count") != 1
        or review_closeout.get("targeted_r6_unresolved_disagreement_count") != 0
        or review_closeout.get("executor_self_approval_count") != 0
    ):
        add_error(errors, "E_P2_FINAL_REVIEW_CLOSEOUT", "counts or digest")

    original_components = {
        row.get("component_id"): row
        for row, _ in read_jsonl(root / P2_COMPONENTS_PATH)
    }
    revised_components = {
        row.get("component_id"): row
        for row, _ in read_jsonl(root / P2_TARGET_R5_REVISED_COMPONENTS_PATH)
    }
    additions = {
        row.get("component_id"): row
        for row, _ in read_jsonl(root / P2_TARGET_R5_ADDITIONS_PATH)
    }
    candidate_pool = {**original_components, **revised_components, **additions}
    active_by_id = {row.get("component_id"): row for row in active_components}
    initial_final_approved = {
        item_id
        for item_id, value in expected_initial.items()
        if value["final_disposition"] == "APPROVE"
    }
    if len(active_components) != len(active_by_id) or len(active_components) != 68:
        add_error(errors, "E_P2_FINAL_COMPONENT_COUNT", str(len(active_components)))
    for component_id, row in active_by_id.items():
        candidate = candidate_pool.get(component_id)
        target_r5_item_id = f"P2R5-COMPONENT-{component_id}"
        target_r4_item_id = f"P2R4-COMPONENT-{component_id}"
        target_r3_item_id = f"P2R3-COMPONENT-{component_id}"
        target_r2_item_id = f"P2R2-COMPONENT-{component_id}"
        target_r1_item_id = f"P2R1-COMPONENT-{component_id}"
        initial_item_id = f"P2-COMPONENT-{component_id}"
        approved = any(
            (
                target_r5_decisions.get(target_r5_item_id)
                == ("APPROVE", "APPROVE"),
                target_r4_decisions.get(target_r4_item_id)
                == ("APPROVE", "APPROVE"),
                target_r3_decisions.get(target_r3_item_id)
                == ("APPROVE", "APPROVE"),
                target_r2_decisions.get(target_r2_item_id)
                == ("APPROVE", "APPROVE"),
                target_r1_decisions.get(target_r1_item_id)
                == ("APPROVE", "APPROVE"),
                initial_item_id in initial_final_approved,
            )
        )
        reviewed_r5_subject = target_r5_subjects.get(target_r5_item_id)
        if (
            not isinstance(candidate, dict)
            or row.get("reviewed_candidate_component_digest")
            != candidate.get("component_digest")
            or row.get("component_digest") != object_digest(row, "component_digest")
            or not preserves_candidate_payload(
                row,
                candidate,
                {
                    "component_digest",
                    "active",
                    "new_generator_consumable",
                    "independent_review_state",
                    "readiness",
                },
            )
            or row.get("active") is not True
            or row.get("new_generator_consumable") is not True
            or row.get("independent_review_state")
            != "APPROVED_BY_REQUIRED_INDEPENDENT_REVIEW"
            or recursively_find_true(row.get("readiness"), READY_KEYS)
            or not approved
            or (
                reviewed_r5_subject is not None
                and canonical_json(candidate)
                != canonical_json(reviewed_r5_subject)
            )
        ):
            add_error(errors, "E_P2_FINAL_COMPONENT", str(component_id))

    target_rule_candidates = {
        row.get("control_rule_id"): row
        for row, _ in read_jsonl(root / P2_TARGET_R5_RULES_PATH)
    }
    if len(active_rules) != 8:
        add_error(errors, "E_P2_FINAL_RULE_COUNT", str(len(active_rules)))
    for row in active_rules:
        rule_id = row.get("control_rule_id")
        candidate = target_rule_candidates.get(rule_id)
        if (
            not isinstance(candidate, dict)
            or not any(
                (
                    target_r2_decisions.get(f"P2R2-CONTROL-{rule_id}")
                    == ("APPROVE", "APPROVE"),
                    target_r1_decisions.get(f"P2R1-CONTROL-{rule_id}")
                    == ("APPROVE", "APPROVE"),
                )
            )
            or row.get("reviewed_candidate_control_rule_digest")
            != candidate.get("control_rule_digest")
            or row.get("control_rule_digest")
            != object_digest(row, "control_rule_digest")
            or not preserves_candidate_payload(
                row,
                candidate,
                {"control_rule_digest", "active", "independent_review_state"},
            )
            or row.get("active") is not True
            or row.get("independent_review_state")
            != "APPROVED_BY_REQUIRED_INDEPENDENT_REVIEW"
            or row.get("contributes_component_supply") is not False
            or row.get("may_write_audience_surface") is not False
        ):
            add_error(errors, "E_P2_FINAL_RULE", str(rule_id))

    target_edge_candidates = {
        row.get("edge_id"): row
        for row, _ in read_jsonl(root / P2_TARGET_R5_EDGES_PATH)
    }
    target_path_candidates = {
        row.get("content_product_type_id"): row
        for row, _ in read_jsonl(root / P2_TARGET_R5_AB_PATH)
    }
    active_path_by_profile = {
        row.get("content_product_type_id"): row for row in active_paths
    }
    active_edge_by_id = {row.get("edge_id"): row for row in active_edges}
    if len(active_edges) != len(active_edge_by_id) or len(active_edges) != 85:
        add_error(errors, "E_P2_FINAL_EDGE_COUNT", str(len(active_edges)))
    for edge_id, row in active_edge_by_id.items():
        candidate = target_edge_candidates.get(edge_id)
        component = active_by_id.get(row.get("component_id"))
        reviewed_path_candidate = target_path_candidates.get(
            row.get("content_product_type_id")
        )
        active_path = active_path_by_profile.get(row.get("content_product_type_id"))
        material_contract = (
            active_path.get("shared_typed_material_contract")
            if isinstance(active_path, dict)
            else None
        )
        path_component_bindings = {
            binding.get("component_id"): binding
            for binding in (
                material_contract.get("component_exact_bindings", [])
                if isinstance(material_contract, dict)
                else []
            )
            if isinstance(binding, dict)
        }
        candidate_exact_binding = (
            next(
                (
                    binding
                    for binding in reviewed_path_candidate.get(
                        "shared_typed_material_contract", {}
                    ).get("component_exact_bindings", [])
                    if isinstance(binding, dict)
                    and binding.get("component_id") == row.get("component_id")
                ),
                None,
            )
            if isinstance(reviewed_path_candidate, dict)
            else None
        )
        expected_exact_binding = (
            expected_active_binding(candidate_exact_binding, component)
            if isinstance(candidate_exact_binding, dict)
            and isinstance(component, dict)
            else None
        )
        exact_binding = row.get("component_exact_binding")
        candidate_profile_binding = (
            reviewed_path_candidate.get("shared_typed_material_contract", {}).get(
                "profile_exact_binding"
            )
            if isinstance(reviewed_path_candidate, dict)
            else None
        )
        profile_binding = row.get("profile_exact_binding")
        path_exact_binding = path_component_bindings.get(row.get("component_id"))
        if (
            not isinstance(candidate, dict)
            or not isinstance(component, dict)
            or not any(
                (
                    target_r3_decisions.get(str(edge_id))
                    == ("APPROVE", "APPROVE"),
                    target_r2_decisions.get(f"P2R2-{edge_id}")
                    == ("APPROVE", "APPROVE"),
                )
            )
            or row.get("reviewed_candidate_edge_digest") != candidate.get("edge_digest")
            or row.get("component_digest") != component.get("component_digest")
            or row.get("edge_digest") != object_digest(row, "edge_digest")
            or not preserves_candidate_payload(
                row,
                candidate,
                {
                    "edge_digest",
                    "component_digest",
                    "component_exact_binding",
                    "profile_exact_binding",
                    "shared_material_contract",
                    "active",
                    "independent_review_state",
                },
            )
            or row.get("active") is not True
            or row.get("independent_review_state")
            != "APPROVED_BY_REQUIRED_INDEPENDENT_REVIEW"
            or row.get("binding_activation_basis")
            != "TARGETED_R5_PATH_MATCHING_TWO_APPROVALS"
            or row.get("binding_review_packet_item_id")
            != f"P2R5-AB-{row.get('content_product_type_id')}"
            or not isinstance(exact_binding, dict)
            or exact_binding.get("binding_digest")
            != digest_value(exact_binding.get("exact_typed_object_bindings"))
            or canonical_json(exact_binding)
            != canonical_json(expected_exact_binding)
            or canonical_json(exact_binding) != canonical_json(path_exact_binding)
            or not isinstance(profile_binding, dict)
            or profile_binding.get("binding_digest")
            != digest_value(profile_binding.get("exact_profile_bindings"))
            or canonical_json(profile_binding)
            != canonical_json(candidate_profile_binding)
            or not isinstance(material_contract, dict)
            or canonical_json(profile_binding)
            != canonical_json(material_contract.get("profile_exact_binding"))
            or row.get("shared_material_contract", {}).get("material_id")
            != material_contract.get("material_id")
            or row.get("shared_material_contract", {}).get("material_digest")
            != material_contract.get("material_digest")
            or row.get("shared_material_contract", {}).get(
                "typed_object_catalog_digest"
            )
            != material_contract.get("typed_object_catalog_digest")
        ):
            add_error(errors, "E_P2_FINAL_EDGE", str(edge_id))

    profiles = profiles_root.get("profiles")
    if not isinstance(profiles, list) or len(profiles) != 20:
        add_error(errors, "E_P2_FINAL_PROFILE", "20 profiles required")
        return
    profile_by_id = {row.get("content_product_type_id"): row for row in profiles}
    complete_profiles = 0
    for profile_id, profile in profile_by_id.items():
        complete = True
        for requirement in profile.get("required_component_roles", []):
            count = sum(
                edge.get("content_product_type_id") == profile_id
                and edge.get("required_component_role") == requirement.get("role")
                for edge in active_edges
            )
            complete &= count >= requirement.get("min_count", 1)
        complete_profiles += complete
    if (
        complete_profiles != 20
        or approved_supply.get("approved_complete_profile_count") != 20
        or approved_supply.get("matrix_digest")
        != object_digest(approved_supply, "matrix_digest")
    ):
        add_error(errors, "E_P2_FINAL_SUPPLY", str(complete_profiles))

    if len(active_paths) != 20:
        add_error(errors, "E_P2_FINAL_AB_COUNT", str(len(active_paths)))
    for row in active_paths:
        profile_id = row.get("content_product_type_id")
        candidate = target_path_candidates.get(profile_id)
        r5_packet_id = f"P2R5-AB-{profile_id}"
        r5_subject = target_r5_subjects.get(r5_packet_id)
        lanes_by_id = {
            lane.get("lane_id"): lane
            for lane in (row.get("lane_a"), row.get("lane_b"))
            if isinstance(lane, dict)
        }
        component_bindings = {
            binding.get("component_id"): binding
            for binding in row.get("shared_typed_material_contract", {}).get(
                "component_exact_bindings", []
            )
            if isinstance(binding, dict)
        }
        component_contracts = {
            contract.get("component_id"): contract
            for contract in row.get("component_realization_contracts", [])
            if isinstance(contract, dict)
        }
        axis_contracts = {
            contract.get("axis"): contract
            for contract in row.get("axis_realization_contracts", [])
            if isinstance(contract, dict)
        }
        r5_path_valid = (
            isinstance(candidate, dict)
            and canonical_json(candidate) == canonical_json(r5_subject)
            and target_r5_decisions.get(r5_packet_id) == ("APPROVE", "APPROVE")
            and row.get("reviewed_candidate_path_digest")
            == candidate.get("path_digest")
            and row.get("path_digest") == object_digest(row, "path_digest")
            and row.get("schema_version") == "v0.3"
            and row.get("active") is True
            and row.get("structural_candidate_only") is False
            and row.get("p2_structural_validation_only") is True
            and row.get("independent_review_state")
            == "APPROVED_BY_REQUIRED_INDEPENDENT_REVIEW"
            and row.get("activation_basis")
            == "TARGETED_R5_MATCHING_TWO_APPROVALS"
            and row.get("review_packet_item_id") == r5_packet_id
            and row.get("content_quality_proven") is False
            and canonical_json(row.get("trusted_profile_contract"))
            == canonical_json(profile_by_id.get(profile_id))
            and set(lanes_by_id) == {"A", "B"}
            and lanes_by_id["A"].get("session_id")
            != lanes_by_id["B"].get("session_id")
            and lanes_by_id["A"].get("other_lane_visible") is False
            and lanes_by_id["B"].get("other_lane_visible") is False
            and set(axis_contracts) == set(P2_AXIS_OPERATOR_ROLE_BY_AXIS)
            and set(row.get("observable_difference_axes", []))
            == set(P2_AXIS_OPERATOR_ROLE_BY_AXIS)
            and row.get("observable_difference_axis_count") == 6
            and row.get("body_level_difference_axis_count") == 6
            and row.get("all_selected_components_have_addressable_output_contract")
            is True
        )
        for component_id, binding in component_bindings.items():
            component = active_by_id.get(component_id)
            exact_objects = binding.get("exact_typed_object_bindings", {})
            exact_slot_contract = (
                isinstance(component, dict)
                and isinstance(exact_objects, dict)
                and {
                    str(row.get("slot_id"))
                    for row in exact_objects.get("input", [])
                    if isinstance(row, dict)
                }
                == set(map(str, component.get("required_input_slots", [])))
                and {
                    str(row.get("slot_id"))
                    for row in exact_objects.get("fact", [])
                    if isinstance(row, dict)
                }
                == set(map(str, component.get("required_fact_slots", [])))
                and {
                    str(row.get("slot_id"))
                    for row in exact_objects.get("authorization", [])
                    if isinstance(row, dict)
                }
                == set(map(str, component.get("required_authorization_slots", [])))
            )
            r5_path_valid &= (
                isinstance(component, dict)
                and exact_slot_contract
                and binding.get("component_digest")
                == component.get("component_digest")
                and binding.get("binding_digest")
                == digest_value(binding.get("exact_typed_object_bindings"))
            )
        selected_ids = set(lanes_by_id.get("A", {}).get("component_ids", []))
        selected_ids.update(lanes_by_id.get("B", {}).get("component_ids", []))
        r5_path_valid &= selected_ids == set(component_bindings)
        operator_ids: set[str] = set()
        for axis, expected_role in P2_AXIS_OPERATOR_ROLE_BY_AXIS.items():
            contract = axis_contracts.get(axis)
            operator_id = (
                contract.get("operator_component_id")
                if isinstance(contract, dict)
                else None
            )
            operator = active_by_id.get(operator_id)
            operator_ids.add(str(operator_id))
            lane_a_program = lanes_by_id.get("A", {}).get("axis_programs", {}).get(axis)
            lane_b_program = lanes_by_id.get("B", {}).get("axis_programs", {}).get(axis)
            lane_a_output = contract.get("lane_a_structural_output", {}) if isinstance(contract, dict) else {}
            lane_b_output = contract.get("lane_b_structural_output", {}) if isinstance(contract, dict) else {}
            r5_path_valid &= (
                isinstance(contract, dict)
                and isinstance(operator, dict)
                and operator.get("component_role") == expected_role
                and operator.get("mechanism", {})
                .get("path_program_schema", {})
                .get("profile_or_lane_payload_in_component_allowed")
                is False
                and operator.get("mechanism", {})
                .get("path_program_schema", {})
                .get("component_reviewed_value_registry_allowed")
                is False
                and contract.get("component_contains_profile_lane_payload") is False
                and contract.get("operator_component_digest")
                == operator.get("component_digest")
                and contract.get("operator_mechanism_digest")
                == digest_value(operator.get("mechanism"))
                and canonical_json(contract.get("operator_component_binding"))
                == canonical_json(component_bindings.get(operator_id))
                and contract.get("lane_a_program_digest")
                == digest_value(lane_a_program)
                and contract.get("lane_b_program_digest")
                == digest_value(lane_b_program)
                and contract.get("lane_a_value")
                == lanes_by_id.get("A", {}).get("axes", {}).get(axis)
                and contract.get("lane_b_value")
                == lanes_by_id.get("B", {}).get("axes", {}).get(axis)
                and contract.get("path_program_is_authoritative") is True
                and isinstance(lane_a_program, dict)
                and isinstance(lane_b_program, dict)
                and set(lane_a_program)
                == set(
                    map(
                        str,
                        operator.get("mechanism", {})
                        .get("path_program_schema", {})
                        .get("required_fields", []),
                    )
                )
                and set(lane_b_program)
                == set(
                    map(
                        str,
                        operator.get("mechanism", {})
                        .get("path_program_schema", {})
                        .get("required_fields", []),
                    )
                )
                and contract.get("same_fact_set_must_be_preserved") is True
                and lane_a_output.get("path_program_digest")
                == digest_value(lane_a_program)
                and lane_b_output.get("path_program_digest")
                == digest_value(lane_b_program)
                and lane_a_output.get("structural_body_digest")
                == digest_value(lane_a_output.get("structural_body"))
                and lane_b_output.get("structural_body_digest")
                == digest_value(lane_b_output.get("structural_body"))
                and lane_a_output.get("structural_output_digest")
                == object_digest(lane_a_output, "structural_output_digest")
                and lane_b_output.get("structural_output_digest")
                == object_digest(lane_b_output, "structural_output_digest")
                and lane_a_output.get("structural_body_digest")
                != lane_b_output.get("structural_body_digest")
            )
        ordinary_ids = selected_ids.difference(operator_ids)
        r5_path_valid &= set(component_contracts) == ordinary_ids
        for component_id, contract in component_contracts.items():
            component = active_by_id.get(component_id)
            binding = component_bindings.get(component_id)
            output = contract.get("expected_structural_output", {})
            r5_path_valid &= (
                isinstance(component, dict)
                and isinstance(binding, dict)
                and contract.get("component_digest")
                == component.get("component_digest")
                and contract.get("exact_binding_digest")
                == binding.get("binding_digest")
                and output.get("component_id") == component_id
                and output.get("component_digest")
                == component.get("component_digest")
                and output.get("component_binding_digest")
                == binding.get("binding_digest")
                and output.get("structural_body_digest")
                == digest_value(output.get("structural_body"))
                and output.get("structural_output_digest")
                == object_digest(output, "structural_output_digest")
            )
        if not r5_path_valid:
            add_error(errors, "E_P2_FINAL_AB_PATH", str(profile_id))
        continue
        lanes = [row.get("lane_a"), row.get("lane_b")]
        axes = row.get("observable_difference_axes")
        material_contract = row.get("shared_typed_material_contract")
        contracts = row.get("axis_realization_contracts")
        material_bindings = {
            binding.get("component_id"): binding
            for binding in (
                material_contract.get("component_exact_bindings", [])
                if isinstance(material_contract, dict)
                else []
            )
            if isinstance(binding, dict)
        }
        contract_by_axis = {
            contract.get("axis"): contract
            for contract in (contracts if isinstance(contracts, list) else [])
            if isinstance(contract, dict)
        }
        expected_shared_binding = (
            material_contract.get("shared_material_binding")
            if isinstance(material_contract, dict)
            else None
        )
        axis_contracts_valid = (
            set(contract_by_axis) == set(P2_AXIS_OPERATOR_ROLE_BY_AXIS)
            and isinstance(axes, list)
            and set(axes) == set(contract_by_axis)
        )
        for axis, expected_role in P2_AXIS_OPERATOR_ROLE_BY_AXIS.items():
            contract = contract_by_axis.get(axis)
            if not isinstance(contract, dict):
                axis_contracts_valid = False
                continue
            operator_id = contract.get("operator_component_id")
            operator = active_by_id.get(operator_id)
            operator_binding = contract.get("operator_component_binding")
            parameter_schema = (
                operator.get("mechanism", {}).get("parameter_schema")
                if isinstance(operator, dict)
                else None
            )
            lane_a_output = contract.get("lane_a_structural_output")
            lane_b_output = contract.get("lane_b_structural_output")
            profile_programs = (
                parameter_schema.get("reviewed_value_programs", {}).get(
                    profile_id
                )
                if isinstance(parameter_schema, dict)
                else None
            )
            outputs_valid = True
            for lane_name, output in (
                ("lane_a", lane_a_output),
                ("lane_b", lane_b_output),
            ):
                if not isinstance(output, dict):
                    outputs_valid = False
                    continue
                lane_value = str(contract.get(f"{lane_name}_value"))
                program = (
                    profile_programs.get(lane_value)
                    if isinstance(profile_programs, dict)
                    else None
                )
                try:
                    expected_body = (
                        expected_axis_body(axis, program, material_contract)
                        if isinstance(program, dict)
                        and isinstance(material_contract, dict)
                        else None
                    )
                except (TypeError, ValueError):
                    expected_body = None
                if (
                    output.get("axis") != axis
                    or output.get("output_kind")
                    != P2_AXIS_OUTPUT_KIND_BY_AXIS[axis]
                    or output.get("reviewed_parameter_value") != lane_value
                    or not isinstance(program, dict)
                    or program.get("axis") != axis
                    or program.get("reviewed_parameter_value") != lane_value
                    or program.get("applicable_profile_id") != profile_id
                    or program.get("unknown_or_other_profile_behavior")
                    != "REJECT"
                    or output.get("semantic_program_digest")
                    != digest_value(program)
                    or output.get("shared_material_binding")
                    != expected_shared_binding
                    or canonical_json(output.get("structural_body"))
                    != canonical_json(expected_body)
                    or output.get("structural_body_digest")
                    != digest_value(output.get("structural_body"))
                    or output.get("structural_effect_digest")
                    != output.get("structural_body_digest")
                    or output.get("structural_output_digest")
                    != object_digest(output, "structural_output_digest")
                ):
                    outputs_valid = False
            if (
                not isinstance(operator, dict)
                or operator.get("component_role") != expected_role
                or not isinstance(parameter_schema, dict)
                or parameter_schema.get("axis") != axis
                or parameter_schema.get("value_type")
                != "PROFILE_AND_LANE_REVIEWED_SEMANTIC_PROGRAM"
                or parameter_schema.get("unknown_value_behavior") != "REJECT"
                or parameter_schema.get("known_but_wrong_lane_value_behavior")
                != "REJECT"
                or parameter_schema.get("known_but_wrong_profile_value_behavior")
                != "REJECT"
                or parameter_schema.get("output_kind")
                != P2_AXIS_OUTPUT_KIND_BY_AXIS[axis]
                or not isinstance(profile_programs, dict)
                or contract.get("lane_a_value")
                not in profile_programs
                or contract.get("lane_b_value")
                not in profile_programs
                or contract.get("allowed_values_digest")
                != digest_value(parameter_schema.get("allowed_values"))
                or contract.get("lane_a_program_digest")
                != digest_value(
                    profile_programs.get(contract.get("lane_a_value"), {})
                )
                or contract.get("lane_b_program_digest")
                != digest_value(
                    profile_programs.get(contract.get("lane_b_value"), {})
                )
                or contract.get("approved_lane_value_is_authoritative") is not True
                or not isinstance(operator_binding, dict)
                or operator_binding.get("binding_digest")
                != digest_value(
                    operator_binding.get("exact_typed_object_bindings")
                )
                or canonical_json(operator_binding)
                != canonical_json(material_bindings.get(operator_id))
                or contract.get("operator_mechanism_digest")
                != hashlib.sha256(
                    canonical_json(operator.get("mechanism")).encode("utf-8")
                ).hexdigest()
                or contract.get("lane_a_value")
                == contract.get("lane_b_value")
                or contract.get("values_must_differ") is not True
                or contract.get("same_fact_set_must_be_preserved") is not True
                or contract.get("structural_bodies_must_differ") is not True
                or contract.get("shared_material_binding")
                != expected_shared_binding
                or not outputs_valid
                or not isinstance(lane_a_output, dict)
                or not isinstance(lane_b_output, dict)
                or lane_a_output.get("structural_body_digest")
                == lane_b_output.get("structural_body_digest")
                or contract.get("realization_target")
                != f"/structural_realization/lane_{{lane_id}}/axes/{axis}"
            ):
                axis_contracts_valid = False
            for lane_index, lane in enumerate(lanes):
                lane_key = "lane_a_value" if lane_index == 0 else "lane_b_value"
                parameter = (
                    lane.get("axis_operator_parameters", {}).get(axis, {})
                    if isinstance(lane, dict)
                    else {}
                )
                if (
                    not isinstance(parameter, dict)
                    or parameter.get("operator_component_id") != operator_id
                    or parameter.get("parameter_value") != contract.get(lane_key)
                    or lane.get(axis) != contract.get(lane_key)
                    or operator_id not in set(lane.get("component_ids", []))
                ):
                    axis_contracts_valid = False
        expected_active_candidate = copy.deepcopy(candidate) if isinstance(candidate, dict) else None
        if isinstance(expected_active_candidate, dict):
            expected_bindings = []
            for binding in expected_active_candidate[
                "shared_typed_material_contract"
            ]["component_exact_bindings"]:
                component = active_by_id.get(binding.get("component_id"))
                if not isinstance(component, dict):
                    axis_contracts_valid = False
                    continue
                expected_bindings.append(expected_active_binding(binding, component))
            expected_active_candidate["shared_typed_material_contract"][
                "component_exact_bindings"
            ] = expected_bindings
            expected_binding_by_id = {
                binding["component_id"]: binding for binding in expected_bindings
            }
            for contract in expected_active_candidate["axis_realization_contracts"]:
                contract["operator_component_binding"] = expected_binding_by_id[
                    contract["operator_component_id"]
                ]
        if (
            not isinstance(candidate, dict)
            or canonical_json(candidate)
            != canonical_json(
                target_r4_subjects.get(f"P2R4-AB-{profile_id}")
            )
            or target_r4_decisions.get(f"P2R4-AB-{profile_id}")
            != ("APPROVE", "APPROVE")
            or row.get("reviewed_candidate_path_digest") != candidate.get("path_digest")
            or row.get("path_digest") != object_digest(row, "path_digest")
            or not preserves_candidate_payload(
                row,
                expected_active_candidate,
                {
                    "path_digest",
                    "active",
                    "structural_candidate_only",
                    "independent_review_state",
                },
            )
            or row.get("active") is not True
            or row.get("independent_review_state")
            != "APPROVED_BY_REQUIRED_INDEPENDENT_REVIEW"
            or row.get("content_quality_proven") is not False
            or not isinstance(axes, list)
            or len(axes) != 6
            or not axis_contracts_valid
            or any(
                not isinstance(lane, dict)
                or not set(lane.get("component_ids", [])).issubset(active_by_id)
                for lane in lanes
            )
            or lanes[0].get("session_policy") == lanes[1].get("session_policy")
        ):
            add_error(errors, "E_P2_FINAL_AB_PATH", str(profile_id))

    component_realization_ids: set[str] = set()
    active_path_by_cp = {
        row.get("content_product_type_id"): row for row in active_paths
    }
    request_by_id = {row.get("request_id"): row for row in requests}
    realization_by_request = {row.get("request_id"): row for row in realizations}
    if len(requests) != 40 or len(realization_by_request) != 40:
        add_error(errors, "E_P2_FINAL_GENERATOR_COUNT", "40 requests/realizations")
    for request_id, request in request_by_id.items():
        profile = profile_by_id.get(request.get("content_product_type_id"))
        realization = realization_by_request.get(request_id)
        material = request.get("typed_material")
        bindings = request.get("component_bindings")
        path = active_path_by_cp.get(request.get("content_product_type_id"))
        lane = request.get("lane")
        lane_key = (
            "lane_a"
            if isinstance(lane, dict) and lane.get("lane_id") == "A"
            else "lane_b"
            if isinstance(lane, dict) and lane.get("lane_id") == "B"
            else ""
        )
        expected_lane = path.get(lane_key) if isinstance(path, dict) and lane_key else None
        path_material = (
            path.get("shared_typed_material_contract")
            if isinstance(path, dict)
            else None
        )
        path_control = (
            path.get("author_request_control_contract")
            if isinstance(path, dict)
            else None
        )
        request_bindings = {
            binding.get("component_id"): binding
            for binding in request.get("component_bindings", [])
            if isinstance(binding, dict)
        }
        material_catalog = (
            {
                "source": [
                    {
                        "slot_id": str(item.get("slot_id")),
                        "object_id": str(item.get("source_id")),
                    }
                    for item in material.get("sources", [])
                ],
                "input": [
                    {
                        "slot_id": str(item.get("slot_id")),
                        "object_id": str(item.get("input_id")),
                    }
                    for item in material.get("component_inputs", [])
                ],
                "fact": [
                    {
                        "slot_id": str(item.get("slot_id")),
                        "object_id": str(item.get("fact_id")),
                    }
                    for item in material.get("facts", [])
                ],
                "authorization": [
                    {
                        "slot_id": str(item.get("slot_id")),
                        "object_id": str(item.get("authorization_id")),
                    }
                    for item in material.get("authorizations", [])
                ],
            }
            if isinstance(material, dict)
            else None
        )
        path_bindings = {
            binding.get("component_id"): binding
            for binding in (
                path_material.get("component_exact_bindings", [])
                if isinstance(path_material, dict)
                else []
            )
            if isinstance(binding, dict)
        }
        realization_contributions = (
            realization.get("component_contributions", [])
            if isinstance(realization, dict)
            else []
        )

        def resolve_realization_pointer(pointer: Any) -> Any:
            node: Any = realization
            for token in str(pointer).removeprefix("/").split("/"):
                if not isinstance(node, dict) or token not in node:
                    return None
                node = node[token]
            return node

        r5_request_valid = (
            isinstance(profile, dict)
            and isinstance(path, dict)
            and isinstance(realization, dict)
            and isinstance(expected_lane, dict)
            and isinstance(path_material, dict)
            and isinstance(path_control, dict)
            and canonical_json(request.get("profile_contract"))
            == canonical_json(profile)
            and request.get("request_digest") == object_digest(request, "request_digest")
            and request.get("generator_version")
            == "gate1-v1.1-p2-composable-successor-v0.4"
            and request.get("external_provider_allowed") is False
            and request.get("publishable") is False
            and request.get("runtime_consumable") is False
            and request.get("may_enter_300") is False
            and canonical_json(request.get("approved_path_binding"))
            == canonical_json(
                (lambda binding: {
                    **binding,
                    "binding_digest": digest_value(binding),
                })(
                    {
                    "content_product_type_id": path.get("content_product_type_id"),
                    "profile_digest": profile.get("profile_digest"),
                    "path_digest": path.get("path_digest"),
                    "lane_key": lane_key,
                    }
                )
            )
            and canonical_json(request.get("lane")) == canonical_json(expected_lane)
            and isinstance(material, dict)
            and material.get("material_digest")
            == object_digest(material, "material_digest")
            and material.get("material_id") == path_material.get("material_id")
            and material.get("material_digest")
            == path_material.get("material_digest")
            and material.get("synthetic_test_only") is True
            and material.get("publishable") is False
            and material.get("runtime_consumable") is False
            and material.get("may_enter_300") is False
            and canonical_json(material_catalog)
            == canonical_json(path_material.get("typed_object_catalog"))
            and digest_value(material_catalog)
            == path_material.get("typed_object_catalog_digest")
            and canonical_json(request_bindings) == canonical_json(path_bindings)
            and canonical_json(request.get("axis_realization_contracts"))
            == canonical_json(path.get("axis_realization_contracts"))
            and canonical_json(request.get("component_realization_contracts"))
            == canonical_json(path.get("component_realization_contracts"))
            and canonical_json(request.get("control_rule_bindings"))
            == canonical_json(path_control.get("control_rule_bindings"))
            and canonical_json(request.get("hard_prohibitions"))
            == canonical_json(path_control.get("hard_prohibitions"))
            and canonical_json(request.get("expected_output_structure"))
            == canonical_json(path_control.get("expected_output_structure"))
            and realization.get("request_digest") == request.get("request_digest")
            and realization.get("realization_digest")
            == object_digest(realization, "realization_digest")
            and realization.get("selected_component_count")
            == realization.get("realized_component_count")
            == len(expected_lane.get("component_ids", []))
            and realization.get("unrealized_component_count") == 0
            and realization.get("audience_title") == ""
            and realization.get("audience_body") == []
            and realization.get("spoken_script") == []
            and realization.get("publishable") is False
            and realization.get("runtime_consumable") is False
            and realization.get("may_enter_300") is False
            and len(realization_contributions)
            == len(expected_lane.get("component_ids", []))
        )
        contribution_ids: set[str] = set()
        for contribution in realization_contributions:
            component_id = str(contribution.get("component_id"))
            component = active_by_id.get(component_id)
            resolved = resolve_realization_pointer(
                contribution.get("implementation_pointer")
            )
            contribution_ids.add(component_id)
            r5_request_valid &= (
                isinstance(component, dict)
                and isinstance(resolved, dict)
                and contribution.get("component_digest")
                == component.get("component_digest")
                and contribution.get("structural_body_digest")
                == resolved.get("structural_body_digest")
                and contribution.get("structural_output_digest")
                == resolved.get("structural_output_digest")
            )
        r5_request_valid &= contribution_ids == set(
            map(str, expected_lane.get("component_ids", []))
        )
        component_realization_ids.update(contribution_ids)
        if not r5_request_valid:
            add_error(errors, "E_P2_FINAL_REQUEST_PATH_BINDING", str(request_id))
        continue
        if (
            not isinstance(profile, dict)
            or canonical_json(request.get("profile_contract")) != canonical_json(profile)
            or request.get("request_digest") != object_digest(request, "request_digest")
            or request.get("external_provider_allowed") is not False
            or request.get("publishable") is not False
            or request.get("runtime_consumable") is not False
            or request.get("may_enter_300") is not False
            or not isinstance(material, dict)
            or material.get("synthetic_test_only") is not True
            or material.get("publishable") is not False
            or material.get("runtime_consumable") is not False
            or material.get("may_enter_300") is not False
            or material.get("material_digest")
            != object_digest(material, "material_digest")
            or not isinstance(bindings, list)
            or not bindings
            or not isinstance(realization, dict)
            or not isinstance(path, dict)
            or not isinstance(lane, dict)
            or not isinstance(expected_lane, dict)
            or not isinstance(path_material, dict)
        ):
            add_error(errors, "E_P2_FINAL_REQUEST", str(request_id))
            continue
        input_by_id = {
            row.get("input_id"): row for row in material.get("component_inputs", [])
        }
        fact_by_id = {row.get("fact_id"): row for row in material.get("facts", [])}
        auth_by_id = {
            row.get("authorization_id"): row
            for row in material.get("authorizations", [])
        }
        material_catalog = {
            "source": [
                {"slot_id": str(row.get("slot_id")), "object_id": str(row.get("source_id"))}
                for row in material.get("sources", [])
            ],
            "input": [
                {"slot_id": str(row.get("slot_id")), "object_id": str(row.get("input_id"))}
                for row in material.get("component_inputs", [])
            ],
            "fact": [
                {"slot_id": str(row.get("slot_id")), "object_id": str(row.get("fact_id"))}
                for row in material.get("facts", [])
            ],
            "authorization": [
                {
                    "slot_id": str(row.get("slot_id")),
                    "object_id": str(row.get("authorization_id")),
                }
                for row in material.get("authorizations", [])
            ],
        }
        if (
            material.get("material_id") != path_material.get("material_id")
            or material.get("material_digest") != path_material.get("material_digest")
            or canonical_json(material_catalog)
            != canonical_json(path_material.get("typed_object_catalog"))
            or hashlib.sha256(canonical_json(material_catalog).encode("utf-8")).hexdigest()
            != path_material.get("typed_object_catalog_digest")
            or canonical_json(lane.get("axes"))
            != canonical_json(
                {
                    axis: expected_lane.get(axis)
                    for axis in P2_AXIS_OPERATOR_ROLE_BY_AXIS
                }
            )
            or canonical_json(lane.get("axis_operator_parameters"))
            != canonical_json(expected_lane.get("axis_operator_parameters"))
            or canonical_json(lane.get("axis_realization_contracts"))
            != canonical_json(path.get("axis_realization_contracts"))
            or canonical_json(shared_material_binding(material))
            != canonical_json(path_material.get("shared_material_binding"))
            or path_material.get("claim_boundary_digest")
            != digest_value(material.get("claim_boundary"))
            or canonical_json(request.get("approved_path_binding"))
            != canonical_json(
                {
                    "content_product_type_id": request.get(
                        "content_product_type_id"
                    ),
                    "path_digest": path.get("path_digest"),
                    "lane_key": lane_key,
                }
            )
        ):
            add_error(errors, "E_P2_FINAL_REQUEST_PATH_BINDING", str(request_id))
        exact_binding_by_component = {
            row.get("component_id"): row
            for row in path_material.get("component_exact_bindings", [])
            if isinstance(row, dict)
        }
        if {row.get("component_id") for row in bindings} != set(
            expected_lane.get("component_ids", [])
        ):
            add_error(errors, "E_P2_FINAL_REQUEST_COMPONENT_SET", str(request_id))
        for binding in bindings:
            component = active_by_id.get(binding.get("component_id"))
            expected_sets = (
                ("required_input_slots", "input_object_ids", input_by_id),
                ("required_fact_slots", "fact_object_ids", fact_by_id),
                (
                    "required_authorization_slots",
                    "authorization_object_ids",
                    auth_by_id,
                ),
            )
            if (
                not isinstance(component, dict)
                or binding.get("component_digest") != component.get("component_digest")
                or binding.get("component_role") != component.get("component_role")
                or canonical_json(binding.get("claim_boundary"))
                != canonical_json(component.get("claim_boundary"))
                or list(map(str, binding.get("required_input_slots", [])))
                != list(map(str, component.get("required_input_slots", [])))
                or list(map(str, binding.get("required_fact_slots", [])))
                != list(map(str, component.get("required_fact_slots", [])))
                or list(map(str, binding.get("required_authorization_slots", [])))
                != list(
                    map(str, component.get("required_authorization_slots", []))
                )
            ):
                add_error(errors, "E_P2_FINAL_REQUEST_COMPONENT", str(request_id))
                continue
            exact_binding = exact_binding_by_component.get(binding.get("component_id"))
            if not isinstance(exact_binding, dict):
                add_error(errors, "E_P2_FINAL_EXACT_BINDING", str(request_id))
                continue
            for slot_key, id_key, object_by_id in expected_sets:
                slots = list(map(str, binding.get(slot_key, [])))
                object_ids = list(map(str, binding.get(id_key, [])))
                actual_slots = [
                    str(object_by_id.get(object_id, {}).get("slot_id"))
                    for object_id in object_ids
                ]
                kind = {
                    "required_input_slots": "input",
                    "required_fact_slots": "fact",
                    "required_authorization_slots": "authorization",
                }[slot_key]
                exact_pairs = exact_binding.get("exact_typed_object_bindings", {}).get(
                    kind, []
                )
                if (
                    not slots
                    or actual_slots != slots
                    or slots != [str(row.get("slot_id")) for row in exact_pairs]
                    or object_ids != [str(row.get("object_id")) for row in exact_pairs]
                ):
                    add_error(
                        errors,
                        "E_P2_FINAL_TYPED_BINDING",
                        f"{request_id}:{binding.get('component_id')}:{slot_key}",
                    )
        contributions = realization.get("component_contributions")
        axis_realizations = realization.get("lane_axis_realizations")
        axis_realization_by_name = {
            row.get("axis"): row
            for row in (axis_realizations if isinstance(axis_realizations, list) else [])
            if isinstance(row, dict)
        }
        expected_contract_by_axis = {
            row.get("axis"): row
            for row in path.get("axis_realization_contracts", [])
            if isinstance(row, dict)
        }
        axis_realizations_valid = set(axis_realization_by_name) == set(
            P2_AXIS_OPERATOR_ROLE_BY_AXIS
        )
        for axis, contract in expected_contract_by_axis.items():
            realized = axis_realization_by_name.get(axis)
            pointer = (
                str(realized.get("implementation_pointer"))
                if isinstance(realized, dict)
                else ""
            )
            structural_output = resolve_pointer(realization, pointer)
            contract_output_key = (
                "lane_a_structural_output"
                if lane.get("lane_id") == "A"
                else "lane_b_structural_output"
            )
            if (
                not isinstance(realized, dict)
                or realized.get("axis_value") != lane.get("axes", {}).get(axis)
                or realized.get("supporting_component_ids")
                != contract.get("supporting_component_ids")
                or realized.get("operator_component_id")
                != contract.get("operator_component_id")
                or realized.get("operator_mechanism_digest")
                != contract.get("operator_mechanism_digest")
                or realized.get("operator_binding_digest")
                != contract.get("operator_component_binding", {}).get("binding_digest")
                or realized.get("implementation_pointer")
                != str(contract.get("realization_target", "")).format(
                    lane_id=lane.get("lane_id")
                )
                or not isinstance(structural_output, dict)
                or structural_output.get("structural_output_digest")
                != realized.get("structural_output_digest")
                or structural_output.get("semantic_program_digest")
                != realized.get("semantic_program_digest")
                or structural_output.get("structural_body_digest")
                != realized.get("structural_body_digest")
                or canonical_json(structural_output)
                != canonical_json(contract.get(contract_output_key))
            ):
                axis_realizations_valid = False
        binding_by_component = {
            row.get("component_id"): row for row in bindings if isinstance(row, dict)
        }
        contribution_by_component = {
            row.get("component_id"): row
            for row in (contributions if isinstance(contributions, list) else [])
            if isinstance(row, dict)
        }
        contributions_valid = set(contribution_by_component) == set(
            binding_by_component
        )
        for component_id, contribution in contribution_by_component.items():
            binding = binding_by_component.get(component_id)
            component = active_by_id.get(component_id)
            effect = contribution.get("observable_structural_effect")
            expected_typed_binding_digest = (
                hashlib.sha256(
                    canonical_json(
                        {
                            "input_object_ids": binding.get("input_object_ids"),
                            "fact_object_ids": binding.get("fact_object_ids"),
                            "authorization_object_ids": binding.get(
                                "authorization_object_ids"
                            ),
                        }
                    ).encode("utf-8")
                ).hexdigest()
                if isinstance(binding, dict)
                else ""
            )
            expected_effect = (
                {
                    "component_role": component.get("component_role"),
                    "mechanism_digest": digest_value(
                        component.get("mechanism", {})
                    ),
                    "typed_binding_digest": expected_typed_binding_digest,
                }
                if isinstance(component, dict)
                else None
            )
            if (
                not isinstance(binding, dict)
                or not isinstance(component, dict)
                or not isinstance(effect, dict)
                or contribution.get("component_digest")
                != component.get("component_digest")
                or canonical_json(effect) != canonical_json(expected_effect)
            ):
                contributions_valid = False
        if (
            realization.get("realization_digest")
            != object_digest(realization, "realization_digest")
            or realization.get("unrealized_component_count") != 0
            or realization.get("selected_component_count")
            != realization.get("realized_component_count")
            or not isinstance(contributions, list)
            or len({row.get("implementation_pointer") for row in contributions})
            != len(contributions)
            or realization.get("audience_title") != ""
            or realization.get("audience_body") != []
            or realization.get("spoken_script") != []
            or not axis_realizations_valid
            or not contributions_valid
        ):
            add_error(errors, "E_P2_FINAL_REALIZATION", str(request_id))
        component_realization_ids.update(
            str(row.get("component_id")) for row in (contributions or [])
        )
    if component_realization_ids != set(map(str, active_by_id)):
        add_error(errors, "E_P2_FINAL_COMPONENT_USE", "selected but unrealized")
    if len(pair_results) != 20 or any(
        row.get("same_source_fact_authorization_boundary") is not True
        or row.get("independent_session_ids") is not True
        or row.get("minimum_four_axes_pass") is not True
        or row.get("observable_difference_axis_count") != 6
        or row.get("all_six_structural_bodies_differ") is not True
        or row.get("ending_action_topology_differs") is not True
        or row.get("content_quality_proven") is not False
        or row.get("pair_digest") != object_digest(row, "pair_digest")
        for row in pair_results
    ):
        add_error(errors, "E_P2_FINAL_AB_PAIR", "20 structural pairs")
    if len(axis_body_pairs) != 120 or any(
        row.get("body_level_difference") is not True
        or row.get("case_digest") != object_digest(row, "case_digest")
        for row in axis_body_pairs
    ):
        add_error(errors, "E_P2_FINAL_AXIS_BODY_PAIR", "120 body differences")
    if len(path_program_tampers) != 120 or any(
        row.get("substitution_rejected") is not True
        or row.get("case_digest") != object_digest(row, "case_digest")
        for row in path_program_tampers
    ):
        add_error(errors, "E_P2_FINAL_PATH_PROGRAM_TAMPER", "120 substitutions")
    if len(trust_contract_tampers) != 180 or any(
        row.get("tamper_rejected") is not True
        or row.get("case_digest") != object_digest(row, "case_digest")
        for row in trust_contract_tampers
    ):
        add_error(errors, "E_P2_FINAL_TRUST_CONTRACT_TAMPER", "180 contract attacks")
    if len(ablations) != 410 or any(
        row.get("ablation_rejected") is not True
        or row.get("required_output_dependency_preserved") is not True
        or row.get("case_digest") != object_digest(row, "case_digest")
        for row in ablations
    ):
        add_error(errors, "E_P2_FINAL_ABLATION", "required output dependency lost")
    if len(component_pointer_results) != 410 or any(
        row.get("pointer_resolved") is not True
        or row.get("digest_matches") is not True
        or row.get("case_digest") != object_digest(row, "case_digest")
        for row in component_pointer_results
    ):
        add_error(errors, "E_P2_FINAL_COMPONENT_POINTER", "unresolved component output")
    if len(observable_effect_tampers) != 62 or any(
        row.get("registry_identity_rejected") is not True
        or row.get("nonmetadata_structure_change_claimed") is not False
        or row.get("case_digest") != object_digest(row, "case_digest")
        for row in observable_effect_tampers
    ):
        add_error(errors, "E_P2_FINAL_COMPONENT_IDENTITY", "identity tamper not rejected")
    if len(bound_fact_effects) != 62 or any(
        row.get("same_required_slot_preserved") is not True
        or row.get("nonmetadata_structure_changed") is not True
        or row.get("case_digest") != object_digest(row, "case_digest")
        for row in bound_fact_effects
    ):
        add_error(errors, "E_P2_FINAL_BOUND_FACT_EFFECT", "bound fact effect missing")
    if len(required_slot_tampers) != 20 or any(
        row.get("tamper_rejected") is not True
        or row.get("error_code") != "E_COMPONENT_REQUIRED_SLOT_MISMATCH"
        or row.get("case_digest") != object_digest(row, "case_digest")
        for row in required_slot_tampers
    ):
        add_error(errors, "E_P2_FINAL_REQUIRED_SLOT", "wrong-slot trust root accepted")
    if len(program_schema_tampers) != 240 or any(
        row.get("tamper_rejected") is not True
        or row.get("error_code") != "E_AXIS_PROGRAM_FIELD_SET"
        or row.get("case_digest") != object_digest(row, "case_digest")
        for row in program_schema_tampers
    ):
        add_error(errors, "E_P2_FINAL_PROGRAM_SCHEMA", "open program schema")

    route_inputs = {
        row.get("case_id"): row for row, _ in read_jsonl(root / ROUTE_INPUT_PATH)
    }
    route_gold = {
        row.get("case_id"): row for row, _ in read_jsonl(root / P1B_ROUTE_GOLD_PATH)
    }
    actual_by_case = {row.get("case_id"): row for row in route_actuals}
    comparison_by_case = {row.get("case_id"): row for row in route_comparisons}
    if not (
        len(route_inputs)
        == len(route_gold)
        == len(actual_by_case)
        == len(comparison_by_case)
        == 60
    ):
        add_error(errors, "E_P2_FINAL_ROUTE_COUNT", "expected 60")
    for case_id, route_input in route_inputs.items():
        profile = profile_by_id.get(route_input.get("profile_id"))
        actual = actual_by_case.get(case_id)
        comparison = comparison_by_case.get(case_id)
        gold = route_gold.get(case_id)
        try:
            expected_action, expected_reason = p2_independent_route(route_input, profile)
        except (TypeError, ValueError) as exc:
            add_error(errors, "E_P2_FINAL_ROUTE_RECOMPUTE", f"{case_id}:{exc}")
            continue
        if (
            not isinstance(actual, dict)
            or not isinstance(comparison, dict)
            or not isinstance(gold, dict)
            or actual.get("route_result_digest")
            != object_digest(actual, "route_result_digest")
            or actual.get("actual_primary_action") != expected_action
            or actual.get("actual_primary_reason_category") != expected_reason
            or expected_action != gold.get("gold_primary_action")
            or expected_reason != gold.get("gold_reason_code")
            or comparison.get("actual_route_result_digest")
            != actual.get("route_result_digest")
            or comparison.get("gold_answer_digest") != gold.get("gold_answer_digest")
            or comparison.get("primary_action_matches_gold") is not True
            or comparison.get("primary_reason_matches_gold") is not True
            or comparison.get("comparison_digest")
            != object_digest(comparison, "comparison_digest")
        ):
            add_error(errors, "E_P2_FINAL_ROUTE", str(case_id))

    events = provider_audit.get("events")
    completed_calls = sum(
        isinstance(row, dict)
        and row.get("network_dispatch_started") is True
        and row.get("provider_response_received") is True
        for row in (events if isinstance(events, list) else [])
    )
    responses = sum(
        isinstance(row, dict) and row.get("provider_response_received") is True
        for row in (events if isinstance(events, list) else [])
    )
    if (
        provider_audit.get("audit_digest")
        != object_digest(provider_audit, "audit_digest")
        or provider_audit.get("derived_from_event_log") is not True
        or provider_audit.get("external_provider_request_count") != completed_calls
        or provider_audit.get("external_provider_response_count") != responses
        or completed_calls != 0
        or responses != 0
        or provider_audit.get("negative_dispatch_test", {}).get(
            "blocked_before_network_dispatch"
        )
        is not True
    ):
        add_error(errors, "E_P2_FINAL_PROVIDER", "audit not derived or nonzero")

    if (
        generator_contract.get("contract_digest")
        != object_digest(generator_contract, "contract_digest")
        or generator_contract.get("external_provider_allowed") is not False
        or generator_contract.get("audience_content_generation_allowed_in_p2")
        is not False
        or generator_contract.get("generator_may_write_composition_plan") is not False
        or generator_contract.get("active_core_module") != "p2_generator_core_r6.py"
        or generator_contract.get("approved_path_registry_is_authoritative") is not True
        or generator_contract.get("axis_component_profile_lane_payload_allowed")
        is not False
        or generator_contract.get(
            "all_selected_components_require_addressable_structural_output"
        )
        is not True
        or generator_contract.get("component_required_slots_must_equal_binding_slots")
        is not True
        or generator_contract.get("path_program_schema_is_executable") is not True
        or generator_contract.get("hash_or_token_semantic_selection_allowed")
        is not False
        or recursively_find_true(generator_contract.get("readiness"), READY_KEYS)
    ):
        add_error(errors, "E_P2_FINAL_GENERATOR_CONTRACT", "boundary")
    if (
        generator_registry.get("registry_digest")
        != object_digest(generator_registry, "registry_digest")
        or generator_registry.get("current_generator_entrypoint_count") != 1
        or not str(generator_registry.get("core_module", {}).get("path", "")).endswith(
            "p2_generator_core_r6.py"
        )
        or generator_registry.get("core_module", {}).get("sha256")
        != sha256_file(root / P2_TASK_ROOT / "p2_generator_core_r6.py")
        or generator_registry.get("historical_generator_entrypoints_consumed") != []
        or any(
            row.get("active") is not False
            for row in generator_registry.get(
                "historical_non_active_core_modules", []
            )
            if isinstance(row, dict)
        )
        or generator_registry.get("generator_qualified") is not False
        or generator_registry.get("runtime_ready") is not False
        or generator_registry.get("production_ready") is not False
    ):
        add_error(errors, "E_P2_FINAL_GENERATOR_REGISTRY", "current entry")
    if (
        final_compat.get("receipt_digest")
        != object_digest(final_compat, "receipt_digest")
        or final_compat.get("current_checker", {}).get(
            "sha256_before_final_closeout"
        )
        != P2_CHECKPOINT_CURRENT_CHECKER_SHA256
        or final_compat.get("current_checker", {}).get(
            "sha256_after_final_closeout"
        )
        != sha256_file(root / CURRENT_CHECKER_PATH)
        or final_compat.get("current_checker", {}).get("recursive_checker_chain")
        is not False
        or final_compat.get("p1a_p1b_task_roots_modified") is not False
        or final_compat.get("checkpoint_assets_rewritten") is not False
    ):
        add_error(errors, "E_P2_FINAL_COMPAT", "checker receipt")
    if (
        final_result.get("result_digest")
        != object_digest(final_result, "result_digest")
        or final_result.get("result_state") != "PASS_TO_P3_OPEN_PROBE"
        or final_result.get("p2_complete") is not True
        or final_result.get("p3_allowed") is not True
        or final_result.get("self_approval_count") != 0
        or final_result.get("targeted_r1_review_record_count_per_reviewer") != 141
        or final_result.get("targeted_r1_review_disposition_counts")
        != {
            "APPROVE": 27,
            "REPAIR": 32,
            "REJECT": 0,
            "DISAGREEMENT_REQUIRES_ADJUDICATION": 82,
        }
        or final_result.get("targeted_r2_review_record_count_per_reviewer") != 134
        or final_result.get("targeted_r2_review_disposition_counts")
        != {
            "APPROVE": 107,
            "REPAIR": 20,
            "REJECT": 0,
            "DISAGREEMENT_REQUIRES_ADJUDICATION": 7,
        }
        or final_result.get("targeted_r2_failure_evidence_preserved") is not True
        or final_result.get("targeted_r3_review_record_count_per_reviewer") != 29
        or final_result.get("targeted_r3_review_disposition_counts")
        != {
            "APPROVE": 2,
            "REPAIR": 21,
            "REJECT": 0,
            "DISAGREEMENT_REQUIRES_ADJUDICATION": 6,
        }
        or final_result.get("targeted_r3_failure_evidence_preserved") is not True
        or final_result.get("targeted_r4_review_record_count_per_reviewer") != 27
        or final_result.get("targeted_r4_review_disposition_counts")
        != {
            "APPROVE": 0,
            "REPAIR": 21,
            "REJECT": 0,
            "DISAGREEMENT_REQUIRES_ADJUDICATION": 6,
        }
        or final_result.get("targeted_r4_failure_evidence_preserved") is not True
        or final_result.get("targeted_r5_review_record_count_per_reviewer") != 27
        or final_result.get("targeted_r5_review_disposition_counts")
        != {
            "APPROVE": 26,
            "REPAIR": 0,
            "REJECT": 0,
            "DISAGREEMENT_REQUIRES_ADJUDICATION": 1,
        }
        or final_result.get("targeted_r5_failure_evidence_preserved") is not True
        or final_result.get("targeted_r6_review_record_count_per_reviewer") != 1
        or final_result.get("targeted_r6_review_disposition_counts")
        != {"APPROVE": 1, "REPAIR": 0, "REJECT": 0}
        or final_result.get("active_component_count") != 68
        or final_result.get("revised_historical_component_count") != 18
        or final_result.get("necessary_addition_count") != 30
        or final_result.get("active_control_rule_count") != 8
        or final_result.get("active_edge_count") != 85
        or final_result.get("approved_supply_complete_profile_count") != 20
        or final_result.get("active_ab_path_profile_count") != 20
        or final_result.get("typed_author_request_count") != 40
        or final_result.get("structural_realization_count") != 40
        or final_result.get("component_ablation_case_count") != len(ablations)
        or final_result.get("axis_body_pair_case_count") != 120
        or final_result.get("component_pointer_case_count") != 410
        or final_result.get("observable_effect_tamper_case_count") != 62
        or final_result.get("bound_fact_effect_case_count") != 62
        or final_result.get("required_slot_tamper_case_count") != 20
        or final_result.get("path_program_schema_tamper_case_count") != 240
        or final_result.get("path_program_tamper_case_count") != 120
        or final_result.get("trust_contract_tamper_case_count") != 180
        or final_result.get("route_primary_action_match_count") != 60
        or final_result.get("route_primary_reason_match_count") != 60
        or final_result.get("external_provider_request_count") != 0
        or final_result.get("external_provider_response_count") != 0
        or final_result.get("audience_content_created_count") != 0
        or final_result.get("composition_plan_created_count") != 0
        or recursively_find_true(final_result.get("readiness"), READY_KEYS)
        or final_result.get("core_number_impact")
        != {
            "target_total": 300,
            "reference_inventory": 120,
            "historical_component_inventory": 86,
            "all_unchanged": True,
        }
    ):
        add_error(errors, "E_P2_FINAL_RESULT", "state or counts")


def validate(root: Path) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    required: tuple[Path, ...] = (
        CURRENT_OWNER_PATH,
        REPORT_PATH,
        STANDARD_SNAPSHOT_PATH,
        STANDARD_CONTRACT_PATH,
        BASELINE_MANIFEST_PATH,
        REVIEW_PACKET_PATH,
        REVIEW_CONTRACT_PATH,
        REVIEW_RECORD_TEMPLATE_PATH,
        LEGACY_EDGE_MANIFEST_PATH,
        COMPAT_RECEIPT_PATH,
        RESULT_PATH,
        B24_CHECKER_PATH,
        SUCCESSOR_CHECKER_PATH,
        P2_MATERIALIZER_PATH,
        P2_MODEL_PATH,
        P2_DOCUMENTS_PATH,
        P2_SUCCESSOR_PATH,
        P2_COMPONENTS_PATH,
        P2_RULES_PATH,
        P2_EDGES_PATH,
        P2_SUPPLY_PATH,
        P2_ADDITION_PATH,
        P2_AB_PATH,
        P2_REVIEW_PACKET_PATH,
        P2_REVIEW_JOB_PATH,
        P2_COMPAT_PATH,
        P2_RESULT_PATH,
    )
    try:
        owner_id = load_yaml(root / CURRENT_OWNER_PATH).get(
            "current_gate1_owner", {}
        ).get("owner_id")
    except (OSError, TypeError, ValueError, yaml.YAMLError):
        owner_id = None
    if owner_id == "GATE1_V11_P2_FINAL_OWNER":
        required += (
            P2_TARGET_REVISED_COMPONENTS_PATH,
            P2_TARGET_ADDITIONS_PATH,
            P2_TARGET_RULES_PATH,
            P2_TARGET_EDGES_PATH,
            P2_TARGET_AB_PATH,
            P2_TARGET_REVIEW_PACKET_PATH,
            P2_TARGET_R2_REVISED_COMPONENTS_PATH,
            P2_TARGET_R2_ADDITIONS_PATH,
            P2_TARGET_R2_RULES_PATH,
            P2_TARGET_R2_EDGES_PATH,
            P2_TARGET_R2_AB_PATH,
            P2_TARGET_R2_REVIEW_PACKET_PATH,
            P2_TARGET_R3_REVISED_COMPONENTS_PATH,
            P2_TARGET_R3_ADDITIONS_PATH,
            P2_TARGET_R3_RULES_PATH,
            P2_TARGET_R3_EDGES_PATH,
            P2_TARGET_R3_AB_PATH,
            P2_TARGET_R3_REVIEW_PACKET_PATH,
            P2_TARGET_R4_REVISED_COMPONENTS_PATH,
            P2_TARGET_R4_ADDITIONS_PATH,
            P2_TARGET_R4_RULES_PATH,
            P2_TARGET_R4_EDGES_PATH,
            P2_TARGET_R4_AB_PATH,
            P2_TARGET_R4_REVIEW_PACKET_PATH,
            P2_TARGET_R5_REVISED_COMPONENTS_PATH,
            P2_TARGET_R5_ADDITIONS_PATH,
            P2_TARGET_R5_RULES_PATH,
            P2_TARGET_R5_EDGES_PATH,
            P2_TARGET_R5_AB_PATH,
            P2_TARGET_R5_REVIEW_PACKET_PATH,
            P2_TARGET_R6_REVIEW_PACKET_PATH,
            P2_TASK_ROOT / "p2_generator_core_r6.py",
            P2_TASK_ROOT / "p2_final_documents_r6.py",
            P2_IMPORT_MANIFEST_PATH,
            P2_INITIAL_COMBINED_PATH,
            P2_TARGET_COMBINED_PATH,
            P2_TARGET_R2_COMBINED_PATH,
            P2_TARGET_R3_COMBINED_PATH,
            P2_TARGET_R4_COMBINED_PATH,
            P2_TARGET_R5_COMBINED_PATH,
            P2_TARGET_R6_COMBINED_PATH,
            P2_REVIEW_CLOSEOUT_PATH,
            P2_ACTIVE_COMPONENTS_PATH,
            P2_ACTIVE_RULES_PATH,
            P2_ACTIVE_EDGES_PATH,
            P2_APPROVED_SUPPLY_PATH,
            P2_ACTIVE_AB_PATH,
            P2_GENERATOR_CONTRACT_PATH,
            P2_GENERATOR_REGISTRY_PATH,
            P2_AUTHOR_REQUESTS_PATH,
            P2_REALIZATIONS_PATH,
            P2_PAIR_RESULTS_PATH,
            P2_AXIS_BODY_PAIR_RESULTS_PATH,
            P2_PATH_PROGRAM_TAMPER_RESULTS_PATH,
            P2_TRUST_CONTRACT_TAMPER_RESULTS_PATH,
            P2_COMPONENT_POINTER_RESULTS_PATH,
            P2_OBSERVABLE_EFFECT_TAMPER_RESULTS_PATH,
            P2_BOUND_FACT_EFFECT_RESULTS_PATH,
            P2_REQUIRED_SLOT_TAMPER_RESULTS_PATH,
            P2_PROGRAM_SCHEMA_TAMPER_RESULTS_PATH,
            P2_ABLATION_RESULTS_PATH,
            P2_ROUTE_ACTUALS_PATH,
            P2_ROUTE_COMPARISONS_PATH,
            P2_PROVIDER_AUDIT_PATH,
            P2_FINAL_COMPAT_PATH,
            P2_FINAL_RESULT_PATH,
            *(P2_INITIAL_PRIMARY_DIR / name for name in ("records.jsonl", "report.md", "run_manifest.yaml")),
            *(P2_INITIAL_SECONDARY_DIR / name for name in ("records.jsonl", "report.md", "run_manifest.yaml")),
            *(P2_INITIAL_ADJUDICATION_DIR / name for name in ("records.jsonl", "report.md", "run_manifest.yaml")),
            *(P2_TARGET_PRIMARY_DIR / name for name in ("records.jsonl", "report.md", "run_manifest.yaml")),
            *(P2_TARGET_SECONDARY_DIR / name for name in ("records.jsonl", "report.md", "run_manifest.yaml")),
            *(P2_TARGET_R2_PRIMARY_DIR / name for name in ("records.jsonl", "report.md", "run_manifest.yaml")),
            *(P2_TARGET_R2_SECONDARY_DIR / name for name in ("records.jsonl", "report.md", "run_manifest.yaml")),
            *(P2_TARGET_R3_PRIMARY_DIR / name for name in ("records.jsonl", "report.md", "run_manifest.yaml")),
            *(P2_TARGET_R3_SECONDARY_DIR / name for name in ("records.jsonl", "report.md", "run_manifest.yaml")),
            *(P2_TARGET_R4_PRIMARY_DIR / name for name in ("records.jsonl", "report.md", "run_manifest.yaml")),
            *(P2_TARGET_R4_SECONDARY_DIR / name for name in ("records.jsonl", "report.md", "run_manifest.yaml")),
            *(P2_TARGET_R5_PRIMARY_DIR / name for name in ("records.jsonl", "report.md", "run_manifest.yaml")),
            *(P2_TARGET_R5_SECONDARY_DIR / name for name in ("records.jsonl", "report.md", "run_manifest.yaml")),
            *(P2_TARGET_R6_PRIMARY_DIR / name for name in ("records.jsonl", "report.md", "run_manifest.yaml")),
            *(P2_TARGET_R6_SECONDARY_DIR / name for name in ("records.jsonl", "report.md", "run_manifest.yaml")),
        )
    for relative_path in required:
        if not (root / relative_path).exists():
            add_error(errors, "E_REQUIRED_FILE", relative_path.as_posix())
    if errors:
        return errors
    validate_write_surface(root, errors)
    validate_p4_write_surface(root, errors)
    validate_report(root, errors)
    source = source_maps(root, errors)
    validate_standard(root, errors)
    validate_baseline_manifest(root, errors)
    if source is not None:
        validate_review_packet(root, source, errors)
        validate_legacy_edges(root, source, errors)
    validate_review_contract(root, errors)
    validate_review_record_template(root, errors)
    validate_result(root, errors)
    validate_owner(root, errors)
    validate_compatibility_receipt(root, errors)
    validate_repair_shape(root, errors)
    if (root / P1B_TASK_ROOT).exists():
        validate_p1b(root, source, errors)
    if (root / P2_TASK_ROOT).exists():
        validate_p2(root, errors)
    if owner_id == "GATE1_V11_P2_FINAL_OWNER":
        validate_p2_final(root, errors)
    successor_active = (root / P4_AUTHOR_RECOVERY_TASK_ROOT).exists()
    if successor_active:
        module_root = root / P4_AUTHOR_RECOVERY_TASK_ROOT
        if str(module_root) not in sys.path:
            sys.path.insert(0, str(module_root))
        try:
            import recovery_guard

            install_public_foundation_recovery_handoff(recovery_guard)
            errors.extend(recovery_guard.validate_recovery(root))
        except (ImportError, OSError, TypeError, ValueError) as exc:
            add_error(errors, "E_P4_AUTHOR_RECOVERY_GUARD_IMPORT", str(exc))
    if (root / P3_TASK_ROOT).exists() and not successor_active:
        validate_p3_successor(root, errors)
    if (root / P4_TASK_ROOT).exists() and not successor_active:
        validate_p4_successor(root, errors)
    if (root / P3_RECOVERY_TASK_ROOT).exists() and not successor_active:
        if (root / P4_RESEALED_TASK_ROOT).exists():
            module_root = root / P4_RESEALED_TASK_ROOT
            if str(module_root) not in sys.path:
                sys.path.insert(0, str(module_root))
            try:
                from p3_recovery_guard_current import validate_p3_recovery_current
                from p4_resealed_guard import validate_p4_resealed

                errors.extend(validate_p3_recovery_current(root))
                errors.extend(validate_p4_resealed(root))
            except (ImportError, OSError, TypeError, ValueError) as exc:
                add_error(errors, "E_P4R_GUARD_IMPORT", str(exc))
        else:
            module_root = root / P3_RECOVERY_TASK_ROOT
            if str(module_root) not in sys.path:
                sys.path.insert(0, str(module_root))
            try:
                from p3_recovery_guard import validate_p3_recovery

                errors.extend(validate_p3_recovery(root))
            except (ImportError, OSError, TypeError, ValueError) as exc:
                add_error(errors, "E_P3R_GUARD_IMPORT", str(exc))
    return errors


def copy_fixture(root: Path, target: Path) -> None:
    relative_paths = (
        CURRENT_OWNER_PATH,
        REPORT_PATH,
        CLEAN_120_PATH,
        ROUTE_INPUT_PATH,
        ROUTE_ACTUAL_PATH,
        COMPONENT_SOURCE_PATH,
        CANDIDATE_SOURCE_PATH,
        PROFILE_PATH,
        AB_CONTRACT_PATH,
        B24_CHECKER_PATH,
        SUCCESSOR_CHECKER_PATH,
        Path("ci/checkers/check_gate1_v1_1_current.py"),
    )
    for relative_path in relative_paths:
        destination = target / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / relative_path, destination)
    shutil.copytree(root / TASK_ROOT, target / TASK_ROOT)
    if (root / P1B_TASK_ROOT).exists():
        shutil.copytree(root / P1B_TASK_ROOT, target / P1B_TASK_ROOT)
    if (root / P2_TASK_ROOT).exists():
        shutil.copytree(root / P2_TASK_ROOT, target / P2_TASK_ROOT)
    if (root / P3_TASK_ROOT).exists():
        shutil.copytree(root / P3_TASK_ROOT, target / P3_TASK_ROOT)
    if (root / P4_TASK_ROOT).exists():
        shutil.copytree(root / P4_TASK_ROOT, target / P4_TASK_ROOT)
    for successor_root in (
        P3_RECOVERY_TASK_ROOT,
        P4_RESEALED_TASK_ROOT,
        P4_AUTHOR_RECOVERY_TASK_ROOT,
        P4_THIRD_TASK_ROOT,
    ):
        if (root / successor_root).exists():
            shutil.copytree(root / successor_root, target / successor_root)


def mutate_yaml(path: Path, mutate: Callable[[dict[str, Any]], None]) -> None:
    value = load_yaml(path)
    mutate(value)
    write_yaml(path, value)


def mutate_json(path: Path, mutate: Callable[[dict[str, Any]], None]) -> None:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"JSON root is not a mapping: {path}")
    mutate(value)
    path.write_text(canonical_json(value) + "\n", encoding="utf-8")


def mutate_jsonl(path: Path, mutate: Callable[[list[dict[str, Any]]], None]) -> None:
    rows = [row for row, _ in read_jsonl(path)]
    mutate(rows)
    write_jsonl(path, rows)


def tamper_p2_parent_digest(rows: list[dict[str, Any]]) -> None:
    rows[0]["provenance"]["parent_assets"][0]["parent_digest"] = "0" * 64
    rows[0]["component_digest"] = object_digest(rows[0], "component_digest")


def tamper_p2_successor_link(rows: list[dict[str, Any]]) -> None:
    rows[0]["successor_digest"] = "0" * 64
    rows[0]["mapping_digest"] = object_digest(rows[0], "mapping_digest")


def tamper_p2_edge_fit(rows: list[dict[str, Any]]) -> None:
    rows[0]["fit_basis"]["business_purpose"] = "forged purpose"
    rows[0]["edge_digest"] = object_digest(rows[0], "edge_digest")


def tamper_p2_ab_axis(rows: list[dict[str, Any]]) -> None:
    axis = rows[0]["observable_difference_axes"][0]
    rows[0]["lane_b"][axis] = rows[0]["lane_a"][axis]
    rows[0]["path_digest"] = object_digest(rows[0], "path_digest")


def tamper_p2_final_exact_binding(rows: list[dict[str, Any]]) -> None:
    binding = rows[0]["component_exact_binding"]
    binding["exact_typed_object_bindings"]["input"][0]["object_id"] += "-FORGED"
    binding["binding_digest"] = hashlib.sha256(
        canonical_json(binding["exact_typed_object_bindings"]).encode("utf-8")
    ).hexdigest()
    rows[0]["edge_digest"] = object_digest(rows[0], "edge_digest")


def tamper_p2_final_axis_operator(rows: list[dict[str, Any]]) -> None:
    contracts = rows[0]["axis_realization_contracts"]
    contracts[0]["operator_component_id"] = contracts[1]["operator_component_id"]
    rows[0]["path_digest"] = object_digest(rows[0], "path_digest")


def tamper_p2_final_request_axis(rows: list[dict[str, Any]]) -> None:
    contracts = rows[0]["axis_realization_contracts"]
    contracts[0]["operator_component_id"] = contracts[1]["operator_component_id"]
    rows[0]["request_digest"] = object_digest(rows[0], "request_digest")


def tamper_p2_r1_failure_evidence(rows: list[dict[str, Any]]) -> None:
    row = next(row for row in rows if row["requires_targeted_adjudication"])
    row["requires_targeted_adjudication"] = False
    row["combined_disposition"] = "APPROVE"
    row["combined_digest"] = object_digest(row, "combined_digest")


def tamper_p2_r2_signed_decision(rows: list[dict[str, Any]]) -> None:
    rows[0]["decision"] = "REPAIR"
    rows[0]["defect_severity"] = "MINOR"
    rows[0]["record_digest"] = object_digest(rows[0], "record_digest")


def tamper_p2_r3_unknown_axis(rows: list[dict[str, Any]]) -> None:
    axis = rows[0]["observable_difference_axes"][0]
    rows[0]["lane_b"]["axes"][axis] = "UNREVIEWED_AXIS_VALUE"
    rows[0]["lane_b"]["axis_programs"][axis][
        "reviewed_path_value"
    ] = "UNREVIEWED_AXIS_VALUE"
    contract = next(
        row for row in rows[0]["axis_realization_contracts"] if row["axis"] == axis
    )
    contract["lane_b_value"] = "UNREVIEWED_AXIS_VALUE"
    rows[0]["path_digest"] = object_digest(rows[0], "path_digest")


def tamper_p2_request_material_truth(rows: list[dict[str, Any]]) -> None:
    rows[0]["typed_material"]["facts"][0]["fact_value_digest"] = "f" * 64
    rows[0]["typed_material"]["material_digest"] = object_digest(
        rows[0]["typed_material"], "material_digest"
    )
    rows[0]["request_digest"] = object_digest(rows[0], "request_digest")


def tamper_p2_request_strip_nonaxis_binding(rows: list[dict[str, Any]]) -> None:
    axis_roles = set(P2_AXIS_OPERATOR_ROLE_BY_AXIS.values())
    binding = next(
        row
        for row in rows[0]["component_bindings"]
        if row["component_role"] not in axis_roles
        and (
            row["exact_typed_object_bindings"].get("fact")
            or row["exact_typed_object_bindings"].get("authorization")
        )
    )
    binding["exact_typed_object_bindings"]["fact"] = []
    binding["exact_typed_object_bindings"]["authorization"] = []
    binding["binding_digest"] = hashlib.sha256(
        canonical_json(binding["exact_typed_object_bindings"]).encode("utf-8")
    ).hexdigest()
    rows[0]["request_digest"] = object_digest(rows[0], "request_digest")


def tamper_p2_evidence_accept(rows: list[dict[str, Any]]) -> None:
    rows[0]["tamper_rejected"] = False
    rows[0]["error_code"] = ""
    rows[0]["case_digest"] = object_digest(rows[0], "case_digest")


def tamper_current_owner_lineage(value: dict[str, Any]) -> None:
    owner = value["current_gate1_owner"]
    authority = owner.get("current_ledger_authority")
    if isinstance(authority, dict):
        authority["shared_horizon_modified"] = True
        return
    predecessor = owner["predecessor"]
    if "final_targeted_review" in predecessor:
        predecessor["final_targeted_review"]["reviewed_checkpoint_commit"] = "0" * 40
        return
    predecessor["owner_digest"] = "0" * 64


def tamper_p3_structure_clone(rows: list[dict[str, Any]]) -> None:
    source = rows[0]
    target = next(
        row
        for row in rows
        if row["profile_id"] == source["profile_id"] and row["variant"] != source["variant"]
    )
    target["axis_values"] = copy.deepcopy(source["axis_values"])
    target["addressable_outputs"] = copy.deepcopy(source["addressable_outputs"])
    target["addressable_output_digest"] = source["addressable_output_digest"]
    target["record_digest"] = object_digest(target, "record_digest")


def tamper_p3_unapproved_component(rows: list[dict[str, Any]]) -> None:
    rows[0]["selected_component_ids"].append("G1V11-P2-FC-01-FULL-SURFACE-FACT-COVERAGE")
    rows[0]["record_digest"] = object_digest(rows[0], "record_digest")


def tamper_p3_structure_audience_content(rows: list[dict[str, Any]]) -> None:
    rows[0]["audience_content"] = True
    rows[0]["audience_title"] = "forbidden"
    rows[0]["record_digest"] = object_digest(rows[0], "record_digest")


def tamper_p3_component_metadata_use(rows: list[dict[str, Any]]) -> None:
    rows[0]["component_usage"][0]["implementation_surface_unit_ids"] = [
        "NONEXISTENT-SURFACE"
    ]
    rows[0]["output_digest"] = object_digest(rows[0], "output_digest")


def tamper_p3_unbound_fact(rows: list[dict[str, Any]]) -> None:
    rows[0]["surface_units"][1]["fact_ids"] = ["FORGED-FACT"]
    rows[0]["output_digest"] = object_digest(rows[0], "output_digest")


def tamper_p3_all_block(rows: list[dict[str, Any]]) -> None:
    for row in rows:
        row["actual_primary_action"] = "BLOCK"
        row["route_result_digest"] = object_digest(row, "route_result_digest")


def tamper_p3_route_gold_leak(rows: list[dict[str, Any]]) -> None:
    rows[0]["gold_primary_action"] = "BLOCK"


def tamper_p3_reviewer_collision(value: dict[str, Any]) -> None:
    value["reviewer_identity"] = "P3-CONTROLLED-AUTHOR-GPT56SOL-001"
    value["signed_record_digest"] = object_digest(value, "signed_record_digest")


def tamper_p3_review_verdict(value: dict[str, Any]) -> None:
    value["overall_verdict"] = "FAIL" if value["overall_verdict"] == "PASS" else "PASS"
    value["signed_record_digest"] = object_digest(value, "signed_record_digest")


def tamper_p3_freeze_window(value: dict[str, Any]) -> None:
    freeze = value["p3_open_repair_freeze"]
    freeze["open_core_repair_window_remaining"] = 1
    freeze["freeze_manifest_digest"] = object_digest(freeze, "freeze_manifest_digest")


def tamper_p3_result_count(value: dict[str, Any]) -> None:
    result = value["p3_open_probe40_result"]
    result["counts_toward_300"] = 20
    result["result_digest"] = object_digest(result, "result_digest")


def tamper_p3_result_readiness(value: dict[str, Any]) -> None:
    result = value["p3_open_probe40_result"]
    result["readiness"]["generation_allowed"] = True
    result["result_digest"] = object_digest(result, "result_digest")


def tamper_p3_handoff_authorization(value: dict[str, Any]) -> None:
    handoff = value["p4_sealed_probe_handoff"]
    handoff["p4_execution_authorized"] = True
    handoff["handoff_digest"] = object_digest(handoff, "handoff_digest")


def create_p3_hidden_material(root: Path) -> None:
    path = root / P3_TASK_ROOT / "hidden/forbidden_case.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{}\n", encoding="utf-8")


def selftest(root: Path) -> int:
    tests: list[tuple[str, str, Callable[[Path], None]]] = [
        (
            "standard_snapshot_mutation",
            "E_STANDARD_SNAPSHOT",
            lambda temp: (temp / STANDARD_SNAPSHOT_PATH).write_bytes(
                (temp / STANDARD_SNAPSHOT_PATH).read_bytes() + b"\nmutation\n"
            ),
        ),
        (
            "active_legacy_edge",
            "E_LEGACY_EDGE_ACTIVE",
            lambda temp: mutate_jsonl(
                temp / LEGACY_EDGE_MANIFEST_PATH,
                lambda rows: rows[0].update({"new_generator_consumable": True}),
            ),
        ),
        (
            "review_decision_created",
            "E_REVIEW_DECISION",
            lambda temp: mutate_jsonl(
                temp / REVIEW_PACKET_PATH,
                lambda rows: rows[0].update({"review_state": "APPROVED"}),
            ),
        ),
        (
            "route_actual_leakage",
            "E_ROUTE_BLINDNESS",
            lambda temp: mutate_jsonl(
                temp / REVIEW_PACKET_PATH,
                lambda rows: rows[120].update(
                    {
                        "observed_implementation_record": {
                            "path": ROUTE_ACTUAL_PATH.as_posix(),
                            "record_sha256": ROUTE_ACTUAL_SHA256,
                        }
                    }
                ),
            ),
        ),
        (
            "missing_scoring_contract",
            "E_SCORING_CONTRACT",
            lambda temp: mutate_yaml(
                temp / REVIEW_CONTRACT_PATH,
                lambda value: value["independent_review_contract"].pop(
                    "scoring_and_decision_contract"
                ),
            ),
        ),
        (
            "review_role_mapped_to_lane",
            "E_LANE_BOUNDARY",
            lambda temp: mutate_yaml(
                temp / REVIEW_CONTRACT_PATH,
                lambda value: value["independent_review_contract"][
                    "creative_channel_boundary"
                ].update({"review_role_may_not_be_mapped_to_generation_lane": False}),
            ),
        ),
        (
            "historical_b_channel_auto_inference",
            "E_LANE_BOUNDARY",
            lambda temp: mutate_yaml(
                temp / REVIEW_CONTRACT_PATH,
                lambda value: value["independent_review_contract"][
                    "creative_channel_boundary"
                ].update(
                    {"historical_b_channel_is_not_generation_lane_evidence": False}
                ),
            ),
        ),
        (
            "readiness_flip",
            "E_READINESS",
            lambda temp: mutate_yaml(
                temp / RESULT_PATH,
                lambda value: value["p1a_standard_baseline_preflight_result"][
                    "readiness"
                ].update({"generation_allowed": True}),
            ),
        ),
        (
            "owner_shared_horizon_flip",
            "E_OWNER_POLICY",
            lambda temp: mutate_yaml(
                temp / CURRENT_OWNER_PATH,
                tamper_current_owner_lineage,
            ),
        ),
        (
            "compatibility_receipt_prior_hash",
            "E_COMPAT_RECEIPT",
            lambda temp: mutate_yaml(
                temp / COMPAT_RECEIPT_PATH,
                lambda value: value["governance_compatibility_repair_receipt"][
                    "modified_live_checkers"
                ][0].update({"sha256_before": "0" * 64}),
            ),
        ),
        (
            "p2_component_activated_before_review",
            "E_P2_SUCCESSOR_MAP",
            lambda temp: mutate_jsonl(
                temp / P2_SUCCESSOR_PATH,
                lambda rows: rows[0].update({"active": True}),
            ),
        ),
        (
            "p2_control_rule_counts_as_supply",
            "E_P2_CONTROL_RULES",
            lambda temp: mutate_jsonl(
                temp / P2_RULES_PATH,
                lambda rows: rows[0].update({"contributes_component_supply": True}),
            ),
        ),
        (
            "p2_source_provenance_removed",
            "E_P2_COMPONENT_PROVENANCE",
            lambda temp: mutate_jsonl(
                temp / P2_COMPONENTS_PATH,
                lambda rows: rows[0]["provenance"].update({"parent_assets": []}),
            ),
        ),
        (
            "p2_parent_digest_forged_with_fresh_object_digest",
            "E_P2_COMPONENT_PROVENANCE",
            lambda temp: mutate_jsonl(
                temp / P2_COMPONENTS_PATH, tamper_p2_parent_digest
            ),
        ),
        (
            "p2_successor_retargeted_with_fresh_mapping_digest",
            "E_P2_SUCCESSOR_MAP",
            lambda temp: mutate_jsonl(
                temp / P2_SUCCESSOR_PATH, tamper_p2_successor_link
            ),
        ),
        (
            "p2_edge_fit_forged_with_fresh_edge_digest",
            "E_P2_EDGE",
            lambda temp: mutate_jsonl(temp / P2_EDGES_PATH, tamper_p2_edge_fit),
        ),
        (
            "p2_review_prefilled",
            "E_P2_REVIEW_PACKET",
            lambda temp: mutate_jsonl(
                temp / P2_REVIEW_PACKET_PATH,
                lambda rows: rows[0].update({"prefilled_decision": "APPROVE"}),
            ),
        ),
        (
            "p2_ab_session_reused",
            "E_P2_AB_PATH",
            lambda temp: mutate_jsonl(
                temp / P2_AB_PATH,
                lambda rows: rows[0]["lane_b"].update(
                    {"session_policy": rows[0]["lane_a"]["session_policy"]}
                ),
            ),
        ),
        (
            "p2_ab_declared_axis_not_observably_different",
            "E_P2_AB_PATH",
            lambda temp: mutate_jsonl(temp / P2_AB_PATH, tamper_p2_ab_axis),
        ),
        (
            "p2_p3_unlock",
            "E_P2_RESULT",
            lambda temp: mutate_yaml(
                temp / P2_RESULT_PATH,
                lambda value: value["p2_component_review_checkpoint_result"].update(
                    {"p3_allowed": True}
                ),
            ),
        ),
    ]
    owner_id = load_yaml(root / CURRENT_OWNER_PATH).get("current_gate1_owner", {}).get(
        "owner_id"
    )
    if owner_id == "GATE1_V11_P2_FINAL_OWNER":
        tests.extend(
            [
                (
                    "p2_final_r1_failure_evidence_erased",
                    "E_P2_FINAL_TARGET_R1_COMBINED",
                    lambda temp: mutate_jsonl(
                        temp / P2_TARGET_COMBINED_PATH,
                        tamper_p2_r1_failure_evidence,
                    ),
                ),
                (
                    "p2_final_r2_signed_decision_forged",
                    "E_P2_FINAL_TARGET_R2_REVIEW",
                    lambda temp: mutate_jsonl(
                        temp / P2_TARGET_R2_PRIMARY_DIR / "records.jsonl",
                        tamper_p2_r2_signed_decision,
                    ),
                ),
                (
                    "p2_final_r3_failure_evidence_erased",
                    "E_P2_FINAL_TARGET_R3_COMBINED",
                    lambda temp: mutate_jsonl(
                        temp / P2_TARGET_R3_COMBINED_PATH,
                        tamper_p2_r1_failure_evidence,
                    ),
                ),
                (
                    "p2_final_r4_failure_evidence_erased",
                    "E_P2_FINAL_TARGET_R4_COMBINED",
                    lambda temp: mutate_jsonl(
                        temp / P2_TARGET_R4_COMBINED_PATH,
                        tamper_p2_r1_failure_evidence,
                    ),
                ),
                (
                    "p2_final_r5_signed_decision_forged",
                    "E_P2_FINAL_TARGET_R5_REVIEW",
                    lambda temp: mutate_jsonl(
                        temp / P2_TARGET_R5_PRIMARY_DIR / "records.jsonl",
                        tamper_p2_r2_signed_decision,
                    ),
                ),
                (
                    "p2_final_r6_signed_decision_forged",
                    "E_P2_FINAL_TARGET_R6_REVIEW",
                    lambda temp: mutate_jsonl(
                        temp / P2_TARGET_R6_PRIMARY_DIR / "records.jsonl",
                        tamper_p2_r2_signed_decision,
                    ),
                ),
                (
                    "p2_final_required_slot_tamper_accepted",
                    "E_P2_FINAL_REQUIRED_SLOT",
                    lambda temp: mutate_jsonl(
                        temp / P2_REQUIRED_SLOT_TAMPER_RESULTS_PATH,
                        tamper_p2_evidence_accept,
                    ),
                ),
                (
                    "p2_final_program_schema_tamper_accepted",
                    "E_P2_FINAL_PROGRAM_SCHEMA",
                    lambda temp: mutate_jsonl(
                        temp / P2_PROGRAM_SCHEMA_TAMPER_RESULTS_PATH,
                        tamper_p2_evidence_accept,
                    ),
                ),
                (
                    "p2_final_exact_object_binding_forged",
                    "E_P2_FINAL_EDGE",
                    lambda temp: mutate_jsonl(
                        temp / P2_ACTIVE_EDGES_PATH,
                        tamper_p2_final_exact_binding,
                    ),
                ),
                (
                    "p2_final_axis_operator_substituted",
                    "E_P2_FINAL_AB_PATH",
                    lambda temp: mutate_jsonl(
                        temp / P2_ACTIVE_AB_PATH,
                        tamper_p2_final_axis_operator,
                    ),
                ),
                (
                    "p2_final_request_operator_substituted",
                    "E_P2_FINAL_REQUEST_PATH_BINDING",
                    lambda temp: mutate_jsonl(
                        temp / P2_AUTHOR_REQUESTS_PATH,
                        tamper_p2_final_request_axis,
                    ),
                ),
                (
                    "p2_final_unreviewed_axis_value",
                    "E_P2_FINAL_AB_PATH",
                    lambda temp: mutate_jsonl(
                        temp / P2_ACTIVE_AB_PATH,
                        tamper_p2_r3_unknown_axis,
                    ),
                ),
                (
                    "p2_final_material_truth_tamper",
                    "E_P2_FINAL_REQUEST_PATH_BINDING",
                    lambda temp: mutate_jsonl(
                        temp / P2_AUTHOR_REQUESTS_PATH,
                        tamper_p2_request_material_truth,
                    ),
                ),
                (
                    "p2_final_nonaxis_binding_stripped",
                    "E_P2_FINAL_REQUEST_PATH_BINDING",
                    lambda temp: mutate_jsonl(
                        temp / P2_AUTHOR_REQUESTS_PATH,
                        tamper_p2_request_strip_nonaxis_binding,
                    ),
                ),
                (
                    "p2_final_readiness_flip",
                    "E_P2_FINAL_RESULT",
                    lambda temp: mutate_yaml(
                        temp / P2_FINAL_RESULT_PATH,
                        lambda value: value["p2_final_result"]["readiness"].update(
                            {"generation_allowed": True}
                        ),
                    ),
                ),
            ]
        )
    if (root / P3_TASK_ROOT).exists():
        p3_structure = P3_TASK_ROOT / "structure/attempt_1/structure_80.v0.2.jsonl"
        p3_outputs = P3_TASK_ROOT / "open_probe/attempt_1/positive_20_first_outputs.v0.2.jsonl"
        p3_route_actuals = P3_TASK_ROOT / "open_probe/attempt_1/route_20_actuals.v0.2.jsonl"
        p3_route_inputs = P3_TASK_ROOT / "freeze/attempt_1/route_inputs_20.v0.2.jsonl"
        p3_freeze = P3_TASK_ROOT / "freeze/attempt_1/p3_open_repair_freeze.v0.2.yaml"
        p3_result = P3_TASK_ROOT / "result/p3_open_probe40_result.v0.2.yaml"
        p3_handoff = P3_TASK_ROOT / "result/p4_sealed_probe_handoff.v0.2.yaml"
        p3_review_one = P3_TASK_ROOT / "review/attempt_1/signed_content_value_review.v0.2.json"
        p3_attempt0_result = P3_TASK_ROOT / "result/p3_open_probe40_result.v0.1.yaml"
        p3_instruction = P3_TASK_ROOT / "freeze/attempt_1/controlled_author_instruction.v0.2.md"
        tests.extend(
            [
                (
                    "p3_structure_template_clone",
                    "E_P3_STRUCTURE_CLONE",
                    lambda temp: mutate_jsonl(temp / p3_structure, tamper_p3_structure_clone),
                ),
                (
                    "p3_component_metadata_only_use",
                    "E_P3_COMPONENT_USE",
                    lambda temp: mutate_jsonl(temp / p3_outputs, tamper_p3_component_metadata_use),
                ),
                (
                    "p3_control_rule_used_as_component",
                    "E_P3_STRUCTURE_COMPONENT",
                    lambda temp: mutate_jsonl(temp / p3_structure, tamper_p3_unapproved_component),
                ),
                (
                    "p3_post_review_structure_mutation",
                    "E_P3_REVIEW_PACKET",
                    lambda temp: mutate_jsonl(temp / p3_structure, tamper_p3_structure_audience_content),
                ),
                (
                    "p3_second_repair_window",
                    "E_P3_REPAIR_WINDOW",
                    lambda temp: mutate_yaml(temp / p3_freeze, tamper_p3_freeze_window),
                ),
                (
                    "p3_attempt0_failure_mutation",
                    "E_P3_ATTEMPT0_INTEGRITY",
                    lambda temp: (temp / p3_attempt0_result).write_bytes(
                        (temp / p3_attempt0_result).read_bytes() + b"\nmutation\n"
                    ),
                ),
                (
                    "p3_structure_audience_content",
                    "E_P3_STRUCTURE_BOUNDARY",
                    lambda temp: mutate_jsonl(temp / p3_structure, tamper_p3_structure_audience_content),
                ),
                (
                    "p3_all_routes_blocked",
                    "E_P3_ROUTE_DISTRIBUTION",
                    lambda temp: mutate_jsonl(temp / p3_route_actuals, tamper_p3_all_block),
                ),
                (
                    "p3_route_gold_leaked_into_input",
                    "E_P3_ROUTE_GOLD_LEAK",
                    lambda temp: mutate_jsonl(temp / p3_route_inputs, tamper_p3_route_gold_leak),
                ),
                (
                    "p3_unbound_fact",
                    "E_P3_UNBOUND_FACT",
                    lambda temp: mutate_jsonl(temp / p3_outputs, tamper_p3_unbound_fact),
                ),
                (
                    "p3_reviewer_author_collision",
                    "E_P3_REVIEW_IDENTITY",
                    lambda temp: mutate_json(temp / p3_review_one, tamper_p3_reviewer_collision),
                ),
                (
                    "p3_review_verdict_forged",
                    "E_P3_REVIEW_VERDICT",
                    lambda temp: mutate_json(temp / p3_review_one, tamper_p3_review_verdict),
                ),
                (
                    "p3_frozen_instruction_mutation",
                    "E_P3_FREEZE",
                    lambda temp: (temp / p3_instruction).write_bytes(
                        (temp / p3_instruction).read_bytes() + b"\nmutation\n"
                    ),
                ),
                (
                    "p3_open_samples_counted_toward_300",
                    "E_P3_CORE_NUMBERS",
                    lambda temp: mutate_yaml(temp / p3_result, tamper_p3_result_count),
                ),
                (
                    "p3_readiness_flipped",
                    "E_P3_READINESS",
                    lambda temp: mutate_yaml(temp / p3_result, tamper_p3_result_readiness),
                ),
                (
                    "p3_hidden_material_created",
                    "E_P3_HIDDEN_MATERIAL",
                    create_p3_hidden_material,
                ),
                (
                    "p3_p2_component_history_mutated",
                    "E_P3_P2_FROZEN",
                    lambda temp: (temp / P2_ACTIVE_COMPONENTS_PATH).write_bytes(
                        (temp / P2_ACTIVE_COMPONENTS_PATH).read_bytes() + b"\n"
                    ),
                ),
                (
                    "p3_positive_denominator_deleted",
                    "E_P3_OUTPUT_COUNT",
                    lambda temp: mutate_jsonl(temp / p3_outputs, lambda rows: rows.pop()),
                ),
                (
                    "p3_p4_execution_self_authorized",
                    "E_P3_HANDOFF",
                    lambda temp: mutate_yaml(temp / p3_handoff, tamper_p3_handoff_authorization),
                ),
            ]
        )
    failures: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="gate1-p1a-checker-selftest-") as temporary:
        base = Path(temporary)
        for name, expected_code, mutate in tests:
            case_root = base / name
            copy_fixture(root, case_root)
            if name.startswith("p3_"):
                shutil.rmtree(
                    case_root / P4_AUTHOR_RECOVERY_TASK_ROOT,
                    ignore_errors=True,
                )
            mutate(case_root)
            codes = {error["code"] for error in validate(case_root)}
            if expected_code not in codes:
                failures.append(
                    {"case": name, "expected": expected_code, "actual": sorted(codes)}
                )
    identity_errors: list[dict[str, str]] = []
    validate_review_identity_set(
        {
            "PRIMARY_CONTENT_VALUE": {
                "reviewer_identity_id": "same-agent",
                "reviewer_instance_or_session_id": "same-session",
                "review_run_id": "same-run",
                "append_only_signature_or_attestation": "same-signature",
            },
            "SECONDARY_FACT_AUTHORIZATION": {
                "reviewer_identity_id": "same-agent",
                "reviewer_instance_or_session_id": "same-session",
                "review_run_id": "same-run",
                "append_only_signature_or_attestation": "same-signature",
            },
        },
        identity_errors,
    )
    if "E_REVIEWER_IDENTITY_COLLISION" not in {
        error["code"] for error in identity_errors
    }:
        failures.append(
            {
                "case": "same_reviewer_identity",
                "expected": "E_REVIEWER_IDENTITY_COLLISION",
                "actual": sorted({error["code"] for error in identity_errors}),
            }
        )
    if not unexpected_write_paths(root, {Path("outside_p1a/unapproved.txt")}):
        failures.append(
            {"case": "unauthorized_path", "expected": "E_WRITE_SURFACE", "actual": []}
        )
    if unexpected_write_paths(
        root,
        {PUBLIC_FOUNDATION_ROOT / "contract/public_foundation_contract.v1.yaml"},
    ):
        failures.append(
            {
                "case": "public_foundation_delegation",
                "expected": "delegated to check_product_foundation.py",
                "actual": ["E_WRITE_SURFACE"],
            }
        )
    if not unexpected_write_paths(
        root,
        {PUBLIC_FOUNDATION_ROOT / "future/arbitrary_successor.yaml"},
    ):
        failures.append(
            {
                "case": "public_foundation_future_path_not_delegated",
                "expected": "E_WRITE_SURFACE",
                "actual": [],
            }
        )
    for package_root, checker_path in DOWNSTREAM_SUCCESSOR_DELEGATIONS:
        with tempfile.TemporaryDirectory(
            prefix="gate1-downstream-successor-selftest-"
        ) as temporary:
            temp_root = Path(temporary)
            workflow_destination = temp_root / CI_WORKFLOW_PATH
            checker_destination = temp_root / checker_path
            workflow_destination.parent.mkdir(parents=True, exist_ok=True)
            checker_destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(root / CI_WORKFLOW_PATH, workflow_destination)
            checker_destination.write_text(
                "#!/usr/bin/env python3\nraise SystemExit(0)\n", encoding="utf-8"
            )
            delegated_path = package_root / "implementation.py"
            if unexpected_write_paths(temp_root, {delegated_path}):
                failures.append(
                    {
                        "case": f"reserved_downstream_successor:{package_root}",
                        "expected": "delegated to registered package checker",
                        "actual": ["E_WRITE_SURFACE"],
                    }
                )
    if not unexpected_write_paths(
        root, {Path("15_unreserved_package/unapproved.txt")}
    ):
        failures.append(
            {
                "case": "unreserved_downstream_successor",
                "expected": "E_WRITE_SURFACE",
                "actual": [],
            }
        )
    if not public_foundation_successor_registration_is_valid(root):
        failures.append(
            {
                "case": "public_foundation_successor_registration",
                "expected": "checker digest and four workflow calls pinned",
                "actual": "invalid",
            }
        )
    with tempfile.TemporaryDirectory(
        prefix="gate1-public-foundation-successor-selftest-"
    ) as temporary:
        temp_root = Path(temporary)
        checker_destination = temp_root / PUBLIC_FOUNDATION_CHECKER_PATH
        workflow_destination = temp_root / CI_WORKFLOW_PATH
        checker_destination.parent.mkdir(parents=True, exist_ok=True)
        workflow_destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / PUBLIC_FOUNDATION_CHECKER_PATH, checker_destination)
        shutil.copy2(root / CI_WORKFLOW_PATH, workflow_destination)
        workflow_text = workflow_destination.read_text(encoding="utf-8")
        workflow_destination.write_text(
            workflow_text.replace(
                "          python3 ci/checkers/check_product_foundation.py\n",
                "          # python3 ci/checkers/check_product_foundation.py\n",
                1,
            ),
            encoding="utf-8",
        )
        if public_foundation_successor_registration_is_valid(temp_root):
            failures.append(
                {
                    "case": "public_foundation_successor_workflow_tamper",
                    "expected": "invalid",
                    "actual": "valid",
                }
            )
        shutil.copy2(root / CI_WORKFLOW_PATH, workflow_destination)
        checker_destination.write_bytes(checker_destination.read_bytes() + b"\n")
        if public_foundation_successor_registration_is_valid(temp_root):
            failures.append(
                {
                    "case": "public_foundation_successor_checker_tamper",
                    "expected": "invalid",
                    "actual": "valid",
                }
            )
    retained_handoff_errors = filter_public_foundation_checker_handoff(
        root,
        [
            {
                "code": "E_T3_TOOL_FILE_DRIFT",
                "detail": CURRENT_CHECKER_PATH.as_posix(),
            },
            {
                "code": "E_T3_TOOL_FILE_DRIFT",
                "detail": "historical/other_frozen_tool.py",
            },
        ],
    )
    if retained_handoff_errors != [
        {
            "code": "E_T3_TOOL_FILE_DRIFT",
            "detail": "historical/other_frozen_tool.py",
        }
    ]:
        failures.append(
            {
                "case": "public_foundation_historical_tool_handoff",
                "expected": "only the exact predecessor self-drift is delegated",
                "actual": retained_handoff_errors,
            }
        )
    if (root / P1B_MATERIALIZER_PATH).exists():
        p1b_selftest = subprocess.run(
            [sys.executable, str(root / P1B_MATERIALIZER_PATH), "--selftest"],
            cwd=root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if p1b_selftest.returncode != 0:
            failures.append(
                {
                    "case": "p1b_negative_tamper_suite",
                    "expected": "exit 0",
                    "actual": p1b_selftest.stderr or p1b_selftest.stdout,
                }
            )
    if (root / P4_TASK_ROOT).exists() and not (
        root / P4_AUTHOR_RECOVERY_TASK_ROOT
    ).exists():
        module_root = root / P4_TASK_ROOT
        if str(module_root) not in sys.path:
            sys.path.insert(0, str(module_root))
        try:
            import p4_guard_current

            if (root / P3_RECOVERY_TASK_ROOT).exists():
                if (root / P4_RESEALED_TASK_ROOT).exists():
                    freeze = load_yaml(
                        root
                        / P4_RESEALED_TASK_ROOT
                        / "freeze/p4_resealed_tool_freeze.v1.0.yaml"
                    ).get("p4_resealed_tool_freeze")
                    expected_checker_sha = (
                        freeze.get("tool_files", {}).get(
                            CURRENT_CHECKER_PATH.as_posix()
                        )
                        if isinstance(freeze, dict)
                        else None
                    )
                else:
                    freeze = load_yaml(
                        root
                        / P3_RECOVERY_TASK_ROOT
                        / "freeze/p3_route_compiler_recovery_freeze.v1.0.yaml"
                    )
                    expected_checker_sha = freeze.get("current_checker_sha256")
                if expected_checker_sha != sha256_file(root / CURRENT_CHECKER_PATH):
                    raise ValueError("E_P3R_CURRENT_CHECKER_BINDING")
                p4_guard_current.CURRENT_CHECKER_COMPAT_SHA256 = expected_checker_sha
                frozen_validate = p4_guard_current.validate_p4_current

                def recovery_compatible_p4_validate(
                    candidate_root: Path,
                ) -> list[dict[str, str]]:
                    return [
                        item
                        for item in frozen_validate(candidate_root)
                        if not (
                            item.get("code") == "E_P4_OWNER_EARLY_ADVANCE"
                            and item.get("detail")
                            in {
                                "GATE1_V11_P3_ROUTE_COMPILER_RECOVERY_OWNER",
                                "GATE1_V11_P4_RESEALED_PENDING_OWNER",
                            }
                        )
                    ]

                p4_guard_current.validate_p4_current = (
                    recovery_compatible_p4_validate
                )

            if p4_guard_current.selftest(root) != 0:
                failures.append(
                    {
                        "case": "p4_negative_tamper_suite",
                        "expected": "return 0",
                        "actual": "nonzero",
                    }
                )
        except (ImportError, OSError, TypeError, ValueError) as exc:
            failures.append(
                {
                    "case": "p4_negative_tamper_suite",
                    "expected": "import and return 0",
                    "actual": str(exc),
                }
            )
    if (root / P3_RECOVERY_TASK_ROOT).exists() and not (
        root / P4_AUTHOR_RECOVERY_TASK_ROOT
    ).exists():
        recovery_root = root / P3_RECOVERY_TASK_ROOT
        if str(recovery_root) not in sys.path:
            sys.path.insert(0, str(recovery_root))
        try:
            from p3_recovery_guard import selftest as p3_recovery_selftest

            if p3_recovery_selftest(root) != 0:
                failures.append(
                    {
                        "case": "p3_recovery_negative_tamper_suite",
                        "expected": "return 0",
                        "actual": "nonzero",
                    }
                )
        except (ImportError, OSError, TypeError, ValueError) as exc:
            failures.append(
                {
                    "case": "p3_recovery_negative_tamper_suite",
                    "expected": "import and return 0",
                    "actual": str(exc),
                }
            )
    if (root / P4_RESEALED_TASK_ROOT).exists() and not (
        root / P4_AUTHOR_RECOVERY_TASK_ROOT
    ).exists():
        successor_root = root / P4_RESEALED_TASK_ROOT
        if str(successor_root) not in sys.path:
            sys.path.insert(0, str(successor_root))
        try:
            from p4_resealed_guard import selftest as p4_resealed_selftest

            if p4_resealed_selftest(root) != 0:
                failures.append(
                    {
                        "case": "p4_resealed_negative_tamper_suite",
                        "expected": "return 0",
                        "actual": "nonzero",
                    }
                )
        except (ImportError, OSError, TypeError, ValueError) as exc:
            failures.append(
                {
                    "case": "p4_resealed_negative_tamper_suite",
                    "expected": "import and return 0",
                    "actual": str(exc),
                }
            )
    if (root / P4_AUTHOR_RECOVERY_TASK_ROOT).exists():
        successor_root = root / P4_AUTHOR_RECOVERY_TASK_ROOT
        if str(successor_root) not in sys.path:
            sys.path.insert(0, str(successor_root))
        try:
            import recovery_guard

            install_public_foundation_recovery_handoff(recovery_guard)
            if recovery_guard.selftest(root) != 0:
                failures.append(
                    {
                        "case": "p4_author_recovery_negative_tamper_suite",
                        "expected": "return 0",
                        "actual": "nonzero",
                    }
                )
        except (ImportError, OSError, TypeError, ValueError) as exc:
            failures.append(
                {
                    "case": "p4_author_recovery_negative_tamper_suite",
                    "expected": "import and return 0",
                    "actual": str(exc),
                }
            )
    if failures:
        print(
            json.dumps(
                {"status": "SELFTEST_FAIL", "failures": failures}, ensure_ascii=False
            )
        )
        return 1
    print(
        json.dumps(
            {
                "status": "SELFTEST_PASS",
                "negative_case_count": len(tests) + 1,
                "unauthorized_write_surface_rejected": True,
                "review_decision_creation_rejected": True,
                "readiness_flip_rejected": True,
                "route_actual_leakage_rejected": True,
                "same_reviewer_identity_rejected": True,
                "missing_scoring_contract_rejected": True,
                "p1b_negative_tamper_suite_passed": (
                    root / P1B_MATERIALIZER_PATH
                ).exists(),
                "p4_negative_tamper_suite_passed": (root / P4_TASK_ROOT).exists(),
                "p3_recovery_negative_tamper_suite_passed": (
                    root / P3_RECOVERY_TASK_ROOT
                ).exists(),
                "p4_resealed_negative_tamper_suite_passed": (
                    root / P4_RESEALED_TASK_ROOT
                ).exists(),
                "p4_author_recovery_negative_tamper_suite_passed": (
                    root / P4_AUTHOR_RECOVERY_TASK_ROOT
                ).exists(),
            },
            ensure_ascii=False,
        )
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        return selftest(ROOT)
    errors = validate(ROOT)
    if errors:
        print(json.dumps({"status": "FAIL", "errors": errors}, ensure_ascii=False))
        return 1
    owner = load_yaml(ROOT / CURRENT_OWNER_PATH).get("current_gate1_owner", {})
    owner_id = owner.get("owner_id")
    print(
        json.dumps(
            {
                "status": "PASS",
                "task_id": owner.get("task_id"),
                "p3_final_validated": owner_id
                in {
                    "GATE1_V11_P3_OPEN_PROBE_FINAL_OWNER",
                    "GATE1_V11_P4_AUTHOR_OUTPUT_RECOVERY_OPEN_OWNER",
                    "GATE1_V11_P4_THIRD_SEALED_OWNER",
                },
                "p2_historical_integrity_validated": owner_id
                in {
                    "GATE1_V11_P2_FINAL_OWNER",
                    "GATE1_V11_P3_OPEN_PROBE_FINAL_OWNER",
                    "GATE1_V11_P4_AUTHOR_OUTPUT_RECOVERY_OPEN_OWNER",
                    "GATE1_V11_P4_THIRD_SEALED_OWNER",
                },
                "shared_horizon_modified": False,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

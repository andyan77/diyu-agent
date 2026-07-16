#!/usr/bin/env python3
"""搬迁链机械验证器：B_LIFT→B_DELIVERY 可执行树同一性、新增面限制、
依赖方向（B 不 import A / 产品不引用源仓）、denylist 前缀、clean-room 环境。

真源：B_LIFT_CHAIN_CONTRACT.v1.json + PRODUCT_BOUNDARY_CONTRACT.v1.md。
M1 只以合成清单/合成树运行负向测试，不接触真实产品仓。
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

DC = Path(__file__).resolve().parents[1]

DEFAULT_ADDITION_ALLOWLIST = (
    "assets/positive_240/", "assets/route_60/", "assets/manifests/",
    "audit_metadata/")

PRODUCT_A_IMPORT_PATTERNS = (
    re.compile(r"^\s*import\s+eval_audit_spine", re.M),
    re.compile(r"^\s*from\s+eval_audit_spine", re.M),
    re.compile(r"^\s*import\s+spine(\.|\s|$)", re.M),
    re.compile(r"^\s*from\s+spine(\.|\s)", re.M),
)
SOURCE_REPO_PATH_PATTERNS = (
    re.compile(r"controlled_content_generator_v2_001/"),
    re.compile(r"/home/diyu/worktrees/gate1-longrun-001"),
    re.compile(r"笛语领域通用数据库"),
)


def check_executable_tree_identity(
        b_lift_manifest: dict[str, str], b_delivery_manifest: dict[str, str],
        addition_allowlist: tuple[str, ...] = DEFAULT_ADDITION_ALLOWLIST
) -> list[str]:
    """输入两份 {path: sha256}；返回违规清单。"""
    violations: list[str] = []
    for path, digest in b_lift_manifest.items():
        if path not in b_delivery_manifest:
            violations.append(f"executable file removed in B_DELIVERY: {path}")
        elif b_delivery_manifest[path] != digest:
            violations.append(f"executable file modified in B_DELIVERY: {path}")
    for path in b_delivery_manifest:
        if path in b_lift_manifest:
            continue
        if not any(path.startswith(prefix) for prefix in addition_allowlist):
            violations.append(
                f"addition outside allowlist (not asset/manifest/audit): {path}")
    return violations


def check_post_e9_immutability(delivery_manifest: dict[str, str],
                               post_e9_manifest: dict[str, str]) -> list[str]:
    if delivery_manifest != post_e9_manifest:
        changed = sorted(set(delivery_manifest.items())
                         ^ set(post_e9_manifest.items()))
        return [f"post-E9 change invalidates qualification: "
                f"{sorted({p for p, _ in changed})[:10]}"]
    return []


def check_dependency_direction(files: dict[str, str],
                               product: str = "B") -> list[str]:
    """files: {path: 文本内容}；B 禁 import A；产品禁引用源仓路径。"""
    violations: list[str] = []
    for path, text in files.items():
        if product == "B":
            for pattern in PRODUCT_A_IMPORT_PATTERNS:
                if pattern.search(text):
                    violations.append(f"product B imports product A: {path}")
                    break
        for pattern in SOURCE_REPO_PATH_PATTERNS:
            if pattern.search(text):
                violations.append(f"source-repo path reference: {path}")
                break
    return violations


def check_no_source_history(export_tree_paths: list[str]) -> list[str]:
    """产品候选树内出现 .git 历史 = 源仓历史带出。"""
    return [f"git history object in product candidate: {p}"
            for p in export_tree_paths
            if p == ".git" or p.startswith(".git/") or "/.git/" in p]


def check_denylist_prefixes(export_tree_paths: list[str],
                            denylist_prefixes: list[str] | None = None
                            ) -> list[str]:
    if denylist_prefixes is None:
        denylist = json.loads((DC / "contracts/DOMAIN_DATA_DENYLIST.v1.json"
                               ).read_text(encoding="utf-8"))
        denylist_prefixes = denylist["denied_path_prefixes"]
    return [f"denied domain data in export tree: {p}"
            for p in export_tree_paths
            if any(p.startswith(prefix) for prefix in denylist_prefixes)]


def check_clean_room_env(env: dict[str, str], sys_paths: list[str],
                         installed_editable_links: list[str]) -> list[str]:
    """clean-room 环境判据：无源仓路径、无宿主缓存借用、无 editable 包。"""
    violations: list[str] = []
    for key, value in env.items():
        for pattern in SOURCE_REPO_PATH_PATTERNS:
            if pattern.search(str(value)):
                violations.append(f"env carries source-repo path: {key}")
                break
    if env.get("PYTHONPATH"):
        violations.append("PYTHONPATH not empty in clean-room")
    for path in sys_paths:
        for pattern in SOURCE_REPO_PATH_PATTERNS:
            if pattern.search(path):
                violations.append(f"sys.path carries source-repo path: {path}")
                break
    for link in installed_editable_links:
        violations.append(f"editable install present: {link}")
    for key in ("PIP_CACHE_DIR", "NPM_CONFIG_CACHE"):
        value = env.get(key, "")
        if value and "clean_room" not in value and "cleanroom" not in value:
            violations.append(f"host cache borrowed: {key}={value}")
    return violations


def check_rights_clearance_gate(clearance: dict) -> list[str]:
    """清权回执缺失或未闭合 = 交付出口不过。"""
    if not clearance:
        return ["rights clearance receipt absent -> delivery gate closed"]
    rows = clearance.get("rows", [])
    blocked = [row for row in rows if row.get("status") == "BLOCKED"]
    missing = [row for row in rows if row.get("status")
               not in ("CLEARED", "N/A", "BLOCKED")]
    violations = []
    if clearance.get("RIGHTS_CLEARANCE_CLOSED") is not True:
        violations.append("RIGHTS_CLEARANCE_CLOSED != true")
    if blocked:
        violations.append(f"blocked rights rows: {len(blocked)}")
    if missing:
        violations.append(f"unfilled rights rows: {len(missing)}")
    if not clearance.get("independent_review_receipt"):
        violations.append("rights clearance lacks independent review receipt")
    return violations


def selftest() -> int:
    failures: list[str] = []

    def expect(name: str, cond: bool) -> None:
        print(f"[{'ok' if cond else 'FAIL'}] lift_chain_selftest:{name}")
        if not cond:
            failures.append(name)

    lift = {"app/generator.py": "a" * 64, "app/gates.py": "b" * 64,
            "tests/test_suite.py": "c" * 64, "requirements.lock": "d" * 64}
    delivery_ok = dict(lift)
    delivery_ok["assets/positive_240/item_001.json"] = "e" * 64
    delivery_ok["assets/manifests/asset_manifest.json"] = "f" * 64
    delivery_ok["audit_metadata/e8_run.json"] = "9" * 64
    expect("legal_delivery_additions_clean",
           check_executable_tree_identity(lift, delivery_ok) == [])

    tampered = dict(delivery_ok)
    tampered["app/gates.py"] = "0" * 64
    expect("executable_modification_detected",
           any("modified" in v for v in
               check_executable_tree_identity(lift, tampered)))

    smuggled = dict(delivery_ok)
    smuggled["app/new_feature.py"] = "1" * 64
    expect("non_asset_addition_detected",
           any("outside allowlist" in v for v in
               check_executable_tree_identity(lift, smuggled)))

    post_e9 = dict(delivery_ok)
    post_e9["requirements.lock"] = "2" * 64
    expect("post_e9_change_invalidates",
           check_post_e9_immutability(delivery_ok, post_e9) != [])
    expect("post_e9_unchanged_clean",
           check_post_e9_immutability(delivery_ok, dict(delivery_ok)) == [])

    expect("b_imports_a_detected",
           any("imports product A" in v for v in check_dependency_direction(
               {"app/x.py": "from spine.cost import metering_report\n"})))
    expect("source_path_reference_detected",
           any("source-repo path" in v for v in check_dependency_direction(
               {"conf.py": "ROOT='/home/diyu/worktrees/gate1-longrun-001'\n"})))
    expect("clean_code_passes",
           check_dependency_direction(
               {"app/x.py": "import json\nfrom app import gates\n"}) == [])

    expect("git_history_in_candidate_detected",
           check_no_source_history([".git/objects/aa/bb", "app/x.py"]) != [])
    expect("denylist_prefix_detected",
           check_denylist_prefixes(
               ["controlled_content_generator_v2_001/gate1_v1_1_001/"
                "p7_successor_longrun_001/pkg1_open_regression/round5/x.jsonl"])
           != [])

    dirty_env = {"PYTHONPATH": "/home/diyu/worktrees/gate1-longrun-001",
                 "PIP_CACHE_DIR": "/home/faye/.cache/pip"}
    violations = check_clean_room_env(dirty_env, ["/usr/lib/python3"], [])
    expect("dirty_clean_room_detected",
           any("PYTHONPATH" in v for v in violations)
           and any("cache" in v for v in violations))
    expect("editable_install_detected",
           check_clean_room_env({}, [], ["src.egg-link"]) != [])
    expect("clean_env_passes", check_clean_room_env(
        {"PATH": "/usr/bin"}, ["/opt/venv/lib"], []) == [])

    expect("missing_rights_clearance_blocks_delivery",
           check_rights_clearance_gate({}) != [])
    expect("blocked_rights_row_blocks_delivery",
           check_rights_clearance_gate({
               "RIGHTS_CLEARANCE_CLOSED": True,
               "independent_review_receipt": "r.json",
               "rows": [{"status": "BLOCKED"}]}) != [])
    expect("closed_rights_clearance_passes",
           check_rights_clearance_gate({
               "RIGHTS_CLEARANCE_CLOSED": True,
               "independent_review_receipt": "r.json",
               "rows": [{"status": "CLEARED"}, {"status": "N/A"}]}) == [])

    print("LIFT_CHAIN_SELFTEST:", "ALL_PASS" if not failures
          else f"FAILED {failures}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else 2)

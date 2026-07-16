#!/usr/bin/env python3
"""GATE1_V11_SUCCESSOR_LONGRUN_001 唯一任务内总检查入口。

按源指令 §8：本任务只建这一个总检查入口及其自测，不为每个执行包新造平行检查器。
各检查节（section）随执行包推进逐步注册；每节返回 (passed, details)。

用法:
    python3 p7_master_check.py                 # 跑全部已注册节
    python3 p7_master_check.py --section NAME  # 只跑指定节
    python3 p7_master_check.py --list          # 列出节

退出码: 全部通过=0；任一失败=1。输出为确定性文本（重复运行零差异）。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

# 仓库根 = 本文件向上 4 层 (p7/checker/ -> p7 -> gate1 -> ccg_v2 -> root)
DEFAULT_ROOT = Path(__file__).resolve().parents[4]

GATE1 = "controlled_content_generator_v2_001/gate1_v1_1_001"
P7 = f"{GATE1}/p7_successor_longrun_001"
G3 = "controlled_content_generator_v2_001/generator_v3_successor_001"
EVAL_SPINE = f"{P7}/eval_audit_spine_001"
V4_RECOVERY = f"{G3}/v4_recovery"
DC = f"{P7}/delivery_control_001"

# v2.5 状态感知检查内部模块（P1 §十七：唯一总入口可拆内部模块，非平行检查器）
import importlib.util as _importlib_util

_v25_spec = _importlib_util.spec_from_file_location(
    "v25_state_checks", Path(__file__).resolve().parent / "v25_state_checks.py")
v25 = _importlib_util.module_from_spec(_v25_spec)
assert _v25_spec.loader is not None
_v25_spec.loader.exec_module(v25)

# 运行上下文：main() 依 CLI 设置。checker 只从磁盘复算，不修改任何阶段状态，
# 也不给自身实现签字（正式签字仅来自独立审核者的 signer_receipt）。
CTX: dict[str, object] = {"milestone": "M1", "mode": "PRE_REVIEW",
                          "state_file": None}

ALLOWED_WRITE_PREFIXES = (P7 + "/", G3 + "/")

BASELINE_COMMIT = "b4c40beb509d81db30b497abf38af1da6dc797da"

# 执行包1各正式轮证据的冻结提交（历史轮字节完整性锚点；新轮证据提交后在此登记）。
# 轮次语义：模块/指令随轮演进是修复协议的合法部分；历史轮的复现性由其冻结提交
# 保证（在该提交处代码+证据同锚），检查器对历史轮做字节完整性、对最新轮做对盘校验。
PKG1_ROUND_FREEZE_COMMITS = {
    1: "c2e5b91a6da72fdf74a8b90edd8e494eaf9b31fc",
    2: "eba66ac3ede5dc9b4820efc5310a6e084d22671a",
    3: "cee8ad8af85491ad7a78a40018339b401f581da7",
}

# 核心口径（源指令 §1，不得改变）
CORE_CALIBER = {"total": 300, "positive": 240, "abnormal": 60,
                "reference_stock": 120, "historical_component_stock": 86}

# 任务级受保护文件基线（除 frozen_inputs 18 锚点与 p5_p6 全树清单外的追加监护）
EXTRA_PROTECTED = {
    f"{GATE1}/p2_component_supply_and_generator_core_repair_001/component/historical_86_successor_dispositions.v0.1.jsonl":
        ("77570bcb2840839c8387e8fafa9ff80707c2f9892016c0fa6c652263ec989af3", 86),
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_yaml_pairs(text: str) -> list[tuple[str, str]]:
    """从 frozen_inputs.v1.1.yaml 提取 (path, sha256) 对（无第三方依赖的窄解析）。"""
    import re
    return re.findall(r"path: (\S+)\n\s+sha256: ([0-9a-f]{64})", text)


# ---------------------------------------------------------------- sections

def check_freeze_integrity(root: Path) -> tuple[bool, list[str]]:
    """冻结输入摘要和受保护文件未漂移；120/86 记录数不变。"""
    details: list[str] = []
    ok = True
    fi = root / P7 / "freeze" / "frozen_inputs.v1.1.yaml"
    if not fi.is_file():
        return False, ["frozen_inputs.v1.1.yaml missing"]
    pairs = _read_yaml_pairs(fi.read_text(encoding="utf-8"))
    anchors = [(p, s) for p, s in pairs if "p7_successor_longrun_001" not in p]
    manifest = [(p, s) for p, s in pairs if p.endswith("p5_p6_full_tree_manifest.v1.1.tsv")]
    if len(anchors) != 18:
        ok = False
        details.append(f"expected 18 anchors in frozen_inputs, got {len(anchors)}")
    for rel, expected in anchors:
        f = root / rel
        if not f.is_file():
            ok = False
            details.append(f"MISSING anchor {rel}")
            continue
        actual = sha256_file(f)
        if actual != expected:
            ok = False
            details.append(f"DRIFT anchor {rel}: {actual[:12]} != {expected[:12]}")
    # p5_p6 全树逐文件比对
    for rel, expected in manifest:
        mf = root / rel
        if not mf.is_file():
            ok = False
            details.append(f"MISSING manifest {rel}")
            continue
        if sha256_file(mf) != expected:
            ok = False
            details.append("DRIFT manifest file itself changed")
        base = root / GATE1
        for line in mf.read_text(encoding="utf-8").splitlines():
            digest, size, path = line.split("\t")
            f = base / path
            if not f.is_file():
                ok = False
                details.append(f"MISSING p5_p6 file {path}")
            elif sha256_file(f) != digest:
                ok = False
                details.append(f"DRIFT p5_p6 file {path}")
    # 追加监护（86 历史候选）
    for rel, (expected, expected_lines) in EXTRA_PROTECTED.items():
        f = root / rel
        if not f.is_file():
            ok = False
            details.append(f"MISSING protected {rel}")
            continue
        if sha256_file(f) != expected:
            ok = False
            details.append(f"DRIFT protected {rel}")
        n = sum(1 for _ in open(f, encoding="utf-8"))
        if n != expected_lines:
            ok = False
            details.append(f"protected {rel} line count {n} != {expected_lines}")
    # 120 记录数（文件本身已在 18 锚点内比对过摘要；此处再验记录数口径）
    ref120 = root / GATE1 / ("p1b_signed_review_closeout_and_baseline_freeze_001"
                             "/content/reference_120_final_dispositions.v0.1.jsonl")
    if ref120.is_file():
        n = sum(1 for _ in open(ref120, encoding="utf-8"))
        if n != CORE_CALIBER["reference_stock"]:
            ok = False
            details.append(f"reference_120 line count {n} != 120")
    details.append(f"anchors_checked={len(anchors)} manifest_files_checked="
                   f"{sum(1 for rel, _ in manifest for _ in (root / rel).read_text(encoding='utf-8').splitlines()) if manifest else 0}")
    return ok, details


def check_write_surface(root: Path) -> tuple[bool, list[str]]:
    """任务分支相对基线的全部改动都落在允许写入面内。"""
    r = subprocess.run(
        ["git", "-C", str(root), "diff", "--name-only", f"{BASELINE_COMMIT}..HEAD"],
        capture_output=True, text=True, check=True)
    changed = [l for l in r.stdout.splitlines() if l.strip()]
    offenders = [p for p in changed if not p.startswith(ALLOWED_WRITE_PREFIXES)]
    details = [f"files_changed_since_baseline={len(changed)}"]
    if offenders:
        details += [f"OUT_OF_SURFACE {p}" for p in offenders]
    # 未提交改动同样必须在面内
    r2 = subprocess.run(["git", "-C", str(root), "status", "--porcelain"],
                        capture_output=True, text=True, check=True)
    dirty = [l[3:].strip() for l in r2.stdout.splitlines() if l.strip()]
    dirty_off = [p for p in dirty
                 if not (p.startswith(ALLOWED_WRITE_PREFIXES)
                         or (p.endswith("/") and p.rstrip("/").startswith(ALLOWED_WRITE_PREFIXES[0].rstrip("/"))
                         ) or any(p.rstrip("/") + "/" == a or p.startswith(a) for a in ALLOWED_WRITE_PREFIXES))]
    if dirty_off:
        details += [f"DIRTY_OUT_OF_SURFACE {p}" for p in dirty_off]
    return not offenders and not dirty_off, details


def check_external_workspaces(root: Path) -> tuple[bool, list[str]]:
    """三个外部工作区没有被本任务写入（外部并行变化如实分类，不算失败）。

    判定逻辑：本任务的全部写入都经由本工作区 git 历史与工作树；
    外部工作区只做只读观察并记录当前状态供交付对照。
    """
    details: list[str] = []
    ok = True
    externals = {
        "original_main": "/home/diyu/笛语领域通用数据库",
        "quality_evidence": "/home/diyu/worktrees/gate1-v1-1-300-quality-baseline",
        "public_foundation": "/home/diyu/worktrees/diyu-public-foundation-001",
    }
    for name, path in externals.items():
        p = Path(path)
        if not p.is_dir():
            details.append(f"{name}: NOT_PRESENT")
            continue
        r = subprocess.run(["git", "-C", path, "rev-parse", "HEAD"],
                           capture_output=True, text=True)
        head = r.stdout.strip()[:12] if r.returncode == 0 else "ERR"
        r2 = subprocess.run(["git", "-C", path, "status", "--porcelain"],
                            capture_output=True, text=True)
        dirty_all = [l for l in r2.stdout.splitlines() if l.strip()]
        # 本任务写入面的路径若出现在外部工作区改动中 → 越界证据
        breach = [l for l in dirty_all
                  if l[3:].startswith(ALLOWED_WRITE_PREFIXES)
                  and name != "original_main"]  # 原主工作区的 P7 v1.0 草案是任务前既有的用户文件
        if name == "original_main":
            # 原主工作区允许存在任务前既有的未跟踪 P7 草案；只有"跟踪文件被改"才算破口
            tracked = subprocess.run(["git", "-C", path, "diff", "--name-only", "HEAD"],
                                     capture_output=True, text=True)
            breach = [l for l in tracked.stdout.splitlines() if l.strip()]
        if breach:
            ok = False
            details.append(f"{name}: WRITE_BREACH {breach[:5]}")
        details.append(f"{name}: head={head} external_parallel_changes={len(dirty_all)}")
    return ok, details


def check_core_caliber(root: Path) -> tuple[bool, list[str]]:
    """300、120、86 口径未被改变（合同文本仍声明同一口径）。"""
    details: list[str] = []
    contract = root / P7 / "contract" / "longrun_execution_contract.v1.1.md"
    if not contract.is_file():
        return False, ["contract v1.1 missing"]
    text = contract.read_text(encoding="utf-8")
    ok = ("300: 240条批准正向内容 + 60条异常处置案例" in text
          and "120: 已冻结历史参考内容库存" in text
          and "86: 历史组件候选库存" in text)
    if not ok:
        details.append("core caliber declaration drifted in contract v1.1")
    details.append("caliber=300/120/86 declared_intact=" + str(ok).lower())
    return ok, details


# ---------------------------------------------------------------- pure helpers
# （供节与反向自测共用；反向自测用合成输入证明检查会失败）

def surface_offenders(paths: list[str]) -> list[str]:
    return [p for p in paths if not p.startswith(ALLOWED_WRITE_PREFIXES)]


def blind_leak_offenders(texts: list[str]) -> list[str]:
    import re
    leak_re = re.compile(
        r"\bCP(?:0[1-9]|1\d|20)\b|G1V11|G3-POS|G3-CUR|甲级|乙级|"
        r"岗位任务VLOG|门店时段微纪录|专业判断切片|用户问题诊断室")
    return sorted({m.group(0) for t in texts for m in [leak_re.search(t)] if m})


def role_collision_offenders(authors: set[str], reviewers: set[str]) -> list[str]:
    return sorted(authors & reviewers)


def denominator_ok(request_count: int, metrics_output_count: int,
                   retained_failed_count: int, acceptable: int) -> bool:
    return (metrics_output_count == request_count
            and retained_failed_count == request_count - acceptable)


def route_gold_ok(root: Path) -> bool:
    gold = root / GATE1 / ("p1b_signed_review_closeout_and_baseline_freeze_001"
                           "/route/route_60_gold_answers.v0.1.jsonl")
    return (gold.is_file() and sha256_file(gold)
            == "f87d984d1780423e7ace0d78c54ba40e97ab5b48c39950f691c7ffca6652e054")


# ---------------------------------------------------------------- pkg sections

def check_g3_selftest(root: Path) -> tuple[bool, list[str]]:
    """G3 单元与反向测试（26 检查含 12 篡改案例）必须全绿。"""
    r = subprocess.run(
        ["python3", str(root / "controlled_content_generator_v2_001"
                        "/generator_v3_successor_001/tests/test_g3.py")],
        capture_output=True, text=True)
    ok = r.returncode == 0 and "ALL" in r.stdout and "PASSED" in r.stdout
    tail = [l for l in r.stdout.splitlines() if l.startswith("ALL")]
    return ok, tail or [r.stdout[-200:], r.stderr[-200:]]


def check_eval_spine_selftest(root: Path) -> tuple[bool, list[str]]:
    """评测脊柱反向测试全绿；通过只证明实现完整，不代表 M0 资格通过。"""
    test_dir = root / EVAL_SPINE / "tests"
    if not test_dir.is_dir():
        return False, ["eval spine selftest directory missing"]
    r = subprocess.run(
        ["python3", "-m", "unittest", "discover", str(test_dir),
         "-p", "test_*.py"],
        capture_output=True, text=True, cwd=str(root))
    combined = r.stdout + r.stderr
    ok = r.returncode == 0 and "OK" in combined
    ran = next((line.strip() for line in combined.splitlines()
                if line.strip().startswith("Ran ")), "Ran ?")
    return ok, [ran, "scope=artifact_integrity_not_m0_qualification"]


def check_v4_recovery_selftest(root: Path) -> tuple[bool, list[str]]:
    """后继生成器的单一测试分配、首稿与全批门反向测试。"""
    test = root / V4_RECOVERY / "tests/test_v4_recovery.py"
    if not test.is_file():
        return False, ["v4 recovery selftest missing"]
    r = subprocess.run(["python3", str(test)], capture_output=True, text=True,
                       cwd=str(root))
    combined = r.stdout + r.stderr
    ok = r.returncode == 0 and ("OK" in combined or "ALL" in combined)
    ran = next((line.strip() for line in combined.splitlines()
                if line.strip().startswith("Ran ") or line.strip().startswith("ALL")),
               "Ran ?")
    return ok, [ran, "historical_g3_modules_untouched=true"]


def check_m0_state_integrity(root: Path) -> tuple[bool, list[str]]:
    """M0 实际态一致性不变量 + 里程碑期望比较（v2.5 §五 状态感知化迁移）。

    v1 语义把 NOT_QUALIFIED/零案例/预算 UNAPPROVED 钉死为唯一通过态，导致
    合法未来状态（金标物化、M0 合格、拨付发生）反而 FAIL——已按阶段参数化
    期望改造；诚实性由一致性不变量（QUALIFIED 必须带证据/裁决、空集不得带
    摘要、NOT_QUALIFIED 必须保留禁用主张）承担，不再靠冻结常量。"""
    return v25.check_m0_state_integrity(root, CTX)


def check_m0_dataset_isolation(root: Path) -> tuple[bool, list[str]]:
    """两轴六分区、来源组不可拆及隐藏公开面合同存在；空集不冒充资格集。"""
    policy_path = root / EVAL_SPINE / "contract/data_isolation.v1.json"
    schema_path = root / EVAL_SPINE / "schema/dataset_manifest.v1.schema.json"
    if not policy_path.is_file() or not schema_path.is_file():
        return False, ["dataset isolation contract/schema missing"]
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    model = policy.get("statistical_partition_model", {})
    origins = model.get("case_origin_axis", [])
    partitions = model.get("visibility_partition_axis", [])
    cells = model.get("six_cells", [])
    required = schema.get("required", [])
    ok = (origins == ["NATURAL", "CHALLENGE"]
          and partitions == ["DEVELOPMENT", "VALIDATION", "HIDDEN"]
          and len(cells) == 6 and len(set(cells)) == 6
          and model.get("source_group_is_indivisible_across_visibility_partitions") is True
          and model.get("natural_and_challenge_metrics_must_not_be_pooled") is True
          and {"case_origin", "visibility_partition", "source_group_id"}.issubset(required))
    return ok, [f"statistical_cells={len(cells)}",
                "case_origin_and_visibility_are_independent=true",
                "hidden_payload_materialized=false"]


def check_stage_contract_v2(root: Path) -> tuple[bool, list[str]]:
    """阶段合同 v2：Y 三状态机、B 轨独立、S3 诊断门、S6 记账入口、旧预算键零残留。

    取代 v1 的 check_budget_stage_gate（其把预算 UNAPPROVED 与 B 轨不得越过 S2
    钉死为通过条件——拨付制落地或 B 轨合法推进即整体 FAIL 的 N4 位点）。"""
    return v25.check_stage_contract_v2(root, CTX)


def check_cost_accounting(root: Path) -> tuple[bool, list[str]]:
    """拨付制记账合同 + 保留面（24 字段、DeepSeek 30 元/日）+ 运行时符号迁移。"""
    return v25.check_cost_accounting_contract(root, CTX)


def check_active_contract_set(root: Path) -> tuple[bool, list[str]]:
    """ACTIVE_CONTRACT_SET 成员摘要复算；冻结清单存在时逐成员比对。"""
    return v25.check_active_contract_set(root, CTX)


def check_d0_status(root: Path) -> tuple[bool, list[str]]:
    """D0 五条件从磁盘复算；布尔速记宣布已批准 = FAIL。"""
    return v25.check_d0_status(root, CTX)


def check_run_journal(root: Path) -> tuple[bool, list[str]]:
    """RUN_JOURNAL 哈希链复算 + 与 Git 互校。"""
    return v25.check_run_journal(root, CTX)


def check_final_receipts(root: Path) -> tuple[bool, list[str]]:
    """FINAL 模式硬门：typed 终态回执 + 两份有效独立签字绑定同一候选。"""
    return v25.check_final_receipts(root, CTX)


def check_candidate_manifest(root: Path) -> tuple[bool, list[str]]:
    """候选清单必须覆盖并精确绑定当前实现，审核/证据自身不参与递归摘要。"""
    manifest_path = root / EVAL_SPINE / "release/candidate_manifest.v1.json"
    if not manifest_path.is_file():
        return False, ["candidate manifest missing"]
    eval_dir = root / EVAL_SPINE
    sys.path.insert(0, str(eval_dir))
    try:
        from spine.manifest import verify_candidate_manifest
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        result = verify_candidate_manifest(root, manifest)
    except (OSError, ValueError, TypeError) as exc:
        return False, [f"candidate_manifest_invalid:{type(exc).__name__}"]
    finally:
        if sys.path and sys.path[0] == str(eval_dir):
            sys.path.pop(0)
    return bool(result.get("passed")), [
        f"candidate_entry_count={manifest.get('entry_count')}",
        f"candidate_manifest_digest={manifest.get('manifest_digest')}",
        *[str(error) for error in result.get("errors", [])],
    ]


def check_independent_reviews(root: Path) -> tuple[bool, list[str]]:
    """两份独立审核必须绑定同一实现提交与同一候选清单摘要。"""
    review_dir = root / EVAL_SPINE / "review"
    request = review_dir / "IMPLEMENTATION_REVIEW_REQUEST.v1.md"
    manifest_path = root / EVAL_SPINE / "release/candidate_manifest.v1.json"
    if not request.is_file():
        return False, ["implementation review request missing"]
    reports = sorted(review_dir.glob("*.review.v1.json"))
    if not reports:
        status_path = root / EVAL_SPINE / "calibration/M0_STATUS.v1.json"
        try:
            actual = json.loads(status_path.read_text(encoding="utf-8")).get(
                "status", "INVALID_STATE")
        except (OSError, ValueError):
            actual = "INVALID_STATE"
        return True, ["PENDING: two independent reviews requested",
                      f"m0_qualification_status={actual}"]
    if len(reports) != 2 or not manifest_path.is_file():
        return False, [f"independent_review_count={len(reports)} expected=2"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    target_digest = manifest.get("manifest_digest")
    rows = [json.loads(path.read_text(encoding="utf-8")) for path in reports]
    errors: list[str] = []
    schema_path = root / EVAL_SPINE / "schema/independent_review.v1.schema.json"
    try:
        from jsonschema import Draft202012Validator
        review_schema = json.loads(schema_path.read_text(encoding="utf-8"))
        validator = Draft202012Validator(review_schema)
        for row, path in zip(rows, reports):
            for error in sorted(validator.iter_errors(row), key=lambda item: list(item.path)):
                errors.append(f"review_schema:{path.name}:{error.message}")
    except (ImportError, OSError, ValueError) as exc:
        errors.append(f"review_schema_validation_unavailable:{type(exc).__name__}")
    identities = {str(row.get("reviewer_identity")) for row in rows}
    roles = {str(row.get("reviewer_role")) for row in rows}
    commits = {str(row.get("target_commit")) for row in rows}
    digests = {str(row.get("target_manifest_digest")) for row in rows}
    if len(identities) != 2:
        errors.append("reviewer_identity_collision")
    if roles != {"METHODOLOGY", "IMPLEMENTATION"}:
        errors.append(f"review_roles={sorted(roles)}")
    if len(commits) != 1:
        errors.append("target_commit_mismatch")
    if digests != {target_digest}:
        errors.append("target_manifest_digest_mismatch")
    target_commit = next(iter(commits)) if len(commits) == 1 else None
    if target_commit:
        commit_exists = subprocess.run(
            ["git", "-C", str(root), "cat-file", "-e", f"{target_commit}^{{commit}}"],
            capture_output=True, text=True).returncode == 0
        if not commit_exists:
            errors.append("target_commit_missing")
        else:
            ancestor = subprocess.run(
                ["git", "-C", str(root), "merge-base", "--is-ancestor", target_commit, "HEAD"],
                capture_output=True, text=True).returncode == 0
            if not ancestor:
                errors.append("target_commit_not_ancestor_of_head")
            for entry in manifest.get("entries", []):
                rel = str(entry.get("path", ""))
                shown = subprocess.run(
                    ["git", "-C", str(root), "show", f"{target_commit}:{rel}"],
                    capture_output=True)
                if shown.returncode != 0:
                    errors.append(f"target_commit_missing_entry:{rel}")
                elif hashlib.sha256(shown.stdout).hexdigest() != entry.get("sha256"):
                    errors.append(f"target_commit_entry_drift:{rel}")
    for row, path in zip(rows, reports):
        attestation = row.get("independence_attestation", {})
        if not isinstance(attestation, dict) or not all(attestation.get(key) is True for key in
                ("did_not_author_reviewed_scope", "did_not_read_peer_review_before_submission",
                 "no_role_collision")):
            errors.append(f"independence_attestation_failed:{path.name}")
        if row.get("final_decision") != "APPROVE_IMPLEMENTATION":
            errors.append(f"review_not_approved:{path.name}")
        if any(value == "FAIL" for value in row.get("gate_decisions", {}).values()):
            errors.append(f"approved_review_contains_failed_gate:{path.name}")
        for finding in row.get("findings", []):
            if (finding.get("severity") in {"P0", "P1"}
                    and finding.get("status") == "OPEN"):
                errors.append(
                    f"approved_review_contains_open_blocker:{path.name}:"
                    f"{finding.get('finding_id')}")
        unsigned = dict(row)
        supplied = unsigned.pop("review_digest", None)
        expected = hashlib.sha256(json.dumps(
            unsigned, ensure_ascii=False, sort_keys=True,
            separators=(",", ":")).encode("utf-8")).hexdigest()
        if supplied != expected:
            errors.append(f"review_digest_mismatch:{path.name}")
    return not errors, ([f"independent_review_count={len(rows)}",
                         f"target_commit={next(iter(commits))}",
                         f"target_manifest_digest={target_digest}"]
                        + sorted(errors))


def check_recovery_shadow_recompute(root: Path) -> tuple[bool, list[str]]:
    """只读复算 R5 的两个结构性缺口：5条旧门漏检、90/120双分配错配。"""
    import importlib.util
    eval_dir = root / EVAL_SPINE
    sys.path.insert(0, str(eval_dir))
    try:
        from spine.runner import r5_shadow_audit
        fixture = eval_dir / "fixtures/r5_known_veto_regression.v1.jsonl"
        shadow = r5_shadow_audit(root, fixture)
    finally:
        if sys.path and sys.path[0] == str(eval_dir):
            sys.path.pop(0)
    allocator_path = root / V4_RECOVERY / "test_allocator.py"
    if not allocator_path.is_file():
        return False, ["v4 recovery allocator missing"]
    v4_parent = root / G3
    sys.path.insert(0, str(v4_parent))
    try:
        spec = importlib.util.spec_from_file_location(
            "v4_recovery.test_allocator", allocator_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)  # type: ignore[union-attr]
        r5 = root / P7 / "pkg1_open_regression/round5"
        mismatch = module.diagnose_legacy_r5_plan_mismatch(
            r5 / "inputs/scenarios.g3.v2.jsonl",
            r5 / "inputs/requests.g3.v1.jsonl")
    finally:
        if sys.path and sys.path[0] == str(v4_parent):
            sys.path.pop(0)
    detected = len(shadow["development_rule_detected_ids"])
    ok = (detected == 5 and shadow["legacy_machine_hard_failure_count"] == 0
          and mismatch["request_count"] == 120 and mismatch["mismatch_count"] == 90
          and mismatch["match_count"] == 30)
    return ok, [f"r5_known_veto_shadow_detected={detected}/5",
                "r5_legacy_machine_known_veto_detected=0/5",
                f"r5_legacy_dual_assignment_mismatch={mismatch['mismatch_count']}/120",
                "qualification_use=false"]


def _pkg1_rounds(root: Path) -> list[tuple[int, Path]]:
    """已物化冻结清单的正式轮列表 [(轮次, 轮目录)]，升序。round1=pkg1 根。"""
    pkg1 = root / P7 / "pkg1_open_regression"
    rounds = []
    if (pkg1 / "inputs/input_freeze.v1.yaml").is_file():
        rounds.append((1, pkg1))
    for d in sorted(pkg1.glob("round[0-9]*")):
        if (d / "inputs/input_freeze.v1.yaml").is_file():
            rounds.append((int(d.name[5:]), d))
    return sorted(rounds)


def history_intact(diff_lines: list[str], status_lines: list[str]) -> bool:
    """历史轮字节完整性判据：对冻结提交零差异 且 无未跟踪/未提交条目。"""
    return not diff_lines and not status_lines


def check_pkg1_input_freeze(root: Path) -> tuple[bool, list[str]]:
    """轮次感知冻结校验：最新轮冻结清单逐摘要对盘（场景基座/本轮请求/作者指令/
    生成器模块 + 分片并集=总文件）；历史轮证据对其冻结提交做字节完整性。"""
    import re as _re
    pkg1 = root / P7 / "pkg1_open_regression"
    rounds = _pkg1_rounds(root)
    if not rounds:
        return True, ["SKIP: not materialized yet"]
    ok = True
    details = []
    # --- 历史轮：对冻结提交零字节漂移（含未跟踪新增） ---
    for rnd, rdir in rounds[:-1]:
        commit = PKG1_ROUND_FREEZE_COMMITS.get(rnd)
        if commit is None:
            ok = False
            details.append(f"round{rnd}: FREEZE COMMIT UNREGISTERED")
            continue
        paths = [str((rdir / p).relative_to(root))
                 for p in ("inputs", "outputs", "review", "result", "route")
                 if (rdir / p).exists()]
        diff = subprocess.run(
            ["git", "diff", "--name-only", commit, "--", *paths],
            capture_output=True, text=True, cwd=str(root))
        status = subprocess.run(
            ["git", "status", "--porcelain", "--", *paths],
            capture_output=True, text=True, cwd=str(root))
        diff_lines = [l for l in diff.stdout.splitlines() if l]
        status_lines = [l for l in status.stdout.splitlines() if l]
        if diff.returncode or status.returncode or not history_intact(
                diff_lines, status_lines):
            ok = False
            details.append(
                f"round{rnd}_HISTORY_TAMPERED {(diff_lines + status_lines)[:4]}")
        else:
            details.append(f"round{rnd}: byte-intact vs {commit[:7]}")
    # --- 最新轮：冻结清单逐摘要对盘 ---
    latest, latest_dir = rounds[-1]
    text = (latest_dir / "inputs/input_freeze.v1.yaml").read_text(encoding="utf-8")
    instruction_ver = {1: "v2.0", 2: "v2.1", 3: "v2.2"}.get(latest, "v2.3")
    instruction = (root / G3
                   / f"contract/g3_author_instruction.{instruction_ver}.md")
    scenarios = (latest_dir / "inputs/scenarios.g3.v2.jsonl" if latest >= 3
                 else pkg1 / "inputs/scenarios.g3.v1.jsonl")
    checks = [("scenarios_sha256", scenarios),
              ("requests_sha256", latest_dir / "inputs/requests.g3.v1.jsonl")]
    if "author_instruction_sha256:" in text:
        checks.append(("author_instruction_sha256", instruction))
    for key, rel in checks:
        m = _re.search(rf"{key}: ([0-9a-f]{{64}})", text)
        if not (m and rel.is_file() and sha256_file(rel) == m.group(1)):
            ok = False
            details.append(f"DRIFT {key}")
    # 模块 SHA：仅当最新轮仍"开放"（判定文件未落盘）时强制与冻结一致——
    # 判定已提交的轮，其复现锚点是冻结提交；此后模块漂移=面向下一轮的合法修复
    round_closed = (latest_dir / f"result/round{latest}_result.v1.yaml").is_file()
    module_drift = []
    for m in _re.finditer(r"  (g3_\w+\.py): ([0-9a-f]{64})", text):
        f = (root / "controlled_content_generator_v2_001"
             / "generator_v3_successor_001" / m.group(1))
        if sha256_file(f) != m.group(2):
            module_drift.append(m.group(1))
    if module_drift:
        if round_closed:
            details.append(f"round{latest} closed; modules evolved toward next"
                           f" round: {len(module_drift)} drifted (anchored by"
                           " freeze commit)")
        else:
            ok = False
            details += [f"DRIFT module {name}" for name in module_drift]
    # 分片并集 = 总文件（最新轮）
    canonical = {l for l in (latest_dir / "inputs/requests.g3.v1.jsonl"
                             ).read_text(encoding="utf-8").splitlines() if l}
    shards = set()
    for shard in sorted((latest_dir / "inputs/requests_by_cp").glob("CP*.jsonl")):
        shards.update(l for l in shard.read_text(encoding="utf-8").splitlines() if l)
    if canonical != shards:
        ok = False
        details.append("shard union != canonical requests")
    details.append(f"round{latest}_requests={len(canonical)}"
                   f" shards_match={canonical == shards}")
    return ok, details


def check_pkg1_route(root: Path) -> tuple[bool, list[str]]:
    """路线60：金标未漂移 + 物化比对与全新重算逐字节一致 + pass 判据成立。"""
    pkg1 = root / P7 / "pkg1_open_regression"
    comparisons = pkg1 / "route/route_comparisons.g3.jsonl"
    if not comparisons.is_file():
        return True, ["SKIP: not materialized yet"]
    if not route_gold_ok(root):
        return False, ["ROUTE GOLD DRIFTED"]
    import importlib.util
    import tempfile
    g3dir = (root / "controlled_content_generator_v2_001"
             / "generator_v3_successor_001")
    sys.path.insert(0, str(g3dir))
    spec = importlib.util.spec_from_file_location(
        "g3_route_driver", g3dir / "g3_route_driver.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    with tempfile.TemporaryDirectory() as tmp:
        result = module.run_route_60(Path(tmp))
        fresh = (Path(tmp) / "route_comparisons.g3.jsonl").read_bytes()
    ok = fresh == comparisons.read_bytes() and result["pass"]
    return ok, [f"recompute_identical={fresh == comparisons.read_bytes()}",
                f"pass={result['pass']} action={result['action_match_count']}"
                f" reason={result['reason_match_count']}"]


def check_pkg1_blind(root: Path) -> tuple[bool, list[str]]:
    """盲审包零标签泄漏 + 映射双射 + 包与首输出一一对应（最新已物化盲包的轮）。"""
    pkg1 = root / P7 / "pkg1_open_regression"
    rounds = _pkg1_rounds(root) or [(1, pkg1)]
    with_packet = [(n, d) for n, d in rounds
                   if (d / "review/blind/neutral_packet.v1.jsonl").is_file()]
    if not with_packet:
        return True, ["SKIP: not materialized yet"]
    rnd, rdir = with_packet[-1]
    pkg1 = rdir
    packet = pkg1 / "review/blind/neutral_packet.v1.jsonl"
    rows = [json.loads(l) for l in packet.read_text(encoding="utf-8").splitlines() if l]
    leaks = []
    for row in rows:
        texts = [row["title"], *row["body"], *row["spoken_lines"], row["cta"],
                 *row["visual_execution"], *row["audio_execution"]]
        leaks += blind_leak_offenders([str(t) for t in texts])
    mapping = [json.loads(l) for l in
               (pkg1 / "review/blind/neutral_mapping.v1.jsonl"
                ).read_text(encoding="utf-8").splitlines() if l]
    neutral_ids = [r["neutral_id"] for r in mapping]
    request_ids = [r["request_id"] for r in mapping]
    bijection = (len(set(neutral_ids)) == len(neutral_ids)
                 and len(set(request_ids)) == len(request_ids)
                 and len(mapping) == len(rows))
    ok = not leaks and bijection
    return ok, [f"round={rnd} items={len(rows)}"
                f" leaks={sorted(set(leaks))} bijection={bijection}"]


def check_pkg1_reviews(root: Path) -> tuple[bool, list[str]]:
    """轮次感知审查校验（对最新已出指标的轮）：角色碰撞=0；分母完整；
    指标重算一致——现行轮用现行模块重算（非破坏：先快照、错则还原判 FAIL）；
    历史轮指标的完整性由 pkg1_input_freeze 节的冻结提交锚点担保，此处不重算。"""
    import os as _os
    pkg1 = root / P7 / "pkg1_open_regression"
    rounds = _pkg1_rounds(root)
    live = [(n, d) for n, d in rounds
            if (d / f"result/round{n}_metrics.v1.json").is_file()]
    if not live:
        return True, ["SKIP: not materialized yet"]
    n, rdir = live[-1]
    latest_freeze_round = rounds[-1][0]
    metrics_file = rdir / f"result/round{n}_metrics.v1.json"
    metrics = json.loads(metrics_file.read_text(encoding="utf-8"))
    requests = [json.loads(l) for l in
                (rdir / "inputs/requests.g3.v1.jsonl"
                 ).read_text(encoding="utf-8").splitlines() if l]
    authors = set()
    for r in requests:
        pool = r["author_identity"]
        authors.update(map(str, pool if isinstance(pool, list) else [pool]))
    reviewers: set[str] = set()
    for f in sorted((rdir / "review").glob("*_review.*.jsonl")):
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.strip():
                reviewers.add(str(json.loads(line).get("reviewer_identity")))
    collisions = role_collision_offenders(authors, reviewers)
    denominator = (metrics["output_count"] == len(requests)
                   and len(metrics["failed_ids_retained_in_denominator"])
                   == metrics["output_count"] - metrics["first_acceptable_count"])
    if n == latest_freeze_round:
        before = metrics_file.read_bytes()
        env = dict(_os.environ, PKG1_ROUND=str(n))
        r = subprocess.run(
            ["python3", str(pkg1 / "run_pkg1.py"), "metrics"],
            capture_output=True, text=True, cwd=str(root), env=env)
        after = metrics_file.read_bytes()
        recompute_identical = (r.returncode == 0 and after == before)
        if after != before:
            metrics_file.write_bytes(before)
        recompute_note = f"metrics_recompute_identical={recompute_identical}"
    else:
        recompute_identical = True
        recompute_note = (f"round{n} metrics anchored to freeze commit"
                          f" (modules superseded by round{latest_freeze_round})")
    ok = not collisions and denominator and recompute_identical
    return ok, [f"round={n} role_collisions={collisions}",
                f"denominator_intact={denominator}", recompute_note]


SECTIONS: dict[str, object] = {
    "freeze_integrity": check_freeze_integrity,
    "write_surface": check_write_surface,
    "external_workspaces": check_external_workspaces,
    "core_caliber": check_core_caliber,
    "g3_selftest": check_g3_selftest,
    "eval_spine_selftest": check_eval_spine_selftest,
    "v4_recovery_selftest": check_v4_recovery_selftest,
    "m0_state_integrity": check_m0_state_integrity,
    "m0_dataset_isolation": check_m0_dataset_isolation,
    "stage_contract_v2": check_stage_contract_v2,
    "cost_accounting": check_cost_accounting,
    "active_contract_set": check_active_contract_set,
    "d0_status": check_d0_status,
    "run_journal": check_run_journal,
    "candidate_manifest": check_candidate_manifest,
    "independent_reviews": check_independent_reviews,
    "recovery_shadow_recompute": check_recovery_shadow_recompute,
    "pkg1_input_freeze": check_pkg1_input_freeze,
    "pkg1_route": check_pkg1_route,
    "pkg1_blind": check_pkg1_blind,
    "pkg1_reviews": check_pkg1_reviews,
    "final_receipts": check_final_receipts,
}

# A/B 分开判断（P1 §十七）：产品域标签；无互相牵连的全局 ALL_PASS。
SECTION_SCOPES: dict[str, str] = {
    "freeze_integrity": "SHARED", "write_surface": "SHARED",
    "external_workspaces": "SHARED", "core_caliber": "SHARED",
    "g3_selftest": "B", "eval_spine_selftest": "A",
    "v4_recovery_selftest": "B", "m0_state_integrity": "A",
    "m0_dataset_isolation": "A", "stage_contract_v2": "SHARED",
    "cost_accounting": "SHARED", "active_contract_set": "SHARED",
    "d0_status": "SHARED", "run_journal": "SHARED",
    "candidate_manifest": "A", "independent_reviews": "A",
    "recovery_shadow_recompute": "SHARED",
    "pkg1_input_freeze": "B", "pkg1_route": "B", "pkg1_blind": "B",
    "pkg1_reviews": "B", "final_receipts": "SHARED",
}

# 仅 FINAL 模式运行的节（PRE_REVIEW 只证送审条件，不要求签字存在）
FINAL_ONLY_SECTIONS = {"final_receipts"}


def selftest() -> int:
    """反向自测：证明检查会失败（源指令 §8 反向案例的机器化子集）。
    其余反向案例由 g3 tests/test_g3.py 的 12 个篡改案例覆盖（伪造组件使用、
    表面篡改、主张脱面、冻结复用、run_id 重复等）。"""
    import shutil
    import tempfile
    failures: list[str] = []

    def expect(name: str, condition: bool) -> None:
        print(f"[{'ok' if condition else 'FAIL'}] selftest:{name}")
        if not condition:
            failures.append(name)

    # 1. 修改一个受保护文件字节 → freeze_integrity 必须 FAIL
    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        fi_src = DEFAULT_ROOT / P7 / "freeze"
        (tmp_root / P7 / "freeze").mkdir(parents=True)
        for f in fi_src.iterdir():
            shutil.copy(f, tmp_root / P7 / "freeze" / f.name)
        # 复制全部锚点与清单文件后篡改其中一个
        import re as _re
        pairs = _re.findall(r"path: (\S+)\n\s+sha256: [0-9a-f]{64}",
                            (fi_src / "frozen_inputs.v1.1.yaml"
                             ).read_text(encoding="utf-8"))
        manifest = (fi_src / "p5_p6_full_tree_manifest.v1.1.tsv"
                    ).read_text(encoding="utf-8")
        for rel in pairs:
            if "p7_successor_longrun_001" in rel:
                continue
            src = DEFAULT_ROOT / rel
            dst = tmp_root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(src, dst)
        for line in manifest.splitlines():
            rel = GATE1 + "/" + line.split("\t")[2]
            src = DEFAULT_ROOT / rel
            dst = tmp_root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(src, dst)
        for rel, (sha, _n) in EXTRA_PROTECTED.items():
            dst = tmp_root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(DEFAULT_ROOT / rel, dst)
        ok_clean, _ = check_freeze_integrity(tmp_root)
        expect("tamper_baseline_clean", ok_clean)
        victim = tmp_root / pairs[0]
        data = bytearray(victim.read_bytes())
        data[0] ^= 1
        victim.write_bytes(bytes(data))
        ok_tampered, _ = check_freeze_integrity(tmp_root)
        expect("protected_byte_tamper_detected", not ok_tampered)

    # 2. 写入允许目录之外 → 必须被 surface_offenders 抓住
    expect("out_of_surface_detected",
           surface_offenders(["ci/checkers/check_gate1_v1_1_current.py"]) != [])
    expect("in_surface_clean",
           surface_offenders([P7 + "/x.txt", G3 + "/y.py"]) == [])

    # 3. 盲审材料塞入 CP 编号/产品名称 → 必须被抓住
    expect("blind_leak_cp_detected",
           blind_leak_offenders(["这条 CP07 内容"]) != [])
    expect("blind_leak_name_detected",
           blind_leak_offenders(["这是专业判断切片式内容"]) != [])
    expect("blind_clean", blind_leak_offenders(["一条干净的正文"]) == [])

    # 4. 作者兼任独立审查者 → 必须被抓住
    expect("role_collision_detected",
           role_collision_offenders({"A1", "A2"}, {"A2", "R1"}) == ["A2"])

    # 5. 删除失败候选操纵分母 → 必须被抓住
    expect("denominator_drop_detected",
           not denominator_ok(120, 119, 5, 114))
    expect("denominator_intact_ok", denominator_ok(120, 120, 6, 114))

    # 5b. 历史轮证据被改写/塞入未跟踪文件 → history_intact 必须失败
    expect("history_committed_tamper_detected",
           not history_intact(["pkg1/result/round1_metrics.v1.json"], []))
    expect("history_untracked_injection_detected",
           not history_intact([], ["?? pkg1/review/extra.jsonl"]))
    expect("history_clean_ok", history_intact([], []))

    # 6. 修改路线黄金答案 → route_gold_ok 必须失败（临时根缺文件即漂移语义）
    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        gold_rel = (GATE1 + "/p1b_signed_review_closeout_and_baseline_freeze_001"
                    "/route/route_60_gold_answers.v0.1.jsonl")
        dst = tmp_root / gold_rel
        dst.parent.mkdir(parents=True)
        data = bytearray((DEFAULT_ROOT / gold_rel).read_bytes())
        data[0] ^= 1
        dst.write_bytes(bytes(data))
        expect("route_gold_tamper_detected", not route_gold_ok(tmp_root))
    expect("route_gold_clean", route_gold_ok(DEFAULT_ROOT))

    # 7. v2.5 状态感知节的代表性负向案例（完整攻击矩阵在
    #    delivery_control_001/tests/ 由 unittest 承载）
    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        dc = tmp_root / DC
        (dc / "contracts").mkdir(parents=True)
        (dc / "state").mkdir(parents=True)
        charter = dc / "contracts/D0_PRODUCT_DECOUPLING_CHARTER.v1.md"
        charter.write_text("charter", encoding="utf-8")
        # 布尔速记：无审核回执却宣布 d0_approved=true → 必须被抓
        (dc / "state/D0_STATUS.v1.json").write_text(json.dumps({
            "charter_path": f"{DC}/contracts/D0_PRODUCT_DECOUPLING_CHARTER.v1.md",
            "charter_sha256": None, "active_contract_set_digest": None,
            "review_receipt_path": None, "review_receipt_digest": None,
            "d0_approved": True}), encoding="utf-8")
        ok_forged, _ = v25.check_d0_status(tmp_root, {"milestone": "M1"})
        expect("d0_boolean_shortcut_detected", not ok_forged)

        # B 轨重新依赖 S1_PASS → 阶段合同节必须 FAIL
        es_contract = tmp_root / EVAL_SPINE / "contract"
        es_contract.mkdir(parents=True)
        stage_v2 = json.loads((DEFAULT_ROOT / EVAL_SPINE
                               / "contract/stage_and_kill.v2.json"
                               ).read_text(encoding="utf-8"))
        for stage in stage_v2["stages"]:
            if stage["stage_id"] == "S2_FEASIBILITY_AND_COST_TELEMETRY":
                stage["entry_requires"].append("S1_PASS")
        (es_contract / "stage_and_kill.v2.json").write_text(
            json.dumps(stage_v2, ensure_ascii=False), encoding="utf-8")
        ok_dep, details_dep = v25.check_stage_contract_v2(
            tmp_root, {"milestone": "M1"})
        expect("b_track_a_dependency_detected", not ok_dep and any(
            "depends on A track" in d or "S2 entry keys drifted" in d
            for d in details_dep))

        # journal 缺失 → run_journal 节必须 FAIL（STOP_RUN_JOURNAL_INVALID）
        (dc / "tools").mkdir(parents=True)
        shutil.copy(DEFAULT_ROOT / DC / "tools/run_journal.py",
                    dc / "tools/run_journal.py")
        ok_journal, details_journal = v25.check_run_journal(
            tmp_root, {"milestone": "M1"})
        expect("missing_journal_detected", not ok_journal and any(
            "STOP_RUN_JOURNAL_INVALID" in d for d in details_journal))

    print("SELFTEST:", "ALL_NEGATIVE_CASES_ENFORCED" if not failures
          else f"FAILED {failures}")
    return 0 if not failures else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(DEFAULT_ROOT))
    ap.add_argument("--section")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--milestone", choices=[f"M{i}" for i in range(1, 8)],
                    default="M1", help="当前里程碑（决定期望状态映射）")
    ap.add_argument("--product", choices=["SHARED", "A", "B", "ALL"],
                    default="ALL", help="产品域过滤；A/B 分开判断，互不牵连")
    ap.add_argument("--mode", choices=["PRE_REVIEW", "FINAL"],
                    default="PRE_REVIEW",
                    help="PRE_REVIEW=送审条件；FINAL=另需 typed PASS + 有效外部签字")
    ap.add_argument("--state-file", default=None,
                    help="覆盖 STATE_EXPECTATION 路径（测试/演进用）")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if args.list:
        for name in SECTIONS:
            print(f"{name}  [{SECTION_SCOPES.get(name, 'SHARED')}]")
        return 0
    CTX["milestone"] = args.milestone
    CTX["mode"] = args.mode
    CTX["state_file"] = args.state_file
    root = Path(args.root)
    if args.section:
        names = [args.section]
    else:
        names = [name for name in SECTIONS
                 if args.product == "ALL"
                 or SECTION_SCOPES.get(name, "SHARED") == args.product]
        if args.mode != "FINAL":
            names = [name for name in names if name not in FINAL_ONLY_SECTIONS]
    results: dict[str, bool] = {}
    for name in names:
        fn = SECTIONS.get(name)
        if fn is None:
            print(f"[ERROR] unknown section {name}")
            return 1
        ok, details = fn(root)  # type: ignore[operator]
        results[name] = ok
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
        for d in details:
            print(f"    {d}")
    # A/B 分开判断：逐产品域汇总，不设互相牵连的全局 ALL_PASS
    print(f"MODE: {args.mode}  MILESTONE: {args.milestone}")
    for scope in ("SHARED", "A", "B"):
        scoped = {n: ok for n, ok in results.items()
                  if SECTION_SCOPES.get(n, "SHARED") == scope}
        if scoped:
            verdict = "PASS" if all(scoped.values()) else "FAILED"
            print(f"RESULT[{scope}]: {verdict} ({len(scoped)} sections)")
    all_ok = all(results.values())
    if not args.section:
        status_path = root / EVAL_SPINE / "calibration/M0_STATUS.v1.json"
        m0 = "NOT_RUN"
        if status_path.is_file():
            try:
                m0 = str(json.loads(status_path.read_text(encoding="utf-8")).get(
                    "status", "NOT_RUN"))
            except (OSError, ValueError):
                m0 = "INVALID_STATE"
        print(f"ARTIFACT_INTEGRITY: {'PASS' if all_ok else 'FAIL'}")
        print(f"M0_QUALIFICATION: {m0}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())

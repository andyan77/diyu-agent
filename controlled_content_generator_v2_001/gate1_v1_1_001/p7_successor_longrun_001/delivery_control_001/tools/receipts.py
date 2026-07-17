#!/usr/bin/env python3
"""typed 回执 / 签字回执 / handoff / 启动记录的加载与机械校验共享库。

原则（v2.5 §三 3.9 + P1 §十三/§十六）：
  - 下游入口按具体状态值匹配；"已关闭"不构成通过；REVIEW_READY 永不满足入口。
  - 资格旗标只在 result==PASS 的回执上生效；FAIL/HONEST_STOP 回执携带的
    正向旗标视为不一致（伪造面）并整体拒绝。
  - 缺必填字段 / 摘要复算不符 / schema 无效 = 该回执视为不存在。
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

DC = Path(__file__).resolve().parents[1]
TERMINAL_RESULTS = {"PASS", "DIAGNOSTIC_FINAL", "FAIL", "HONEST_STOP"}
MILESTONES = ("M1", "M2", "M3", "M4", "M5", "M6", "M7")

# schema_version → schema 文件（版本分发；未知版本 = 无效）
HANDOFF_SCHEMAS = {
    "p7-handoff-v1": "handoff.v1.schema.json",
    "p7-handoff-v2": "handoff.v2.schema.json",
}
SIGNER_SCHEMAS = {
    "p7-signer-receipt-v1": "signer_receipt.v1.schema.json",
    "p7-signer-receipt-v2": "signer_receipt.v2.schema.json",
}
LAUNCH_RECORD_SCHEMAS = {
    "p7-launch-record-v1": "launch_record.v1.schema.json",
    "p7-launch-record-v2": "launch_record.v2.schema.json",
}
# typed 回执双方在 FINAL/八件套中必须逐字段一致的比较面（指令第 4 条）
TYPED_PAIR_COMPARED_FIELDS = (
    "milestone_id", "product_scope", "result", "terminal",
    "candidate_commit", "output_manifest_digest", "evidence_manifest_digest",
    "stop_code",
)


class ReceiptError(ValueError):
    """回执无效（等价于回执不存在，永不满足入口）。"""


def resolve_versioned(directory: Path, base: str, ext: str = "json") -> Path:
    """工件版本解析：优先最新 schema 版（v2），回退 v1；均缺则返回 v2 路径供报错。"""
    for version in ("v2", "v1"):
        path = directory / f"{base}.{version}.{ext}"
        if path.is_file():
            return path
    return directory / f"{base}.v2.{ext}"


def canonical_digest(record: dict, digest_field: str) -> str:
    unsigned = {k: v for k, v in record.items() if k != digest_field}
    return hashlib.sha256(json.dumps(
        unsigned, ensure_ascii=False, sort_keys=True,
        separators=(",", ":")).encode("utf-8")).hexdigest()


def close_record(record: dict, digest_field: str) -> dict:
    record = dict(record)
    record[digest_field] = canonical_digest(record, digest_field)
    return record


def _schema_validate(value: dict, schema_name: str) -> list[str]:
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        return ["jsonschema unavailable -> receipt unverifiable -> invalid"]
    schema = json.loads((DC / "schema" / schema_name).read_text(encoding="utf-8"))
    return [f"schema:{e.message[:100]}" for e in sorted(
        Draft202012Validator(schema).iter_errors(value),
        key=lambda item: list(item.path))]


def load_typed_receipt(path: Path) -> dict:
    """加载并硬校验 typed 回执；任何缺陷 → ReceiptError（= 未提交回执）。"""
    if not path.is_file():
        raise ReceiptError(f"receipt missing: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ReceiptError(f"receipt unreadable: {path}: {exc}") from exc
    errors = _schema_validate(value, "typed_receipt.v1.schema.json")
    if value.get("receipt_digest") != canonical_digest(value, "receipt_digest"):
        errors.append("receipt_digest recompute mismatch")
    result = value.get("result")
    if value.get("receipt_kind") in ("STAGE_DECISION", "CLOSEOUT_RECEIPT"):
        if result not in TERMINAL_RESULTS:
            errors.append(f"non-terminal result '{result}' cannot close "
                          "(REVIEW_READY is not PASS)")
        flags = value.get("qualification_flags") or {}
        if result in ("FAIL", "HONEST_STOP") and any(
                flags.get(key) is True for key in
                ("A2_QUALIFIED", "A_LIFT_READY", "B_LIFT_READY",
                 "LOGICAL_CORE_SEPARATED")):
            errors.append(f"failed receipt carries positive qualification "
                          f"flags {sorted(k for k, v in flags.items() if v is True)}"
                          " (forgery surface)")
    if errors:
        raise ReceiptError(f"{path.name}: " + "; ".join(errors))
    return value


def milestone_result(root: Path, milestone: str,
                     milestones_dir: Path | None = None) -> dict | None:
    """返回校验通过的关闭回执；不存在返回 None；无效回执抛 ReceiptError。"""
    if milestones_dir is None:
        milestones_dir = _milestones_dir(root)
    path = resolve_versioned(milestones_dir / milestone, "CLOSEOUT_RECEIPT")
    if not path.is_file():
        return None
    receipt = load_typed_receipt(path)
    if receipt.get("milestone_id") != milestone:
        # 回执移植伪造：把别的里程碑的 PASS 回执复制进本目录
        raise ReceiptError(
            f"receipt milestone_id={receipt.get('milestone_id')} transplanted "
            f"into milestones/{milestone}/ (forgery surface)")
    return receipt


def _milestones_dir(root: Path) -> Path:
    return (root / "controlled_content_generator_v2_001/gate1_v1_1_001"
            "/p7_successor_longrun_001/delivery_control_001/milestones")


def qualification_flag(receipt: dict | None, flag: str) -> bool:
    """资格旗标读取：只认 PASS 回执上的显式 true；其余一律 False。

    这排除四种伪造/混淆（P1 §十三）：通用关闭回执、A2_DIAGNOSTIC_FINAL
    冒充 A2_QUALIFIED、失败回执携带旗标、缺状态值的回执。"""
    if receipt is None:
        return False
    if receipt.get("result") != "PASS":
        return False
    flags = receipt.get("qualification_flags") or {}
    return flags.get(flag) is True


def route_binding(root: Path) -> str | None:
    """B 评测路线冻结记录：state/B_EVAL_ROUTE.v1.json。未冻结返回 None。"""
    path = (root / "controlled_content_generator_v2_001/gate1_v1_1_001"
            "/p7_successor_longrun_001/delivery_control_001"
            "/state/B_EVAL_ROUTE.v1.json")
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if value.get("frozen") is not True:
        return None
    route = value.get("route")
    return route if route in ("a", "b") else None


def validate_handoff(path: Path) -> dict:
    """schema 级校验（按 schema_version 分发）；全引用复算见 tools/closure.py。"""
    if not path.is_file():
        raise ReceiptError(f"handoff missing: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    schema_name = HANDOFF_SCHEMAS.get(str(value.get("schema_version")))
    if schema_name is None:
        raise ReceiptError(f"{path.name}: unknown handoff schema_version "
                           f"{value.get('schema_version')!r}")
    errors = _schema_validate(value, schema_name)
    if value.get("handoff_digest") != canonical_digest(value, "handoff_digest"):
        errors.append("handoff_digest recompute mismatch")
    if errors:
        raise ReceiptError(f"{path.name}: " + "; ".join(errors))
    return value


def load_signer_receipt(path: Path) -> dict:
    """签字回执加载与硬校验（版本分发）：schema、摘要复算、隔离声明。
    缺任一必填字段 = 未签 → ReceiptError。"""
    if not path.is_file():
        raise ReceiptError(f"signer receipt missing: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ReceiptError(f"signer receipt unreadable: {path}: {exc}") from exc
    schema_name = SIGNER_SCHEMAS.get(str(value.get("schema_version")))
    if schema_name is None:
        raise ReceiptError(f"{path.name}: unknown signer schema_version "
                           f"{value.get('schema_version')!r}")
    errors = _schema_validate(value, schema_name)
    if value.get("receipt_digest") != canonical_digest(value, "receipt_digest"):
        errors.append("receipt_digest recompute mismatch")
    attestation = value.get("session_isolation_attestation", {})
    if not isinstance(attestation, dict) or not all(
            attestation.get(key) is True for key in (
                "fresh_session_not_fork_not_resume",
                "did_not_author_reviewed_scope",
                "auto_memory_disabled_or_not_applicable")):
        errors.append("isolation attestation invalid -> unsigned")
    if errors:
        raise ReceiptError(f"{path.name}: " + "; ".join(errors))
    return value


def compare_typed_pair(decision: dict, closeout: dict) -> list[str]:
    """STAGE_DECISION 与 CLOSEOUT_RECEIPT 的强制逐字段比对（指令第 4 条）。

    两份 typed 回执必须对同一候选、同一产品域、同一结果、同一 manifest
    摘要与同一审核绑定集合作证；任何一项分叉 = 关闭无效。"""
    errors: list[str] = []
    if decision.get("receipt_kind") != "STAGE_DECISION":
        errors.append(f"first receipt kind={decision.get('receipt_kind')} "
                      "!= STAGE_DECISION")
    if closeout.get("receipt_kind") != "CLOSEOUT_RECEIPT":
        errors.append(f"second receipt kind={closeout.get('receipt_kind')} "
                      "!= CLOSEOUT_RECEIPT")
    for field in TYPED_PAIR_COMPARED_FIELDS:
        if decision.get(field) != closeout.get(field):
            errors.append(f"typed pair diverges on {field}: "
                          f"{decision.get(field)!r} != {closeout.get(field)!r}")
    if (decision.get("qualification_flags") or {}) != (
            closeout.get("qualification_flags") or {}):
        errors.append("typed pair diverges on qualification_flags")

    def binding_set(receipt: dict) -> set[tuple]:
        return {(b.get("receipt_path"), b.get("receipt_digest"),
                 b.get("reviewer_kind"), b.get("verdict"))
                for b in receipt.get("review_bindings", [])}

    if binding_set(decision) != binding_set(closeout):
        errors.append("typed pair diverges on review_bindings")
    return errors


def _git_ok(repo_root: Path, *args: str) -> bool:
    return subprocess.run(["git", "-C", str(repo_root), *args],
                          capture_output=True).returncode == 0


def validate_launch_record(value: dict, repo_root: Path | None = None,
                           expected_head: str | None = None) -> list[str]:
    """启动记录校验（版本分发）。

    v1（封存）：单文件承载 spawn 前后全部字段。
    v2：只承载 spawn 前事实；必须声明先落盘（record_written_before_spawn）、
    原子写协议与实际 HEAD 绑定；会话结果由 validate_launch_outcome 单独校验。

    HEAD 绑定不自证（Codex R4 BLOCKING 修复）：record_digest 只能证明记录
    内部一致，不能证明 launched_at_head 是真实 HEAD——伪造者可改值后重算摘要。
    因此：①传入 repo_root 时对仓库复核（提交存在、位于分支历史、input_commit
    为其祖先）；②传入 expected_head（启动现场）时强制逐字相等；③启动流程另将
    record_digest 交叉登记进哈希链 RUN_JOURNAL（git_head 由 journal 独立采集），
    事后核验走 launcher.verify_launch_binding。"""
    schema_name = LAUNCH_RECORD_SCHEMAS.get(str(value.get("schema_version")))
    if schema_name is None:
        return [f"unknown launch record schema_version "
                f"{value.get('schema_version')!r}"]
    errors = _schema_validate(value, schema_name)
    if value.get("record_digest") != canonical_digest(value, "record_digest"):
        errors.append("record_digest recompute mismatch")
    if value.get("session_kind") != "TOP_LEVEL_FRESH":
        errors.append("launch must create a fresh top-level session "
                      "(subagent impersonation rejected)")
    if value.get("auto_memory_disabled") is not True:
        errors.append("auto memory not disabled for launched session")
    if value.get("schema_version") == "p7-launch-record-v2":
        if value.get("record_written_before_spawn") is not True:
            errors.append("launch record not written before spawn")
        if value.get("write_protocol") != "ATOMIC_WRITE_TMP_FSYNC_RENAME":
            errors.append("launch record write protocol not atomic")
        head_value = str(value.get("launched_at_head", ""))
        if expected_head is not None and head_value != expected_head:
            errors.append(f"launched_at_head {head_value[:12]} != actual "
                          f"HEAD {expected_head[:12]} at validation site")
        if repo_root is not None:
            if not _git_ok(repo_root, "cat-file", "-e",
                           f"{head_value}^{{commit}}"):
                errors.append("launched_at_head unknown to repository "
                              "(forged HEAD binding)")
            else:
                if not _git_ok(repo_root, "merge-base", "--is-ancestor",
                               head_value, "HEAD"):
                    errors.append("launched_at_head not in branch history")
                input_value = str(value.get("input_commit", ""))
                if input_value and not _git_ok(
                        repo_root, "merge-base", "--is-ancestor",
                        input_value, head_value):
                    errors.append("input_commit not ancestor of "
                                  "launched_at_head")
    return errors


def validate_launch_outcome(value: dict, record: dict | None = None) -> list[str]:
    """启动结果校验：schema + 摘要复算 + 回绑启动记录 + 子代理伪装拒绝。"""
    errors = _schema_validate(value, "launch_outcome.v1.schema.json")
    if value.get("outcome_digest") != canonical_digest(value, "outcome_digest"):
        errors.append("outcome_digest recompute mismatch")
    if record is not None and value.get("launch_record_digest") != record.get(
            "record_digest"):
        errors.append("outcome not bound to launch record digest")
    if (value.get("launch_capability") == "AUTO_LAUNCHED"
            and value.get("session_kind") != "TOP_LEVEL_FRESH"):
        errors.append("spawned session is not a fresh top-level session "
                      "(subagent impersonation rejected)")
    return errors

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
from pathlib import Path
from typing import Any

DC = Path(__file__).resolve().parents[1]
TERMINAL_RESULTS = {"PASS", "DIAGNOSTIC_FINAL", "FAIL", "HONEST_STOP"}
MILESTONES = ("M1", "M2", "M3", "M4", "M5", "M6", "M7")


class ReceiptError(ValueError):
    """回执无效（等价于回执不存在，永不满足入口）。"""


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
    path = milestones_dir / milestone / "CLOSEOUT_RECEIPT.v1.json"
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
    if not path.is_file():
        raise ReceiptError(f"handoff missing: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    errors = _schema_validate(value, "handoff.v1.schema.json")
    if value.get("handoff_digest") != canonical_digest(value, "handoff_digest"):
        errors.append("handoff_digest recompute mismatch")
    if errors:
        raise ReceiptError(f"{path.name}: " + "; ".join(errors))
    return value


def validate_launch_record(value: dict) -> list[str]:
    errors = _schema_validate(value, "launch_record.v1.schema.json")
    if value.get("record_digest") != canonical_digest(value, "record_digest"):
        errors.append("record_digest recompute mismatch")
    if value.get("session_kind") != "TOP_LEVEL_FRESH":
        errors.append("launch must create a fresh top-level session "
                      "(subagent impersonation rejected)")
    if value.get("auto_memory_disabled") is not True:
        errors.append("auto memory not disabled for launched session")
    return errors

#!/usr/bin/env python3
"""Prompt renderer（P1 §十二）：把 P2–P7 模板绑定为可启动 Prompt。

绑定内容：最新接受的前序 handoff、前序 PASS 回执、精确输入提交、当前路线、
当前写面、实际模型与会话要求。渲染结果有独立摘要，写入对应启动记录。
模板占位符：{{KEY}}；渲染后残留占位符 = 渲染失败。
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from pathlib import Path

DC = Path(__file__).resolve().parents[1]
PLACEHOLDER = re.compile(r"\{\{([A-Z0-9_]+)\}\}")


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


receipts = _load(DC / "tools/receipts.py", "p7_receipts_renderer")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def render(template_path: Path, bindings: dict[str, str]) -> dict:
    """返回 {text, rendered_digest, template_digest, bindings}；残留占位符即失败。"""
    template = template_path.read_text(encoding="utf-8")
    template_digest = sha256_text(template)
    text = template
    for key, value in bindings.items():
        text = text.replace("{{" + key + "}}", str(value))
    leftover = sorted(set(PLACEHOLDER.findall(text)))
    if leftover:
        raise ValueError(f"unbound placeholders: {leftover}")
    return {"text": text, "rendered_digest": sha256_text(text),
            "template_digest": template_digest,
            "bindings": dict(sorted(bindings.items()))}


def build_bindings(root: Path, milestone: str, registry: dict,
                   milestones_dir: Path | None = None) -> dict[str, str]:
    """从磁盘装配绑定值；前序回执必须为 PASS（或 M5 的有效最终结果规则由
    ready-set 把关——本函数只在 ready-set 判定 ready 后调用）。"""
    entry = next(row for row in registry["prompts"]
                 if row["milestone_id"] == milestone)
    predecessor = entry["predecessor_milestone"]
    receipt = receipts.milestone_result(root, predecessor,
                                        milestones_dir=milestones_dir)
    if receipt is None:
        raise receipts.ReceiptError(
            f"predecessor {predecessor} closeout receipt absent")
    handoff_path = (milestones_dir or (
        root / "controlled_content_generator_v2_001/gate1_v1_1_001"
        "/p7_successor_longrun_001/delivery_control_001/milestones")
    ) / predecessor / "HANDOFF.v1.json"
    handoff = receipts.validate_handoff(handoff_path)
    route = receipts.route_binding(root) or "UNFROZEN"
    return {
        "MILESTONE_ID": milestone,
        "PROMPT_ID": entry["prompt_id"],
        "INPUT_COMMIT": handoff["accepted_candidate_commit"],
        "CONTROL_PLANE_COMMIT": handoff["control_plane_commit"],
        "PREDECESSOR_MILESTONE": predecessor,
        "PREDECESSOR_RESULT": receipt["result"],
        "PREDECESSOR_RECEIPT_DIGEST": receipt["receipt_digest"],
        "HANDOFF_DIGEST": handoff["handoff_digest"],
        "ACTIVE_CONTRACT_SET_DIGEST": handoff["active_contract_set_digest"],
        "ROUTE": route,
        "WRITE_SURFACE_ALLOWLIST": "\n".join(
            f"- `{p}`" for p in entry["write_surface_allowlist"]),
        "WRITE_SURFACE_DENYLIST": "\n".join(
            f"- {p}" for p in entry["write_surface_denylist"]),
        "SESSION_REQUIREMENTS": entry["session_requirements"],
    }


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(DC.parents[3]))
    ap.add_argument("--milestone", required=True)
    ap.add_argument("--out")
    args = ap.parse_args()
    registry = json.loads((DC / "PROMPT_REGISTRY.v1.json").read_text(
        encoding="utf-8"))
    entry = next(row for row in registry["prompts"]
                 if row["milestone_id"] == args.milestone)
    bindings = build_bindings(Path(args.root), args.milestone, registry)
    result = render(DC / entry["template_path"], bindings)
    if args.out:
        Path(args.out).write_text(result["text"], encoding="utf-8")
    print(json.dumps({"rendered_digest": result["rendered_digest"],
                      "template_digest": result["template_digest"],
                      "out": args.out}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())

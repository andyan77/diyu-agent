#!/usr/bin/env python3
"""§四.4 真实 generation/index 绑定：把「active generation」从一个仅格式校验的字符串，
升级为磁盘上可复算的工件链——

  active generation pointer 文件  →  generation manifest 文件  →  qualification index 文件

绑定验证不再只看名字格式和 digest 格式，而是逐层用**真实文件**复算：
  1. active pointer 自洽 + 指向的 generation manifest 在盘且文件 sha256 吻合；
  2. generation manifest 自洽 + generation_id == pointer.active_generation_id + set 匹配 +
     generation_id 结构化（QUAL_[AB]_GEN_…）；
  3. qualification index 路径在盘、文件 sha256 == manifest 声明；index 内容 digest 自洽、
     verify_qualification_record_index 过、dataset_manifest_digest 与 generation 一致、
     record_count 一致；
  4. custody/readiness/closed-pass 侧声明的 (active_generation_id / index digest / gold /
     faces / dataset_manifest_digest) 必须 == 本链复算——任何不符 fail-closed。

明文零入：index 只含 case_id + 摘要（HIDDEN 分区证据闭包），无题面/答案；pointer/manifest
只载摘要。由保全/隔离会话或 R3-run 产出；主编排会话只读公开摘要复核。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve()
P7 = HERE.parents[2]
sys.path.insert(0, str(P7 / "eval_audit_spine_001"))
sys.path.insert(0, str(HERE.parent))
from spine.canonical import digest_json  # noqa: E402
from spine import qualification_data as qd  # noqa: E402

_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_GENERATION_RE = re.compile(r"^QUAL_[AB]_GEN_[0-9A-Za-z_]+$")

POINTER_SCHEMA = "p7-qual-active-generation-pointer-v1"
MANIFEST_SCHEMA = "p7-qual-generation-manifest-v1"


def _sha_file(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _self_digest(obj: dict[str, Any], key: str) -> str:
    return digest_json({k: v for k, v in obj.items() if k != key})


def _records_recompute_digest(records: list[dict]) -> str:
    return digest_json(sorted(str(r.get("case_digest")) for r in records))


def pointer_path(qual_dir: Path, set_id: str) -> Path:
    return qual_dir / f"QUAL_{set_id}_ACTIVE_GENERATION.v1.json"


def generation_dir(qual_dir: Path) -> Path:
    return qual_dir / "generations"


def combined_index_digest(manifest_a: dict, manifest_b: dict) -> str:
    """两套 index 内容摘要的合取摘要——closed-pass binding 单字段绑两套真 index。"""
    return digest_json({
        "QUAL_A": manifest_a.get("qualification_index_content_digest"),
        "QUAL_B": manifest_b.get("qualification_index_content_digest")})


# ------------------------------------------------------------------ builders

def build_generation(records: list[dict], *, set_id: str, generation_id: str,
                     dataset_manifest_digest: str, faces_sha256: str,
                     gold_sha256: str, qual_dir: Path) -> dict[str, Any]:
    """由密封 gold 记录产出：index 文件 + generation manifest 文件 + active pointer 文件。

    返回 {"manifest": …, "pointer": …, "index_path": …, "manifest_path": …,
          "pointer_path": …}。写文件为原子（先写文本再计 sha）。
    """
    if not _GENERATION_RE.match(generation_id):
        raise ValueError(f"generation_id not structured: {generation_id}")
    if generation_id.split("_")[1] != set_id:
        raise ValueError(f"generation_id set mismatch: {generation_id} vs {set_id}")
    for name, val in (("dataset_manifest_digest", dataset_manifest_digest),
                      ("faces_sha256", faces_sha256), ("gold_sha256", gold_sha256)):
        if not _DIGEST_RE.fullmatch(str(val)):
            raise ValueError(f"{name} not a 64-hex digest")
    gdir = generation_dir(qual_dir)
    gdir.mkdir(parents=True, exist_ok=True)

    index = qd.build_qualification_record_index(
        records, dataset_manifest_digest=dataset_manifest_digest)
    index_path = gdir / f"{generation_id}.index.json"
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=1) + "\n",
                          encoding="utf-8")
    index_file_sha = _sha_file(index_path)

    # 路径存 qual_dir-相对（自包含；resolve 侧同以 qual_dir 为根，不依赖仓库根定位）。
    manifest = {
        "schema_version": MANIFEST_SCHEMA,
        "generation_id": generation_id, "set": set_id,
        "dataset_manifest_digest": dataset_manifest_digest,
        "faces_sha256": faces_sha256, "gold_sha256": gold_sha256,
        "record_count": len(records),
        "records_recompute_digest": _records_recompute_digest(records),
        "qualification_index_path": str(index_path.relative_to(qual_dir)),
        "qualification_index_file_sha256": index_file_sha,
        "qualification_index_content_digest": index["index_digest"],
        "generation_manifest_digest": "",
    }
    manifest["generation_manifest_digest"] = _self_digest(
        manifest, "generation_manifest_digest")
    manifest_path = gdir / f"{generation_id}.manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n",
                             encoding="utf-8")
    manifest_file_sha = _sha_file(manifest_path)

    pointer = {
        "schema_version": POINTER_SCHEMA, "set": set_id,
        "active_generation_id": generation_id,
        "generation_manifest_path": str(manifest_path.relative_to(qual_dir)),
        "generation_manifest_file_sha256": manifest_file_sha,
        "pointer_digest": "",
    }
    pointer["pointer_digest"] = _self_digest(pointer, "pointer_digest")
    ppath = pointer_path(qual_dir, set_id)
    ppath.write_text(json.dumps(pointer, ensure_ascii=False, indent=1) + "\n",
                     encoding="utf-8")
    return {"manifest": manifest, "pointer": pointer, "index": index,
            "index_path": index_path, "manifest_path": manifest_path,
            "pointer_path": ppath}


# ------------------------------------------------------------------ verifier

def resolve_active_generation(qual_dir: Path, set_id: str) -> dict[str, Any]:
    """跟随 pointer→manifest→index 链复算，返回
    {"errors": [...], "manifest": {...}|None, "index": {...}|None}。errors 空即链自洽。"""
    errors: list[str] = []
    ppath = pointer_path(qual_dir, set_id)
    try:
        pointer = json.loads(ppath.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {"errors": [f"active_pointer_unreadable:{exc}"],
                "manifest": None, "index": None}
    if (pointer.get("schema_version") != POINTER_SCHEMA
            or pointer.get("set") != set_id):
        errors.append("active_pointer_schema_or_set")
    if pointer.get("pointer_digest") != _self_digest(pointer, "pointer_digest"):
        errors.append("active_pointer_self_digest")
    gen_id = str(pointer.get("active_generation_id", ""))
    if not _GENERATION_RE.match(gen_id):
        errors.append("active_generation_id_not_structured")
    # pointer -> manifest 文件（qual_dir-相对）
    mrel = pointer.get("generation_manifest_path")
    manifest = None
    if not isinstance(mrel, str) or not mrel:
        errors.append("generation_manifest_path_missing")
    else:
        mpath = qual_dir / mrel
        got_sha = _sha_file(mpath)
        if got_sha is None:
            errors.append("generation_manifest_absent")
        elif got_sha != pointer.get("generation_manifest_file_sha256"):
            errors.append("generation_manifest_file_sha_mismatch")
        else:
            try:
                manifest = json.loads(mpath.read_text(encoding="utf-8"))
            except ValueError as exc:
                errors.append(f"generation_manifest_unreadable:{exc}")
    if manifest is None:
        return {"errors": sorted(set(errors)), "manifest": None, "index": None}
    # manifest 自洽 + 与 pointer 一致
    if manifest.get("schema_version") != MANIFEST_SCHEMA:
        errors.append("generation_manifest_schema")
    if manifest.get("generation_manifest_digest") != _self_digest(
            manifest, "generation_manifest_digest"):
        errors.append("generation_manifest_self_digest")
    if manifest.get("generation_id") != gen_id:
        errors.append("generation_id_pointer_manifest_mismatch")
    if manifest.get("set") != set_id:
        errors.append("generation_manifest_set_mismatch")
    # manifest -> index 文件（qual_dir-相对）
    index = None
    irel = manifest.get("qualification_index_path")
    if not isinstance(irel, str) or not irel:
        errors.append("qualification_index_path_missing")
    else:
        ipath = qual_dir / irel
        got_sha = _sha_file(ipath)
        if got_sha is None:
            errors.append("qualification_index_absent")
        elif got_sha != manifest.get("qualification_index_file_sha256"):
            errors.append("qualification_index_file_sha_mismatch")
        else:
            try:
                index = json.loads(ipath.read_text(encoding="utf-8"))
            except ValueError as exc:
                errors.append(f"qualification_index_unreadable:{exc}")
    if index is not None:
        idx_errors = qd.verify_qualification_record_index(
            index, expected_dataset_manifest_digest=manifest.get(
                "dataset_manifest_digest"))
        errors.extend(f"index:{e}" for e in idx_errors)
        if index.get("index_digest") != manifest.get(
                "qualification_index_content_digest"):
            errors.append("index_content_digest_manifest_mismatch")
        if index.get("record_count") != manifest.get("record_count"):
            errors.append("index_record_count_manifest_mismatch")
        if index.get("dataset_manifest_digest") != manifest.get(
                "dataset_manifest_digest"):
            errors.append("index_dataset_manifest_mismatch")
    return {"errors": sorted(set(errors)), "manifest": manifest, "index": index}


def verify_generation_binding(qual_dir: Path, set_id: str,
                              expected: dict[str, Any]) -> list[str]:
    """closed-pass/custody/readiness 侧硬复核：链自洽 + 声明字段 == 本链复算值。

    expected 键（任缺/不符即报错 fail-closed）:
      active_generation_id / qualification_index_digest / gold_sha256 /
      faces_sha256 / dataset_manifest_digest
    """
    resolved = resolve_active_generation(qual_dir, set_id)
    errors = list(resolved["errors"])
    manifest = resolved["manifest"]
    if manifest is None:
        return sorted(set(errors)) or ["generation_chain_unresolved"]
    pairs = (
        ("active_generation_id", manifest.get("generation_id")),
        ("qualification_index_digest", manifest.get(
            "qualification_index_content_digest")),
        ("gold_sha256", manifest.get("gold_sha256")),
        ("faces_sha256", manifest.get("faces_sha256")),
        ("dataset_manifest_digest", manifest.get("dataset_manifest_digest")),
    )
    for key, actual in pairs:
        want = expected.get(key)
        if want is None:
            errors.append(f"expected_{key}_absent")
        elif want != actual:
            errors.append(f"{key}_not_bound_to_active_generation")
    return sorted(set(errors))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", choices=["A", "B"], help="复核某套 generation 链自洽")
    ap.add_argument("--qual-dir", default=str(HERE.parent.parent / "gold/qual"))
    args = ap.parse_args()
    if args.verify:
        resolved = resolve_active_generation(Path(args.qual_dir), args.verify)
        print(json.dumps({"set": args.verify, "errors": resolved["errors"],
                          "generation_id": (resolved["manifest"] or {}).get(
                              "generation_id")}, ensure_ascii=False, indent=1))
        return 0 if not resolved["errors"] else 1
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())

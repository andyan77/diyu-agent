"""候选实现清单生成与复算。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from .canonical import digest_json, file_digest

DEFAULT_PREFIXES = (
    "controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001/"
    ".gitignore",
    "controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001/"
    "EVAL_AUDIT_SPINE_PRODUCT_MAP.v1.1.md",
    "controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001/"
    "eval_audit_spine_001",
    "controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001/"
    "checker/p7_master_check.py",
    "controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001/"
    "checker/v25_state_checks.py",
    "controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001/"
    "EVAL_AUDIT_SPINE_PRODUCT_MAP.v1.2.md",
    "controlled_content_generator_v2_001/generator_v3_successor_001/v4_recovery",
)


def _files(repo_root: Path, prefixes: Iterable[str]) -> list[Path]:
    files: list[Path] = []
    for prefix in prefixes:
        path = repo_root / prefix
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            files.extend(item for item in path.rglob("*") if item.is_file())
    # .pytest_cache/.ruff_cache/.mypy_cache：审查者用 pytest/linter 复跑套件产生的
    # 会话性缓存不属于候选实现（Fable R4 ADVISORY：缓存被拾取会让 A 域误 FAIL）
    excluded_parts = {"__pycache__", "review", "evidence", "release",
                      ".pytest_cache", ".ruff_cache", ".mypy_cache"}
    return sorted({path for path in files
                   if not excluded_parts.intersection(path.relative_to(repo_root).parts)
                   and not path.name.startswith(".env")
                   and "secret" not in path.name.lower()
                   and "credential" not in path.name.lower()
                   and path.suffix != ".pyc"})


def build_candidate_manifest(repo_root: Path,
                             prefixes: Iterable[str] = DEFAULT_PREFIXES) -> dict[str, Any]:
    entries = [{"path": path.relative_to(repo_root).as_posix(),
                "sha256": file_digest(path), "size_bytes": path.stat().st_size}
               for path in _files(repo_root, prefixes)]
    manifest: dict[str, Any] = {
        "schema_version": "eval-spine-candidate-manifest-v1",
        "scope": "IMPLEMENTATION_WITHOUT_REVIEW_OR_GENERATED_EVIDENCE",
        "entry_count": len(entries), "entries": entries, "manifest_digest": "",
    }
    unsigned = dict(manifest)
    unsigned.pop("manifest_digest")
    manifest["manifest_digest"] = digest_json(unsigned)
    return manifest


def verify_candidate_manifest(repo_root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    unsigned = dict(manifest)
    supplied = unsigned.pop("manifest_digest", None)
    errors: list[str] = []
    if manifest.get("schema_version") != "eval-spine-candidate-manifest-v1":
        errors.append("schema_version_mismatch")
    if manifest.get("scope") != "IMPLEMENTATION_WITHOUT_REVIEW_OR_GENERATED_EVIDENCE":
        errors.append("scope_mismatch")
    if supplied != digest_json(unsigned):
        errors.append("manifest_digest_mismatch")
    for entry in manifest.get("entries", []):
        path = repo_root / str(entry.get("path", ""))
        if not path.is_file():
            errors.append(f"missing:{entry.get('path')}")
        elif file_digest(path) != entry.get("sha256"):
            errors.append(f"drift:{entry.get('path')}")
        elif path.stat().st_size != entry.get("size_bytes"):
            errors.append(f"size_drift:{entry.get('path')}")
    if manifest.get("entry_count") != len(manifest.get("entries", [])):
        errors.append("entry_count_mismatch")
    expected = build_candidate_manifest(repo_root)
    supplied_by_path = {str(entry.get("path")): entry
                        for entry in manifest.get("entries", [])}
    expected_by_path = {str(entry["path"]): entry for entry in expected["entries"]}
    if len(supplied_by_path) != len(manifest.get("entries", [])):
        errors.append("duplicate_entry_path")
    missing = sorted(set(expected_by_path) - set(supplied_by_path))
    extra = sorted(set(supplied_by_path) - set(expected_by_path))
    errors.extend(f"missing_expected_entry:{path}" for path in missing)
    errors.extend(f"unexpected_entry:{path}" for path in extra)
    for path in sorted(set(expected_by_path) & set(supplied_by_path)):
        if supplied_by_path[path] != expected_by_path[path]:
            errors.append(f"entry_mismatch:{path}")
    return {"passed": not errors, "errors": sorted(errors)}

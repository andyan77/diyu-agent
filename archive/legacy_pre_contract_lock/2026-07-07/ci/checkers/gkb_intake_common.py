#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

import yaml

READINESS_FLAGS = (
    "candidatepack_ready",
    "KE_ready",
    "RAG_ready",
    "DIFY_ready",
    "production_servable",
    "generation_eligible",
    "generation_allowed",
    "release_ready",
    "production_ready",
)

DATA_SUFFIXES = {".yaml", ".yml", ".json"}


@dataclass(frozen=True)
class Finding:
    code: str
    path: str
    message: str
    object_id: str = ""
    location: str = ""
    severity: str = "error"


@dataclass(frozen=True)
class GateResult:
    gate_id: str
    passed: bool
    findings: list[Finding]
    checked_files: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "gate_id": self.gate_id,
            "passed": self.passed,
            "checked_files": self.checked_files,
            "findings": [asdict(finding) for finding in self.findings],
        }


def is_true(value: Any) -> bool:
    return value is True or (isinstance(value, str) and value.strip().lower() == "true")


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def load_structured(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        return json.loads(text)
    return yaml.safe_load(text)


def load_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def iter_data_files(root: Path, dirs: Iterable[str] | None = None) -> list[Path]:
    if root.is_file():
        return [root] if root.suffix in DATA_SUFFIXES else []
    if dirs is None:
        return sorted(path for path in root.rglob("*") if path.is_file() and path.suffix in DATA_SUFFIXES)
    files: list[Path] = []
    for directory in dirs:
        target = root / directory
        if target.exists():
            files.extend(path for path in target.rglob("*") if path.is_file() and path.suffix in DATA_SUFFIXES)
    return sorted(files)


def iter_csv_files(root: Path, dirs: Iterable[str] | None = None) -> list[Path]:
    if root.is_file():
        return [root] if root.suffix == ".csv" else []
    if dirs is None:
        return sorted(path for path in root.rglob("*") if path.is_file() and path.suffix == ".csv")
    files: list[Path] = []
    for directory in dirs:
        target = root / directory
        if target.exists():
            files.extend(path for path in target.rglob("*") if path.is_file() and path.suffix == ".csv")
    return sorted(files)


def walk(value: Any, prefix: str = "$") -> list[tuple[str, Any, str]]:
    if isinstance(value, dict):
        rows: list[tuple[str, Any, str]] = []
        for key, child in value.items():
            location = f"{prefix}.{key}"
            rows.append((str(key), child, location))
            rows.extend(walk(child, location))
        return rows
    if isinstance(value, list):
        rows = []
        for index, child in enumerate(value):
            rows.extend(walk(child, f"{prefix}[{index}]"))
        return rows
    return []


def nested_get(data: dict[str, Any], keys: Iterable[str]) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def iter_candidate_objects(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        candidates: list[dict[str, Any]] = []
        if "candidate_id" in value:
            candidates.append(value)
        for child in value.values():
            candidates.extend(iter_candidate_objects(child))
        return candidates
    if isinstance(value, list):
        candidates = []
        for child in value:
            candidates.extend(iter_candidate_objects(child))
        return candidates
    return []


def iter_objects_with_any_key(value: Any, keys: set[str]) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        matches: list[dict[str, Any]] = []
        if any(key in value for key in keys):
            matches.append(value)
        for child in value.values():
            matches.extend(iter_objects_with_any_key(child, keys))
        return matches
    if isinstance(value, list):
        matches = []
        for child in value:
            matches.extend(iter_objects_with_any_key(child, keys))
        return matches
    return []


def has_source_anchor(candidate: dict[str, Any]) -> bool:
    source_pack_refs = as_list(candidate.get("source_pack_refs"))
    source_trace = candidate.get("source_trace")
    excerpt_refs = nested_get(candidate, ("source_trace", "source_excerpt_refs"))
    excerpt_digests = nested_get(candidate, ("source_trace", "excerpt_digests"))
    return bool(source_pack_refs) and isinstance(source_trace, dict) and bool(excerpt_refs) and bool(excerpt_digests)


def path_id(path: Path) -> str:
    return str(path)


def build_result(gate_id: str, checked_files: int, findings: list[Finding]) -> GateResult:
    return GateResult(gate_id=gate_id, passed=not findings, findings=findings, checked_files=checked_files)


def emit_result(result: GateResult, report_json: Path | None = None) -> None:
    payload = result.as_dict()
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)
    if report_json is not None:
        report_json.parent.mkdir(parents=True, exist_ok=True)
        report_json.write_text(text + "\n", encoding="utf-8")
    print(text)

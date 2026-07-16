"""确定性序列化、摘要与 JSONL 辅助函数。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


def digest_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def digest_json(value: Any) -> str:
    return digest_text(canonical_json(value))


def file_digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def canonical_jsonl(rows: Iterable[dict[str, Any]]) -> bytes:
    return ("".join(canonical_json(row) + "\n" for row in rows)).encode("utf-8")


def stable_id(prefix: str, *parts: Any) -> str:
    return f"{prefix}-{digest_json(list(parts))[:20]}"

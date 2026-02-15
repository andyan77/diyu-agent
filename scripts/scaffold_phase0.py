#!/usr/bin/env python3
"""DIYU Agent Phase 0 scaffold generator.

Checks and creates the directory structure and skeleton files required by
Phase 0 task cards.  Idempotent: existing files are never overwritten.

Usage:
    python3 scripts/scaffold_phase0.py          # Human-readable output
    python3 scripts/scaffold_phase0.py --json   # JSON output for CI
    python3 scripts/scaffold_phase0.py --check  # Dry-run: report only, create nothing

Exit codes:
    0 - All items present (or created successfully)
    1 - --check mode found missing items
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


# ------------------------------------------------------------------
# Scaffold specification
# ------------------------------------------------------------------


@dataclass
class Item:
    """A single file or directory expected by Phase 0."""

    path: str
    kind: str  # "dir" | "file"
    content: str = ""  # default content for new files
    source: str = ""  # task card reference


def _init(name: str) -> str:
    """Minimal __init__.py content."""
    return f'"""{name} package."""\n'


def _docker_compose_stub() -> str:
    return """\
# DIYU Agent Development Services
# Usage: docker compose up -d
version: "3.9"
services:
  postgres:
    image: pgvector/pgvector:pg16
    ports: ["5432:5432"]
    environment:
      POSTGRES_USER: diyu
      POSTGRES_PASSWORD: diyu_dev
      POSTGRES_DB: diyu
    volumes: ["pgdata:/var/lib/postgresql/data"]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  qdrant:
    image: qdrant/qdrant:v1.12.6
    ports: ["6333:6333", "6334:6334"]
    volumes: ["qdrant_data:/qdrant/storage"]

  neo4j:
    image: neo4j:5-community
    ports: ["7474:7474", "7687:7687"]
    environment:
      NEO4J_AUTH: neo4j/diyu_dev
    volumes: ["neo4j_data:/data"]

  minio:
    image: minio/minio:latest
    ports: ["9000:9000", "9001:9001"]
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: diyu
      MINIO_ROOT_PASSWORD: diyu_dev_minio
    volumes: ["minio_data:/data"]

volumes:
  pgdata:
  qdrant_data:
  neo4j_data:
  minio_data:
"""


def _eslint_stub() -> str:
    return """\
/** @type {import('eslint').Linter.Config} */
module.exports = {
  root: true,
  extends: ['next/core-web-vitals', 'plugin:jsx-a11y/recommended'],
  plugins: ['jsx-a11y'],
  rules: {},
};
"""


ITEMS: list[Item] = [
    # --- Backend layer modules ---
    Item("src/brain/__init__.py", "file", _init("Brain layer"), "B0-1"),
    Item("src/knowledge/__init__.py", "file", _init("Knowledge layer"), "K0-1"),
    Item("src/skill/__init__.py", "file", _init("Skill layer"), "S0-1"),
    Item("src/tool/__init__.py", "file", _init("Tool layer"), "T0-1"),
    Item("src/gateway/__init__.py", "file", _init("Gateway layer"), "G0-1"),
    Item("src/infra/__init__.py", "file", _init("Infrastructure layer"), "I0-1"),
    # --- Ports (already exist, verify only) ---
    Item("src/ports/__init__.py", "file", _init("Port interfaces (Day-1)"), "B0-2"),
    Item("src/ports/memory_core_port.py", "file", "", "MC0-1"),
    Item("src/ports/llm_call_port.py", "file", "", "T0-1"),
    Item("src/ports/knowledge_port.py", "file", "", "K0-1"),
    Item("src/ports/skill_registry.py", "file", "", "S0-1"),
    Item("src/ports/org_context.py", "file", "", "B0-2"),
    Item("src/ports/storage_port.py", "file", "", "B0-2"),
    # --- Shared types ---
    Item("src/shared/__init__.py", "file", _init("Shared types and errors"), "B0-1"),
    Item("src/shared/types", "dir", "", "B0-1"),
    Item("src/shared/errors", "dir", "", "B0-1"),
    # --- Test directories ---
    Item("tests/__init__.py", "file", "", "I0-6"),
    Item("tests/unit/__init__.py", "file", "", "I0-6"),
    Item("tests/unit/ports/__init__.py", "file", "", "MC0-2"),
    Item("tests/isolation/__init__.py", "file", "", "I0-6"),
    Item("tests/smoke", "dir", "", "I0-6"),
    # --- Migrations ---
    Item("migrations/versions", "dir", "", "I0-3"),
    # --- Docker Compose (dev) ---
    Item("docker-compose.yml", "file", _docker_compose_stub(), "I0-1"),
    # --- Frontend monorepo ---
    Item("frontend/pnpm-workspace.yaml", "file", "", "FW0-2"),
    Item("frontend/turbo.json", "file", "", "FW0-2"),
    Item("frontend/apps/web", "dir", "", "FW0-1"),
    Item("frontend/apps/admin", "dir", "", "FW0-1"),
    Item("frontend/packages/ui", "dir", "", "FW0-3"),
    Item("frontend/packages/shared", "dir", "", "FW0-4"),
    Item("frontend/packages/api-client", "dir", "", "FW0-5"),
    # --- Frontend quality tooling (skeleton configs) ---
    Item("frontend/.eslintrc.js", "file", _eslint_stub(), "FW0-6"),
    # --- Engineering configs ---
    Item("pyproject.toml", "file", "", "I0-2"),
    Item("Makefile", "file", "", "I0-4"),
    Item(".env.example", "file", "", "I0-5"),
    Item(".gitignore", "file", "", "I0-7"),
    Item(".editorconfig", "file", "", "I0-7"),
    Item("CLAUDE.md", "file", "", "Stage E"),
    Item("alembic.ini", "file", "", "I0-3"),
    # --- Delivery ---
    Item("delivery/milestone-matrix.yaml", "file", "", "Stage E"),
    Item("delivery/milestone-matrix.schema.yaml", "file", "", "Stage E"),
]


# ------------------------------------------------------------------
# Runner
# ------------------------------------------------------------------


@dataclass
class ScaffoldResult:
    path: str
    status: str  # "exists" | "created" | "missing" (check-only)
    source: str


def run(*, check_only: bool = False) -> list[ScaffoldResult]:
    results: list[ScaffoldResult] = []

    for item in ITEMS:
        full = ROOT / item.path

        if item.kind == "dir":
            if full.is_dir():
                results.append(ScaffoldResult(item.path, "exists", item.source))
            elif check_only:
                results.append(ScaffoldResult(item.path, "missing", item.source))
            else:
                full.mkdir(parents=True, exist_ok=True)
                results.append(ScaffoldResult(item.path, "created", item.source))
        else:  # file
            if full.exists():
                results.append(ScaffoldResult(item.path, "exists", item.source))
            elif check_only:
                results.append(ScaffoldResult(item.path, "missing", item.source))
            elif item.content:
                full.parent.mkdir(parents=True, exist_ok=True)
                full.write_text(item.content)
                results.append(ScaffoldResult(item.path, "created", item.source))
            else:
                # No default content and file does not exist -- flag missing
                results.append(ScaffoldResult(item.path, "missing", item.source))

    return results


def main() -> int:
    check_only = "--check" in sys.argv
    as_json = "--json" in sys.argv

    results = run(check_only=check_only)

    exists_count = sum(1 for r in results if r.status == "exists")
    created_count = sum(1 for r in results if r.status == "created")
    missing_count = sum(1 for r in results if r.status == "missing")

    if as_json:
        out = {
            "phase": 0,
            "mode": "check" if check_only else "scaffold",
            "total": len(results),
            "exists": exists_count,
            "created": created_count,
            "missing": missing_count,
            "items": [{"path": r.path, "status": r.status, "source": r.source} for r in results],
        }
        print(json.dumps(out, indent=2))
    else:
        for r in results:
            tag = {"exists": "OK", "created": "NEW", "missing": "MISS"}[r.status]
            print(f"  [{tag:4s}]  {r.path}  ({r.source})")
        print()
        print(
            f"  Total: {len(results)}  |  "
            f"Exists: {exists_count}  |  "
            f"Created: {created_count}  |  "
            f"Missing: {missing_count}"
        )

    if missing_count > 0 and check_only:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Scaffold a new ADR from the template.

Usage:
    python3 scripts/scaffold_adr.py "Title of Decision"
    make scaffold-adr TITLE="Title of Decision"

Creates docs/adr/ADR-NNN-slugified-title.md with auto-incremented number.
"""

from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path

ADR_DIR = Path("docs/adr")
TEMPLATE = ADR_DIR / "_template.md"


def next_number() -> int:
    """Find the highest existing ADR number and return +1."""
    max_num = 0
    for f in ADR_DIR.glob("ADR-*.md"):
        match = re.match(r"ADR-(\d+)", f.name)
        if match:
            max_num = max(max_num, int(match.group(1)))
    return max_num + 1


def slugify(title: str) -> str:
    """Convert title to filename-safe slug."""
    slug = title.lower().strip()
    slug = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", slug)
    return slug.strip("-")[:80]


def main() -> None:
    if len(sys.argv) < 2 or not sys.argv[1].strip():
        print("Usage: scaffold_adr.py <title>", file=sys.stderr)
        sys.exit(2)

    title = sys.argv[1].strip()
    num = next_number()
    slug = slugify(title)
    filename = f"ADR-{num:03d}-{slug}.md"
    target = ADR_DIR / filename

    if not TEMPLATE.exists():
        print(f"ERROR: template not found: {TEMPLATE}", file=sys.stderr)
        sys.exit(2)

    content = TEMPLATE.read_text()
    content = content.replace("ADR-NNN", f"ADR-{num:03d}")
    content = content.replace("Title", title, 1)
    # Add date after Status section
    content = content.replace(
        "Proposed | Accepted | Deprecated | Superseded by ADR-XXX",
        f"Proposed\n\n## Date\n\n{date.today().isoformat()}",
    )

    target.write_text(content)
    print(f"Created: {target}")


if __name__ == "__main__":
    main()

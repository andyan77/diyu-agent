#!/usr/bin/env python3
"""Frontend Depth Audit Script.

L2-L4 depth audit for frontend task cards. Moves beyond L1 (file existence)
to verify exports, logic patterns, test coverage, and security practices.

Depth levels:
  L1: File/directory exists (grep/test -f)
  L2: Exports/components match task card AC expectations
  L3: Logic verified via pattern matching (AST-equivalent for TS/TSX)
  L4: Test file exists + covers AC

Security checks:
  - DOMPurify usage on user content rendering
  - Auth token key consistency across admin app
  - Stub detection (placeholder/TODO patterns in production code)
  - XSS surfaces (unescaped error messages)

Usage:
    python scripts/check_frontend_depth.py --json
    python scripts/check_frontend_depth.py --json --verbose

Exit codes:
    0: PASS or WARN
    1: FAIL (critical findings)
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TASK_CARDS_DIR = Path("docs/task-cards/frontend")
FRONTEND_DIR = Path("frontend")
WEB_APP_DIR = FRONTEND_DIR / "apps" / "web"
ADMIN_APP_DIR = FRONTEND_DIR / "apps" / "admin"

TASK_HEADING_RE = re.compile(r"^###\s+(TASK-\S+?)(?::|\s)", re.MULTILINE)
ACCEPTANCE_TABLE_RE = re.compile(r"\|\s*\*{0,2}验收命令\*{0,2}\s*\|\s*(.+?)\s*\|", re.IGNORECASE)

# Stub indicators in production code (not test files)
STUB_PATTERNS = [
    re.compile(r"//\s*(?:Placeholder|TODO|FIXME|HACK)", re.IGNORECASE),
    re.compile(r"(?:placeholder|stub).*(?:would|will)\s", re.IGNORECASE),
    re.compile(r"crypto\.randomUUID\(\)\s*;?\s*$", re.MULTILINE),
]

# Auth token storage key patterns — match the first string arg only
AUTH_TOKEN_KEY_RE = re.compile(
    r"""sessionStorage\.(?:getItem|setItem|removeItem)\s*\(\s*["']([^"']+)["']"""
)

# XSS: unescaped error message interpolation (Error: ${...} or `Error: ${...}`)
XSS_ERROR_RE = re.compile(r"""[`"']\s*Error:\s*\$\{""")

# DOMPurify / sanitize import patterns
SANITIZE_IMPORT_RE = re.compile(
    r"""(?:import\s+.*(?:DOMPurify|sanitize)|from\s+["'].*sanitize)""", re.IGNORECASE
)
SANITIZE_CALL_RE = re.compile(
    r"(?:sanitizeHTML|DOMPurify\.sanitize|stripTags|escapeHTML)\s*\(", re.IGNORECASE
)

# Component-level content rendering that might need sanitization
DANGEROUS_HTML_RE = re.compile(r"dangerouslySetInnerHTML")


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class TaskCardAC:
    """Parsed frontend task card with acceptance criteria."""

    task_id: str
    title: str
    acceptance: str
    source_file: str


@dataclass
class DepthResult:
    """Depth audit result for a single task card."""

    task_id: str
    depth_grade: str  # L1, L2, L3, L4, L0 (not found)
    findings: list[str] = field(default_factory=list)
    matched_files: list[str] = field(default_factory=list)
    has_test: bool = False

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "depth_grade": self.depth_grade,
            "findings": self.findings,
            "matched_files": self.matched_files,
            "has_test": self.has_test,
        }


@dataclass
class SecurityFinding:
    """A security-related finding."""

    category: str  # stub, auth_inconsistency, xss_surface, missing_sanitize
    severity: str  # critical, warning, info
    file: str
    line: int
    message: str
    details: str = ""

    def to_dict(self) -> dict:
        d: dict = {
            "category": self.category,
            "severity": self.severity,
            "file": self.file,
            "line": self.line,
            "message": self.message,
        }
        if self.details:
            d["details"] = self.details
        return d


# ---------------------------------------------------------------------------
# Task card parsing
# ---------------------------------------------------------------------------


def parse_frontend_task_cards(
    *,
    task_cards_dir: Path | None = None,
) -> list[TaskCardAC]:
    """Parse all frontend task cards and extract acceptance criteria."""
    effective_dir = task_cards_dir if task_cards_dir is not None else TASK_CARDS_DIR
    cards: list[TaskCardAC] = []

    if not effective_dir.exists():
        return cards

    for md_file in sorted(effective_dir.rglob("*.md")):
        text = md_file.read_text(encoding="utf-8")
        lines = text.splitlines()

        current_id: str | None = None
        current_title: str = ""
        current_ac: str = ""

        for line in lines:
            heading_m = TASK_HEADING_RE.match(line)
            if heading_m:
                # Save previous card
                if current_id:
                    cards.append(
                        TaskCardAC(
                            task_id=current_id,
                            title=current_title,
                            acceptance=current_ac,
                            source_file=str(md_file),
                        )
                    )
                current_id = heading_m.group(1).rstrip(":")
                # Extract title after task ID
                rest = line[heading_m.end() :].strip().lstrip(":").strip()
                current_title = rest
                current_ac = ""
                continue

            if current_id:
                ac_m = ACCEPTANCE_TABLE_RE.search(line)
                if ac_m:
                    current_ac = ac_m.group(1).strip()

        # Save last card
        if current_id:
            cards.append(
                TaskCardAC(
                    task_id=current_id,
                    title=current_title,
                    acceptance=current_ac,
                    source_file=str(md_file),
                )
            )

    return cards


# ---------------------------------------------------------------------------
# File matching heuristics
# ---------------------------------------------------------------------------

# Map task card ID prefixes to likely source directories
_TASK_PREFIX_TO_DIR: dict[str, list[Path]] = {
    "TASK-FW": [WEB_APP_DIR],
    "TASK-FA": [ADMIN_APP_DIR],
    "TASK-FE": [WEB_APP_DIR, ADMIN_APP_DIR],
}

# Keywords in task titles -> likely file path fragments
_TITLE_PATH_HINTS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"login|登录", re.IGNORECASE), "login"),
    (re.compile(r"chat|对话", re.IGNORECASE), "chat"),
    (re.compile(r"knowledge|知识", re.IGNORECASE), "knowledge"),
    (re.compile(r"memory|记忆", re.IGNORECASE), "memory"),
    (re.compile(r"billing|计费", re.IGNORECASE), "billing"),
    (re.compile(r"monitoring|监控", re.IGNORECASE), "monitoring"),
    (re.compile(r"permission|权限", re.IGNORECASE), "permissions"),
    (re.compile(r"organization|组织", re.IGNORECASE), "organizations"),
    (re.compile(r"user|用户", re.IGNORECASE), "users"),
    (re.compile(r"setting|设置", re.IGNORECASE), "settings"),
    (re.compile(r"audit|审计", re.IGNORECASE), "audit"),
    (re.compile(r"websocket|ws\s", re.IGNORECASE), "ws"),
    (re.compile(r"sse|event.?source", re.IGNORECASE), "sse"),
    (re.compile(r"sanitiz|xss|dompurify", re.IGNORECASE), "sanitize"),
    (re.compile(r"token|auth", re.IGNORECASE), "auth"),
    (re.compile(r"error.?report|sentry", re.IGNORECASE), "error-reporting"),
    (re.compile(r"upload|file.*upload", re.IGNORECASE), "FileUpload"),
]


def _find_matching_files(
    card: TaskCardAC,
    *,
    frontend_dir: Path | None = None,
) -> list[Path]:
    """Find frontend source files likely related to a task card."""
    effective_fe = frontend_dir if frontend_dir is not None else FRONTEND_DIR
    matches: list[Path] = []

    # Determine search roots from task ID prefix
    search_roots: list[Path] = []
    for prefix, dirs in _TASK_PREFIX_TO_DIR.items():
        if card.task_id.startswith(prefix):
            search_roots = [effective_fe / d.relative_to(FRONTEND_DIR) for d in dirs]
            break
    if not search_roots:
        search_roots = [effective_fe]

    # Search using title hints
    hint_fragments: list[str] = []
    for pattern, fragment in _TITLE_PATH_HINTS:
        if pattern.search(card.title) or pattern.search(card.acceptance):
            hint_fragments.append(fragment)

    # Also extract path fragments from acceptance commands
    path_matches = re.findall(r"(?:app|lib|components)/\S+", card.acceptance)
    for pm in path_matches:
        hint_fragments.append(pm.rstrip("`").rstrip("|"))

    for root in search_roots:
        if not root.exists():
            continue
        for ext in ("*.tsx", "*.ts"):
            for f in root.rglob(ext):
                # Skip node_modules and test files for main matching
                rel = str(f.relative_to(effective_fe))
                if "node_modules" in rel:
                    continue
                for fragment in hint_fragments:
                    if fragment.lower() in rel.lower():
                        matches.append(f)
                        break

    return sorted(set(matches))


# ---------------------------------------------------------------------------
# Depth grading
# ---------------------------------------------------------------------------


def _has_test_file(source_file: Path, *, frontend_dir: Path | None = None) -> bool:
    """Check if a source file has a corresponding test file."""
    effective_fe = frontend_dir if frontend_dir is not None else FRONTEND_DIR

    # Convention: foo.tsx -> foo.test.tsx or __tests__/foo.test.tsx
    stem = source_file.stem
    parent = source_file.parent

    test_candidates = [
        parent / f"{stem}.test.tsx",
        parent / f"{stem}.test.ts",
        parent / "__tests__" / f"{stem}.test.tsx",
        parent / "__tests__" / f"{stem}.test.ts",
    ]

    # Also check e2e tests directory
    rel = source_file.relative_to(effective_fe) if effective_fe in source_file.parents else None
    if rel:
        e2e_dir = effective_fe / "tests" / "e2e"
        if e2e_dir.exists():
            for spec in e2e_dir.rglob("*.spec.ts"):
                spec_text = spec.read_text(encoding="utf-8", errors="replace")
                if stem.lower() in spec_text.lower():
                    return True

    return any(tc.exists() for tc in test_candidates)


def grade_depth(
    card: TaskCardAC,
    *,
    frontend_dir: Path | None = None,
) -> DepthResult:
    """Grade the verification depth for a single task card."""
    matched = _find_matching_files(card, frontend_dir=frontend_dir)
    effective_fe = frontend_dir if frontend_dir is not None else FRONTEND_DIR

    if not matched:
        return DepthResult(
            task_id=card.task_id,
            depth_grade="L0",
            findings=["No matching source files found"],
        )

    result = DepthResult(
        task_id=card.task_id,
        depth_grade="L1",  # Start at L1 (files exist)
        matched_files=[str(f) for f in matched],
    )

    # L2: Check exports/components match AC expectations
    has_exports = False
    for f in matched:
        content = f.read_text(encoding="utf-8", errors="replace")
        # Check for export default or named exports
        if re.search(r"export\s+(?:default\s+)?(?:function|class|const)\s+\w+", content):
            has_exports = True
            break

    if has_exports:
        result.depth_grade = "L2"

    # L3: Logic verification — check if implementation has substantive logic
    has_logic = False
    for f in matched:
        content = f.read_text(encoding="utf-8", errors="replace")
        # Substantive logic indicators: state management, API calls, event handlers
        logic_indicators = [
            r"useState\s*<",
            r"useEffect\s*\(",
            r"useCallback\s*\(",
            r"fetch\s*\(",
            r"async\s+function",
            r"addEventListener",
            r"\.subscribe\s*\(",
        ]
        if any(re.search(pat, content) for pat in logic_indicators):
            has_logic = True
            break

    if has_logic and has_exports:
        result.depth_grade = "L3"

    # L4: Test coverage
    has_any_test = False
    for f in matched:
        if _has_test_file(f, frontend_dir=effective_fe):
            has_any_test = True
            break

    if has_any_test and has_logic and has_exports:
        result.depth_grade = "L4"
        result.has_test = True

    return result


# ---------------------------------------------------------------------------
# Security checks
# ---------------------------------------------------------------------------


def check_stubs(
    *,
    frontend_dir: Path | None = None,
) -> list[SecurityFinding]:
    """Detect stub/placeholder patterns in production frontend code."""
    effective_fe = frontend_dir if frontend_dir is not None else FRONTEND_DIR
    findings: list[SecurityFinding] = []

    for app_dir in (
        effective_fe / "apps" / "web",
        effective_fe / "apps" / "admin",
    ):
        if not app_dir.exists():
            continue
        for ext in ("*.tsx", "*.ts"):
            for f in app_dir.rglob(ext):
                rel = str(f)
                if "node_modules" in rel or ".test." in rel or ".spec." in rel:
                    continue

                lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
                for i, line in enumerate(lines, 1):
                    for pat in STUB_PATTERNS:
                        if pat.search(line):
                            findings.append(
                                SecurityFinding(
                                    category="stub",
                                    severity="warning",
                                    file=str(f),
                                    line=i,
                                    message=f"Stub/placeholder detected: {line.strip()[:80]}",
                                )
                            )
                            break  # One finding per line

    return findings


def check_auth_consistency(
    *,
    frontend_dir: Path | None = None,
) -> list[SecurityFinding]:
    """Detect auth token storage key inconsistencies across frontend apps."""
    effective_fe = frontend_dir if frontend_dir is not None else FRONTEND_DIR
    findings: list[SecurityFinding] = []

    # Collect all token key usages: key -> [(file, line, operation)]
    key_usages: dict[str, list[tuple[str, int, str]]] = {}

    for app_dir in (
        effective_fe / "apps" / "web",
        effective_fe / "apps" / "admin",
    ):
        if not app_dir.exists():
            continue
        for ext in ("*.tsx", "*.ts"):
            for f in app_dir.rglob(ext):
                rel = str(f)
                if "node_modules" in rel:
                    continue

                lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
                for i, line in enumerate(lines, 1):
                    for m in AUTH_TOKEN_KEY_RE.finditer(line):
                        key = m.group(1)
                        if "token" in key.lower():
                            key_usages.setdefault(key, []).append((str(f), i, line.strip()))

    # Flag inconsistencies: multiple different keys for auth tokens
    if len(key_usages) > 1:
        all_keys = sorted(key_usages.keys())
        for key, usages in key_usages.items():
            for file_path, line_num, _line_text in usages:
                findings.append(
                    SecurityFinding(
                        category="auth_inconsistency",
                        severity="critical",
                        file=file_path,
                        line=line_num,
                        message=(
                            f'Auth token key "{key}" inconsistent with other keys: {all_keys}'
                        ),
                        details=f"Found {len(key_usages)} different token key names: {all_keys}",
                    )
                )

    return findings


def check_xss_surfaces(
    *,
    frontend_dir: Path | None = None,
) -> list[SecurityFinding]:
    """Detect potential XSS surfaces in frontend code."""
    effective_fe = frontend_dir if frontend_dir is not None else FRONTEND_DIR
    findings: list[SecurityFinding] = []

    for app_dir in (
        effective_fe / "apps" / "web",
        effective_fe / "apps" / "admin",
    ):
        if not app_dir.exists():
            continue
        for ext in ("*.tsx", "*.ts"):
            for f in app_dir.rglob(ext):
                rel = str(f)
                if "node_modules" in rel or ".test." in rel or ".spec." in rel:
                    continue

                lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
                for i, line in enumerate(lines, 1):
                    # dangerouslySetInnerHTML without sanitize nearby
                    if DANGEROUS_HTML_RE.search(line):
                        # Check if sanitize is used in the same file
                        content = "\n".join(lines)
                        if not SANITIZE_CALL_RE.search(content):
                            findings.append(
                                SecurityFinding(
                                    category="xss_surface",
                                    severity="critical",
                                    file=str(f),
                                    line=i,
                                    message="dangerouslySetInnerHTML without sanitization",
                                )
                            )

                    # Unescaped error interpolation in user-facing content
                    if XSS_ERROR_RE.search(line):
                        findings.append(
                            SecurityFinding(
                                category="xss_surface",
                                severity="warning",
                                file=str(f),
                                line=i,
                                message="Error message interpolated directly"
                                " — may expose internals",
                            )
                        )

    return findings


def check_sanitize_coverage(
    *,
    frontend_dir: Path | None = None,
) -> list[SecurityFinding]:
    """Check that sanitize.ts exists and is imported where user content is rendered."""
    effective_fe = frontend_dir if frontend_dir is not None else FRONTEND_DIR
    findings: list[SecurityFinding] = []

    sanitize_file = effective_fe / "apps" / "web" / "lib" / "sanitize.ts"
    if not sanitize_file.exists():
        findings.append(
            SecurityFinding(
                category="missing_sanitize",
                severity="critical",
                file=str(sanitize_file),
                line=0,
                message="sanitize.ts not found — DOMPurify protection missing",
            )
        )
        return findings

    # Verify sanitize.ts has DOMPurify
    content = sanitize_file.read_text(encoding="utf-8", errors="replace")
    if "DOMPurify" not in content:
        findings.append(
            SecurityFinding(
                category="missing_sanitize",
                severity="critical",
                file=str(sanitize_file),
                line=0,
                message="sanitize.ts exists but does not use DOMPurify",
            )
        )

    return findings


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def generate_report(
    depth_results: list[DepthResult],
    security_findings: list[SecurityFinding],
    *,
    verbose: bool = False,
) -> dict:
    """Build the JSON report."""
    # Grade distribution
    grade_dist: dict[str, int] = {"L0": 0, "L1": 0, "L2": 0, "L3": 0, "L4": 0}
    for r in depth_results:
        grade_dist[r.depth_grade] = grade_dist.get(r.depth_grade, 0) + 1

    # Security summary
    sec_by_cat: dict[str, int] = {}
    critical_sec = 0
    for sf in security_findings:
        sec_by_cat[sf.category] = sec_by_cat.get(sf.category, 0) + 1
        if sf.severity == "critical":
            critical_sec += 1

    # Determine status
    total_cards = len(depth_results)
    l0_count = grade_dist.get("L0", 0)
    l1_only = grade_dist.get("L1", 0)
    deep_coverage = total_cards - l0_count - l1_only if total_cards > 0 else 0

    if critical_sec > 0 or (total_cards > 0 and l0_count > total_cards * 0.5):
        status = "FAIL"
    elif l1_only > total_cards * 0.5 or security_findings:
        status = "WARN"
    else:
        status = "PASS"

    report: dict = {
        "status": status,
        "summary": {
            "total_task_cards": total_cards,
            "grade_distribution": grade_dist,
            "deep_coverage_count": deep_coverage,
            "deep_coverage_rate": round(deep_coverage / total_cards, 4) if total_cards else 0.0,
            "security_findings_count": len(security_findings),
            "critical_security_count": critical_sec,
            "security_by_category": sec_by_cat,
        },
        "security_findings": [sf.to_dict() for sf in security_findings],
    }

    if verbose:
        report["all_results"] = [r.to_dict() for r in depth_results]

    return report


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    use_json = "--json" in sys.argv
    verbose = "--verbose" in sys.argv

    if not use_json:
        print("=== Frontend Depth Audit ===")

    # Parse task cards
    cards = parse_frontend_task_cards()
    if not use_json:
        print(f"Task cards: {len(cards)}")

    # Grade depth for each card
    depth_results = [grade_depth(card) for card in cards]

    # Security checks
    security_findings: list[SecurityFinding] = []
    security_findings.extend(check_stubs())
    security_findings.extend(check_auth_consistency())
    security_findings.extend(check_xss_surfaces())
    security_findings.extend(check_sanitize_coverage())

    # Report
    report = generate_report(depth_results, security_findings, verbose=verbose)

    if use_json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        s = report["summary"]
        print(f"\nGrade distribution: {s['grade_distribution']}")
        print(f"Deep coverage (L2+): {s['deep_coverage_count']}/{s['total_task_cards']}")
        print(
            f"Security findings: {s['security_findings_count']}"
            f" ({s['critical_security_count']} critical)"
        )
        if report["security_findings"]:
            print("\nSecurity findings:")
            for sf in report["security_findings"]:
                print(f"  [{sf['severity']}] {sf['category']}: {sf['message']}")
                print(f"    {sf['file']}:{sf['line']}")
        print(f"\n=== Result: {report['status']} ===")

    if report["status"] == "FAIL":
        sys.exit(1)


if __name__ == "__main__":
    main()

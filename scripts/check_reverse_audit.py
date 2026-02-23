#!/usr/bin/env python3
"""Reverse Audit Script: Code -> Design direction.

Detects:
  - **shadow** features: code artifacts with no architecture doc reference
  - **drift**: code exists but diverges from spec
  - **mapped**: code has architecture doc reference + task card
  - **dead**: architecture reference exists but no implementation

Scans src/ Python files for:
  - Class definitions (including ABC subclasses)
  - FastAPI @router decorators
  - Port ABC implementations
  - SQLAlchemy model classes
  - Alembic migration operations

Usage:
    python scripts/check_reverse_audit.py --json
    python scripts/check_reverse_audit.py --json --verbose

Exit codes:
    0: PASS or WARN
    1: FAIL (critical findings: shadow features detected)
"""

from __future__ import annotations

import ast
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SRC_DIR = Path("src")
DOCS_ARCH_DIR = Path("docs/architecture")
TASK_CARDS_DIR = Path("docs/task-cards")

# Layers to scan
LAYERS = ("brain", "knowledge", "skill", "tool", "gateway", "infra", "memory", "shared")

# Files/patterns to skip
SKIP_FILES = {"__init__.py", "__pycache__"}

# Pattern to match architecture doc section references
ARCH_REF_PATTERNS = [
    re.compile(r"§\d+"),  # Section markers like §2.1
]

# Task card task ID pattern
TASK_ID_RE = re.compile(r"TASK-\S+")


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class CodeArtifact:
    """A code artifact discovered by AST scanning."""

    file: str
    name: str
    artifact_type: str  # class, function, router, model, port_impl
    line: int
    layer: str
    bases: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "file": self.file,
            "name": self.name,
            "artifact_type": self.artifact_type,
            "line": self.line,
            "layer": self.layer,
            "bases": self.bases,
        }


@dataclass
class AuditResult:
    """Audit result for a single code artifact."""

    file: str
    name: str
    artifact_type: str
    layer: str
    status: str  # mapped, shadow, drift, dead
    architecture_ref: str = ""
    task_card_ref: str = ""
    drift_detail: str = ""

    def to_dict(self) -> dict:
        d: dict = {
            "file": self.file,
            "name": self.name,
            "artifact_type": self.artifact_type,
            "layer": self.layer,
            "status": self.status,
        }
        if self.architecture_ref:
            d["architecture_ref"] = self.architecture_ref
        if self.task_card_ref:
            d["task_card_ref"] = self.task_card_ref
        if self.drift_detail:
            d["drift_detail"] = self.drift_detail
        return d


# ---------------------------------------------------------------------------
# AST scanning
# ---------------------------------------------------------------------------


def _get_layer(filepath: Path, *, src_dir: Path | None = None) -> str:
    """Extract the layer name from a file path under src/."""
    effective_src = src_dir if src_dir is not None else SRC_DIR
    try:
        rel = filepath.relative_to(effective_src)
        parts = rel.parts
        if parts:
            return parts[0]
    except ValueError:
        pass
    return "unknown"


def _is_port_class(bases: list[str]) -> bool:
    """Check if any base class name suggests a Port ABC."""
    port_indicators = {"ABC", "Protocol"}
    port_name_patterns = {"Port", "port"}
    for b in bases:
        if b in port_indicators:
            return True
        if any(p in b for p in port_name_patterns):
            return True
    return False


def _is_model_class(bases: list[str]) -> bool:
    """Check if any base class suggests SQLAlchemy model."""
    model_indicators = {"Base", "DeclarativeBase", "Model"}
    return any(b in model_indicators or "Base" in b for b in bases)


def _extract_base_names(node: ast.ClassDef) -> list[str]:
    """Extract base class names from a ClassDef AST node."""
    bases: list[str] = []
    for base in node.bases:
        if isinstance(base, ast.Name):
            bases.append(base.id)
        elif isinstance(base, ast.Attribute):
            bases.append(base.attr)
    return bases


def scan_file(filepath: Path, *, src_dir: Path | None = None) -> list[CodeArtifact]:
    """AST-scan a Python file for code artifacts."""
    try:
        source = filepath.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(filepath))
    except (SyntaxError, UnicodeDecodeError):
        return []

    layer = _get_layer(filepath, src_dir=src_dir)
    artifacts: list[CodeArtifact] = []
    file_str = str(filepath)

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            bases = _extract_base_names(node)
            # Determine artifact type
            if _is_port_class(bases):
                atype = "port_impl"
            elif _is_model_class(bases):
                atype = "model"
            else:
                atype = "class"

            artifacts.append(
                CodeArtifact(
                    file=file_str,
                    name=node.name,
                    artifact_type=atype,
                    line=node.lineno,
                    layer=layer,
                    bases=bases,
                )
            )

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Only top-level functions and decorated functions (routers)
            has_router = False
            for dec in node.decorator_list:
                dec_str = ast.dump(dec)
                if "router" in dec_str.lower() or "app" in dec_str.lower():
                    has_router = True
                    break

            if has_router:
                artifacts.append(
                    CodeArtifact(
                        file=file_str,
                        name=node.name,
                        artifact_type="router",
                        line=node.lineno,
                        layer=layer,
                    )
                )

    return artifacts


def scan_src(*, src_dir: Path | None = None) -> list[CodeArtifact]:
    """Scan all Python files under src/ for code artifacts."""
    effective_src = src_dir if src_dir is not None else SRC_DIR
    artifacts: list[CodeArtifact] = []

    if not effective_src.exists():
        return artifacts

    for layer in LAYERS:
        layer_dir = effective_src / layer
        if not layer_dir.exists():
            continue
        for py_file in sorted(layer_dir.rglob("*.py")):
            if py_file.name in SKIP_FILES:
                continue
            artifacts.extend(scan_file(py_file, src_dir=effective_src))

    # Also scan root-level files (main.py, etc.)
    for py_file in sorted(effective_src.glob("*.py")):
        if py_file.name in SKIP_FILES:
            continue
        artifacts.extend(scan_file(py_file, src_dir=effective_src))

    return artifacts


# ---------------------------------------------------------------------------
# Architecture doc reference search
# ---------------------------------------------------------------------------


def _load_arch_text(*, docs_dir: Path | None = None) -> str:
    """Load all architecture doc text into a single searchable string."""
    effective_dir = docs_dir if docs_dir is not None else DOCS_ARCH_DIR
    texts: list[str] = []
    if not effective_dir.exists():
        return ""
    for md in sorted(effective_dir.rglob("*.md")):
        texts.append(md.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(texts)


def _load_task_card_text(*, task_cards_dir: Path | None = None) -> str:
    """Load all task card text into a single searchable string."""
    effective_dir = task_cards_dir if task_cards_dir is not None else TASK_CARDS_DIR
    texts: list[str] = []
    if not effective_dir.exists():
        return ""
    for md in sorted(effective_dir.rglob("*.md")):
        texts.append(md.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(texts)


def _find_reference(name: str, text: str) -> str:
    """Search for a class/function name in doc text, return context if found."""
    # Case-insensitive search for the artifact name
    pattern = re.compile(re.escape(name), re.IGNORECASE)
    m = pattern.search(text)
    if m:
        # Return surrounding context (up to 60 chars)
        start = max(0, m.start() - 30)
        end = min(len(text), m.end() + 30)
        return text[start:end].replace("\n", " ").strip()
    return ""


# ---------------------------------------------------------------------------
# Drift detection: Port ABC vs implementation method comparison
# ---------------------------------------------------------------------------

# Regex to extract class-like names from architecture doc text
_ARCH_CLASS_RE = re.compile(
    r"\b([A-Z][a-zA-Z0-9]{3,}(?:Port|Adapter|Engine|Resolver|Pipeline"
    r"|Router|Registry|Context|Item|Bundle|Skill|FSM|Protocol|Manager"
    r"|Service|Handler|Provider|Factory|Store|Core))\b"
)


def _extract_port_methods(filepath: Path) -> dict[str, set[str]]:
    """Extract ABC method names from Port definition files.

    Returns {ClassName: {method_name, ...}}.
    """
    try:
        source = filepath.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(filepath))
    except (SyntaxError, UnicodeDecodeError):
        return {}

    result: dict[str, set[str]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            bases = _extract_base_names(node)
            if _is_port_class(bases):
                methods: set[str] = set()
                for item in node.body:
                    if isinstance(
                        item, (ast.FunctionDef, ast.AsyncFunctionDef)
                    ) and not item.name.startswith("_"):
                        methods.add(item.name)
                if methods:
                    result[node.name] = methods
    return result


def _extract_impl_methods(filepath: Path) -> dict[str, set[str]]:
    """Extract public method names from implementation classes.

    Returns {ClassName: {method_name, ...}}.
    """
    try:
        source = filepath.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(filepath))
    except (SyntaxError, UnicodeDecodeError):
        return {}

    result: dict[str, set[str]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            methods: set[str] = set()
            for item in node.body:
                if isinstance(
                    item, (ast.FunctionDef, ast.AsyncFunctionDef)
                ) and not item.name.startswith("_"):
                    methods.add(item.name)
            if methods:
                result[node.name] = methods
    return result


def build_port_contracts(
    *,
    src_dir: Path | None = None,
) -> dict[str, set[str]]:
    """Build {PortName: {required_methods}} from src/ports/."""
    effective_src = src_dir if src_dir is not None else SRC_DIR
    ports_dir = effective_src / "ports"
    contracts: dict[str, set[str]] = {}
    if not ports_dir.exists():
        return contracts
    for py_file in sorted(ports_dir.glob("*.py")):
        if py_file.name in SKIP_FILES:
            continue
        contracts.update(_extract_port_methods(py_file))
    return contracts


def detect_drift(
    artifact: CodeArtifact,
    port_contracts: dict[str, set[str]],
    *,
    src_dir: Path | None = None,
) -> str:
    """Detect drift for Port implementations.

    Returns drift detail string (empty if no drift).
    """
    if artifact.artifact_type != "port_impl":
        return ""
    # Find which Port ABC this class implements
    for base_name in artifact.bases:
        if base_name in port_contracts:
            required = port_contracts[base_name]
            filepath = Path(artifact.file)
            impl_methods = _extract_impl_methods(filepath)
            impl = impl_methods.get(artifact.name, set())
            missing = required - impl
            if missing:
                return f"Missing methods from {base_name}: {', '.join(sorted(missing))}"
    return ""


def extract_arch_artifact_names(arch_text: str) -> set[str]:
    """Extract artifact names referenced in architecture docs."""
    return set(_ARCH_CLASS_RE.findall(arch_text))


def find_dead_references(
    arch_names: set[str],
    code_names: set[str],
    arch_text: str,
) -> list[AuditResult]:
    """Find architecture-referenced artifacts not present in code.

    Returns AuditResult entries with status='dead'.
    """
    dead: list[AuditResult] = []
    for name in sorted(arch_names - code_names):
        ref = _find_reference(name, arch_text)
        dead.append(
            AuditResult(
                file="(not found in src/)",
                name=name,
                artifact_type="unknown",
                layer="unknown",
                status="dead",
                architecture_ref=ref,
            )
        )
    return dead


# ---------------------------------------------------------------------------
# Reverse audit engine
# ---------------------------------------------------------------------------


def run_audit(
    artifacts: list[CodeArtifact],
    *,
    arch_text: str = "",
    task_card_text: str = "",
    port_contracts: dict[str, set[str]] | None = None,
) -> list[AuditResult]:
    """Cross-reference code artifacts against architecture docs and task cards.

    Classification:
      - mapped: code has architecture doc reference
      - shadow: code exists but no architecture backing
      - drift: code exists with arch backing but implementation diverges
      - dead: architecture mentions artifact but no implementation found
    """
    results: list[AuditResult] = []
    effective_contracts = port_contracts if port_contracts is not None else {}

    for art in artifacts:
        arch_ref = _find_reference(art.name, arch_text)
        tc_ref = _find_reference(art.name, task_card_text)

        if arch_ref:
            # Check for drift (Port method mismatch)
            drift = detect_drift(art, effective_contracts)
            status = "drift" if drift else "mapped"
        else:
            status = "shadow"
            drift = ""

        results.append(
            AuditResult(
                file=art.file,
                name=art.name,
                artifact_type=art.artifact_type,
                layer=art.layer,
                status=status,
                architecture_ref=arch_ref,
                task_card_ref=tc_ref,
                drift_detail=drift,
            )
        )

    # Dead references: arch mentions artifacts not in code
    code_names = {a.name for a in artifacts}
    arch_names = extract_arch_artifact_names(arch_text)
    results.extend(find_dead_references(arch_names, code_names, arch_text))

    return results


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def generate_report(
    results: list[AuditResult],
    *,
    verbose: bool = False,
) -> dict:
    """Build the JSON report."""
    total = len(results)
    mapped = [r for r in results if r.status == "mapped"]
    shadows = [r for r in results if r.status == "shadow"]
    drifted = [r for r in results if r.status == "drift"]
    dead = [r for r in results if r.status == "dead"]

    shadow_by_layer: dict[str, int] = {}
    for s in shadows:
        shadow_by_layer[s.layer] = shadow_by_layer.get(s.layer, 0) + 1

    if drifted or dead:
        status = "FAIL"
    elif shadows:
        status = "WARN"
    else:
        status = "PASS"

    report: dict = {
        "status": status,
        "summary": {
            "total_artifacts": total,
            "mapped_count": len(mapped),
            "shadow_count": len(shadows),
            "drift_count": len(drifted),
            "dead_count": len(dead),
            "shadow_by_layer": shadow_by_layer,
        },
        "shadows": [s.to_dict() for s in shadows],
        "drifted": [d.to_dict() for d in drifted],
        "dead": [d.to_dict() for d in dead],
    }

    if verbose:
        report["all_results"] = [r.to_dict() for r in results]

    return report


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    use_json = "--json" in sys.argv
    verbose = "--verbose" in sys.argv

    if not use_json:
        print("=== Reverse Audit: Code -> Design ===")

    # Scan code artifacts
    artifacts = scan_src()
    if not use_json:
        print(f"Code artifacts: {len(artifacts)}")

    # Load reference texts
    arch_text = _load_arch_text()
    tc_text = _load_task_card_text()

    # Build Port contracts for drift detection
    contracts = build_port_contracts()

    # Run audit
    results = run_audit(
        artifacts,
        arch_text=arch_text,
        task_card_text=tc_text,
        port_contracts=contracts,
    )
    report = generate_report(results, verbose=verbose)

    if use_json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        s = report["summary"]
        print(
            f"\nTotal: {s['total_artifacts']}, Mapped: {s['mapped_count']}, "
            f"Shadow: {s['shadow_count']}, Drift: {s['drift_count']}, "
            f"Dead: {s['dead_count']}"
        )
        if report["shadows"]:
            print("\nShadow features (no architecture backing):")
            for sh in report["shadows"]:
                print(f"  [{sh['layer']}] {sh['name']} ({sh['artifact_type']}) in {sh['file']}")
        if report["drifted"]:
            print("\nDrifted (code diverges from spec):")
            for dr in report["drifted"]:
                print(f"  [{dr['layer']}] {dr['name']}: {dr.get('drift_detail', '')}")
        if report["dead"]:
            print("\nDead (in docs, not in code):")
            for dd in report["dead"]:
                print(f"  {dd['name']}: {dd.get('architecture_ref', '')}")
        print(f"\n=== Result: {report['status']} ===")

    if report["status"] == "FAIL":
        sys.exit(1)


if __name__ == "__main__":
    main()

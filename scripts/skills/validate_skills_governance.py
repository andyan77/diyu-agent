#!/usr/bin/env python3
"""Unified Skills Governance Validator.

Checks all D1-D12 requirements from opus-skills-gap-closure-instructions-v1.0.md:
1. 4 pattern + 4 guard skills exist
2. Every SKILL.md has compliant frontmatter (only name/description)
3. Every skill has agents/openai.yaml with required fields
4. taskcard-governance has W1-W4 handoff scripts
5. Latest skill session log exists and is replayable
6. 3 Agents have task-card-aware anchor points

Usage:
    python scripts/skills/validate_skills_governance.py
    python scripts/skills/validate_skills_governance.py --json

Exit codes: 0 = all pass, 1 = failures found
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = ROOT / ".claude" / "skills"
AGENTS_DIR = ROOT / ".claude" / "agents"

PATTERN_SKILLS = [
    "taskcard-governance",
    "systematic-review",
    "cross-reference-audit",
    "adversarial-fix-verification",
]

GUARD_SKILLS = [
    "guard-layer-boundary",
    "guard-port-compat",
    "guard-migration-safety",
    "guard-taskcard-schema",
]

ALL_SKILLS = PATTERN_SKILLS + GUARD_SKILLS

AGENT_FILES = [
    "diyu-architect.md",
    "diyu-tdd-guide.md",
    "diyu-security-reviewer.md",
]

W_SCRIPTS = [
    "run_w1_schema_normalization.sh",
    "run_w2_traceability_link.sh",
    "run_w3_acceptance_normalizer.sh",
    "run_w4_evidence_gate.sh",
    "run_all.sh",
]

OPENAI_REQUIRED_FIELDS = [
    "interface.display_name",
    "interface.short_description",
    "interface.default_prompt",
]


def check_result(name: str, passed: bool, detail: str = "", *, warn: bool = False) -> dict:
    if passed:
        status = "pass"
    elif warn:
        status = "warn"
    else:
        status = "fail"
    return {"check": name, "status": status, "detail": detail}


def validate_all() -> list[dict]:
    results = []

    # 1. Check 4 pattern + 4 guard skills exist
    for skill in ALL_SKILLS:
        skill_dir = SKILLS_DIR / skill
        skill_md = skill_dir / "SKILL.md"
        exists = skill_md.exists()
        results.append(
            check_result(f"skill-exists:{skill}", exists, str(skill_md) if not exists else "")
        )

    # 2. Frontmatter compliance (only name + description, no metadata)
    for skill in ALL_SKILLS:
        skill_md = SKILLS_DIR / skill / "SKILL.md"
        if not skill_md.exists():
            results.append(check_result(f"frontmatter:{skill}", False, "file missing"))
            continue

        text = skill_md.read_text()
        if not text.startswith("---"):
            results.append(check_result(f"frontmatter:{skill}", False, "no frontmatter"))
            continue

        parts = text.split("---", 2)
        if len(parts) < 3:
            results.append(check_result(f"frontmatter:{skill}", False, "unclosed frontmatter"))
            continue

        fm = parts[1]
        has_name = "name:" in fm
        has_desc = "description:" in fm
        has_metadata = "metadata:" in fm
        ok = has_name and has_desc and not has_metadata
        detail = ""
        if not has_name:
            detail = "missing name"
        elif not has_desc:
            detail = "missing description"
        elif has_metadata:
            detail = "contains metadata (forbidden)"
        results.append(check_result(f"frontmatter:{skill}", ok, detail))

    # 3. agents/openai.yaml existence and fields
    for skill in ALL_SKILLS:
        yaml_path = SKILLS_DIR / skill / "agents" / "openai.yaml"
        if not yaml_path.exists():
            results.append(check_result(f"openai-yaml:{skill}", False, "missing"))
            continue

        content = yaml_path.read_text()
        # Check required fields (simple string check, not full YAML parse)
        missing = []
        if "display_name" not in content:
            missing.append("display_name")
        if "short_description" not in content:
            missing.append("short_description")
        if "default_prompt" not in content:
            missing.append("default_prompt")

        # Check $skill-name pattern in default_prompt
        has_skill_ref = "$" in content
        if not has_skill_ref:
            missing.append("$skill-name in default_prompt")

        # Check all string fields are quoted
        lines = content.strip().splitlines()
        unquoted = []
        for line in lines:
            if ":" in line and not line.strip().startswith("#"):
                key, _, val = line.partition(":")
                val = val.strip()
                if (
                    val
                    and not val.startswith('"')
                    and not val.startswith("'")
                    and val not in ("", "|", ">")
                    and not val.endswith(":")
                ):
                    unquoted.append(key.strip())

        if unquoted:
            missing.append(f"unquoted fields: {', '.join(unquoted)}")

        results.append(
            check_result(
                f"openai-yaml:{skill}", len(missing) == 0, "; ".join(missing) if missing else ""
            )
        )

    # 4. taskcard-governance W1-W4 scripts
    scripts_dir = SKILLS_DIR / "taskcard-governance" / "scripts"
    for script in W_SCRIPTS:
        script_path = scripts_dir / script
        exists = script_path.exists()
        results.append(check_result(f"w-script:{script}", exists))
        if exists:
            content = script_path.read_text()
            # Must not be placeholder (echo-only)
            is_real = "set -euo pipefail" in content and "echo PASS" not in content
            results.append(
                check_result(
                    f"w-script-real:{script}",
                    is_real,
                    "placeholder detected" if not is_real else "",
                )
            )

    # 5. Session log replayable
    # In CI (no .audit/ dir), this is a warning, not a hard failure.
    audit_dir = ROOT / ".audit"
    is_ci = os.environ.get("CI", "").lower() == "true"
    logs = (
        sorted(audit_dir.glob("skill-session-*.jsonl"), reverse=True) if audit_dir.exists() else []
    )
    has_log = len(logs) > 0
    results.append(
        check_result(
            "session-log-exists",
            has_log,
            str(logs[0])
            if has_log
            else ("no logs in .audit/ (CI environment)" if is_ci else "no logs in .audit/"),
            warn=not has_log and is_ci,
        )
    )
    if has_log:
        # Check it has at least one valid JSONL entry
        try:
            with open(logs[0]) as f:
                first_line = f.readline().strip()
            entry = json.loads(first_line)
            has_fields = all(k in entry for k in ["skill", "step", "status"])
            results.append(check_result("session-log-valid", has_fields))
        except (json.JSONDecodeError, IndexError):
            results.append(check_result("session-log-valid", False, "invalid JSONL"))

    # 6. Agent task-card-aware anchors
    for agent_file in AGENT_FILES:
        agent_path = AGENTS_DIR / agent_file
        if not agent_path.exists():
            results.append(check_result(f"agent-anchor:{agent_file}", False, "file missing"))
            continue
        text = agent_path.read_text()
        has_anchor = "ANCHOR:task-card-aware" in text
        results.append(
            check_result(
                f"agent-anchor:{agent_file}",
                has_anchor,
                "" if has_anchor else "missing task-card-aware anchor",
            )
        )

    return results


def main() -> None:
    as_json = "--json" in sys.argv
    results = validate_all()

    failures = [r for r in results if r["status"] == "fail"]
    warnings = [r for r in results if r["status"] == "warn"]
    passes = [r for r in results if r["status"] == "pass"]

    if as_json:
        output = {
            "total": len(results),
            "passed": len(passes),
            "warned": len(warnings),
            "failed": len(failures),
            "results": results,
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        print("=" * 60)
        print("  Skills Governance Validation")
        print("=" * 60)
        print(f"  Total checks: {len(results)}")
        print(f"  Passed:       {len(passes)}")
        if warnings:
            print(f"  Warnings:     {len(warnings)}")
        print(f"  Failed:       {len(failures)}")
        print()

        if warnings:
            print("WARNINGS:")
            for w in warnings:
                detail = f" -- {w['detail']}" if w["detail"] else ""
                print(f"  WARN: {w['check']}{detail}")
            print()

        if failures:
            print("FAILURES:")
            for f in failures:
                detail = f" -- {f['detail']}" if f["detail"] else ""
                print(f"  FAIL: {f['check']}{detail}")
            print()

        print("=" * 60)
        if failures:
            print(f"  RESULT: FAIL ({len(failures)} checks failed)")
        elif warnings:
            print(f"  RESULT: PASS with warnings ({len(warnings)} warnings)")
        else:
            print(f"  RESULT: PASS (all {len(results)} checks passed)")
        print("=" * 60)

    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()

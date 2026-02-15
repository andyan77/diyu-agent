"""Tests for taskcard-governance workflow handoff (D3-D5).

Covers:
- W1-W4 scripts produce correct artifact structure
- run_all.sh orchestrates in correct order
- Session logger produces valid JSONL
- Replay script can parse logged entries
- Real script execution (not echo placeholder)
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import ClassVar

import pytest

ROOT = Path(__file__).resolve().parents[3]
SKILLS_DIR = ROOT / ".claude" / "skills"
TC_SCRIPTS = SKILLS_DIR / "taskcard-governance" / "scripts"


class TestWorkflowScriptStructure:
    """Each W script must have correct internal structure."""

    W_SCRIPTS: ClassVar[list[str]] = [
        "run_w1_schema_normalization.sh",
        "run_w2_traceability_link.sh",
        "run_w3_acceptance_normalizer.sh",
        "run_w4_evidence_gate.sh",
    ]

    @pytest.mark.parametrize("script", W_SCRIPTS)
    def test_creates_output_dir(self, script: str) -> None:
        text = (TC_SCRIPTS / script).read_text()
        assert "mkdir -p" in text, f"{script} does not create output directory"

    @pytest.mark.parametrize("script", W_SCRIPTS)
    def test_writes_input_json(self, script: str) -> None:
        text = (TC_SCRIPTS / script).read_text()
        assert "input.json" in text, f"{script} does not write input.json"

    @pytest.mark.parametrize("script", W_SCRIPTS)
    def test_writes_output_json(self, script: str) -> None:
        text = (TC_SCRIPTS / script).read_text()
        assert "output.json" in text, f"{script} does not write output.json"

    @pytest.mark.parametrize("script", W_SCRIPTS)
    def test_writes_next_step(self, script: str) -> None:
        text = (TC_SCRIPTS / script).read_text()
        assert "next-step.md" in text, f"{script} does not write next-step.md"

    @pytest.mark.parametrize("script", W_SCRIPTS)
    def test_failure_md_on_fail(self, script: str) -> None:
        text = (TC_SCRIPTS / script).read_text()
        assert "failure.md" in text, f"{script} does not write failure.md on failure"

    @pytest.mark.parametrize("script", W_SCRIPTS)
    def test_uses_session_id(self, script: str) -> None:
        text = (TC_SCRIPTS / script).read_text()
        assert "SESSION_ID" in text, f"{script} does not use SESSION_ID"


class TestRunAllOrchestration:
    """run_all.sh must orchestrate W1-W4 in correct order."""

    def test_run_all_exists(self) -> None:
        assert (TC_SCRIPTS / "run_all.sh").exists()

    def test_correct_order(self) -> None:
        text = (TC_SCRIPTS / "run_all.sh").read_text()
        w1_pos = text.find("run_w1")
        w2_pos = text.find("run_w2")
        w3_pos = text.find("run_w3")
        w4_pos = text.find("run_w4")
        assert w1_pos < w2_pos < w3_pos < w4_pos, "W scripts not in W1->W2->W3->W4 order"

    def test_stops_on_failure(self) -> None:
        text = (TC_SCRIPTS / "run_all.sh").read_text()
        assert "exit 1" in text, "run_all.sh does not stop on failure"

    def test_exports_session_id(self) -> None:
        text = (TC_SCRIPTS / "run_all.sh").read_text()
        assert "export SESSION_ID" in text, "run_all.sh does not export SESSION_ID"


class TestSessionLoggerUnit:
    """Session logger produces valid JSONL entries."""

    def test_logger_syntax_valid(self) -> None:
        result = subprocess.run(
            [
                "uv",
                "run",
                "python",
                "-c",
                "import ast; ast.parse(open('scripts/skills/skill_session_logger.py').read())",
            ],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
        )
        assert result.returncode == 0

    def test_logger_writes_jsonl(self) -> None:
        """Actually invoke the logger and verify output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            audit_dir = Path(tmpdir) / ".audit"
            audit_dir.mkdir()

            env = os.environ.copy()
            env["SESSION_ID"] = "test-session-001"

            # We need to run from ROOT but write .audit to tmpdir
            # Use a wrapper that changes the .audit location
            result = subprocess.run(
                [
                    "uv",
                    "run",
                    "python",
                    "-c",
                    f"""
import sys, os
sys.path.insert(0, 'scripts/skills')
os.environ['SESSION_ID'] = 'test-session-001'
import skill_session_logger as logger
def patched():
    from pathlib import Path
    return Path('{audit_dir}/skill-session-test-session-001.jsonl')
logger.get_session_log_path = patched
path = logger.log_step('test-skill', 'W1', 'pass', artifacts_dir='/tmp/test')
print(f'wrote to {{path}}')
""",
                ],
                capture_output=True,
                text=True,
                cwd=str(ROOT),
            )
            assert result.returncode == 0, f"Logger failed: {result.stderr}"

            log_file = audit_dir / "skill-session-test-session-001.jsonl"
            assert log_file.exists(), "Logger did not create JSONL file"
            line = log_file.read_text().strip()
            entry = json.loads(line)
            assert entry["skill"] == "test-skill"
            assert entry["step"] == "W1"
            assert entry["status"] == "pass"


class TestReplayScriptUnit:
    """Replay script must parse JSONL and produce summary."""

    def test_replay_syntax_valid(self) -> None:
        result = subprocess.run(
            [
                "uv",
                "run",
                "python",
                "-c",
                "import ast; ast.parse(open('scripts/skills/replay_skill_session.py').read())",
            ],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
        )
        assert result.returncode == 0

    def test_replay_parses_jsonl(self) -> None:
        """Create a test JSONL and replay it."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            entries = [
                {
                    "timestamp": "2026-02-15T12:00:00Z",
                    "skill": "test",
                    "step": "W1",
                    "status": "pass",
                    "session_id": "test-001",
                },
                {
                    "timestamp": "2026-02-15T12:01:00Z",
                    "skill": "test",
                    "step": "W2",
                    "status": "pass",
                    "session_id": "test-001",
                },
            ]
            for e in entries:
                f.write(json.dumps(e) + "\n")
            tmpfile = f.name

        try:
            result = subprocess.run(
                [
                    "uv",
                    "run",
                    "python",
                    "scripts/skills/replay_skill_session.py",
                    "--file",
                    tmpfile,
                    "--json",
                ],
                capture_output=True,
                text=True,
                cwd=str(ROOT),
            )
            assert result.returncode == 0, f"Replay failed: {result.stderr}"
            summary = json.loads(result.stdout)
            assert summary["entries"] == 2
            assert summary["passed"] == 2
            assert summary["failed"] == 0
        finally:
            os.unlink(tmpfile)

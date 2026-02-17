"""Tests for task_card_traceability_check.py.

TDD RED phase: These tests define expected behavior BEFORE implementation.
Tests cover:
  - Chinese regex matching (> 矩阵条目: ID)
  - English regex matching (> Matrix ref: ID) for backward compat
  - M-Track cross-reference extraction
  - Dual coverage output (main_coverage vs all_coverage)
  - Threshold-based PASS/FAIL

Uses DI parameters (matrix_path, cards_dir) instead of runtime mocking.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Import the module under test.  We pass matrix_path / cards_dir
# via DI parameters so that real filesystem paths are not required.
# ---------------------------------------------------------------------------
import importlib
import sys
import textwrap
from pathlib import Path

import yaml

# Ensure scripts/ is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
traceability = importlib.import_module("task_card_traceability_check")


# ---------------------------------------------------------------------------
# Regex unit tests
# ---------------------------------------------------------------------------
class TestRegexPatterns:
    """Verify regex patterns match both Chinese and English formats."""

    def test_chinese_matrix_ref(self):
        """Must match '> 矩阵条目: MC0-1'."""
        line = "> 矩阵条目: MC0-1 | V-x: X0-1"
        match = traceability.MATRIX_REF_RE.match(line)
        assert match is not None
        assert match.group(1) == "MC0-1"

    def test_chinese_matrix_ref_no_extra(self):
        """Must match bare '> 矩阵条目: B0-3'."""
        line = "> 矩阵条目: B0-3"
        match = traceability.MATRIX_REF_RE.match(line)
        assert match is not None
        assert match.group(1) == "B0-3"

    def test_english_matrix_ref(self):
        """Must match '> Matrix ref: K0-1' for backward compat."""
        line = "> Matrix ref: K0-1"
        match = traceability.MATRIX_REF_RE.match(line)
        assert match is not None
        assert match.group(1) == "K0-1"

    def test_english_matrix_entry(self):
        """Must match '> Matrix entry: S0-2'."""
        line = "> Matrix entry: S0-2"
        match = traceability.MATRIX_REF_RE.match(line)
        assert match is not None
        assert match.group(1) == "S0-2"

    def test_no_match_plain_text(self):
        """Must not match regular text lines."""
        line = "This is a regular line about the matrix."
        match = traceability.MATRIX_REF_RE.match(line)
        assert match is None

    def test_m_track_regex_exists(self):
        """M_TRACK_RE must exist and match M-Track references."""
        assert hasattr(traceability, "M_TRACK_RE")
        line = "> 矩阵条目: B2-1 | V-x: X2-1 | M-Track: MM1-4 (comment)"
        match = traceability.M_TRACK_RE.search(line)
        assert match is not None
        assert match.group(1) == "MM1-4"

    def test_m_track_multiple(self):
        """M_TRACK_RE must match standalone M-Track line."""
        line = "> 矩阵条目: MC4-1 | V-x: X4-4 | V-fb: XF4-3 | M-Track: MM1-6 (note)"
        match = traceability.M_TRACK_RE.search(line)
        assert match is not None
        assert match.group(1) == "MM1-6"


# ---------------------------------------------------------------------------
# scan_task_cards tests with fixture data
# ---------------------------------------------------------------------------
class TestScanTaskCards:
    """Verify scan_task_cards returns both main refs and M-Track refs."""

    SAMPLE_CARD = textwrap.dedent("""\
        # Brain Layer Task Cards

        ### TASK-B-001

        | Field | Value |
        |-------|-------|
        | **ID** | TASK-B-001 |

        > 矩阵条目: B0-1 | V-x: X0-1

        ### TASK-B-002

        | Field | Value |
        |-------|-------|
        | **ID** | TASK-B-002 |

        > 矩阵条目: B2-1 | V-x: X2-1 | M-Track: MM1-4 (vision model)

        ### TASK-B-003

        > Matrix ref: B0-3
    """)

    def test_scan_returns_main_refs(self, tmp_path: Path):
        """scan_task_cards must return main refs keyed by milestone ID."""
        cards_dir = tmp_path / "task-cards"
        cards_dir.mkdir()
        (cards_dir / "brain.md").write_text(self.SAMPLE_CARD)

        result = traceability.scan_task_cards(cards_dir=cards_dir)

        assert "B0-1" in result["main_refs"]
        assert "B2-1" in result["main_refs"]
        assert "B0-3" in result["main_refs"]

    def test_scan_returns_m_track_refs(self, tmp_path: Path):
        """scan_task_cards must return M-Track refs separately."""
        cards_dir = tmp_path / "task-cards"
        cards_dir.mkdir()
        (cards_dir / "brain.md").write_text(self.SAMPLE_CARD)

        result = traceability.scan_task_cards(cards_dir=cards_dir)

        assert "MM1-4" in result["m_track_refs"]

    def test_scan_returns_dict_with_both_keys(self, tmp_path: Path):
        """scan_task_cards must return dict with main_refs and m_track_refs."""
        cards_dir = tmp_path / "task-cards"
        cards_dir.mkdir()
        (cards_dir / "test.md").write_text("> 矩阵条目: T0-1\n")

        result = traceability.scan_task_cards(cards_dir=cards_dir)

        assert "main_refs" in result
        assert "m_track_refs" in result


# ---------------------------------------------------------------------------
# Dual coverage output tests
# ---------------------------------------------------------------------------
class TestDualCoverage:
    """Verify JSON output contains both main_coverage and all_coverage."""

    def _make_yaml(self, tmp_path: Path, milestones: list[dict]) -> Path:
        yaml_path = tmp_path / "matrix.yaml"
        data = {
            "schema_version": "1.0",
            "current_phase": "phase_0",
            "phases": {
                "phase_0": {
                    "name": "Test",
                    "milestones": milestones,
                }
            },
        }
        yaml_path.write_text(yaml.dump(data))
        return yaml_path

    def _make_cards(self, tmp_path: Path, content: str) -> Path:
        cards_dir = tmp_path / "cards"
        cards_dir.mkdir()
        (cards_dir / "test.md").write_text(content)
        return cards_dir

    def test_main_coverage_only_counts_primary_refs(self, tmp_path: Path):
        milestones = [
            {"id": "A-1", "layer": "Brain", "summary": "test"},
            {"id": "A-2", "layer": "Brain", "summary": "test"},
            {"id": "MM-1", "layer": "Multimodal", "summary": "test"},
        ]
        yaml_path = self._make_yaml(tmp_path, milestones)
        card_content = textwrap.dedent("""\
            ### TASK-001
            > 矩阵条目: A-1
            ### TASK-002
            > 矩阵条目: A-2 | M-Track: MM-1
        """)
        cards_dir = self._make_cards(tmp_path, card_content)

        milestone_ids = traceability.load_milestone_ids(matrix_path=yaml_path)
        card_data = traceability.scan_task_cards(cards_dir=cards_dir)
        result = traceability.compute_result(milestone_ids, card_data)

        # main_coverage: A-1 and A-2 are primary refs = 2/3
        assert result["main_coverage"]["covered"] == 2
        assert result["main_coverage"]["total"] == 3
        # all_coverage: A-1, A-2, MM-1 all covered = 3/3
        assert result["all_coverage"]["covered"] == 3
        assert result["all_coverage"]["total"] == 3
        # status PASS because all_coverage = 100% >= 98%
        assert result["status"] == "PASS"

    def test_threshold_fail_below_98(self, tmp_path: Path):
        """status must be FAIL when all_coverage < threshold."""
        milestones = [{"id": f"X-{i}", "layer": "Brain", "summary": "t"} for i in range(100)]
        yaml_path = self._make_yaml(tmp_path, milestones)
        # Cover only 95 of 100 (no M-Track either)
        lines = []
        for i in range(95):
            lines.append(f"### TASK-{i:03d}")
            lines.append(f"> 矩阵条目: X-{i}")
        cards_dir = self._make_cards(tmp_path, "\n".join(lines))

        milestone_ids = traceability.load_milestone_ids(matrix_path=yaml_path)
        card_data = traceability.scan_task_cards(cards_dir=cards_dir)
        result = traceability.compute_result(milestone_ids, card_data)

        assert result["status"] == "FAIL"
        assert result["all_coverage"]["coverage_pct"] == 95.0

    def test_threshold_pass_at_100(self, tmp_path: Path):
        milestones = [
            {"id": "Z-1", "layer": "Brain", "summary": "t"},
            {"id": "Z-2", "layer": "Brain", "summary": "t"},
        ]
        yaml_path = self._make_yaml(tmp_path, milestones)
        card_content = "### TASK-1\n> 矩阵条目: Z-1\n### TASK-2\n> 矩阵条目: Z-2\n"
        cards_dir = self._make_cards(tmp_path, card_content)

        milestone_ids = traceability.load_milestone_ids(matrix_path=yaml_path)
        card_data = traceability.scan_task_cards(cards_dir=cards_dir)
        result = traceability.compute_result(milestone_ids, card_data)

        assert result["status"] == "PASS"
        assert result["main_coverage"]["coverage_pct"] == 100.0


# ---------------------------------------------------------------------------
# load_milestone_ids tests
# ---------------------------------------------------------------------------
class TestLoadMilestoneIds:
    def test_phase_filter(self, tmp_path: Path):
        data = {
            "phases": {
                "phase_0": {"milestones": [{"id": "A-1"}]},
                "phase_1": {"milestones": [{"id": "B-1"}]},
            }
        }
        yaml_path = tmp_path / "matrix.yaml"
        yaml_path.write_text(yaml.dump(data))

        ids = traceability.load_milestone_ids(phase_filter=0, matrix_path=yaml_path)

        assert ids == {"A-1"}

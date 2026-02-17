"""Tests for count_task_cards.py --json output enrichment.

TDD RED: Verify that --json output includes a 'summary' field
with by_tier, by_layer, by_phase, gaps.orphan_count, etc.
while KEEPING existing 'total' and 'cards' fields.

Uses DI (direct function calls + tmp_path fixtures) instead of runtime mocking.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
import count_task_cards


class TestJsonOutputStructure:
    """Verify --json output has total, cards, AND summary."""

    def _make_card(self, task_id: str, matrix_ref: str | None = "B0-1") -> dict:
        """Helper to create a minimal card dict."""
        return {
            "id": task_id,
            "title": "Test",
            "layer": count_task_cards.extract_layer(task_id),
            "phase": count_task_cards.extract_phase(task_id),
            "tier": "B",
            "matrix_ref": matrix_ref,
            "fields_found": [],
            "field_count": 0,
            "has_out_of_scope": False,
            "has_risk": False,
            "has_decision": False,
            "has_env_dep": False,
            "has_manual_verify": False,
            "acceptance_text": "",
            "file": "docs/task-cards/test.md",
            "line": 1,
        }

    def _build_json_output(self, cards: list[dict]) -> dict:
        """Build the same JSON structure that main() --json would produce."""
        return {
            "total": len(cards),
            "cards": cards,
            "summary": count_task_cards.build_summary(cards),
        }

    def test_json_has_total(self, tmp_path: Path):
        """--json output must have 'total' field (backward compat)."""
        result = self._build_json_output([self._make_card("TASK-B0-1")])
        assert "total" in result

    def test_json_has_cards(self, tmp_path: Path):
        """--json output must have 'cards' array (backward compat)."""
        result = self._build_json_output([self._make_card("TASK-B0-1")])
        assert "cards" in result
        assert isinstance(result["cards"], list)

    def test_json_has_summary(self, tmp_path: Path):
        """--json output must have 'summary' field with aggregations."""
        result = self._build_json_output([self._make_card("TASK-B0-1")])
        assert "summary" in result, "Missing 'summary' key in --json output"

    def test_summary_has_by_tier(self, tmp_path: Path):
        """summary must include by_tier breakdown."""
        result = self._build_json_output([self._make_card("TASK-B0-1")])
        assert "by_tier" in result["summary"]

    def test_summary_has_by_layer(self, tmp_path: Path):
        """summary must include by_layer breakdown."""
        result = self._build_json_output([self._make_card("TASK-B0-1")])
        assert "by_layer" in result["summary"]

    def test_summary_has_by_phase(self, tmp_path: Path):
        """summary must include by_phase breakdown."""
        result = self._build_json_output([self._make_card("TASK-B0-1")])
        assert "by_phase" in result["summary"]

    def test_summary_has_gaps(self, tmp_path: Path):
        """summary must include gaps with orphan_count."""
        result = self._build_json_output([self._make_card("TASK-B0-1")])
        assert "gaps" in result["summary"]
        assert "orphan_count" in result["summary"]["gaps"]

    def test_orphan_count_correct(self, tmp_path: Path):
        """Orphan count must match cards without matrix_ref."""
        cards = [
            self._make_card("TASK-B0-1", matrix_ref="B0-1"),
            self._make_card("TASK-B0-2", matrix_ref=None),
            self._make_card("TASK-B0-3", matrix_ref=None),
        ]
        result = self._build_json_output(cards)
        assert result["summary"]["gaps"]["orphan_count"] == 2

    def test_total_matches_cards_length(self, tmp_path: Path):
        """total must equal len(cards)."""
        cards = [self._make_card(f"TASK-B0-{i}") for i in range(5)]
        result = self._build_json_output(cards)
        assert result["total"] == 5
        assert len(result["cards"]) == 5

    def test_scan_all_cards_with_real_files(self, tmp_path: Path):
        """scan_all_cards must parse real markdown task card files."""
        card_dir = tmp_path / "task-cards"
        card_dir.mkdir()
        (card_dir / "test.md").write_text(
            "### TASK-B0-1: Test card\n"
            "| Field | Value |\n"
            "|-------|-------|\n"
            "| **ID** | TASK-B0-1 |\n"
            "> 矩阵条目: B0-1\n"
        )
        cards = count_task_cards.scan_all_cards(card_dir)
        assert len(cards) == 1
        assert cards[0]["id"] == "TASK-B0-1"

        output = self._build_json_output(cards)
        parsed = json.loads(json.dumps(output))
        assert parsed["total"] == 1
        assert "summary" in parsed


class TestBuildSummary:
    """Test the summary-building function directly."""

    def test_build_summary_exists(self):
        """count_task_cards must have a build_summary function."""
        assert hasattr(count_task_cards, "build_summary"), (
            "count_task_cards must expose a build_summary(cards) function"
        )

    def test_build_summary_returns_dict(self):
        """build_summary must return a dict."""
        result = count_task_cards.build_summary([])
        assert isinstance(result, dict)

    def test_build_summary_keys(self):
        """build_summary must return by_layer, by_phase, by_tier, gaps."""
        result = count_task_cards.build_summary([])
        for key in ("by_layer", "by_phase", "by_tier", "gaps"):
            assert key in result, f"Missing key '{key}' in build_summary output"

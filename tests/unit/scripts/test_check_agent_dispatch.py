"""Tests for check_agent_dispatch.py task-card expansion.

TDD RED: Verify that:
  - load_required_dispatches expands task_cards when cards_dir provided
  - Per-card agent dispatch entries are generated from workflow scope
  - Fallback: no expansion when cards_dir is None (existing behavior)

Uses DI (cards_dir parameter) -- no runtime mocking.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
import check_agent_dispatch


class TestLoadRequiredDispatches:
    """Verify basic dispatch loading (existing behavior)."""

    def test_loads_workflow_level_dispatches(self, tmp_path: Path):
        """Must load agent dispatches from workflow YAML."""
        wf_yaml = tmp_path / "workflows.yaml"
        wf_yaml.write_text(
            yaml.dump(
                {
                    "workflows": [
                        {
                            "id": "WF-1",
                            "agent_dispatch": [
                                {"agent": "tdd-guide", "scope": "all cards"},
                            ],
                        }
                    ],
                }
            )
        )

        result = check_agent_dispatch.load_required_dispatches(wf_yaml)
        assert len(result) == 1
        assert result[0]["agent"] == "tdd-guide"
        assert result[0]["workflow"] == "WF-1"


class TestTaskCardExpansion:
    """Verify task-card level dispatch expansion."""

    def _make_workflow(self, tmp_path: Path) -> Path:
        wf_yaml = tmp_path / "workflows.yaml"
        wf_yaml.write_text(
            yaml.dump(
                {
                    "workflows": [
                        {
                            "id": "WF2-B1",
                            "task_cards": ["MC2-1", "MC2-2", "I2-1"],
                            "agent_dispatch": [
                                {"agent": "diyu-tdd-guide", "scope": "all cards"},
                            ],
                        }
                    ],
                }
            )
        )
        return wf_yaml

    def _make_cards(self, tmp_path: Path) -> Path:
        cards_dir = tmp_path / "task-cards"
        cards_dir.mkdir()
        (cards_dir / "memory.md").write_text(
            "### TASK-MC2-1: PG adapter\n"
            "> 矩阵条目: MC2-1\n\n"
            "### TASK-MC2-2: conversation CRUD\n"
            "> 矩阵条目: MC2-2\n"
        )
        (cards_dir / "infra.md").write_text("### TASK-I2-1: Redis cache\n> 矩阵条目: I2-1\n")
        return cards_dir

    def test_expand_returns_per_card_entries(self, tmp_path: Path):
        """With cards_dir, dispatches must be expanded per task card."""
        wf_yaml = self._make_workflow(tmp_path)
        cards_dir = self._make_cards(tmp_path)

        result = check_agent_dispatch.load_required_dispatches(
            wf_yaml,
            cards_dir=cards_dir,
        )

        # "all cards" scope with 3 cards -> 3 per-card entries
        card_ids = {r["card_id"] for r in result if "card_id" in r}
        assert "MC2-1" in card_ids
        assert "MC2-2" in card_ids
        assert "I2-1" in card_ids

    def test_no_expansion_without_cards_dir(self, tmp_path: Path):
        """Without cards_dir, existing workflow-level behavior preserved."""
        wf_yaml = self._make_workflow(tmp_path)

        result = check_agent_dispatch.load_required_dispatches(wf_yaml)
        # Should return 1 workflow-level entry, no card_id
        assert len(result) == 1
        assert "card_id" not in result[0]

    def test_scoped_expansion_filters_cards(self, tmp_path: Path):
        """Scoped dispatches only expand to matching cards."""
        wf_yaml = tmp_path / "workflows.yaml"
        wf_yaml.write_text(
            yaml.dump(
                {
                    "workflows": [
                        {
                            "id": "WF2-B2",
                            "task_cards": ["T2-1", "B2-1", "B2-2"],
                            "agent_dispatch": [
                                {"agent": "architect", "scope": "B2-1, T2-1"},
                            ],
                        }
                    ],
                }
            )
        )

        cards_dir = tmp_path / "task-cards"
        cards_dir.mkdir()
        (cards_dir / "brain.md").write_text(
            "### TASK-B2-1: Conv engine\n> 矩阵条目: B2-1\n\n"
            "### TASK-B2-2: Intent\n> 矩阵条目: B2-2\n"
        )
        (cards_dir / "tool.md").write_text("### TASK-T2-1: LLM impl\n> 矩阵条目: T2-1\n")

        result = check_agent_dispatch.load_required_dispatches(
            wf_yaml,
            cards_dir=cards_dir,
        )

        card_ids = {r["card_id"] for r in result if "card_id" in r}
        assert "B2-1" in card_ids
        assert "T2-1" in card_ids
        assert "B2-2" not in card_ids, "B2-2 should not be included in scope 'B2-1, T2-1'"

"""Unit tests for Evolution Pipeline (MC2-5).

Tests all 3 stages: Observer, Analyzer, Evolver.
Complies with no-mock policy.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.memory.evolution.pipeline import (
    Analyzer,
    EvolutionPipeline,
    EvolutionResult,
    Evolver,
    ExtractedObservation,
    Observer,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def observer() -> Observer:
    return Observer()


@pytest.fixture()
def analyzer() -> Analyzer:
    return Analyzer()


@pytest.fixture()
def evolver() -> Evolver:
    return Evolver()


@pytest.fixture()
def pipeline() -> EvolutionPipeline:
    return EvolutionPipeline()


@pytest.fixture()
def session_id():
    return uuid4()


# ---------------------------------------------------------------------------
# Tests: Observer (Stage 1)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestObserver:
    """MC2-5 Stage 1: Observer extracts observations."""

    async def test_extract_preference(
        self,
        observer: Observer,
        session_id,
    ) -> None:
        messages = [{"role": "user", "content": "I prefer dark mode for coding"}]
        observations = await observer.extract(session_id, messages)
        assert len(observations) >= 1
        assert observations[0].memory_type == "preference"

    async def test_extract_fact(
        self,
        observer: Observer,
        session_id,
    ) -> None:
        messages = [{"role": "user", "content": "I am a software engineer"}]
        observations = await observer.extract(session_id, messages)
        assert len(observations) >= 1
        assert observations[0].memory_type == "observation"

    async def test_skip_assistant_messages(
        self,
        observer: Observer,
        session_id,
    ) -> None:
        messages = [
            {"role": "assistant", "content": "I prefer to help you"},
        ]
        observations = await observer.extract(session_id, messages)
        assert len(observations) == 0

    async def test_confidence_ceiling_06(
        self,
        observer: Observer,
        session_id,
    ) -> None:
        messages = [{"role": "user", "content": "I prefer Python"}]
        observations = await observer.extract(session_id, messages)
        for obs in observations:
            assert obs.confidence <= Observer.MAX_CONFIDENCE

    async def test_empty_messages(
        self,
        observer: Observer,
        session_id,
    ) -> None:
        observations = await observer.extract(session_id, [])
        assert observations == []


# ---------------------------------------------------------------------------
# Tests: Analyzer (Stage 2)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAnalyzer:
    """MC2-5 Stage 2: Analyzer finds patterns."""

    async def test_analyze_preference(self, analyzer: Analyzer) -> None:
        obs = ExtractedObservation(
            id=uuid4(),
            content="I prefer dark mode",
            memory_type="preference",
            confidence=0.5,
            source_session_id=uuid4(),
        )
        result = await analyzer.analyze(obs)
        assert result.pattern_detected is True
        assert result.suggested_memory_type == "preference"

    async def test_analyze_observation(self, analyzer: Analyzer) -> None:
        obs = ExtractedObservation(
            id=uuid4(),
            content="I work at Acme",
            memory_type="observation",
            confidence=0.6,
            source_session_id=uuid4(),
        )
        result = await analyzer.analyze(obs)
        assert result.observation_id == obs.id

    async def test_confidence_ceiling_08(self, analyzer: Analyzer) -> None:
        obs = ExtractedObservation(
            id=uuid4(),
            content="test",
            memory_type="observation",
            confidence=0.6,
            source_session_id=uuid4(),
        )
        result = await analyzer.analyze(obs)
        assert result.suggested_confidence <= Analyzer.MAX_CONFIDENCE


# ---------------------------------------------------------------------------
# Tests: Evolver (Stage 3)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestEvolver:
    """MC2-5 Stage 3: Evolver writes/updates memory."""

    async def test_evolve_creates_memory(self, evolver: Evolver) -> None:
        from src.memory.evolution.pipeline import AnalysisResult

        obs = ExtractedObservation(
            id=uuid4(),
            content="test",
            memory_type="observation",
            confidence=0.5,
            source_session_id=uuid4(),
        )
        analysis = AnalysisResult(
            observation_id=obs.id,
            pattern_detected=True,
            suggested_memory_type="observation",
            suggested_confidence=0.6,
            reasoning="test",
        )
        result = await evolver.evolve(obs, analysis)
        assert result.action == "created"
        assert result.memory_id is not None

    async def test_evolve_skips_low_confidence(self, evolver: Evolver) -> None:
        from src.memory.evolution.pipeline import AnalysisResult

        obs = ExtractedObservation(
            id=uuid4(),
            content="test",
            memory_type="observation",
            confidence=0.1,
            source_session_id=uuid4(),
        )
        analysis = AnalysisResult(
            observation_id=obs.id,
            pattern_detected=False,
            suggested_memory_type="observation",
            suggested_confidence=0.2,
            reasoning="low confidence",
        )
        result = await evolver.evolve(obs, analysis)
        assert result.action == "skipped"


# ---------------------------------------------------------------------------
# Tests: Full Pipeline
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestEvolutionPipeline:
    """MC2-5: Full pipeline integration."""

    async def test_full_pipeline_processes_session(
        self,
        pipeline: EvolutionPipeline,
        session_id,
    ) -> None:
        messages = [
            {"role": "user", "content": "I prefer using Python for data science"},
            {"role": "assistant", "content": "Python is great for data science!"},
            {"role": "user", "content": "I work at a startup in SF"},
        ]
        results = await pipeline.process_session(session_id, messages)
        assert len(results) >= 1
        assert all(isinstance(r, EvolutionResult) for r in results)

    async def test_pipeline_empty_session(
        self,
        pipeline: EvolutionPipeline,
        session_id,
    ) -> None:
        results = await pipeline.process_session(session_id, [])
        assert results == []

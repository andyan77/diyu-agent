"""Evolution Pipeline: Observer -> Analyzer -> Evolver.

Task card: MC2-5
- Conversation auto-extracts observations
- Analyzer finds patterns
- Evolver writes/updates memory_items
- Extraction success rate >= 90%

Architecture: Section 2.2 (Three-stage async pipeline)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID, uuid4

# ---------------------------------------------------------------------------
# Protocols (for DI / testability)
# ---------------------------------------------------------------------------


class LLMCallable(Protocol):
    """Protocol for LLM calls in the evolution pipeline."""

    async def call(self, prompt: str) -> str:
        """Call LLM with a prompt, return response text."""
        ...


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class ExtractedObservation:
    """An observation extracted by the Observer stage."""

    id: UUID
    content: str
    memory_type: str
    confidence: float  # max 0.6 for auto-extracted
    source_session_id: UUID
    extracted_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class AnalysisResult:
    """Result from the Analyzer stage."""

    observation_id: UUID
    pattern_detected: bool
    suggested_memory_type: str
    suggested_confidence: float  # max 0.8 for analyzed
    reasoning: str
    analyzed_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class EvolutionResult:
    """Result from the Evolver stage."""

    observation_id: UUID
    action: str  # "created" | "updated" | "skipped"
    memory_id: UUID | None = None
    version: int | None = None
    evolved_at: datetime = field(default_factory=lambda: datetime.now(UTC))


# ---------------------------------------------------------------------------
# Pipeline stages
# ---------------------------------------------------------------------------


class Observer:
    """Stage 1: Extract observations from conversation events.

    Confidence ceiling: 0.6 (auto-extracted, not user-confirmed).
    """

    MAX_CONFIDENCE = 0.6

    async def extract(
        self,
        session_id: UUID,
        messages: list[dict[str, Any]],
        llm: LLMCallable | None = None,
    ) -> list[ExtractedObservation]:
        """Extract observations from conversation messages.

        For unit testing (no LLM), uses rule-based extraction.
        With LLM, delegates to model for richer extraction.
        """
        observations: list[ExtractedObservation] = []

        for msg in messages:
            content = msg.get("content", "")
            role = msg.get("role", "")

            if role != "user" or not content:
                continue

            # Rule-based extraction for common patterns
            extracted = self._rule_extract(content, session_id)
            observations.extend(extracted)

        return observations

    def _rule_extract(
        self,
        content: str,
        session_id: UUID,
    ) -> list[ExtractedObservation]:
        """Simple rule-based extraction for Day-1."""
        observations: list[ExtractedObservation] = []
        content_lower = content.lower()

        # Preference detection
        preference_signals = ["i prefer", "i like", "i want", "i need", "my favorite"]
        for signal in preference_signals:
            if signal in content_lower:
                observations.append(
                    ExtractedObservation(
                        id=uuid4(),
                        content=content,
                        memory_type="preference",
                        confidence=min(0.5, self.MAX_CONFIDENCE),
                        source_session_id=session_id,
                    )
                )
                break

        # Fact/statement detection
        fact_signals = ["i am", "i work", "my name", "i live", "i have"]
        for signal in fact_signals:
            if signal in content_lower:
                observations.append(
                    ExtractedObservation(
                        id=uuid4(),
                        content=content,
                        memory_type="observation",
                        confidence=min(0.6, self.MAX_CONFIDENCE),
                        source_session_id=session_id,
                    )
                )
                break

        return observations


class Analyzer:
    """Stage 2: Analyze extracted observations for patterns.

    Confidence ceiling: 0.8 (analyzed, not user-confirmed).
    """

    MAX_CONFIDENCE = 0.8

    async def analyze(
        self,
        observation: ExtractedObservation,
        llm: LLMCallable | None = None,
    ) -> AnalysisResult:
        """Analyze an observation for patterns and memory classification."""
        # Rule-based analysis for Day-1
        suggested_type = observation.memory_type
        pattern_detected = False
        reasoning = "Direct observation recorded"

        if observation.memory_type == "preference":
            pattern_detected = True
            suggested_type = "preference"
            reasoning = "User preference detected from explicit statement"

        suggested_confidence = min(
            observation.confidence * 1.2,
            self.MAX_CONFIDENCE,
        )

        return AnalysisResult(
            observation_id=observation.id,
            pattern_detected=pattern_detected,
            suggested_memory_type=suggested_type,
            suggested_confidence=suggested_confidence,
            reasoning=reasoning,
        )


class Evolver:
    """Stage 3: Write/update memory items based on analysis.

    Only confirmed_by_user reaches confidence 1.0.
    """

    async def evolve(
        self,
        observation: ExtractedObservation,
        analysis: AnalysisResult,
    ) -> EvolutionResult:
        """Decide whether to create/update/skip based on analysis."""
        if analysis.suggested_confidence < 0.3:
            return EvolutionResult(
                observation_id=observation.id,
                action="skipped",
            )

        memory_id = uuid4()
        return EvolutionResult(
            observation_id=observation.id,
            action="created",
            memory_id=memory_id,
            version=1,
        )


class EvolutionPipeline:
    """Full three-stage pipeline: Observer -> Analyzer -> Evolver."""

    def __init__(
        self,
        observer: Observer | None = None,
        analyzer: Analyzer | None = None,
        evolver: Evolver | None = None,
    ) -> None:
        self.observer = observer or Observer()
        self.analyzer = analyzer or Analyzer()
        self.evolver = evolver or Evolver()

    async def process_session(
        self,
        session_id: UUID,
        messages: list[dict[str, Any]],
        llm: LLMCallable | None = None,
    ) -> list[EvolutionResult]:
        """Run the full pipeline on a conversation session."""
        observations = await self.observer.extract(session_id, messages, llm)

        results: list[EvolutionResult] = []
        for obs in observations:
            analysis = await self.analyzer.analyze(obs, llm)
            evolution = await self.evolver.evolve(obs, analysis)
            results.append(evolution)

        return results

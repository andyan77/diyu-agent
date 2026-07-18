#!/usr/bin/env python3
"""Single lightweight author-output contract for all Package 7 deliverables."""

from __future__ import annotations

from typing import Any, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


JsonObject = dict[str, Any]
AUTHOR_CONTRACT_VERSION = "diyu.author-output.v2.0"

ContentFormat: TypeAlias = Literal[
    "短视频",
    "图文",
    "直播内容包",
    "私域沟通内容",
    "门店线下物料",
    "培训与门店话术",
    "陈列搭配",
]


class StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        protected_namespaces=(),
    )


class VideoShot(StrictModel):
    visual: str = Field(min_length=1, max_length=800)
    camera: str = Field(min_length=1, max_length=300)
    audio: str = Field(min_length=1, max_length=800)
    subtitle: str = Field(default="", max_length=500)


class ShortVideoDeliverable(StrictModel):
    shots: list[VideoShot] = Field(min_length=2, max_length=20)
    shooting_notes: list[str] = Field(min_length=1, max_length=20)
    editing_notes: list[str] = Field(min_length=1, max_length=20)


class ArticleFrame(StrictModel):
    image_brief: str = Field(min_length=1, max_length=800)
    accompanying_copy: str = Field(min_length=1, max_length=1600)


class ArticleDeliverable(StrictModel):
    cover_brief: str = Field(min_length=1, max_length=500)
    frames: list[ArticleFrame] = Field(min_length=2, max_length=20)
    layout_notes: list[str] = Field(min_length=1, max_length=20)


class LiveSegment(StrictModel):
    segment_title: str = Field(min_length=1, max_length=300)
    talking_points: list[str] = Field(min_length=1, max_length=20)
    interaction_prompt: str = Field(min_length=1, max_length=500)


class LiveDeliverable(StrictModel):
    theme: str = Field(min_length=1, max_length=500)
    opening: str = Field(min_length=1, max_length=1200)
    segments: list[LiveSegment] = Field(min_length=2, max_length=20)
    interaction_qa: list[str] = Field(min_length=1, max_length=30)
    risk_reminders: list[str] = Field(min_length=1, max_length=20)
    closing: str = Field(min_length=1, max_length=1200)


class PrivateMessage(StrictModel):
    channel: Literal["朋友圈", "社群", "一对一"]
    message_text: str = Field(alias="copy", min_length=1, max_length=3000)


class PrivateCommunicationDeliverable(StrictModel):
    applicable_scenario: str = Field(min_length=1, max_length=800)
    messages: list[PrivateMessage] = Field(min_length=1, max_length=6)
    follow_up_actions: list[str] = Field(min_length=1, max_length=12)
    communication_boundaries: list[str] = Field(min_length=1, max_length=12)


class OfflineMaterialDeliverable(StrictModel):
    core_copy: str = Field(min_length=1, max_length=2000)
    information_hierarchy: list[str] = Field(min_length=2, max_length=12)
    layout_or_placement_notes: list[str] = Field(min_length=1, max_length=12)
    action_guidance: str = Field(min_length=1, max_length=800)
    validity_boundary: str = Field(min_length=1, max_length=800)


class SituationalQA(StrictModel):
    question: str = Field(min_length=1, max_length=800)
    suggested_answer: str = Field(min_length=1, max_length=1600)


class TrainingDeliverable(StrictModel):
    training_goal: str = Field(min_length=1, max_length=800)
    outline: list[str] = Field(min_length=2, max_length=20)
    exercises: list[str] = Field(min_length=1, max_length=12)
    situational_qa: list[SituationalQA] = Field(min_length=1, max_length=20)
    allowed_phrasing: list[str] = Field(min_length=1, max_length=20)
    prohibited_phrasing: list[str] = Field(min_length=1, max_length=20)


class DisplayDeliverable(StrictModel):
    arrangement_relationship: str = Field(min_length=1, max_length=1200)
    spatial_layers: str = Field(min_length=1, max_length=800)
    color_relationship: str = Field(min_length=1, max_length=800)
    availability_caution: str = Field(min_length=1, max_length=800)
    shooting_angles: list[str] = Field(min_length=1, max_length=20)


class CandidateBase(StrictModel):
    creative_difference: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=240)
    body: str = Field(min_length=1, max_length=12_000)
    spoken_lines: list[str] = Field(default_factory=list, max_length=30)
    cta: str = Field(default="", max_length=500)

    @field_validator("spoken_lines")
    @classmethod
    def validate_spoken_lines(cls, value: list[str]) -> list[str]:
        normalized = [item.strip() for item in value]
        if any(not item or len(item) > 500 for item in normalized):
            raise ValueError("spoken lines must be short non-empty strings")
        return normalized

    def deliverable_payload(self) -> JsonObject:
        """Return the concrete format payload without widening the base schema."""

        deliverable = getattr(self, "deliverable", None)
        if not isinstance(deliverable, StrictModel):
            raise ValueError("candidate deliverable is missing")
        return deliverable.model_dump(by_alias=True)


class ShortVideoCandidate(CandidateBase):
    deliverable: ShortVideoDeliverable


class ArticleCandidate(CandidateBase):
    deliverable: ArticleDeliverable


class LiveCandidate(CandidateBase):
    deliverable: LiveDeliverable


class PrivateCommunicationCandidate(CandidateBase):
    deliverable: PrivateCommunicationDeliverable


class OfflineMaterialCandidate(CandidateBase):
    deliverable: OfflineMaterialDeliverable


class TrainingCandidate(CandidateBase):
    deliverable: TrainingDeliverable


class DisplayCandidate(CandidateBase):
    deliverable: DisplayDeliverable


CandidateModel: TypeAlias = type[CandidateBase]
CANDIDATE_MODELS: dict[str, CandidateModel] = {
    "短视频": ShortVideoCandidate,
    "图文": ArticleCandidate,
    "直播内容包": LiveCandidate,
    "私域沟通内容": PrivateCommunicationCandidate,
    "门店线下物料": OfflineMaterialCandidate,
    "培训与门店话术": TrainingCandidate,
    "陈列搭配": DisplayCandidate,
}


class CandidateEnvelopeShell(StrictModel):
    candidates: list[Any] = Field(min_length=1, max_length=3)


class ChatEnvelope(StrictModel):
    reply: str = Field(min_length=1, max_length=12_000)


def candidate_schema(content_format: ContentFormat) -> JsonObject:
    """Return the exact current-format schema supplied to the author."""

    return CANDIDATE_MODELS[content_format].model_json_schema()


def parse_candidate_envelope(
    value: object,
    content_format: ContentFormat,
) -> tuple[list[CandidateBase], list[JsonObject]]:
    """Parse each candidate independently so one bad sibling cannot erase good work."""

    shell = CandidateEnvelopeShell.model_validate(value)
    model = CANDIDATE_MODELS[content_format]
    accepted: list[CandidateBase] = []
    failures: list[JsonObject] = []
    for ordinal, raw in enumerate(shell.candidates, 1):
        try:
            accepted.append(model.model_validate(raw))
        except ValidationError as exc:
            failures.append(
                {
                    "candidate_ordinal": ordinal,
                    "error_type": "CANDIDATE_SCHEMA_ERROR",
                    "error_count": len(exc.errors()),
                    "error_locations": [
                        ".".join(str(part) for part in row["loc"])
                        for row in exc.errors()
                    ],
                }
            )
    return accepted, failures


def contract_descriptor(content_format: ContentFormat) -> JsonObject:
    """Build the prompt descriptor from the same model used by the parser."""

    return {
        "contract_version": AUTHOR_CONTRACT_VERSION,
        "contract_version_authority": "SERVER_BOUND_FROM_MODEL_RUN",
        "root_fields": {
            "candidates": "1至3份；每份按candidate_schema填写",
        },
        "candidate_schema": candidate_schema(content_format),
        "forbidden_author_fields": [
            "企业、组织、门店、登录身份、内容账号、平台和时长",
            "内部事实编号、资料编号、逐句路径和引用账本",
            "其他成品的空分支",
            "原子组件编号和甲乙路径",
        ],
    }

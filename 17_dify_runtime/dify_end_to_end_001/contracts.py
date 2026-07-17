#!/usr/bin/env python3
"""Closed request and model-output contracts for the Package 7 bridge."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def normalize_model_json_text(raw: str) -> tuple[str, str]:
    """Remove only known provider wrappers around one JSON object."""
    value = raw.strip()
    normalization = "NONE"
    if value.startswith("<think>"):
        end = value.find("</think>")
        if end < 0:
            raise ValueError("Unclosed model reasoning wrapper")
        value = value[end + len("</think>") :].strip()
        normalization = "STRIPPED_LEADING_REASONING_WRAPPER"
    if value.startswith("```json\n") and value.endswith("```"):
        value = value[len("```json\n") : -len("```")].strip()
        normalization = (
            "STRIPPED_JSON_FENCE"
            if normalization == "NONE"
            else f"{normalization}+STRIPPED_JSON_FENCE"
        )
    if not value.startswith("{") or not value.endswith("}"):
        raise ValueError("Model output is not one JSON object")
    return value, normalization


Operation = Literal[
    "普通聊天",
    "找灵感",
    "确认制作",
    "选择候选",
    "局部修改",
    "审核",
    "导出",
    "查看来源",
    "提交反馈",
]

PortalOperation = Literal[
    "随便聊聊",
    "找点灵感",
    "直接做内容",
    "把已有内容改好",
    "继续一个系列",
    "选择候选",
    "审核",
    "导出",
    "查看来源",
    "提交反馈",
]

ContentFormat = Literal[
    "短视频",
    "图文",
    "直播内容包",
    "私域沟通内容",
    "门店线下物料",
    "培训与门店话术",
    "陈列搭配",
]
OrganizationLevel = Literal["品牌总部", "区域组织", "门店"]
ContentIdentity = Literal[
    "品牌价值身份",
    "专业身份",
    "区域经营身份",
    "门店关系身份",
    "商品或栏目身份",
]
LongTermStoryline = Literal[
    "品牌为什么存在",
    "衣服如何服务真实生活",
    "商品为什么这样设计",
    "一群人如何把品牌做好",
]
ContentDirection = Literal[
    "品牌与价值叙事",
    "商品专业解释",
    "真实组织与幕后",
    "消费者生活与穿搭判断",
    "活动、交易与关系承接",
]
BusinessGoal = Literal[
    "品牌认知",
    "商品理解",
    "建立信任",
    "引发咨询",
    "到店",
    "复购",
    "招商",
    "招聘",
]
ExpressionMethod = Literal["故事", "问答", "对比", "观察", "幕后", "演示", "纪实"]
NarrativeArchitecture = Literal[
    "EVIDENCE_FIRST",
    "QUESTION_ANSWER",
    "OBJECT_OR_TIMELINE",
]
ClaimClass = Literal["SOURCE_CLAIM", "CREATIVE_DIRECTION", "DISCLOSURE"]
DurationLabel = Literal[
    "15秒左右",
    "30秒左右",
    "60秒左右",
    "1至3分钟",
    "5至15分钟",
    "15至30分钟",
    "30至60分钟",
    "由系统建议",
]
ExpressionFeeling = Literal[
    "真实记录",
    "专业讲明白",
    "生活分享",
    "搭配演示",
    "门店日常",
    "情绪故事",
    "质感画面",
    "由系统建议",
]
PreciseFactKind = Literal[
    "SKU",
    "SPECIFICATION",
    "PRICE",
    "STOCK",
    "TIME_POINT",
    "AUTHORIZATION",
    "REVOCATION",
]

TopicLabel = Literal[
    "真实工作与人物",
    "手艺、工艺与专业知识",
    "用户问题与理性选择",
    "产品研发与验证",
    "穿搭与衣橱关系",
    "商品质感与视觉审美",
    "门店运营与空间经营",
    "城市门店与本地生活",
    "品牌和企业故事",
    "创始人或主理人的工作日常与观点",
    "商品为什么这样设计",
    "穿搭、试穿和选购建议",
    "门店日常与顾客服务",
    "团队幕后、跨岗位协作和岗位成长",
    "陈列调整与空间经营",
    "城市、区域与本地生活",
    "活动、直播、咨询、到店、私域和复购承接",
    "招商、招聘与组织信任",
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", protected_namespaces=())


class LoginRequest(StrictModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=12, max_length=256)


class PreciseFactRequest(StrictModel):
    fact_kind: PreciseFactKind
    selectors: dict[str, Any] = Field(default_factory=dict)
    required: bool = True

    @field_validator("selectors")
    @classmethod
    def validate_selectors(cls, value: dict[str, Any]) -> dict[str, Any]:
        if any(not key.strip() or len(key) > 80 for key in value):
            raise ValueError("fact selector names must be short non-empty strings")
        return value


class BridgePrepareRequest(StrictModel):
    session_token: str = Field(min_length=32, max_length=4096)
    account_display_name: str = Field(min_length=1, max_length=200)
    operation: Operation
    topic_label: TopicLabel | None = None
    selected_content_product_id: str | None = Field(
        default=None, pattern=r"^CP(?:0[1-9]|1[0-9]|20)$"
    )
    primary_audience: str | None = Field(default=None, min_length=1, max_length=300)
    message: str = Field(min_length=1, max_length=4000)
    target_platform: str = Field(default="内部测试", min_length=1, max_length=80)
    candidate_number: int | None = Field(default=None, ge=1, le=3)
    content_goal: str | None = Field(default=None, max_length=500)
    key_takeaway: str | None = Field(default=None, max_length=500)
    speaker_role_id: str | None = Field(default=None, max_length=160)
    speaker_role_name: str | None = Field(default=None, max_length=200)
    storyline_id: str | None = Field(default=None, max_length=160)
    storyline_name: str | None = Field(default=None, max_length=200)
    column_id: str | None = Field(default=None, max_length=160)
    column_name: str | None = Field(default=None, max_length=200)
    previous_content_ref: str | None = Field(default=None, max_length=240)
    localization_allowed: bool = False
    duration_label: DurationLabel = "由系统建议"
    expression_feeling: ExpressionFeeling = "由系统建议"
    content_format: ContentFormat = "短视频"
    organization_level: OrganizationLevel | None = None
    content_identity: ContentIdentity | None = None
    long_term_storyline: LongTermStoryline = "品牌为什么存在"
    content_direction: ContentDirection = "品牌与价值叙事"
    business_goal: BusinessGoal = "品牌认知"
    expression_method: ExpressionMethod = "纪实"
    existing_material_kinds: list[str] = Field(default_factory=list, max_length=8)
    user_material_refs: list[str] = Field(default_factory=list, max_length=20)
    precise_fact_requests: list[PreciseFactRequest] = Field(default_factory=list, max_length=10)

    @field_validator("message", "target_platform", "account_display_name")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("text must not be blank")
        return normalized

    @field_validator(
        "content_goal",
        "key_takeaway",
        "speaker_role_id",
        "speaker_role_name",
        "storyline_id",
        "storyline_name",
        "column_id",
        "column_name",
        "previous_content_ref",
    )
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("existing_material_kinds", "user_material_refs")
    @classmethod
    def validate_short_string_lists(cls, value: list[str]) -> list[str]:
        normalized = [item.strip() for item in value]
        if any(not item or len(item) > 240 for item in normalized):
            raise ValueError("list values must be short non-empty strings")
        if len(normalized) != len(set(normalized)):
            raise ValueError("list values must not repeat")
        return normalized

    @model_validator(mode="after")
    def require_operation_inputs(self) -> BridgePrepareRequest:
        if self.operation in {"选择候选", "局部修改"} and self.candidate_number is None:
            raise ValueError("candidate_number is required for candidate operations")
        return self


class PortalTaskRequest(StrictModel):
    account_display_name: str = Field(min_length=1, max_length=200)
    operation: PortalOperation
    topic_label: TopicLabel | None = None
    primary_audience: str | None = Field(default=None, max_length=300)
    message: str = Field(min_length=1, max_length=4000)
    target_platform: str = Field(default="其他", min_length=1, max_length=80)
    candidate_number: int | None = Field(default=None, ge=1, le=3)
    content_goal: str | None = Field(default=None, max_length=500)
    key_takeaway: str | None = Field(default=None, max_length=500)
    speaker_role_name: str | None = Field(default=None, max_length=200)
    storyline_name: str | None = Field(default=None, max_length=200)
    column_name: str | None = Field(default=None, max_length=200)
    continue_previous: bool = False
    localization_allowed: bool = False
    duration_label: DurationLabel = "由系统建议"
    expression_feeling: ExpressionFeeling = "由系统建议"
    content_format: ContentFormat = "短视频"
    organization_level: OrganizationLevel | None = None
    content_identity: ContentIdentity | None = None
    long_term_storyline: LongTermStoryline = "品牌为什么存在"
    content_direction: ContentDirection = "品牌与价值叙事"
    business_goal: BusinessGoal = "品牌认知"
    expression_method: ExpressionMethod = "纪实"
    existing_material_kinds: list[str] = Field(default_factory=list, max_length=8)

    @field_validator(
        "account_display_name",
        "message",
        "target_platform",
    )
    @classmethod
    def normalize_required_portal_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("portal text must not be blank")
        return normalized

    @field_validator(
        "primary_audience",
        "content_goal",
        "key_takeaway",
        "speaker_role_name",
        "storyline_name",
        "column_name",
    )
    @classmethod
    def normalize_optional_portal_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("existing_material_kinds")
    @classmethod
    def validate_portal_material_kinds(cls, value: list[str]) -> list[str]:
        normalized = [item.strip() for item in value]
        if any(not item or len(item) > 120 for item in normalized):
            raise ValueError("material descriptions must be short non-empty strings")
        if len(normalized) != len(set(normalized)):
            raise ValueError("material descriptions must not repeat")
        return normalized


class BridgeFinalizeRequest(StrictModel):
    session_token: str = Field(min_length=32, max_length=4096)
    run_id: str = Field(min_length=8, max_length=160)
    model_output_b64: str = Field(min_length=4, max_length=500_000)


class VideoShot(StrictModel):
    time_range: str = Field(min_length=1, max_length=80)
    visual: str = Field(min_length=1, max_length=800)
    action: str = Field(default="", max_length=500)
    camera: str = Field(min_length=1, max_length=300)
    audio: str = Field(min_length=1, max_length=800)
    subtitle: str = Field(default="", max_length=500)
    scene_product_props: str = Field(default="", max_length=500)
    edit_note: str = Field(default="", max_length=500)


class VideoProduction(StrictModel):
    shots: list[VideoShot] = Field(min_length=2, max_length=30)
    shooting_notes: list[str] = Field(min_length=1, max_length=20)
    editing_notes: list[str] = Field(min_length=1, max_length=20)


class ArticleFrame(StrictModel):
    order: int = Field(ge=1, le=30)
    image_brief: str = Field(min_length=1, max_length=800)
    accompanying_copy: str = Field(min_length=1, max_length=1600)


class ArticleProduction(StrictModel):
    frames: list[ArticleFrame] = Field(min_length=2, max_length=30)
    cover_brief: str = Field(min_length=1, max_length=500)
    layout_notes: list[str] = Field(min_length=1, max_length=20)


class DisplayProduction(StrictModel):
    referenced_items_or_facts: list[str] = Field(min_length=1, max_length=20)
    arrangement_relationship: str = Field(min_length=1, max_length=1200)
    spatial_layers: str = Field(min_length=1, max_length=800)
    color_relationship: str = Field(min_length=1, max_length=800)
    availability_caution: str = Field(min_length=1, max_length=800)
    shooting_angles: list[str] = Field(min_length=1, max_length=20)


class LiveSegment(StrictModel):
    segment_title: str = Field(min_length=1, max_length=300)
    duration_or_order: str = Field(min_length=1, max_length=120)
    talking_points: list[str] = Field(min_length=1, max_length=20)
    interaction_prompt: str = Field(min_length=1, max_length=500)


class LiveProduction(StrictModel):
    theme: str = Field(min_length=1, max_length=500)
    opening: str = Field(min_length=1, max_length=1200)
    segments: list[LiveSegment] = Field(min_length=2, max_length=20)
    interaction_qa: list[str] = Field(min_length=1, max_length=30)
    product_or_event_linkage: str = Field(min_length=1, max_length=1200)
    risk_reminders: list[str] = Field(min_length=1, max_length=20)
    closing: str = Field(min_length=1, max_length=1200)


class PrivateMessage(StrictModel):
    channel: Literal["朋友圈", "社群", "一对一"]
    copy: str = Field(min_length=1, max_length=3000)


class PrivateCommunicationProduction(StrictModel):
    applicable_scenario: str = Field(min_length=1, max_length=800)
    messages: list[PrivateMessage] = Field(min_length=1, max_length=6)
    follow_up_actions: list[str] = Field(min_length=1, max_length=12)
    communication_boundaries: list[str] = Field(min_length=1, max_length=12)


class OfflineMaterialProduction(StrictModel):
    core_copy: str = Field(min_length=1, max_length=2000)
    information_hierarchy: list[str] = Field(min_length=2, max_length=12)
    layout_or_placement_notes: list[str] = Field(min_length=1, max_length=12)
    action_guidance: str = Field(min_length=1, max_length=800)
    validity_boundary: str = Field(min_length=1, max_length=800)


class SituationalQA(StrictModel):
    question: str = Field(min_length=1, max_length=800)
    suggested_answer: str = Field(min_length=1, max_length=1600)


class TrainingProduction(StrictModel):
    training_goal: str = Field(min_length=1, max_length=800)
    audience: str = Field(min_length=1, max_length=500)
    outline: list[str] = Field(min_length=2, max_length=20)
    cases: list[str] = Field(min_length=1, max_length=12)
    exercises: list[str] = Field(min_length=1, max_length=12)
    facilitator_notes: list[str] = Field(min_length=1, max_length=20)
    situational_qa: list[SituationalQA] = Field(min_length=1, max_length=20)
    allowed_phrasing: list[str] = Field(min_length=1, max_length=20)
    prohibited_phrasing: list[str] = Field(min_length=1, max_length=20)


class ProductionPackage(StrictModel):
    production_format: ContentFormat
    task_summary: str = Field(min_length=1, max_length=1000)
    content_direction: str = Field(min_length=1, max_length=800)
    core_idea: str = Field(min_length=1, max_length=800)
    cover_or_first_screen_copy: str = Field(min_length=1, max_length=500)
    opening_hook: str = Field(min_length=1, max_length=800)
    story_or_full_script: str = Field(min_length=1, max_length=12_000)
    target_platform: str = Field(min_length=1, max_length=80)
    duration_label: str = Field(min_length=1, max_length=80)
    ending_and_action: str = Field(min_length=1, max_length=1200)
    publishing_copy: str = Field(min_length=1, max_length=2000)
    next_actions: list[str] = Field(min_length=1, max_length=12)
    video: VideoProduction | None = None
    article: ArticleProduction | None = None
    live: LiveProduction | None = None
    private_communication: PrivateCommunicationProduction | None = None
    offline_material: OfflineMaterialProduction | None = None
    training: TrainingProduction | None = None
    display: DisplayProduction | None = None

    @model_validator(mode="after")
    def validate_format_payload(self) -> ProductionPackage:
        payloads = {
            "短视频": self.video,
            "图文": self.article,
            "直播内容包": self.live,
            "私域沟通内容": self.private_communication,
            "门店线下物料": self.offline_material,
            "培训与门店话术": self.training,
            "陈列搭配": self.display,
        }
        if payloads[self.production_format] is None:
            raise ValueError("the selected content format needs its production payload")
        if sum(item is not None for item in payloads.values()) != 1:
            raise ValueError("exactly one format-specific production payload is allowed")
        return self


class CandidateSurfaces(StrictModel):
    title: str = Field(min_length=1, max_length=240)
    body: str = Field(min_length=1, max_length=12_000)
    spoken_lines: list[str] = Field(default_factory=list, max_length=30)
    CTA: str = Field(default="", max_length=500)
    execution_payload: ProductionPackage
    surface_units: list[dict[str, Any]] = Field(default_factory=list, max_length=80)

    @field_validator("spoken_lines")
    @classmethod
    def validate_spoken_lines(cls, value: list[str]) -> list[str]:
        if any(not isinstance(item, str) or not item.strip() or len(item) > 500 for item in value):
            raise ValueError("spoken_lines must contain short non-empty strings")
        return [item.strip() for item in value]


class ClaimBinding(StrictModel):
    surface_path: str = Field(
        min_length=1,
        max_length=240,
        pattern=r"^[a-zA-Z_][a-zA-Z0-9_]*(?:\[[0-9]+\]|\.[a-zA-Z_][a-zA-Z0-9_]*)*$",
    )
    exact_text: str = Field(min_length=1, max_length=12_000)
    claim_class: ClaimClass
    source_refs: list[str] = Field(default_factory=list, max_length=30)

    @field_validator("exact_text")
    @classmethod
    def normalize_exact_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("claim binding text must not be blank")
        return normalized

    @field_validator("source_refs")
    @classmethod
    def validate_source_refs(cls, value: list[str]) -> list[str]:
        normalized = [item.strip() for item in value]
        if any(not item or len(item) > 240 for item in normalized):
            raise ValueError("claim source refs must be short non-empty strings")
        if len(normalized) != len(set(normalized)):
            raise ValueError("claim source refs must not repeat")
        return normalized

    @model_validator(mode="after")
    def validate_claim_sources(self) -> ClaimBinding:
        if self.claim_class == "SOURCE_CLAIM" and not self.source_refs:
            raise ValueError("source claims need at least one source ref")
        if self.claim_class != "SOURCE_CLAIM" and self.source_refs:
            raise ValueError("creative directions and disclosures cannot cite source refs")
        return self


class ModelCandidate(StrictModel):
    difference_label: str = Field(min_length=1, max_length=120)
    narrative_architecture: NarrativeArchitecture | None = None
    difference_dimensions: list[
        Literal["核心创意", "切入问题或场景", "情绪钩子", "叙事视角", "事实或证明路径", "画面组织方法"]
    ] = Field(min_length=2, max_length=6)
    surfaces: CandidateSurfaces
    claim_bindings: list[ClaimBinding] = Field(default_factory=list, max_length=120)
    used_fact_refs: list[str] = Field(default_factory=list, max_length=30)
    used_material_refs: list[str] = Field(default_factory=list, max_length=30)

    @field_validator("difference_dimensions")
    @classmethod
    def validate_difference_dimensions(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("candidate difference dimensions must not repeat")
        return value


class ModelEnvelope(StrictModel):
    kind: Literal["CHAT_REPLY", "CANDIDATE_SET"]
    reply: str | None = Field(default=None, max_length=12_000)
    candidates: list[ModelCandidate] = Field(default_factory=list, max_length=3)

    @model_validator(mode="after")
    def validate_kind_payload(self) -> ModelEnvelope:
        if self.kind == "CHAT_REPLY":
            if not self.reply or self.candidates:
                raise ValueError("chat reply must contain reply only")
        elif len(self.candidates) not in {2, 3} or self.reply is not None:
            raise ValueError("candidate set must contain exactly two or three candidates")
        return self


class UsageReceipt(StrictModel):
    workflow_run_id: str = Field(min_length=1, max_length=160)
    model_provider: str = Field(min_length=1, max_length=200)
    model_name: str = Field(min_length=1, max_length=200)
    prompt_tokens: int = Field(ge=0)
    completion_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    total_price: str = Field(min_length=1, max_length=64)
    currency: str = Field(min_length=1, max_length=32)

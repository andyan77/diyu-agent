"""Application composition root -- wires all layers into a runnable FastAPI app.

Assembly layer for Phase 2 + Phase 3 delivery.
- Reads configuration from environment variables
- Creates async DB engine + session factory
- Instantiates all Port adapters and domain services
- Mounts P2 + P3 routers onto the FastAPI app
- Wires post-auth middleware chain (RBAC + RateLimit + Budget)
- Wires Skill orchestration into ConversationEngine

Entry point: uvicorn src.main:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import FastAPI

from src.brain.engine.conversation import ConversationEngine
from src.brain.engine.ws_handler import WSChatHandler
from src.brain.intent.classifier import IntentClassifier
from src.brain.memory.pipeline import MemoryWritePipeline
from src.brain.skill.orchestrator import SkillOrchestrator
from src.brain.skill.router import SkillRouter
from src.gateway.api.admin.auth import create_admin_auth_router
from src.gateway.api.admin.knowledge import create_knowledge_admin_router
from src.gateway.api.auth import create_auth_router
from src.gateway.api.conversations import create_conversation_router
from src.gateway.api.skills import create_skill_router
from src.gateway.api.upload import create_upload_router
from src.gateway.app import create_app
from src.gateway.llm.router import create_llm_router
from src.gateway.middleware.budget import BudgetPreCheckMiddleware, BudgetResolver
from src.gateway.middleware.rate_limit import RateLimitMiddleware
from src.gateway.middleware.rbac import RBACMiddleware
from src.gateway.sse.events import SSEBroadcaster, create_sse_router
from src.gateway.ws.conversation import create_ws_router
from src.infra.billing.budget import TokenBudgetManager
from src.infra.cache.redis import RedisStorageAdapter
from src.infra.db import create_db_engine, create_session_factory
from src.infra.graph.neo4j_adapter import Neo4jAdapter
from src.infra.vector.qdrant_adapter import QdrantAdapter
from src.knowledge.api.write_adapter import KnowledgeWriteAdapter
from src.knowledge.embedding import DeterministicEmbedder
from src.knowledge.resolver.resolver import DiyuResolver
from src.knowledge.sync.fk_registry import FKRegistry
from src.memory.events import PgConversationEventStore
from src.memory.pg_adapter import PgMemoryCoreAdapter
from src.memory.receipt import PgReceiptStore
from src.ports.skill_registry import SkillDefinition, SkillStatus
from src.skill.implementations.content_writer import ContentWriterSkill
from src.skill.implementations.merchandising import MerchandisingSkill
from src.skill.registry.lifecycle import LifecycleRegistry
from src.tool.llm.gateway_adapter import LiteLLMGatewayAdapter
from src.tool.llm.model_registry import ModelRegistry, ProviderConfig
from src.tool.llm.usage_tracker import UsageTracker

logger = logging.getLogger(__name__)


async def _bootstrap_skill_registry(registry: LifecycleRegistry) -> None:
    """Populate the skill registry with built-in skills.

    Called during app startup (async context). Registers directly
    on the live registry instance -- no copy needed.
    """
    # Register content_writer skill
    cw_defn = await registry.register(
        SkillDefinition(
            skill_id="content_writer",
            name="Content Writer",
            description="Generate marketing content from brand knowledge",
            intent_types=["content_writing", "copywriting"],
            version="1.0.0",
        ),
    )
    registry.bind_implementation(cw_defn.skill_id, ContentWriterSkill())
    await registry.update_status(cw_defn.skill_id, SkillStatus.ACTIVE)

    # Register merchandising skill
    merch_defn = await registry.register(
        SkillDefinition(
            skill_id="merchandising",
            name="Merchandising Advisor",
            description="Product merchandising recommendations",
            intent_types=["merchandising", "product_recommendation"],
            version="1.0.0",
        ),
    )
    registry.bind_implementation(merch_defn.skill_id, MerchandisingSkill())
    await registry.update_status(merch_defn.skill_id, SkillStatus.ACTIVE)

    logger.info("Skill registry bootstrapped: %d skills active", len(registry.list_skills()))


def build_app() -> FastAPI:
    """Build the application: instantiate adapters, wire dependencies, mount routers.

    This function is the single composition root. All DI wiring happens here.
    No other module should instantiate adapters or create cross-layer references.
    """
    # -- Configuration from environment --
    jwt_secret = os.environ.get("JWT_SECRET_KEY", "")
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    llm_api_key = os.environ.get("LLM_API_KEY", "")
    llm_model = os.environ.get("LLM_MODEL", "gpt-4o")
    llm_base_url = os.environ.get("LLM_BASE_URL", "") or None
    cors_origins_raw = os.environ.get("CORS_ORIGINS", "http://localhost:3000")
    cors_origins = [o.strip() for o in cors_origins_raw.split(",") if o.strip()]
    storage_base_url = os.environ.get("STORAGE_BASE_URL", "http://localhost:9000")
    database_url = os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://diyu:diyu_dev@localhost:25432/diyu",
    )

    if not jwt_secret:
        msg = "JWT_SECRET_KEY environment variable is required"
        raise RuntimeError(msg)

    # -- Infrastructure layer --
    storage = RedisStorageAdapter(redis_url=redis_url)
    db_engine = create_db_engine(database_url)
    session_factory = create_session_factory(db_engine)

    # -- Memory Core (Port adapter) --
    memory_core = PgMemoryCoreAdapter(session_factory=session_factory)
    event_store = PgConversationEventStore(session_factory=session_factory)
    receipt_store = PgReceiptStore(session_factory=session_factory)

    # -- Tool layer --
    llm_adapter = LiteLLMGatewayAdapter(
        default_model=llm_model,
        api_key=llm_api_key or None,
        base_url=llm_base_url,
    )
    model_registry = ModelRegistry(
        adapter=llm_adapter,
        primary="openai",
        providers={
            "openai": ProviderConfig(
                name="openai",
                models=[llm_model],
                default_model=llm_model,
            ),
        },
    )
    usage_tracker = UsageTracker()

    # -- Skill layer (P3) --
    skill_registry = LifecycleRegistry()

    # -- Knowledge layer: Neo4j + Qdrant + FK Registry + Resolver (P3) --
    neo4j_adapter = Neo4jAdapter()
    qdrant_adapter = QdrantAdapter()
    fk_registry = FKRegistry(neo4j=neo4j_adapter, qdrant=qdrant_adapter)
    knowledge_resolver = DiyuResolver(neo4j=neo4j_adapter, qdrant=qdrant_adapter)

    # -- Embedding adapter (Decision 1-B: deterministic dummy) --
    embedder = DeterministicEmbedder()

    # -- Knowledge write adapter for Gateway (P3) --
    # Accepts Neo4j/Qdrant for dual-write; falls back to in-memory if connect() fails.
    knowledge_writer = KnowledgeWriteAdapter(
        neo4j=neo4j_adapter,
        qdrant=qdrant_adapter,
        fk_registry=fk_registry,
        embedder=embedder,
    )

    # -- Brain layer --
    intent_classifier = IntentClassifier()
    memory_pipeline = MemoryWritePipeline(
        memory_core=memory_core,
        receipt_store=receipt_store,
    )

    # Skill orchestration (P3): Router -> Orchestrator -> injected into Engine
    skill_router = SkillRouter(registry=skill_registry)
    skill_orchestrator = SkillOrchestrator(
        router=skill_router,
        registry=skill_registry,
        knowledge=knowledge_resolver,
    )

    engine = ConversationEngine(
        llm=model_registry,
        memory_core=memory_core,
        intent_classifier=intent_classifier,
        memory_pipeline=memory_pipeline,
        usage_tracker=usage_tracker,
        event_store=event_store,
        default_model=llm_model,
        skill_orchestrator=skill_orchestrator,
        knowledge=knowledge_resolver,
    )
    ws_handler = WSChatHandler(engine=engine)
    sse_broadcaster = SSEBroadcaster()

    # -- Middleware (post-auth chain) --
    rbac_mw = RBACMiddleware()
    budget_manager = TokenBudgetManager()
    budget_resolver = BudgetResolver()
    rate_limit_mw = RateLimitMiddleware()
    budget_mw = BudgetPreCheckMiddleware(
        budget_manager=budget_manager,
        budget_resolver=budget_resolver,
    )

    # -- Create FastAPI app with middleware chain --
    # Order: rate_limit (cheapest check first), RBAC (auth boundary), then budget
    application = create_app(
        jwt_secret=jwt_secret,
        cors_origins=cors_origins,
        post_auth_middlewares=[rate_limit_mw, rbac_mw, budget_mw],
    )

    # -- Store references on app.state for lifespan management --
    application.state.db_engine = db_engine
    application.state.session_factory = session_factory
    application.state.storage = storage
    application.state.sse_broadcaster = sse_broadcaster
    application.state.usage_tracker = usage_tracker
    application.state.skill_registry = skill_registry
    application.state.neo4j_adapter = neo4j_adapter
    application.state.qdrant_adapter = qdrant_adapter
    application.state.knowledge_writer = knowledge_writer

    # -- Mount P2 routers --
    application.include_router(create_auth_router())
    application.include_router(
        create_conversation_router(engine=engine),
    )
    application.include_router(
        create_ws_router(handler=ws_handler, jwt_secret=jwt_secret),
    )
    application.include_router(
        create_sse_router(broadcaster=sse_broadcaster, jwt_secret=jwt_secret),
    )
    application.include_router(
        create_llm_router(llm_adapter=llm_adapter, usage_tracker=usage_tracker),
    )
    application.include_router(
        create_upload_router(storage_base_url=storage_base_url),
    )

    # -- Mount P3 routers --
    application.include_router(
        create_skill_router(registry=skill_registry),
    )
    application.include_router(
        create_knowledge_admin_router(knowledge_writer=knowledge_writer),
    )
    application.include_router(
        create_admin_auth_router(),
    )

    # -- Knowledge store connection mode (Decision 2-C) --
    # "required" = startup fails if stores unavailable (production)
    # "optional" = degrade to in-memory silently (dev/CI)
    knowledge_store_mode = os.environ.get("KNOWLEDGE_STORE_MODE", "optional")

    # -- Lifespan: connect knowledge stores + bootstrap skills on startup --
    @application.on_event("startup")
    async def _startup_bootstrap() -> None:
        # Connect Neo4j + Qdrant
        try:
            await neo4j_adapter.connect()
            await qdrant_adapter.connect()
            logger.info("Knowledge stores connected (Neo4j + Qdrant)")
        except Exception:
            if knowledge_store_mode == "required":
                logger.error(
                    "Knowledge stores unavailable and KNOWLEDGE_STORE_MODE=required. "
                    "Aborting startup."
                )
                raise
            logger.warning(
                "Knowledge stores unavailable — falling back to in-memory adapter. "
                "Set NEO4J_URI / QDRANT_URL env vars or start docker-compose. "
                "Set KNOWLEDGE_STORE_MODE=required to make this a fatal error.",
                exc_info=True,
            )
            # Clear references so write_adapter degrades to in-memory
            knowledge_writer._neo4j = None
            knowledge_writer._qdrant = None
            knowledge_writer._fk_registry = None

        await _bootstrap_skill_registry(skill_registry)
        logger.info("Startup bootstrap complete: %d skills", len(skill_registry.list_skills()))

    @application.on_event("shutdown")
    async def _shutdown_cleanup() -> None:
        try:
            await neo4j_adapter.close()
        except Exception:
            logger.debug("Neo4j close failed", exc_info=True)
        try:
            await qdrant_adapter.close()
        except Exception:
            logger.debug("Qdrant close failed", exc_info=True)

    logger.info(
        "DIYU Agent app assembled: %d routes mounted",
        len(application.routes),
    )

    return application


app = build_app()

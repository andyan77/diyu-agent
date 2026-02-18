"""Application composition root -- wires all layers into a runnable FastAPI app.

Wave 0 + Wave 1: Assembly layer for Phase 2 delivery.
- Reads configuration from environment variables
- Creates async DB engine + session factory (Wave 1)
- Instantiates all Port adapters and domain services
- Mounts all P2 routers onto the FastAPI app
- Wires post-auth middleware chain (RateLimit + Budget)

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
from src.gateway.api.conversations import create_conversation_router
from src.gateway.api.upload import create_upload_router
from src.gateway.app import create_app
from src.gateway.llm.router import create_llm_router
from src.gateway.middleware.budget import BudgetPreCheckMiddleware, BudgetResolver
from src.gateway.middleware.rate_limit import RateLimitMiddleware
from src.gateway.sse.events import SSEBroadcaster, create_sse_router
from src.gateway.ws.conversation import create_ws_router
from src.infra.billing.budget import TokenBudgetManager
from src.infra.cache.redis import RedisStorageAdapter
from src.infra.db import create_db_engine, create_session_factory
from src.memory.events import PgConversationEventStore
from src.memory.pg_adapter import PgMemoryCoreAdapter
from src.memory.receipt import PgReceiptStore
from src.tool.llm.gateway_adapter import LiteLLMGatewayAdapter
from src.tool.llm.model_registry import ModelRegistry, ProviderConfig
from src.tool.llm.usage_tracker import UsageTracker

logger = logging.getLogger(__name__)


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
        "postgresql+asyncpg://diyu:diyu_dev@localhost:5432/diyu",
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

    # -- Brain layer --
    intent_classifier = IntentClassifier()
    memory_pipeline = MemoryWritePipeline(
        memory_core=memory_core,
        receipt_store=receipt_store,
    )
    engine = ConversationEngine(
        llm=model_registry,
        memory_core=memory_core,
        intent_classifier=intent_classifier,
        memory_pipeline=memory_pipeline,
        usage_tracker=usage_tracker,
        event_store=event_store,
        default_model=llm_model,
    )
    ws_handler = WSChatHandler(engine=engine)
    sse_broadcaster = SSEBroadcaster()

    # -- Middleware (post-auth chain) --
    budget_manager = TokenBudgetManager()
    budget_resolver = BudgetResolver()
    rate_limit_mw = RateLimitMiddleware()
    budget_mw = BudgetPreCheckMiddleware(
        budget_manager=budget_manager,
        budget_resolver=budget_resolver,
    )

    # -- Create FastAPI app with middleware chain --
    # Order: rate limit first (cheap check), then budget (requires org lookup)
    application = create_app(
        jwt_secret=jwt_secret,
        cors_origins=cors_origins,
        post_auth_middlewares=[rate_limit_mw, budget_mw],
    )

    # -- Store references on app.state for lifespan management --
    application.state.db_engine = db_engine
    application.state.session_factory = session_factory
    application.state.storage = storage
    application.state.sse_broadcaster = sse_broadcaster
    application.state.usage_tracker = usage_tracker

    # -- Mount P2 routers --
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
        create_llm_router(llm_adapter=model_registry, usage_tracker=usage_tracker),
    )
    application.include_router(
        create_upload_router(storage_base_url=storage_base_url),
    )

    logger.info(
        "DIYU Agent app assembled: %d routes mounted",
        len(application.routes),
    )

    return application


app = build_app()

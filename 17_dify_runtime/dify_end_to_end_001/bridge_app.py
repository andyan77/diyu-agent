#!/usr/bin/env python3
"""HTTP entrypoint for the isolated non-production Package 7 bridge."""

from __future__ import annotations

import base64
import hashlib
import ipaddress
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flask import Flask, g, jsonify, request, send_from_directory
from pydantic import ValidationError

from contracts import (
    BridgeFinalizeRequest,
    BridgePrepareRequest,
    LoginRequest,
    PortalTaskRequest,
    normalize_model_json_text,
)
from dify_chat import DifyChatClient, DifyChatError
from dify_knowledge import DifyKnowledgeClient, KnowledgeRetrievalError
from persistence import (
    RuntimeRepository,
    SqlAlchemyPlanStore,
    TrustedDatabaseScope,
    create_runtime_engine,
    create_session_factory,
    digest_object,
    trusted_database_scope,
)
from runtime_retrieval import RuntimeBrandFactRetrievalService
from runtime_service import Package7Runtime, RuntimeContractError
from security import issue_session, verify_bridge_secret, verify_password, verify_session
from seed_runtime import seed_database


JsonObject = dict[str, Any]
PACKAGE_ROOT = Path(__file__).resolve().parent
SESSION_COOKIE = "diyu_pkg7_session"
PORTAL_HEADER = "same-origin-v1"
PORTAL_OPERATION_MAP = {
    "随便聊聊": "普通聊天",
    "找点灵感": "找灵感",
    "直接做内容": "确认制作",
    "把已有内容改好": "局部修改",
    "继续一个系列": "确认制作",
    "选择候选": "选择候选",
    "审核": "审核",
    "导出": "导出",
    "查看来源": "查看来源",
    "提交反馈": "提交反馈",
}


def required_env(name: str, *, minimum_length: int = 1) -> str:
    value = os.environ.get(name, "")
    if len(value) < minimum_length:
        raise RuntimeError(f"Required configuration is missing: {name}")
    return value


def build_runtime() -> tuple[Package7Runtime, RuntimeRepository, DifyChatClient]:
    database_url = required_env("DIYU_PKG7_DATABASE_URL")
    engine = create_runtime_engine(database_url)
    sessions = create_session_factory(engine)
    repository = RuntimeRepository(sessions)
    database_is_managed = (
        os.environ.get("DIYU_PKG9_MANAGED_DATABASE", "false").lower() == "true"
    )
    if not database_is_managed:
        repository.initialize_schema(engine)
        seed_database(
            engine,
            sessions,
            username=required_env("DIYU_SIM_USERNAME"),
            password=required_env("DIYU_SIM_PASSWORD", minimum_length=12),
        )
    state_path = Path(required_env("DIYU_DIFY_STATE_PATH"))
    state = json.loads(state_path.read_text(encoding="utf-8"))
    document_mapping = state.get("fragment_document_ids") if isinstance(state, dict) else None
    if not isinstance(document_mapping, dict) or any(
        not isinstance(key, str)
        or not isinstance(value, dict)
        or not isinstance(value.get("document_id"), str)
        or not isinstance(value.get("source_content_sha256"), str)
        or not isinstance(value.get("index_content_sha256"), str)
        for key, value in document_mapping.items()
    ):
        raise RuntimeError("The Dify fragment mapping is invalid")
    mapping_digest = state.get("fragment_document_mapping_digest") if isinstance(state, dict) else None
    if not isinstance(mapping_digest, str) or mapping_digest != digest_object(document_mapping):
        raise RuntimeError("The Dify fragment mapping digest is invalid")
    dataset_api_token = state.get("dataset_api_token") if isinstance(state, dict) else None
    app_api_token = state.get("app_api_token") if isinstance(state, dict) else None
    if not isinstance(dataset_api_token, str) or len(dataset_api_token) < 16:
        raise RuntimeError("The Dify dataset API credential is invalid")
    if not isinstance(app_api_token, str) or len(app_api_token) < 16:
        raise RuntimeError("The Dify app API credential is invalid")
    if not database_is_managed:
        repository.bind_dify_documents(document_mapping)
    knowledge = DifyKnowledgeClient(
        base_url=required_env("DIYU_DIFY_SERVICE_API_URL"),
        dataset_api_token=dataset_api_token,
        dataset_id=required_env("DIYU_DIFY_DATASET_ID"),
    )
    retrieval = RuntimeBrandFactRetrievalService(repository, knowledge)
    runtime = Package7Runtime(repository, SqlAlchemyPlanStore(sessions), retrieval)
    chat = DifyChatClient(
        base_url=required_env("DIYU_DIFY_SERVICE_API_URL"),
        app_api_token=app_api_token,
        repository=repository,
        maximum_model_calls=int(os.environ.get("DIYU_PKG7_MAX_MODEL_CALLS", "40")),
    )
    return runtime, repository, chat


def create_app(
    runtime: Package7Runtime | None = None,
    repository: RuntimeRepository | None = None,
    dify_chat: DifyChatClient | None = None,
) -> Flask:
    app = Flask(__name__)
    if runtime is not None and repository is not None:
        active_runtime, active_repository, active_chat = runtime, repository, dify_chat
    else:
        active_runtime, active_repository, active_chat = build_runtime()
    signing_key = required_env("DIYU_SESSION_SIGNING_KEY", minimum_length=32)
    bridge_secret = required_env("DIYU_BRIDGE_SECRET", minimum_length=32)
    trusted_tenant_id = os.environ.get("DIYU_SIM_TENANT_ID", "TENANT-DIYU-SIM-001")
    if not trusted_tenant_id.strip():
        raise RuntimeError("The trusted simulation tenant is missing")
    secure_cookie = os.environ.get("DIYU_COOKIE_SECURE", "false").lower() == "true"

    @app.before_request
    def establish_database_scope() -> None:
        principal_id = None
        token = request.cookies.get(SESSION_COOKIE, "")
        if token:
            try:
                principal_id = str(verify_session(token, signing_key)["principal_id"])
            except ValueError:
                principal_id = None
        manager = trusted_database_scope(
            TrustedDatabaseScope(
                tenant_id=trusted_tenant_id,
                principal_id=principal_id,
            )
        )
        manager.__enter__()
        g.diyu_database_scope_manager = manager

    @app.teardown_request
    def clear_database_scope(error: BaseException | None) -> None:
        manager = getattr(g, "diyu_database_scope_manager", None)
        if manager is not None:
            manager.__exit__(
                None if error is None else type(error),
                error,
                None if error is None else error.__traceback__,
            )

    @app.before_request
    def keep_portal_on_trusted_networks() -> Any:
        portal_paths = ("/portal", "/login", "/logout", "/v1/portal")
        if not request.path.startswith(portal_paths):
            return None
        try:
            address = ipaddress.ip_address(request.remote_addr or "")
        except ValueError:
            return _plain_error("当前入口不可用。"), 404
        if not (address.is_private or address.is_loopback):
            return _plain_error("当前入口不可用。"), 404
        return None

    @app.after_request
    def security_headers(response: Any) -> Any:
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'"
        )
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        return response

    @app.get("/health")
    def health() -> Any:
        return jsonify(
            {
                "status": "healthy",
                "service": "diyu-package7-nonproduction-bridge",
                "simulation_only": True,
                "production_ready": False,
            }
        )

    @app.get("/portal")
    @app.get("/")
    def portal() -> Any:
        return send_from_directory(PACKAGE_ROOT, "portal.html")

    @app.get("/portal.js")
    def portal_javascript() -> Any:
        return send_from_directory(PACKAGE_ROOT, "portal.js", mimetype="application/javascript")

    @app.get("/portal.css")
    def portal_stylesheet() -> Any:
        return send_from_directory(PACKAGE_ROOT, "portal.css", mimetype="text/css")

    @app.post("/login")
    def login() -> Any:
        try:
            payload = LoginRequest.model_validate(request.get_json(force=True, silent=False))
        except (ValidationError, ValueError):
            return _plain_error("登录信息格式不正确。"), 400
        principal = active_repository.principal_by_username(payload.username)
        if (
            principal is None
            or principal.status != "ACTIVE"
            or not verify_password(payload.password, principal.password_hash)
        ):
            return _plain_error("登录信息不匹配。"), 401
        token = issue_session(
            principal_id=principal.principal_id,
            allowed_account_ids=principal.allowed_account_ids,
            signing_key=signing_key,
        )
        response = jsonify(
            {
                "simulation_only": True,
                "notice": "仅用于内部非生产测试，不可发布。",
                "options": active_runtime.portal_options(principal.principal_id),
            }
        )
        response.set_cookie(
            SESSION_COOKIE,
            token,
            httponly=True,
            secure=secure_cookie,
            samesite="Strict",
            max_age=3_600,
            path="/",
        )
        return response

    @app.post("/logout")
    def logout() -> Any:
        if request.headers.get("X-Diyu-Portal") != PORTAL_HEADER:
            return _plain_error("当前访问未通过页面确认。"), 404
        response = jsonify({"logged_out": True})
        response.delete_cookie(SESSION_COOKIE, path="/")
        return response

    @app.get("/v1/portal/options")
    def portal_options() -> Any:
        try:
            session = _portal_session(signing_key)
            return jsonify(active_runtime.portal_options(str(session["principal_id"])))
        except ValueError:
            return _plain_error("登录已失效，请重新登录。"), 401

    @app.post("/v1/portal/chat")
    def portal_chat() -> Any:
        if request.headers.get("X-Diyu-Portal") != PORTAL_HEADER:
            return _plain_error("当前访问未通过页面确认。"), 404
        if active_chat is None:
            return _plain_error("Dify内部入口尚未连接。"), 503
        try:
            session = _portal_session(signing_key)
            payload = PortalTaskRequest.model_validate(request.get_json(force=True, silent=False))
            principal_id = str(session["principal_id"])
            runtime_request = _portal_inputs(payload, principal_id, active_repository)
            _, account = active_repository.require_active_scope_by_display_name(
                principal_id,
                payload.account_display_name,
            )
            conversation_scope = account.account_id
            user_key = hashlib.sha256(
                f"package7-dify-user:{principal_id}:{conversation_scope}".encode("utf-8")
            ).hexdigest()
            if runtime_request["operation"] == "确认制作":
                classifier = active_chat.invoke(
                    invocation_id=_invocation_id(principal_id, payload.message, "CLASSIFY"),
                    principal_id=principal_id,
                    conversation_scope=conversation_scope,
                    user_key=f"pkg7-{user_key[:24]}",
                    query=payload.message,
                    inputs={
                        "execution_phase": "CLASSIFY",
                        "operation": runtime_request["operation"],
                        "topic_label": payload.topic_label or "未指定题材",
                        "message": payload.message,
                        "classification_options": json.dumps(
                            active_runtime.classification_options(payload.topic_label),
                            ensure_ascii=False,
                            separators=(",", ":"),
                        ),
                        "author_prompt": "",
                    },
                    reuse_conversation=False,
                )
                runtime_request["selected_content_product_id"] = _selected_product(
                    classifier["answer"]
                )
            prepared = active_runtime.prepare(
                BridgePrepareRequest.model_validate(runtime_request),
                principal_id,
            )
            if prepared.get("response_kind") != "MODEL_REQUIRED":
                return jsonify(
                    {
                        "answer": str(prepared.get("user_visible_text", "当前请求已停止。")),
                        "simulation_only": True,
                        "publish_allowed": False,
                    }
                )
            author_prompt = prepared.get("author_prompt")
            run_id = prepared.get("run_id")
            if not isinstance(author_prompt, dict) or not isinstance(run_id, str):
                raise RuntimeContractError("Prepared model run is incomplete")
            author_query = (
                payload.message
                if runtime_request["operation"] in {"普通聊天", "找灵感"}
                else "执行服务端受控的首次内部内容任务。"
            )
            result = active_chat.invoke(
                invocation_id=_invocation_id(principal_id, run_id, "AUTHOR"),
                principal_id=principal_id,
                conversation_scope=conversation_scope,
                user_key=f"pkg7-{user_key[:24]}",
                query=author_query,
                inputs={
                    "execution_phase": "AUTHOR",
                    "operation": runtime_request["operation"],
                    "topic_label": payload.topic_label or "未指定题材",
                    "message": payload.message,
                    "classification_options": "[]",
                    "author_prompt": json.dumps(
                        author_prompt,
                        ensure_ascii=False,
                        separators=(",", ":"),
                    ),
                },
                reuse_conversation=runtime_request["operation"]
                in {"普通聊天", "找灵感"},
            )
            finalized = active_runtime.finalize_model_output(
                run_id,
                base64.b64encode(result["answer"].encode("utf-8")).decode("ascii"),
            )
            return jsonify(
                {
                    "answer": str(finalized.get("user_visible_text", "当前结果已停止。")),
                    "simulation_only": True,
                    "publish_allowed": False,
                }
            )
        except (
            ValidationError,
            RuntimeContractError,
            DifyChatError,
            KnowledgeRetrievalError,
            ValueError,
            KeyError,
        ):
            return _plain_error("当前操作无法继续，请核对账号、题材和已确认信息。"), 400

    @app.post("/v1/workflow/prepare")
    def workflow_prepare() -> Any:
        if not verify_bridge_secret(request.headers.get("X-Diyu-Bridge-Key"), bridge_secret):
            return _plain_error("当前访问未通过可信入口确认。"), 404
        try:
            payload = BridgePrepareRequest.model_validate(request.get_json(force=True, silent=False))
            session = verify_session(payload.session_token, signing_key)
            with trusted_database_scope(
                TrustedDatabaseScope(
                    tenant_id=trusted_tenant_id,
                    principal_id=str(session["principal_id"]),
                )
            ):
                result = active_runtime.prepare(payload, str(session["principal_id"]))
            return jsonify(result)
        except (
            ValidationError,
            RuntimeContractError,
            KnowledgeRetrievalError,
            ValueError,
            KeyError,
        ):
            return _plain_error("当前操作无法继续，请核对账号、题材和已确认信息。"), 400

    @app.post("/v1/workflow/finalize")
    def workflow_finalize() -> Any:
        if not verify_bridge_secret(request.headers.get("X-Diyu-Bridge-Key"), bridge_secret):
            return _plain_error("当前访问未通过可信入口确认。"), 404
        try:
            payload = BridgeFinalizeRequest.model_validate(request.get_json(force=True, silent=False))
            session = verify_session(payload.session_token, signing_key)
            with trusted_database_scope(
                TrustedDatabaseScope(
                    tenant_id=trusted_tenant_id,
                    principal_id=str(session["principal_id"]),
                )
            ):
                run = active_repository.model_run(payload.run_id)
                if run is None or run.principal_id != session["principal_id"]:
                    raise RuntimeContractError("Run scope mismatch")
                return jsonify(
                    active_runtime.finalize_model_output(
                        payload.run_id,
                        payload.model_output_b64,
                    )
                )
        except (ValidationError, RuntimeContractError, ValueError, KeyError):
            return _plain_error("模型结果未通过当前检查，已保留首次结果并停止。"), 400

    return app


def _portal_session(signing_key: str) -> JsonObject:
    token = request.cookies.get(SESSION_COOKIE, "")
    return verify_session(token, signing_key)


def _portal_inputs(
    payload: PortalTaskRequest,
    principal_id: str,
    repository: RuntimeRepository,
) -> JsonObject:
    try:
        _, account = repository.require_active_scope_by_display_name(
            principal_id,
            payload.account_display_name,
        )
    except ValueError as exc:
        raise RuntimeContractError("Portal account is outside the current scope") from exc
    previous_ref = None
    if payload.continue_previous or payload.operation == "继续一个系列":
        previous = repository.latest_candidate(account.account_id)
        if previous is None:
            raise RuntimeContractError("No previous content is available for this account")
        previous_ref = previous.candidate_id
    operation = PORTAL_OPERATION_MAP[payload.operation]
    candidate_number = payload.candidate_number
    if operation == "局部修改" and candidate_number is None:
        candidate_number = 1
    return {
        "session_token": request.cookies.get(SESSION_COOKIE, ""),
        "account_display_name": payload.account_display_name,
        "operation": operation,
        "topic_label": payload.topic_label,
        "selected_content_product_id": None,
        "primary_audience": payload.primary_audience,
        "message": payload.message,
        "target_platform": payload.target_platform,
        "candidate_number": candidate_number,
        "content_goal": payload.content_goal,
        "key_takeaway": payload.key_takeaway,
        "speaker_role_name": payload.speaker_role_name,
        "storyline_name": payload.storyline_name,
        "column_name": payload.column_name,
        "previous_content_ref": previous_ref,
        "localization_allowed": payload.localization_allowed,
        "duration_label": payload.duration_label,
        "expression_feeling": payload.expression_feeling,
        "content_format": payload.content_format,
        "existing_material_kinds": payload.existing_material_kinds,
    }


def _invocation_id(principal_id: str, subject: str, phase: str) -> str:
    now = datetime.now(timezone.utc).isoformat()
    return f"DIFY-{phase}-{digest_object([principal_id, subject, phase, now])[:20].upper()}"


def _selected_product(answer: str) -> str | None:
    try:
        normalized, _ = normalize_model_json_text(answer)
        value = json.loads(normalized).get("selected_content_product_id")
    except (AttributeError, ValueError, json.JSONDecodeError):
        return None
    if isinstance(value, str) and len(value) == 4 and value.startswith("CP") and value[2:].isdigit():
        return value
    return None


def _plain_error(message: str) -> Any:
    return jsonify({"response_kind": "DIRECT", "user_visible_text": message, "action_card": True})


def main() -> int:
    app = create_app()
    host = os.environ.get("DIYU_BRIDGE_BIND_HOST", "0.0.0.0")
    port = int(required_env("DIYU_BRIDGE_PORT"))
    app.run(host=host, port=port, debug=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

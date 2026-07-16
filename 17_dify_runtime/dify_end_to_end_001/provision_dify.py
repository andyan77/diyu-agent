#!/usr/bin/env python3
"""Idempotently create the one Package 7 Dify app and knowledge base."""

from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from flask_login import login_user
from sqlalchemy import select


APP_NAME = "DIYU Package 7 End-to-End (non-production)"
DATASET_NAME = "DIYU Package 7 Narrative Truth (non-production)"
METADATA_FIELDS = {
    "fragment_id": "string",
    "tenant_id": "string",
    "brand_id": "string",
    "status": "string",
    "authorization_state": "string",
    "authorization_ref": "string",
    "account_scope": "string",
    "organization_scope": "string",
    "store_scope": "string",
    "valid_from": "time",
    "valid_until": "time",
    "revocation_state": "string",
    "source_ref": "string",
    "content_digest": "string",
}


def _token(value: object) -> str:
    return f"|{value if value is not None else 'NONE'}|"


def _scope(values: list[object]) -> str:
    return "".join(sorted(_token(value) for value in values))


def _timestamp(value: str) -> float:
    normalized = f"{value[:-1]}+00:00" if value.endswith("Z") else value
    return datetime.fromisoformat(normalized).timestamp()


def _read_fragments(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=lambda item: item.model_dump(mode="json"),
    )


def _workflow_payload(workflow: Any) -> tuple[object, ...]:
    """Return a semantic snapshot of fields copied into a published workflow."""
    return (
        str(workflow.type),
        workflow.kind_or_standard,
        _canonical_json(workflow.graph_dict),
        _canonical_json(workflow.features_dict),
        _canonical_json(workflow.environment_variables),
        _canonical_json(workflow.conversation_variables),
        _canonical_json(workflow.rag_pipeline_variables),
    )


def main() -> int:
    dsl_path = Path(os.environ["PACKAGE7_DSL_PATH"])
    fragments_path = Path(os.environ["PACKAGE7_FRAGMENTS_PATH"])
    state_path = Path(os.environ["PACKAGE7_STATE_PATH"])

    from app_factory import create_app

    app = create_app()[1]
    with app.app_context(), app.test_request_context("/package7-provision"):
        from extensions.ext_database import db
        from models import Account, App
        from models.dataset import Dataset, DatasetMetadata, Document, DocumentSegment
        from models.enums import ApiTokenType
        from models.model import ApiToken
        from services.app_dsl_service import AppDslService
        from services.dataset_service import DatasetService, DocumentService
        from services.entities.knowledge_entities.knowledge_entities import (
            DataSource,
            DocumentMetadataOperation,
            FileInfo,
            InfoList,
            KnowledgeConfig,
            MetadataArgs,
            MetadataDetail,
            MetadataOperationData,
            ProcessRule,
            RetrievalModel,
        )
        from services.file_service import FileService
        from services.metadata_service import MetadataService
        from services.workflow_service import WorkflowService

        locked_state: dict[str, Any] = {}
        if state_path.exists():
            parsed_state = json.loads(state_path.read_text(encoding="utf-8"))
            if not isinstance(parsed_state, dict):
                raise RuntimeError("The Package 7 Dify state is invalid")
            locked_state = parsed_state
        locked_app_id = locked_state.get("app_id")
        existing_app = db.session.get(App, locked_app_id) if isinstance(locked_app_id, str) else None
        if locked_app_id is not None and (
            existing_app is None
            or existing_app.name != APP_NAME
            or str(existing_app.tenant_id) != str(locked_state.get("tenant_id"))
        ):
            raise RuntimeError("The locked Package 7 Dify application drifted")
        if existing_app is not None:
            tenant_id = existing_app.tenant_id
            locked_owner_id = locked_state.get("owner_account_id")
            owner_account_id = (
                locked_owner_id if isinstance(locked_owner_id, str) else existing_app.created_by
            )
            owner_binding_source = (
                "LOCKED_PACKAGE7_STATE"
                if isinstance(locked_owner_id, str)
                else "CURRENT_PACKAGE7_APP_ONE_TIME_LOCK"
            )
            if str(existing_app.created_by) != str(owner_account_id):
                raise RuntimeError("The locked Package 7 Dify application owner drifted")
        else:
            tenant_id = os.environ.get("PACKAGE7_APPROVED_DIFY_TENANT_ID")
            owner_account_id = os.environ.get("PACKAGE7_APPROVED_DIFY_OWNER_ACCOUNT_ID")
            if not tenant_id or not owner_account_id:
                raise RuntimeError("An explicit Package 7 Dify workspace and owner are required")
            matching_apps = list(
                db.session.scalars(
                    select(App).where(App.tenant_id == tenant_id, App.name == APP_NAME)
                ).all()
            )
            if len(matching_apps) > 1:
                raise RuntimeError("Multiple Package 7 Dify applications exist")
            existing_app = matching_apps[0] if matching_apps else None
            if existing_app is not None and str(existing_app.created_by) != owner_account_id:
                raise RuntimeError("The approved Package 7 Dify owner does not own the existing app")
            owner_binding_source = "EXPLICIT_OPERATOR_APPROVAL"
        account = db.session.get(Account, owner_account_id)
        if account is None:
            raise RuntimeError("The approved Package 7 Dify owner is unavailable")
        account.set_tenant_id(tenant_id)
        login_user(account)

        dsl = dsl_path.read_text(encoding="utf-8")
        imported = AppDslService(db.session()).import_app(
            account=account,
            import_mode="yaml-content",
            yaml_content=dsl,
            app_id=None if existing_app is None else existing_app.id,
        )
        if imported.status.value != "completed" or imported.app_id is None:
            raise RuntimeError(f"Dify app import failed: {imported.error}")
        app_model = db.session.get(App, imported.app_id)
        if app_model is None:
            raise RuntimeError("Imported Dify app is missing")
        if locked_app_id is not None and str(app_model.id) != locked_app_id:
            raise RuntimeError("The Package 7 Dify application identity changed")
        app_name_matches = list(
            db.session.scalars(
                select(App).where(App.tenant_id == tenant_id, App.name == APP_NAME)
            ).all()
        )
        if len(app_name_matches) != 1 or str(app_name_matches[0].id) != str(app_model.id):
            raise RuntimeError("The Package 7 Dify application is not unique")
        if not hasattr(app_model, "enable_site") or not hasattr(app_model, "enable_api"):
            raise RuntimeError("This Dify version cannot enforce an API-only Package 7 app")
        app_model.enable_site = False
        app_model.enable_api = True
        db.session.commit()
        workflow_service = WorkflowService()
        draft_workflow = workflow_service.get_draft_workflow(app_model, session=db.session)
        if draft_workflow is None:
            raise RuntimeError("Imported Dify app has no draft workflow")
        published_workflow = None
        if app_model.workflow_id is not None:
            published_workflow = workflow_service.get_published_workflow_by_id(
                app_model,
                app_model.workflow_id,
                session=db.session,
            )
        if published_workflow is None or _workflow_payload(published_workflow) != _workflow_payload(draft_workflow):
            published_workflow = workflow_service.publish_workflow(
                session=db.session,
                app_model=app_model,
                account=account,
                marked_name="Package 7 frozen non-production graph",
                marked_comment="Internal acceptance only; all readiness flags remain false.",
            )
            db.session.flush()
            app_model.workflow_id = published_workflow.id
            app_model.updated_by = account.id
            db.session.commit()
            db.session.refresh(app_model)
        if published_workflow is None or app_model.workflow_id != published_workflow.id:
            raise RuntimeError("Published Package 7 workflow is not active")

        locked_dataset_id = locked_state.get("dataset_id")
        dataset = (
            db.session.get(Dataset, locked_dataset_id)
            if isinstance(locked_dataset_id, str)
            else None
        )
        if locked_dataset_id is not None and (
            dataset is None
            or dataset.name != DATASET_NAME
            or str(dataset.tenant_id) != str(tenant_id)
        ):
            raise RuntimeError("The locked Package 7 Dify dataset drifted")
        if dataset is None:
            matching_datasets = list(
                db.session.scalars(
                    select(Dataset).where(
                        Dataset.tenant_id == tenant_id,
                        Dataset.name == DATASET_NAME,
                    )
                ).all()
            )
            if len(matching_datasets) > 1:
                raise RuntimeError("Multiple Package 7 Dify datasets exist")
            dataset = matching_datasets[0] if matching_datasets else None
        if dataset is None:
            dataset = DatasetService.create_empty_dataset(
                tenant_id=tenant_id,
                name=DATASET_NAME,
                description="Package 7 isolated narrative retrieval truth; simulation-only and non-production.",
                indexing_technique="economy",
                account=account,
                permission="only_me",
                retrieval_model=RetrievalModel(
                    search_method="keyword_search",
                    reranking_enable=False,
                    reranking_model=None,
                    reranking_mode=None,
                    top_k=8,
                    score_threshold_enabled=False,
                    score_threshold=None,
                ),
            )
            db.session.commit()
        if not hasattr(dataset, "enable_api"):
            raise RuntimeError("This Dify version cannot enable the Package 7 dataset API")
        dataset_name_matches = list(
            db.session.scalars(
                select(Dataset).where(
                    Dataset.tenant_id == tenant_id,
                    Dataset.name == DATASET_NAME,
                )
            ).all()
        )
        if len(dataset_name_matches) != 1 or str(dataset_name_matches[0].id) != str(dataset.id):
            raise RuntimeError("The Package 7 Dify dataset is not unique")
        dataset.enable_api = True
        db.session.commit()

        fields = {
            row.name: row
            for row in db.session.scalars(
                select(DatasetMetadata).where(DatasetMetadata.dataset_id == dataset.id)
            ).all()
        }
        for name, kind in METADATA_FIELDS.items():
            if name not in fields:
                fields[name] = MetadataService.create_metadata(
                    db.session,
                    dataset.id,
                    MetadataArgs(name=name, type=kind),
                    current_user=account,
                    current_tenant_id=tenant_id,
                )

        fragments = _read_fragments(fragments_path)
        fragment_by_id = {str(fragment["fragment_id"]): fragment for fragment in fragments}
        if len(fragment_by_id) != len(fragments):
            raise RuntimeError("Package 7 narrative fragments contain duplicate IDs")
        document_ids: dict[str, str] = {}
        for fragment in fragments:
            fragment_id = str(fragment["fragment_id"])
            name = f"PKG7 {fragment_id}"
            document = db.session.scalar(
                select(Document).where(Document.dataset_id == dataset.id, Document.name == name).limit(1)
            )
            if document is None:
                text = str(fragment["text"]).replace("\r\n", "\n").replace("\r", "\n").strip()
                upload = FileService(db.engine).upload_text(
                    text=text,
                    text_name=name,
                    user_id=account.id,
                    tenant_id=tenant_id,
                )
                config = KnowledgeConfig(
                    indexing_technique="economy",
                    data_source=DataSource(
                        info_list=InfoList(
                            data_source_type="upload_file",
                            file_info_list=FileInfo(file_ids=[upload.id]),
                        )
                    ),
                    process_rule=ProcessRule.model_validate(
                        {
                            "mode": "custom",
                            "rules": {
                                "pre_processing_rules": [
                                    {"id": "remove_extra_spaces", "enabled": False},
                                    {"id": "remove_urls_emails", "enabled": False},
                                ],
                                "segmentation": {
                                    "separator": "\u241ePACKAGE7-NEVER-SPLIT\u241e",
                                    "max_tokens": 4000,
                                    "chunk_overlap": 0,
                                },
                            },
                        }
                    ),
                    retrieval_model=RetrievalModel(
                        search_method="keyword_search",
                        reranking_enable=False,
                        reranking_model=None,
                        reranking_mode=None,
                        top_k=8,
                        score_threshold_enabled=False,
                        score_threshold=None,
                    ),
                    doc_form="text_model",
                    doc_language="Chinese",
                    name=name,
                )
                documents, _ = DocumentService.save_document_with_dataset_id(
                    dataset,
                    config,
                    account,
                    created_from="api",
                )
                document = documents[0]
            metadata_values: dict[str, str | float] = {
                "fragment_id": fragment_id,
                "tenant_id": str(fragment["tenant_id"]),
                "brand_id": str(fragment["brand_id"]),
                "status": str(fragment["status"]),
                "authorization_state": str(fragment["authorization_state"]),
                "authorization_ref": str(fragment["authorization_ref"]),
                "account_scope": _scope(fragment["applicable_content_account_ids"]),
                "organization_scope": _scope(fragment["applicable_organization_ids"]),
                "store_scope": _scope(fragment["applicable_store_ids"]),
                "valid_from": _timestamp(str(fragment["observed_at"])),
                "valid_until": _timestamp(str(fragment["valid_until"])),
                "revocation_state": "CLEAR" if fragment.get("revocation_ref") is None else "REVOKED",
                "source_ref": str(fragment["source_ref"]),
                "content_digest": str(fragment["fragment_sha256"]),
            }
            operation = DocumentMetadataOperation(
                document_id=document.id,
                metadata_list=[
                    MetadataDetail(id=fields[key].id, name=key, value=value)
                    for key, value in metadata_values.items()
                ],
                partial_update=False,
            )
            MetadataService.update_documents_metadata(
                db.session,
                dataset,
                MetadataOperationData(operation_data=[operation]),
                current_user=account,
                current_tenant_id=tenant_id,
            )
            document_ids[fragment_id] = document.id

        segment_by_document: dict[str, Any] = {}
        for _attempt in range(60):
            db.session.expire_all()
            segments = db.session.scalars(
                select(DocumentSegment)
                .where(
                    DocumentSegment.document_id.in_(document_ids.values()),
                    DocumentSegment.enabled.is_(True),
                    DocumentSegment.status == "completed",
                )
                .order_by(DocumentSegment.document_id, DocumentSegment.position)
            ).all()
            grouped: dict[str, list[Any]] = {}
            for segment in segments:
                grouped.setdefault(str(segment.document_id), []).append(segment)
            if all(len(grouped.get(document_id, [])) == 1 for document_id in document_ids.values()):
                segment_by_document = {
                    document_id: grouped[document_id][0] for document_id in document_ids.values()
                }
                break
            time.sleep(1)
        if len(segment_by_document) != len(document_ids):
            raise RuntimeError("Package 7 documents did not converge to one completed segment each")
        mapping = {
            fragment_id: {
                "document_id": document_id,
                "source_content_sha256": hashlib.sha256(
                    str(fragment_by_id[fragment_id]["text"])
                    .replace("\r\n", "\n")
                    .replace("\r", "\n")
                    .strip()
                    .encode("utf-8")
                ).hexdigest(),
                "index_content_sha256": hashlib.sha256(
                    str(segment_by_document[document_id].content)
                    .replace("\r\n", "\n")
                    .replace("\r", "\n")
                    .strip()
                    .encode("utf-8")
                ).hexdigest(),
            }
            for fragment_id, document_id in document_ids.items()
        }

        token = db.session.scalar(
            select(ApiToken).where(ApiToken.app_id == app_model.id, ApiToken.type == ApiTokenType.APP).limit(1)
        )
        if token is None:
            token = ApiToken(
                app_id=app_model.id,
                tenant_id=tenant_id,
                type=ApiTokenType.APP,
                token=ApiToken.generate_api_key("app-", 32),
            )
            db.session.add(token)
            db.session.commit()

        dataset_token = db.session.scalar(
            select(ApiToken)
            .where(ApiToken.app_id == dataset.id, ApiToken.type == ApiTokenType.DATASET)
            .limit(1)
        )
        if dataset_token is None:
            dataset_token = ApiToken(
                app_id=dataset.id,
                tenant_id=tenant_id,
                type=ApiTokenType.DATASET,
                token=ApiToken.generate_api_key("ds-", 32),
            )
            db.session.add(dataset_token)
            db.session.commit()

        state = {
            "tenant_id": tenant_id,
            "owner_account_id": str(owner_account_id),
            "owner_binding_source": owner_binding_source,
            "app_id": app_model.id,
            "dataset_id": dataset.id,
            "workflow_id": published_workflow.id,
            "app_api_token": token.token,
            "dataset_api_token": dataset_token.token,
            "fragment_document_ids": mapping,
            "fragment_document_mapping_digest": hashlib.sha256(
                _canonical_json(mapping).encode("utf-8")
            ).hexdigest(),
            "app_name": APP_NAME,
            "dataset_name": DATASET_NAME,
            "simulation_only": True,
            "production_ready": False,
            "public_webapp_enabled": False,
            "api_only": True,
        }
        state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        state_path.chmod(0o600)
        print(
            json.dumps(
                {
                    "app_id": app_model.id,
                    "dataset_id": dataset.id,
                    "document_count": len(mapping),
                    "simulation_only": True,
                },
                sort_keys=True,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

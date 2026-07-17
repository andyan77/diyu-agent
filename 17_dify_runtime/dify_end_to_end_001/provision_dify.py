#!/usr/bin/env python3
"""Idempotently create the one Package 7 Dify app and knowledge base."""

from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, TypedDict

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
    "source_id": "string",
    "content_digest": "string",
    "data_mode": "string",
    "simulation_only": "string",
    "test_fixture_only": "string",
}
DOCUMENT_NAME_PREFIX = "PKG7 "


class ReconciliationOperation(TypedDict):
    action: str
    document_id: str | None
    fragment_id: str
    name: str
    source_content_sha256: str


class DocumentReconciliation(TypedDict):
    upserts: list[ReconciliationOperation]
    delete_document_ids: list[str]


def _token(value: object) -> str:
    return f"|{value if value is not None else 'NONE'}|"


def _scope(values: list[object]) -> str:
    return "".join(sorted(_token(value) for value in values))


def _timestamp(value: str) -> float:
    normalized = f"{value[:-1]}+00:00" if value.endswith("Z") else value
    return datetime.fromisoformat(normalized).timestamp()


def _read_fragments(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _normalized_text(value: object) -> str:
    return str(value).replace("\r\n", "\n").replace("\r", "\n").strip()


def _content_sha256(value: object) -> str:
    return hashlib.sha256(_normalized_text(value).encode("utf-8")).hexdigest()


def plan_document_reconciliation(
    existing_documents: list[dict[str, Any]],
    fragments: list[dict[str, Any]],
) -> DocumentReconciliation:
    """Plan one convergent replacement of the Package 7 document namespace."""
    existing_by_name: dict[str, dict[str, Any]] = {}
    for row in existing_documents:
        name = row.get("name")
        document_id = row.get("document_id")
        if not isinstance(name, str) or not isinstance(document_id, str):
            raise RuntimeError("The existing Dify document inventory is invalid")
        if not name.startswith(DOCUMENT_NAME_PREFIX):
            continue
        if name in existing_by_name:
            raise RuntimeError("The Package 7 Dify document namespace is not unique")
        existing_by_name[name] = dict(row)

    desired_by_name: dict[str, dict[str, Any]] = {}
    for fragment in fragments:
        fragment_id = fragment.get("fragment_id")
        if not isinstance(fragment_id, str) or not fragment_id:
            raise RuntimeError("The materialized fragment ID is invalid")
        name = f"{DOCUMENT_NAME_PREFIX}{fragment_id}"
        if name in desired_by_name:
            raise RuntimeError("The materialized Dify document namespace is not unique")
        desired_by_name[name] = fragment

    upserts: list[ReconciliationOperation] = []
    for name in sorted(desired_by_name):
        fragment = desired_by_name[name]
        desired_digest = _content_sha256(fragment.get("text", ""))
        existing = existing_by_name.get(name)
        if existing is None:
            action = "CREATE"
            document_id = None
        elif existing.get("index_content_sha256") == desired_digest:
            action = "KEEP"
            document_id = existing["document_id"]
        else:
            action = "REPLACE"
            document_id = existing["document_id"]
        upserts.append(
            {
                "action": action,
                "document_id": document_id,
                "fragment_id": fragment["fragment_id"],
                "name": name,
                "source_content_sha256": desired_digest,
            }
        )

    delete_document_ids = [
        str(existing_by_name[name]["document_id"])
        for name in sorted(set(existing_by_name) - set(desired_by_name))
    ]
    return {
        "upserts": upserts,
        "delete_document_ids": delete_document_ids,
    }


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=lambda item: item.model_dump(mode="json"),
    )


def resolve_materialized_fragments(manifest_path: Path) -> tuple[Path, dict[str, Any]]:
    """Validate one Package 8 runtime projection before Dify consumes it."""

    raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise RuntimeError("The Package 8 Dify materialization manifest is invalid")
    manifest = dict(raw)
    recorded_digest = manifest.pop("materialization_digest", None)
    if (
        manifest.get("schema_version") != "v1.0"
        or manifest.get("materialization_kind") != "DIFY_NARRATIVE_IMPORT"
        or manifest.get("source_kind") != "RUNTIME_POSTGRESQL_PROJECTION"
        or manifest.get("real_dify_import_performed") is not False
        or manifest.get("second_retrieval_truth_created") is not False
        or not isinstance(recorded_digest, str)
        or hashlib.sha256(_canonical_json(manifest).encode("utf-8")).hexdigest()
        != recorded_digest
    ):
        raise RuntimeError("The Package 8 Dify materialization identity is invalid")
    readiness = manifest.get("readiness")
    if not isinstance(readiness, dict) or any(readiness.values()):
        raise RuntimeError("The Package 8 Dify materialization unlocked readiness")
    raw_document_path = manifest.get("document_file")
    if not isinstance(raw_document_path, str) or not raw_document_path:
        raise RuntimeError("The Package 8 Dify materialization document is missing")
    relative = Path(raw_document_path)
    if relative.is_absolute() or ".." in relative.parts or len(relative.parts) != 1:
        raise RuntimeError("The Package 8 Dify materialization document path escaped")
    document_path = manifest_path.parent / relative
    if not document_path.is_file():
        raise RuntimeError("The Package 8 Dify materialization document is missing")
    digest = hashlib.sha256(document_path.read_bytes()).hexdigest()
    fragments = _read_fragments(document_path)
    if (
        digest != manifest.get("document_sha256")
        or len(fragments) != manifest.get("document_count")
        or any(
            row.get("publish_allowed") is not False
            or row.get("status") != "ACTIVE"
            or row.get("authorization_state") != "GRANTED"
            or row.get("revocation_ref") is not None
            for row in fragments
        )
    ):
        raise RuntimeError("The Package 8 Dify materialization content is invalid")
    manifest["materialization_digest"] = recorded_digest
    return document_path, manifest


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
    materialization_manifest_path = Path(
        os.environ["PACKAGE8_DIFY_MATERIALIZATION_MANIFEST_PATH"]
    )
    fragments_path, materialization_manifest = resolve_materialized_fragments(
        materialization_manifest_path
    )
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
        existing_app = (
            db.session.get(App, locked_app_id)
            if isinstance(locked_app_id, str)
            else None
        )
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
                locked_owner_id
                if isinstance(locked_owner_id, str)
                else existing_app.created_by
            )
            owner_binding_source = (
                "LOCKED_PACKAGE7_STATE"
                if isinstance(locked_owner_id, str)
                else "CURRENT_PACKAGE7_APP_ONE_TIME_LOCK"
            )
            if str(existing_app.created_by) != str(owner_account_id):
                raise RuntimeError(
                    "The locked Package 7 Dify application owner drifted"
                )
        else:
            tenant_id = os.environ.get("PACKAGE7_APPROVED_DIFY_TENANT_ID")
            owner_account_id = os.environ.get("PACKAGE7_APPROVED_DIFY_OWNER_ACCOUNT_ID")
            if not tenant_id or not owner_account_id:
                raise RuntimeError(
                    "An explicit Package 7 Dify workspace and owner are required"
                )
            matching_apps = list(
                db.session.scalars(
                    select(App).where(App.tenant_id == tenant_id, App.name == APP_NAME)
                ).all()
            )
            if len(matching_apps) > 1:
                raise RuntimeError("Multiple Package 7 Dify applications exist")
            existing_app = matching_apps[0] if matching_apps else None
            if (
                existing_app is not None
                and str(existing_app.created_by) != owner_account_id
            ):
                raise RuntimeError(
                    "The approved Package 7 Dify owner does not own the existing app"
                )
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
        if len(app_name_matches) != 1 or str(app_name_matches[0].id) != str(
            app_model.id
        ):
            raise RuntimeError("The Package 7 Dify application is not unique")
        if not hasattr(app_model, "enable_site") or not hasattr(
            app_model, "enable_api"
        ):
            raise RuntimeError(
                "This Dify version cannot enforce an API-only Package 7 app"
            )
        app_model.enable_site = False
        app_model.enable_api = True
        db.session.commit()
        workflow_service = WorkflowService()
        draft_workflow = workflow_service.get_draft_workflow(
            app_model, session=db.session
        )
        if draft_workflow is None:
            raise RuntimeError("Imported Dify app has no draft workflow")
        published_workflow = None
        if app_model.workflow_id is not None:
            published_workflow = workflow_service.get_published_workflow_by_id(
                app_model,
                app_model.workflow_id,
                session=db.session,
            )
        if published_workflow is None or _workflow_payload(
            published_workflow
        ) != _workflow_payload(draft_workflow):
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
                description="Package 7 isolated authorized narrative projection; non-production.",
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
            raise RuntimeError(
                "This Dify version cannot enable the Package 7 dataset API"
            )
        dataset_name_matches = list(
            db.session.scalars(
                select(Dataset).where(
                    Dataset.tenant_id == tenant_id,
                    Dataset.name == DATASET_NAME,
                )
            ).all()
        )
        if len(dataset_name_matches) != 1 or str(dataset_name_matches[0].id) != str(
            dataset.id
        ):
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
        fragment_by_id = {
            str(fragment["fragment_id"]): fragment for fragment in fragments
        }
        if len(fragment_by_id) != len(fragments):
            raise RuntimeError("Package 7 narrative fragments contain duplicate IDs")
        package_documents = list(
            db.session.scalars(
                select(Document).where(
                    Document.dataset_id == dataset.id,
                    Document.name.like(f"{DOCUMENT_NAME_PREFIX}%"),
                )
            ).all()
        )
        package_document_ids = [document.id for document in package_documents]
        completed_segments = (
            list(
                db.session.scalars(
                    select(DocumentSegment).where(
                        DocumentSegment.document_id.in_(package_document_ids),
                        DocumentSegment.enabled.is_(True),
                        DocumentSegment.status == "completed",
                    )
                ).all()
            )
            if package_document_ids
            else []
        )
        existing_segment_groups: dict[str, list[Any]] = {}
        for segment in completed_segments:
            existing_segment_groups.setdefault(str(segment.document_id), []).append(
                segment
            )
        existing_inventory = [
            {
                "document_id": str(document.id),
                "name": str(document.name),
                "index_content_sha256": (
                    _content_sha256(
                        existing_segment_groups[str(document.id)][0].content
                    )
                    if len(existing_segment_groups.get(str(document.id), [])) == 1
                    else None
                ),
            }
            for document in package_documents
        ]
        reconciliation = plan_document_reconciliation(existing_inventory, fragments)
        package_documents_by_id = {
            str(document.id): document for document in package_documents
        }
        for stale_document_id in reconciliation["delete_document_ids"]:
            document = package_documents_by_id.get(str(stale_document_id))
            if document is None:
                raise RuntimeError(
                    "The stale Dify document disappeared during reconciliation"
                )
            DocumentService.delete_document(document)

        document_ids: dict[str, str] = {}
        for operation in reconciliation["upserts"]:
            fragment_id = str(operation["fragment_id"])
            fragment = fragment_by_id[fragment_id]
            name = str(operation["name"])
            existing_document_id = operation.get("document_id")
            document = (
                None
                if existing_document_id is None
                else package_documents_by_id.get(str(existing_document_id))
            )
            if operation["action"] != "KEEP":
                text = _normalized_text(fragment["text"])
                upload = FileService(db.engine).upload_text(
                    text=text,
                    text_name=name,
                    user_id=account.id,
                    tenant_id=tenant_id,
                )
                config = KnowledgeConfig(
                    original_document_id=(
                        None if document is None else str(document.id)
                    ),
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
                if document is None:
                    documents, _ = DocumentService.save_document_with_dataset_id(
                        dataset,
                        config,
                        account,
                        created_from="api",
                    )
                    document = documents[0]
                else:
                    document = DocumentService.update_document_with_dataset_id(
                        dataset,
                        config,
                        account,
                        created_from="api",
                    )
            if document is None:
                raise RuntimeError("The Dify reconciliation plan lost a document")
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
                "revocation_state": "CLEAR"
                if fragment.get("revocation_ref") is None
                else "REVOKED",
                "source_ref": str(fragment["source_ref"]),
                "source_id": str(fragment["source_id"]),
                "content_digest": str(fragment["fragment_sha256"]),
                "data_mode": str(fragment["data_mode"]),
                "simulation_only": str(bool(fragment["simulation_only"])).lower(),
                "test_fixture_only": str(bool(fragment["test_fixture_only"])).lower(),
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
            if all(
                len(grouped.get(document_id, [])) == 1
                for document_id in document_ids.values()
            ):
                segment_by_document = {
                    document_id: grouped[document_id][0]
                    for document_id in document_ids.values()
                }
                break
            time.sleep(1)
        if len(segment_by_document) != len(document_ids):
            raise RuntimeError(
                "Package 7 documents did not converge to one completed segment each"
            )
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
        if any(
            row["source_content_sha256"] != row["index_content_sha256"]
            for row in mapping.values()
        ):
            raise RuntimeError(
                "The Dify index content does not match runtime materialization"
            )
        managed_names = set(
            db.session.scalars(
                select(Document.name).where(
                    Document.dataset_id == dataset.id,
                    Document.name.like(f"{DOCUMENT_NAME_PREFIX}%"),
                )
            ).all()
        )
        expected_names = {
            f"{DOCUMENT_NAME_PREFIX}{fragment_id}" for fragment_id in fragment_by_id
        }
        if managed_names != expected_names:
            raise RuntimeError("The Dify document namespace did not converge")

        token = db.session.scalar(
            select(ApiToken)
            .where(ApiToken.app_id == app_model.id, ApiToken.type == ApiTokenType.APP)
            .limit(1)
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
            "materialization_digest": materialization_manifest[
                "materialization_digest"
            ],
            "simulation_only": all(
                fragment.get("simulation_only") is True for fragment in fragments
            ),
            "production_ready": False,
            "public_webapp_enabled": False,
            "api_only": True,
        }
        state_path.write_text(
            json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        state_path.chmod(0o600)
        print(
            json.dumps(
                {
                    "app_id": app_model.id,
                    "dataset_id": dataset.id,
                    "document_count": len(mapping),
                    "simulation_only": all(
                        fragment.get("simulation_only") is True
                        for fragment in fragments
                    ),
                },
                sort_keys=True,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

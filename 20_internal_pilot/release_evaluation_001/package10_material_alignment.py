#!/usr/bin/env python3
"""Scope frozen Source 08 records through the existing Package 8 import entrypoint."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from sqlalchemy import select


JsonObject = dict[str, Any]
PACKAGE_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = PACKAGE_ROOT.parents[1]
PACKAGE_7_ROOT = REPOSITORY_ROOT / "17_dify_runtime/dify_end_to_end_001"
PACKAGE_8_ROOT = REPOSITORY_ROOT / "18_deployment/hosted_operations_001"
for root in (PACKAGE_7_ROOT, PACKAGE_8_ROOT):
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

from brand_import import (  # noqa: E402
    BrandImportBundle,
    load_simulation_bundle,
    preflight_brand_bundle,
)
from operations import HostedOperations  # noqa: E402
from persistence import create_runtime_engine, create_session_factory, digest_object  # noqa: E402
from runtime_models import (  # noqa: E402
    RuntimeNarrativeFragment,
    RuntimePreciseFact,
    RuntimePrincipal,
    RuntimeSetting,
)


SOURCE_PATH = (
    REPOSITORY_ROOT
    / "13_brand_data/brand_data_import_001/source_snapshots/source-08.md"
)
TENANT_ID = "TENANT-DIYU-SIM-001"
OBSERVED_AT = "2026-07-14T00:00:00Z"
VALID_UNTIL = "2026-12-31T23:59:59Z"


@dataclass(frozen=True)
class SourceBlock:
    block_kind: str
    account_id: str
    ordinal: int
    line_start: int
    line_end: int
    text: str


ACCOUNT_CARD_IDS = (
    "ACCOUNT-DIYU-HQ-OFFICIAL",
    "ACCOUNT-DIYU-FOUNDER",
    "ACCOUNT-DIYU-PRODUCT-LEAD",
    "ACCOUNT-DIYU-RETAIL-DISPLAY",
    "ACCOUNT-DIYU-CONTENT-LEAD",
    "ACCOUNT-DIYU-HZ-BINJIANG",
    "ACCOUNT-DIYU-JS-OFFICIAL",
    "ACCOUNT-DIYU-JS-PRINCIPAL",
    "ACCOUNT-DIYU-JS-STYLING-SERVICE",
    "ACCOUNT-DIYU-SZ-PARK",
    "ACCOUNT-DIYU-WX-BINHU",
)
PERSON_ACCOUNT_IDS = (
    "ACCOUNT-DIYU-FOUNDER",
    "ACCOUNT-DIYU-PRODUCT-LEAD",
    "ACCOUNT-DIYU-RETAIL-DISPLAY",
    "ACCOUNT-DIYU-CONTENT-LEAD",
    "ACCOUNT-DIYU-JS-PRINCIPAL",
    "ACCOUNT-DIYU-JS-STYLING-SERVICE",
    "ACCOUNT-DIYU-HZ-BINJIANG",
    "ACCOUNT-DIYU-SZ-PARK",
    "ACCOUNT-DIYU-WX-BINHU",
)
HQ_RECORD_ACCOUNT_BY_HEADING = {
    "商品研发负责人：五条": "ACCOUNT-DIYU-PRODUCT-LEAD",
    "零售运营与陈列负责人：五条": "ACCOUNT-DIYU-RETAIL-DISPLAY",
    "内容负责人：五条": "ACCOUNT-DIYU-CONTENT-LEAD",
}
STORE_ACCOUNT_BY_HEADING = {
    "杭州滨江直营店：十条": "ACCOUNT-DIYU-HZ-BINJIANG",
    "苏州园区加盟店：十条": "ACCOUNT-DIYU-SZ-PARK",
    "无锡滨湖加盟店：十条": "ACCOUNT-DIYU-WX-BINHU",
}


def canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def section_bounds(lines: list[str], start: str, end: str) -> tuple[int, int]:
    start_index = next(index for index, line in enumerate(lines) if line.strip() == start)
    end_index = next(
        index
        for index, line in enumerate(lines[start_index + 1 :], start_index + 1)
        if line.strip() == end
    )
    return start_index + 1, end_index


def numbered_blocks(
    lines: list[str],
    start: int,
    end: int,
    *,
    heading_level: int,
    block_kind: str,
    account_ids: tuple[str, ...],
) -> list[SourceBlock]:
    pattern = re.compile(rf"^{'#' * heading_level}\s+(\d+)\.")
    headings = [index for index in range(start, end) if pattern.match(lines[index])]
    if len(headings) != len(account_ids):
        raise RuntimeError(f"{block_kind} block count drifted")
    blocks: list[SourceBlock] = []
    for ordinal, (line_index, account_id) in enumerate(
        zip(headings, account_ids, strict=True), 1
    ):
        block_end = headings[ordinal] if ordinal < len(headings) else end
        text = "".join(lines[line_index:block_end]).strip()
        blocks.append(
            SourceBlock(
                block_kind=block_kind,
                account_id=account_id,
                ordinal=ordinal,
                line_start=line_index + 1,
                line_end=block_end,
                text=text,
            )
        )
    return blocks


def record_blocks(
    lines: list[str],
    start: int,
    end: int,
    *,
    block_kind: str,
    account_by_heading: dict[str, str] | None = None,
    fixed_account_id: str | None = None,
) -> list[SourceBlock]:
    active_account = fixed_account_id
    record_indexes: list[tuple[int, str]] = []
    for index in range(start, end):
        text = lines[index].strip()
        if text.startswith("## ") and account_by_heading is not None:
            active_account = account_by_heading.get(text[3:])
        if text.startswith("### 记录"):
            if active_account is None:
                raise RuntimeError(f"{block_kind} record has no account scope")
            record_indexes.append((index, active_account))
    blocks: list[SourceBlock] = []
    for ordinal, (line_index, account_id) in enumerate(record_indexes, 1):
        block_end = (
            record_indexes[ordinal][0]
            if ordinal < len(record_indexes)
            else end
        )
        while block_end > line_index and lines[block_end - 1].strip() in {"", "---"}:
            block_end -= 1
        text = "".join(lines[line_index:block_end]).strip()
        blocks.append(
            SourceBlock(
                block_kind=block_kind,
                account_id=account_id,
                ordinal=ordinal,
                line_start=line_index + 1,
                line_end=block_end,
                text=text,
            )
        )
    return blocks


def source_blocks(source_path: Path = SOURCE_PATH) -> tuple[SourceBlock, ...]:
    lines = source_path.read_text(encoding="utf-8").splitlines(keepends=True)
    account_start, account_end = section_bounds(
        lines,
        "# 三、十一个账号资料卡",
        "# 四、九名人物账号档案",
    )
    person_start, person_end = section_bounds(
        lines,
        "# 四、九名人物账号档案",
        "# 五、总部三个岗位的十五条连续工作记录",
    )
    hq_start, hq_end = section_bounds(
        lines,
        "# 五、总部三个岗位的十五条连续工作记录",
        "# 六、江苏省级代理商十五条经营记录",
    )
    region_start, region_end = section_bounds(
        lines,
        "# 六、江苏省级代理商十五条经营记录",
        "# 七、三家门店三十条连续记录",
    )
    store_start, store_end = section_bounds(
        lines,
        "# 七、三家门店三十条连续记录",
        "# 八、十五款商品在三家试运行门店的当前状态",
    )
    blocks = [
        *numbered_blocks(
            lines,
            account_start,
            account_end,
            heading_level=2,
            block_kind="ACCOUNT_CARD",
            account_ids=ACCOUNT_CARD_IDS,
        ),
        *numbered_blocks(
            lines,
            person_start,
            person_end,
            heading_level=2,
            block_kind="PERSON_PROFILE",
            account_ids=PERSON_ACCOUNT_IDS,
        ),
        *record_blocks(
            lines,
            hq_start,
            hq_end,
            block_kind="HQ_CONTINUOUS_RECORD",
            account_by_heading=HQ_RECORD_ACCOUNT_BY_HEADING,
        ),
        *record_blocks(
            lines,
            region_start,
            region_end,
            block_kind="REGION_CONTINUOUS_RECORD",
            fixed_account_id="ACCOUNT-DIYU-JS-PRINCIPAL",
        ),
        *record_blocks(
            lines,
            store_start,
            store_end,
            block_kind="STORE_CONTINUOUS_RECORD",
            account_by_heading=STORE_ACCOUNT_BY_HEADING,
        ),
    ]
    expected = {
        "ACCOUNT_CARD": 11,
        "PERSON_PROFILE": 9,
        "HQ_CONTINUOUS_RECORD": 15,
        "REGION_CONTINUOUS_RECORD": 15,
        "STORE_CONTINUOUS_RECORD": 30,
    }
    actual = {
        kind: sum(block.block_kind == kind for block in blocks) for kind in expected
    }
    if actual != expected:
        raise RuntimeError(f"Source 08 extraction drifted: {actual}")
    return tuple(blocks)


def _payloads(session: Any, model: Any, tenant_id: str) -> tuple[JsonObject, ...]:
    rows = session.scalars(select(model).where(model.tenant_id == tenant_id)).all()
    return tuple(copy.deepcopy(row.payload) for row in rows)


def _setting(session: Any, key: str) -> JsonObject:
    row = session.get(RuntimeSetting, key)
    if row is None or not isinstance(row.payload, dict):
        raise RuntimeError(f"Required runtime setting is missing: {key}")
    return copy.deepcopy(row.payload)


def authorization_for_account(identity: JsonObject, account_id: str) -> str:
    candidates = [
        row
        for row in identity["authorization_grants"]
        if row.get("status") == "GRANTED"
        and row.get("disclosure_scope") == "CONTENT_ACCOUNT_ONLY"
        and account_id in row.get("permitted_content_account_ids", [])
    ]
    if not candidates:
        raise RuntimeError(f"No scoped disclosure grant for {account_id}")
    return str(
        sorted(candidates, key=lambda row: str(row["authorization_id"]))[0][
            "authorization_id"
        ]
    )


def fragment_from_block(
    block: SourceBlock,
    *,
    identity: JsonObject,
    source_sha256: str,
) -> JsonObject:
    account = next(
        row
        for row in identity["content_accounts"]
        if row["account_id"] == block.account_id
    )
    source_ref = f"snapshot://SOURCE-08/L{block.line_start}-L{block.line_end}"
    fragment_id = f"PKG10-SOURCE08-{block.block_kind}-{block.ordinal:03d}"
    fragment_sha256 = hashlib.sha256(block.text.encode("utf-8")).hexdigest()
    return {
        "applicable_content_account_ids": [block.account_id],
        "applicable_organization_ids": [account["organization_id"]],
        "applicable_store_ids": [account.get("store_id")],
        "authorization_ref": authorization_for_account(identity, block.account_id),
        "authorization_state": "GRANTED",
        "brand_id": identity["tenant"]["brand_id"],
        "data_version_digest": digest_object(
            [source_sha256, source_ref, block.account_id, fragment_sha256]
        ),
        "derivation_review_state": "PACKAGE10_SOURCE08_SCOPE_CLOSED",
        "disclosure_scope": "CONTENT_ACCOUNT_ONLY",
        "fragment_id": fragment_id,
        "fragment_sha256": fragment_sha256,
        "observed_at": OBSERVED_AT,
        "package6_adapter_eligible": True,
        "publish_allowed": False,
        "revocation_ref": None,
        "runtime_consumable": False,
        "simulation_only": True,
        "source_id": "SOURCE-08",
        "source_organization_id": account["organization_id"],
        "source_position": {
            "line_start": block.line_start,
            "line_end": block.line_end,
        },
        "source_ref": source_ref,
        "source_sha256": source_sha256,
        "source_store_id": account.get("store_id"),
        "source_time_precision": "SIMULATED_SEQUENCE_SOURCE_CAPTURED_AT_DAY_START",
        "status": "ACTIVE",
        "tenant_id": identity["tenant"]["tenant_id"],
        "text": block.text,
        "unit_id": fragment_id.replace("PKG10-SOURCE08-", "SOURCE08-"),
        "valid_until": VALID_UNTIL,
    }


def build_aligned_bundle(database_url: str) -> tuple[BrandImportBundle, JsonObject]:
    engine = create_runtime_engine(database_url)
    sessions = create_session_factory(engine)
    source_sha256 = hashlib.sha256(SOURCE_PATH.read_bytes()).hexdigest()
    try:
        with sessions() as session:
            identity = _setting(session, f"identity_authority:{TENANT_ID}")
            for principal_projection in identity["login_principals"]:
                principal = session.get(
                    RuntimePrincipal,
                    str(principal_projection["principal_id"]),
                )
                if principal is None or principal.tenant_id != TENANT_ID:
                    raise RuntimeError("Current simulation principal is unavailable")
                principal_projection["username"] = principal.username
                principal_projection["status"] = principal.status
            grants_by_id = {
                str(row["authorization_id"]): row
                for row in identity["authorization_grants"]
            }
            for account_projection in identity["content_accounts"]:
                account_id = str(account_projection["account_id"])
                suffix = hashlib.sha256(account_id.encode("utf-8")).hexdigest()[
                    :16
                ].upper()
                authorization_ref = f"PKG7-AUTH-TASK-CONFIRM-{suffix}"
                authorization = grants_by_id.get(authorization_ref)
                if (
                    authorization is None
                    or authorization.get("status") != "GRANTED"
                    or authorization.get("authorization_kind")
                    != "REQUIREMENT_CONFIRMATION"
                    or authorization.get("permitted_content_account_ids")
                    != [account_id]
                ):
                    raise RuntimeError(
                        "Current account confirmation authorization is unavailable"
                    )
                account_projection["runtime_confirmation_authorization_ref"] = (
                    authorization_ref
                )
            profile = _setting(
                session,
                f"brand_expression_profile:{identity['tenant']['brand_id']}",
            )
            current_fragments = list(
                _payloads(session, RuntimeNarrativeFragment, TENANT_ID)
            )
            current_facts = _payloads(session, RuntimePreciseFact, TENANT_ID)
            source_manifest = copy.deepcopy(
                load_simulation_bundle(REPOSITORY_ROOT).source_manifest
            )
        existing_ids = {str(row["fragment_id"]) for row in current_fragments}
        additions = [
            fragment_from_block(
                block,
                identity=identity,
                source_sha256=source_sha256,
            )
            for block in source_blocks()
        ]
        addition_ids = {str(row["fragment_id"]) for row in additions}
        if existing_ids & addition_ids:
            current_fragments = [
                row
                for row in current_fragments
                if row["fragment_id"] not in addition_ids
            ]
        current_fragments.extend(additions)
        source_manifest.update(
            {
                "package10_source08_alignment": {
                    "path": SOURCE_PATH.relative_to(REPOSITORY_ROOT).as_posix(),
                    "sha256": source_sha256,
                    "fragment_count": len(additions),
                    "source_content_mutated": False,
                    "operational_username_bound_from_current_runtime": True,
                    "runtime_confirmation_refs_rebound_from_seed_policy": True,
                },
                "derived_source_refs": sorted(
                    {
                        *source_manifest.get("derived_source_refs", []),
                        *(str(row["source_ref"]) for row in additions),
                    }
                ),
            }
        )
        bundle = BrandImportBundle(
            identity=identity,
            narrative_fragments=tuple(
                sorted(current_fragments, key=lambda row: str(row["fragment_id"]))
            ),
            precise_facts=tuple(
                sorted(current_facts, key=lambda row: str(row["fact_id"]))
            ),
            expression_profile=profile,
            source_manifest=source_manifest,
        )
        preflight = preflight_brand_bundle(bundle)
        return bundle, {
            "preflight": preflight,
            "source_sha256": source_sha256,
            "aligned_fragment_count": len(additions),
            "total_fragment_count": len(bundle.narrative_fragments),
            "account_count": len(identity["content_accounts"]),
        }
    finally:
        engine.dispose()


def apply_alignment(database_url: str, namespace: str, password: str) -> JsonObject:
    bundle, report = build_aligned_bundle(database_url)
    if report["preflight"]["state"] != "CAN_IMPORT":
        raise RuntimeError(f"Alignment preflight failed: {report['preflight']}")
    engine = create_runtime_engine(database_url)
    sessions = create_session_factory(engine)
    try:
        result = HostedOperations(engine, sessions, namespace).import_brand(
            bundle,
            principal_password=password,
            reason="PACKAGE10_SOURCE08_SCOPE_ALIGNMENT",
        )
    finally:
        engine.dispose()
    return {**report, "import_result": result}


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--database-url", default=os.environ.get("DIYU_PKG9_ADMIN_DATABASE_URL")
    )
    parser.add_argument("--namespace", default="diyu-pkg8-package10")
    parser.add_argument("--apply", action="store_true")
    arguments = parser.parse_args(argv)
    if not arguments.database_url:
        raise SystemExit("DIYU_PKG9_ADMIN_DATABASE_URL is required")
    if arguments.apply:
        password = os.environ.get("DIYU_SIM_PASSWORD")
        if not password:
            raise SystemExit(
                "DIYU_SIM_PASSWORD is required for the existing import entrypoint"
            )
        result = apply_alignment(arguments.database_url, arguments.namespace, password)
    else:
        _, result = build_aligned_bundle(arguments.database_url)
    print(canonical_json(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

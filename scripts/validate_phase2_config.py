#!/usr/bin/env python3
"""Validate Phase 2 runtime configuration (fail-closed).

Validates ONLY primary + fallback_chain providers. Unused providers are ignored.
Checks that required env_key entries exist in .env (not that they have values --
actual secrets are in vault).

Usage:
    uv run python scripts/validate_phase2_config.py
    uv run python scripts/validate_phase2_config.py --json

Exit codes:
    0 - Configuration valid
    1 - Configuration invalid
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

CONFIG_PATH = Path("delivery/phase2-runtime-config.yaml")
ENV_FILE = Path(".env")


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {"_error": f"{CONFIG_PATH} not found"}
    with CONFIG_PATH.open() as f:
        return yaml.safe_load(f)


def load_env_keys() -> set[str]:
    """Parse .env file and return set of defined key names."""
    keys: set[str] = set()
    if not ENV_FILE.exists():
        return keys
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key = line.split("=", 1)[0].strip()
            keys.add(key)
    return keys


def validate(config: dict) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []

    if "_error" in config:
        errors.append({"section": "file", "message": config["_error"]})
        return errors

    # --- LLM ---
    llm = config.get("llm", {})
    primary = llm.get("primary")
    fallback_chain = llm.get("fallback_chain", [])
    providers = llm.get("providers", {})

    if not primary:
        errors.append({"section": "llm", "message": "primary provider not set"})

    # Validate only primary + fallback_chain
    active_providers = [primary, *fallback_chain] if primary else fallback_chain
    for p in active_providers:
        if p not in providers:
            errors.append(
                {
                    "section": "llm",
                    "message": f"active provider '{p}' not defined in providers",
                }
            )
            continue
        prov = providers[p]
        if "env_key" not in prov:
            errors.append(
                {
                    "section": "llm",
                    "message": f"provider '{p}' missing env_key",
                }
            )
        if not prov.get("models"):
            errors.append(
                {
                    "section": "llm",
                    "message": f"provider '{p}' has no models defined",
                }
            )

    # --- Billing ---
    billing = config.get("billing", {})
    if not billing.get("enforcement", {}).get("pre_check"):
        errors.append(
            {
                "section": "billing",
                "message": "pre_check enforcement must be enabled",
            }
        )
    if not billing.get("enforcement", {}).get("post_settle"):
        errors.append(
            {
                "section": "billing",
                "message": "post_settle enforcement must be enabled",
            }
        )

    # --- Realtime ---
    realtime = config.get("realtime", {})
    if realtime.get("primary") not in ("websocket", "sse"):
        errors.append(
            {
                "section": "realtime",
                "message": "primary must be 'websocket' or 'sse'",
            }
        )

    # --- Storage ---
    storage = config.get("storage", {})
    upload = storage.get("file_upload", {})
    if upload.get("flow") != "3-step":
        errors.append(
            {
                "section": "storage",
                "message": "file_upload flow must be '3-step'",
            }
        )

    # --- Embedding ---
    embedding = config.get("embedding", {})
    if embedding.get("ddl_dimension") != 1024:
        errors.append(
            {
                "section": "embedding",
                "message": "ddl_dimension must be 1024 (DDL fixed)",
            }
        )

    # --- Database ---
    db = config.get("database", {})
    if not db.get("primary", {}).get("env_key"):
        errors.append(
            {
                "section": "database",
                "message": "primary database env_key not set",
            }
        )

    # --- Redis ---
    redis_cfg = config.get("redis", {})
    if not redis_cfg.get("env_key"):
        errors.append(
            {
                "section": "redis",
                "message": "redis env_key not set",
            }
        )
    test_cfg = redis_cfg.get("test", {})
    if test_cfg.get("db") != 15:
        errors.append(
            {
                "section": "redis",
                "message": "test db must be 15",
            }
        )

    return errors


def main() -> None:
    json_output = "--json" in sys.argv

    config = load_config()
    errors = validate(config)

    if json_output:
        print(
            json.dumps(
                {
                    "tool": "validate_phase2_config",
                    "config_file": str(CONFIG_PATH),
                    "errors": errors,
                    "count": len(errors),
                    "status": "fail" if errors else "pass",
                },
                indent=2,
            )
        )
    else:
        if errors:
            print(f"FAIL: {len(errors)} configuration error(s):\n")
            for e in errors:
                print(f"  [{e['section']}] {e['message']}")
        else:
            print(f"PASS: {CONFIG_PATH} validated (primary + fallback_chain)")

    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()

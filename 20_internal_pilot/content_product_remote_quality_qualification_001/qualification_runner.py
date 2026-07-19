#!/usr/bin/env python3
"""Run the frozen Q20 qualification only through the Diyu HTTPS webpage."""
from __future__ import annotations
import argparse
import hashlib
import http.cookiejar
import json
import logging
import os
import re
import stat
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Literal, cast
LOGGER = logging.getLogger("diyu.q20.qualification_runner")
PACKAGE_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = PACKAGE_ROOT.parents[1]
EVIDENCE_ROOT = PACKAGE_ROOT / "evidence"
DEFAULT_TASKS = PACKAGE_ROOT / "frozen_tasks.v1.jsonl"
DEFAULT_MANIFEST = PACKAGE_ROOT / "freeze_manifest.v1.json"
DEFAULT_SNAPSHOT = EVIDENCE_ROOT / "run_boundary_snapshot.v1.json"
DEFAULT_EVIDENCE_DIR = EVIDENCE_ROOT / "official_remote_run"
MAX_RESPONSE_BYTES = 4 * 1024 * 1024
MAX_CALLS = 300
MAX_COST_CNY = Decimal("5")
TASKS_PER_PROCESS = 1
BROWSER_GROUPS = frozenset(f"BROWSER-{index:02d}" for index in range(1, 6))
PORTAL_SUFFIXES = frozenset({"/login", "/logout", "/v1/portal/options", "/v1/portal/chat"})
PORTAL_OPERATIONS = frozenset({"找点灵感", "直接做内容", "把已有内容改好", "选择候选", "审核", "导出"})
PORTAL_KEYS = frozenset(
    {
        "account_display_name", "operation", "topic_label", "primary_audience", "message", "target_platform",
        "candidate_number", "content_goal", "key_takeaway", "speaker_role_name", "storyline_name", "column_name",
        "continue_previous", "localization_allowed", "duration_label", "expression_feeling", "content_format",
        "organization_level", "content_identity", "long_term_storyline", "content_direction", "business_goal",
        "expression_method", "existing_material_kinds",
    }
)
RunnerError = RuntimeError
class BudgetBoundaryError(RunnerError):
    pass
@dataclass(frozen=True, repr=False)
class Credentials:
    username: str
    password: str
@dataclass(frozen=True)
class HttpResult:
    status: int
    payload: dict[str, object]
    started_at: str
    ended_at: str
    elapsed_ms: int
@dataclass(frozen=True)
class FrozenTask:
    task_id: str
    ordinal: int
    browser_group: str
    request: dict[str, object]
    fuzzy_prelude: dict[str, object] | None
    fuzzy_confirmation: str | None
    revision_instruction: str | None
@dataclass(frozen=True)
class BoundarySnapshot:
    provider: str
    model: str
    model_digest: str
    cumulative_calls: int
    cumulative_limit: int
    task_calls_used: int
    task_cost_used: Decimal
    cost_planning_rate: Decimal
    planned_calls: int
    planned_cost: Decimal
    completed_tasks: int
    event_sequence: int
@dataclass(frozen=True)
class PortalStep:
    name: str
    request: dict[str, object]
    model_call_upper_bound: int
class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args: Any, **kwargs: Any) -> None:
        return None
class PortalPolicy:
    def __init__(self, value: str) -> None:
        parsed = urllib.parse.urlsplit(value.strip())
        if (
            parsed.scheme != "https" or parsed.hostname != "dify.diyuai.cc"
            or parsed.username is not None or parsed.password is not None
            or parsed.query or parsed.fragment or parsed.path.rstrip("/") != "/apps"
        ):
            raise RunnerError("DIYU_Q20_PORTAL_BASE_URL must be a credential-free HTTPS URL rooted at /apps")
        if parsed.port is not None:
            raise RunnerError("DIYU_Q20_PORTAL_BASE_URL must use the implicit HTTPS port")
        self.base_url = urllib.parse.urlunsplit(("https", parsed.netloc, "/apps", "", ""))
    def endpoint(self, suffix: str) -> str:
        if suffix not in PORTAL_SUFFIXES:
            raise RunnerError("requested path is not an approved Diyu webpage endpoint")
        return f"{self.base_url}{suffix}"
class PortalClient:
    def __init__(self, policy: PortalPolicy, timeout: int, cookie_path: Path | None = None) -> None:
        self._policy = policy
        self._timeout = timeout
        self._cookie_path = cookie_path
        if cookie_path is None:
            self._jar: http.cookiejar.CookieJar = http.cookiejar.CookieJar()
        else:
            jar = http.cookiejar.MozillaCookieJar(str(cookie_path))
            if cookie_path.exists():
                _validate_cookie_file(cookie_path)
                jar.load(ignore_discard=True, ignore_expires=True)
            self._jar = jar
        self._opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self._jar), NoRedirectHandler())
    def login(self, credentials: Credentials) -> dict[str, object]:
        result = self._request(
            "/login", "POST", {"username": credentials.username, "password": credentials.password}, portal_header=False
        )
        if result.status != 200 or result.payload.get("simulation_only") is not True:
            raise RunnerError(f"non-production portal login failed with HTTP {result.status}")
        return _validate_options(result.payload.get("options"))
    def options(self) -> dict[str, object] | None:
        result = self._request("/v1/portal/options", "GET", None, portal_header=False)
        if result.status == 401:
            return None
        if result.status != 200:
            raise RunnerError(f"portal options failed with HTTP {result.status}")
        return _validate_options(result.payload)
    def chat(self, payload: dict[str, object]) -> HttpResult:
        return self._request("/v1/portal/chat", "POST", payload, portal_header=True)
    def logout(self) -> None:
        result = self._request("/logout", "POST", {}, portal_header=True)
        if result.status != 200 or result.payload.get("logged_out") is not True:
            raise RunnerError("portal logout did not revoke the browser session")
    def save_cookie(self) -> str:
        if self._cookie_path is None or not isinstance(self._jar, http.cookiejar.FileCookieJar):
            raise RunnerError("persistent cookie storage is unavailable")
        _create_cookie_file(self._cookie_path)
        self._jar.save(ignore_discard=True, ignore_expires=True)
        os.chmod(self._cookie_path, 0o600)
        _validate_cookie_file(self._cookie_path)
        return _sha256(self._cookie_path.read_bytes())
    def _request(
        self, suffix: str, method: Literal["GET", "POST"], payload: dict[str, object] | None, *, portal_header: bool
    ) -> HttpResult:
        url = self._policy.endpoint(suffix)
        headers = {"Accept": "application/json", "User-Agent": "diyu-q20-qualification-runner/1"}
        data = None
        if payload is not None:
            headers["Content-Type"] = "application/json"
            data = _canonical(payload)
        if portal_header:
            headers["X-Diyu-Portal"] = "same-origin-v1"
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        started_at, started = _utc_now(), time.monotonic()
        try:
            with self._opener.open(request, timeout=self._timeout) as response:
                status, response_url, body = response.status, response.geturl(), response.read(MAX_RESPONSE_BYTES + 1)
        except urllib.error.HTTPError as exc:
            status, response_url, body = exc.code, exc.geturl(), exc.read(MAX_RESPONSE_BYTES + 1)
        except (TimeoutError, urllib.error.URLError, OSError) as exc:
            raise RunnerError(f"portal transport ended without a complete HTTP response: {type(exc).__name__}") from exc
        if response_url != url or len(body) > MAX_RESPONSE_BYTES:
            raise RunnerError("portal response escaped its endpoint or size boundary")
        try:
            value = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RunnerError("portal response was not valid UTF-8 JSON") from exc
        if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
            raise RunnerError("portal response was not a JSON object")
        return HttpResult(
            status, cast(dict[str, object], value), started_at, _utc_now(),
            round((time.monotonic() - started) * 1000),
        )
def _utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()
def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
def _json_object(path: Path) -> tuple[dict[str, object], str]:
    raw = path.read_bytes()
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RunnerError(f"invalid JSON input: {path}") from exc
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise RunnerError(f"JSON input is not an object: {path}")
    return cast(dict[str, object], value), _sha256(raw)
def _required_string(value: object, label: str, maximum: int = 4000) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise RunnerError(f"{label} must be a short non-empty string")
    return value
def _optional_string(value: object, label: str, maximum: int = 1000) -> str | None:
    if value is None:
        return None
    return _required_string(value, label, maximum)
def _integer(value: object, label: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise RunnerError(f"{label} must be an integer >= {minimum}")
    return value
def _decimal(value: object, label: str) -> Decimal:
    if isinstance(value, bool):
        raise RunnerError(f"{label} must be a decimal")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise RunnerError(f"{label} must be a decimal") from exc
    if not result.is_finite() or result < 0:
        raise RunnerError(f"{label} must be a finite non-negative decimal")
    return result
def _validate_portal_request(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != PORTAL_KEYS:
        raise RunnerError("frozen portal request fields differ from the webpage contract")
    request = cast(dict[str, object], value)
    for key in (
        "account_display_name", "message", "target_platform", "duration_label", "expression_feeling", "content_format",
    ):
        _required_string(request[key], key)
    if request["operation"] not in PORTAL_OPERATIONS:
        raise RunnerError("frozen operation is outside the approved webpage flow")
    for key in (
        "topic_label", "primary_audience", "content_goal", "key_takeaway", "speaker_role_name", "storyline_name",
        "column_name", "organization_level", "content_identity", "long_term_storyline", "content_direction",
        "business_goal", "expression_method",
    ):
        _optional_string(request[key], key)
    if not isinstance(request["continue_previous"], bool) or not isinstance(request["localization_allowed"], bool):
        raise RunnerError("portal request boolean fields are invalid")
    candidate = request["candidate_number"]
    if candidate is not None and (
        isinstance(candidate, bool) or not isinstance(candidate, int) or candidate not in range(1, 4)
    ):
        raise RunnerError("candidate_number must be null or 1..3")
    materials = request["existing_material_kinds"]
    if not isinstance(materials, list) or len(materials) > 8 or any(
        not isinstance(item, str) or not item.strip() or len(item) > 120 for item in materials
    ):
        raise RunnerError("existing_material_kinds is invalid")
    if request["content_format"] == "门店线下物料":
        raise RunnerError("the temporarily unavailable offline material format cannot enter this run")
    return request
def _load_tasks(tasks_path: Path, manifest_path: Path) -> tuple[list[FrozenTask], str]:
    manifest, _ = _json_object(manifest_path)
    expected_manifest = {
        "schema": "diyu.q20.freeze_manifest.v1", "official_task_count": 100, "content_product_count": 20,
        "tasks_per_product": 5, "official_model_calls_before_freeze": 0, "old_package10_results_consumed": False,
        "frozen_once": True,
    }
    if any(manifest.get(key) != expected for key, expected in expected_manifest.items()):
        raise RunnerError("freeze manifest invariants are invalid")
    tasks_raw = tasks_path.read_bytes()
    digest = _sha256(tasks_raw)
    if manifest.get("tasks_sha256") != digest:
        raise RunnerError("frozen task digest differs from the freeze manifest")
    tasks: list[FrozenTask] = []
    try:
        lines = tasks_raw.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise RunnerError("frozen tasks are not UTF-8") from exc
    for number, line in enumerate(lines, 1):
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise RunnerError(f"frozen task line {number} is invalid JSON") from exc
        if not isinstance(value, dict):
            raise RunnerError(f"frozen task line {number} is not an object")
        row = cast(dict[str, object], value)
        task_id = _required_string(row.get("task_id"), "task_id", 40)
        ordinal = _integer(row.get("ordinal"), "ordinal", 1)
        scenario = row.get("scenario")
        internal = row.get("internal")
        if not re.fullmatch(r"Q20-CP(?:0[1-9]|1[0-9]|20)-S[1-5]", task_id) or not isinstance(scenario, dict):
            raise RunnerError("frozen task identity or scenario is invalid")
        group = scenario.get("browser_session_group")
        if (
            group not in BROWSER_GROUPS or not isinstance(internal, dict)
            or internal.get("hidden_from_author") is not True
        ):
            raise RunnerError("frozen browser group or hidden product boundary is invalid")
        prelude_raw = row.get("fuzzy_prelude")
        tasks.append(
            FrozenTask(
                task_id, ordinal, cast(str, group), _validate_portal_request(row.get("author_visible_request")),
                None if prelude_raw is None else _validate_portal_request(prelude_raw),
                _optional_string(row.get("fuzzy_confirmation"), "fuzzy_confirmation"),
                _optional_string(row.get("revision_instruction"), "revision_instruction"),
            )
        )
        if row.get("automatic_publish") is not False or row.get("real_customer_data") is not False:
            raise RunnerError("frozen safety flags are invalid")
    if (
        len(tasks) != 100 or [task.ordinal for task in tasks] != list(range(1, 101))
        or len({task.task_id for task in tasks}) != 100 or {task.browser_group for task in tasks} != BROWSER_GROUPS
    ):
        raise RunnerError("frozen task count, order, or identifiers are invalid")
    if sum(step.model_call_upper_bound for task in tasks for step in _steps(task)) != 240:
        raise RunnerError("frozen task set no longer has the expected 240-call upper-bound plan")
    return tasks, digest
def _load_snapshot(path: Path) -> tuple[BoundarySnapshot, str]:
    value, digest = _json_object(path)
    if value.get("schema") != "diyu.q20.run_boundary_snapshot.v1" or value.get("automatic_publish") is not False:
        raise BudgetBoundaryError("run boundary snapshot invariants are invalid")
    if value.get("old_package10_results_consumed") is not False:
        raise BudgetBoundaryError("old Package 10 results cannot enter this run")
    model_digest = _required_string(value.get("model_config_sha256"), "model_config_sha256", 64)
    digests = (model_digest, _required_string(value.get("remote_runtime_sha256"), "remote_runtime_sha256", 64))
    if any(not re.fullmatch(r"[0-9a-f]{64}", digest) for digest in digests):
        raise BudgetBoundaryError("runtime or model digest is invalid")
    if (
        value.get("task_model_call_limit") != MAX_CALLS
        or _decimal(value.get("task_cost_limit_cny"), "limit") != MAX_COST_CNY
    ):
        raise BudgetBoundaryError("task call or cost authorization changed")
    return (
        BoundarySnapshot(
            _required_string(value.get("model_provider"), "model_provider", 200),
            _required_string(value.get("model_name"), "model_name", 200), model_digest,
            _integer(value.get("cumulative_model_call_upper_bound"), "cumulative calls"),
            _integer(value.get("configured_cumulative_model_call_limit"), "cumulative limit", 1),
            _integer(value.get("task_new_model_calls_used"), "task calls"),
            _decimal(value.get("task_new_cost_cny_used"), "task cost"),
            _decimal(value.get("model_call_cost_planning_rate_cny"), "planning rate"),
            _integer(value.get("planned_remaining_model_call_upper_bound"), "planned calls"),
            _decimal(value.get("planned_remaining_cost_upper_bound_cny"), "planned cost"),
            _integer(value.get("official_tasks_completed"), "completed tasks"),
            _integer(value.get("event_sequence_at_capture"), "event sequence"),
        ),
        digest,
    )
def _validate_options(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise RunnerError("portal options are not an object")
    options = cast(dict[str, object], value)
    for key in (
        "content_accounts", "topics", "platforms", "durations", "feelings", "content_formats", "storylines",
        "organization_levels", "content_identities", "long_term_storylines", "content_directions", "business_goals",
        "expression_methods", "material_kinds",
    ):
        rows = options.get(key)
        if not isinstance(rows, list) or any(not isinstance(item, str) or not item for item in rows):
            raise RunnerError(f"portal option {key} is invalid")
    for key in ("roles_by_account", "columns_by_storyline"):
        mapping = options.get(key)
        if not isinstance(mapping, dict) or any(
            not isinstance(name, str) or not isinstance(rows, list) or any(not isinstance(item, str) for item in rows)
            for name, rows in mapping.items()
        ):
            raise RunnerError(f"portal option mapping {key} is invalid")
    return options
def _validate_request_options(request: dict[str, object], options: dict[str, object]) -> None:
    pairs = (
        ("account_display_name", "content_accounts"), ("topic_label", "topics"), ("target_platform", "platforms"),
        ("duration_label", "durations"), ("expression_feeling", "feelings"), ("content_format", "content_formats"),
        ("storyline_name", "storylines"), ("organization_level", "organization_levels"),
        ("content_identity", "content_identities"), ("long_term_storyline", "long_term_storylines"),
        ("content_direction", "content_directions"), ("business_goal", "business_goals"),
        ("expression_method", "expression_methods"),
    )
    for field, option in pairs:
        if request[field] is not None and request[field] not in cast(list[object], options[option]):
            raise RunnerError(f"frozen {field} is unavailable in the authenticated webpage")
    roles = cast(dict[str, list[str]], options["roles_by_account"])
    columns = cast(dict[str, list[str]], options["columns_by_storyline"])
    if request["speaker_role_name"] is not None and request["speaker_role_name"] not in roles.get(
        cast(str, request["account_display_name"]), []
    ):
        raise RunnerError("frozen speaker role is unavailable for the selected webpage account")
    if request["column_name"] is not None and request["column_name"] not in columns.get(
        cast(str, request["storyline_name"]), []
    ):
        raise RunnerError("frozen column is unavailable for the selected storyline")
    materials = cast(list[str], options["material_kinds"])
    if any(item not in materials for item in cast(list[str], request["existing_material_kinds"])):
        raise RunnerError("frozen material kind is unavailable in the authenticated webpage")
def _with_operation(
    source: dict[str, object], operation: str, message: str, candidate: int | None
) -> dict[str, object]:
    return _validate_portal_request(
        {
            **source, "operation": operation, "message": message,
            "candidate_number": candidate, "continue_previous": False,
        }
    )
def _steps(task: FrozenTask) -> list[PortalStep]:
    request = task.request
    steps: list[PortalStep] = []
    if task.fuzzy_prelude is not None:
        steps.append(PortalStep("FUZZY_INSPIRATION", task.fuzzy_prelude, 1))
        if task.fuzzy_confirmation is None:
            raise RunnerError("fuzzy task is missing its frozen confirmation")
        request = _validate_portal_request(
            {**request, "message": f"{request['message']}\n确认：{task.fuzzy_confirmation}"}
        )
    steps.extend(
        [
            PortalStep("FIRST_CANDIDATE_SET", request, 2),
            PortalStep("SELECT_FIRST_CANDIDATE", _with_operation(request, "选择候选", "选择第1份首次候选。", 1), 0),
        ]
    )
    if task.revision_instruction is not None:
        steps.extend(
            [
                PortalStep("ONE_LOCAL_REVISION", _with_operation(request, "把已有内容改好", task.revision_instruction, 1), 1),
                PortalStep("SELECT_REVISED_CANDIDATE", _with_operation(request, "选择候选", "选择第1份修改后候选。", 1), 0),
            ]
        )
    steps.extend(
        [
            PortalStep("MANUAL_REVIEW_STATUS", _with_operation(request, "审核", "提交内部人工审核状态，不发布。", None), 0),
            PortalStep("INTERNAL_EXPORT", _with_operation(request, "导出", "导出当前内部测试稿，不发布。", None), 0),
        ]
    )
    return steps
def _atomic_write(path: Path, content: bytes) -> None:
    try:
        path.resolve().relative_to(EVIDENCE_ROOT.resolve())
    except ValueError as exc:
        raise RunnerError("runner evidence writes are restricted to this package's evidence directory") from exc
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
def _write_json(path: Path, value: object) -> None:
    _atomic_write(path, _canonical(value) + b"\n")
def _load_events(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    events: list[dict[str, object]] = []
    previous = "0" * 64
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise RunnerError(f"event ledger line {number} is invalid") from exc
        if (
            not isinstance(value, dict) or value.get("sequence") != number
            or value.get("previous_event_sha256") != previous
        ):
            raise RunnerError("event ledger order or digest chain is invalid")
        event = cast(dict[str, object], value)
        unsigned = {key: item for key, item in event.items() if key != "event_sha256"}
        if event.get("event_sha256") != _sha256(_canonical(unsigned)):
            raise RunnerError("event ledger digest chain is invalid")
        previous = cast(str, event["event_sha256"])
        events.append(event)
    return events
def _append_event(path: Path, events: list[dict[str, object]], fields: dict[str, object]) -> None:
    event: dict[str, object] = {
        "schema": "diyu.q20.official_run_event.v1", "sequence": len(events) + 1, "recorded_at": _utc_now(),
        "previous_event_sha256": cast(str, events[-1]["event_sha256"]) if events else "0" * 64, **fields,
    }
    event["event_sha256"] = _sha256(_canonical(event))
    events.append(event)
    _atomic_write(path, b"".join(_canonical(item) + b"\n" for item in events))
def _pending_event(events: list[dict[str, object]]) -> dict[str, object] | None:
    pending: dict[str, object] | None = None
    for event in events:
        kind = event.get("event_type")
        if kind == "PORTAL_REQUEST_STARTED":
            if pending is not None:
                raise RunnerError("event ledger contains overlapping portal requests")
            pending = event
        elif kind == "PORTAL_REQUEST_REPLAYED":
            if pending is None or pending.get("event_type") != "PORTAL_REQUEST_STARTED" or any(
                event.get(key) != pending.get(key)
                for key in ("task_id", "step", "request_sha256", "browser_cookie_sha256")):
                raise RunnerError("event ledger contains an unmatched portal replay")
            pending = event
        elif kind == "PORTAL_REQUEST_COMPLETED":
            if pending is None or any(
                event.get(key) != pending.get(key) for key in ("task_id", "step", "request_sha256")
            ):
                raise RunnerError("event ledger contains an unmatched portal response")
            pending = None
    return pending
def _completed_tasks(events: list[dict[str, object]]) -> list[str]:
    return [cast(str, row["task_id"]) for row in events if row.get("event_type") == "TASK_COMPLETED"]
def _completed_steps(events: list[dict[str, object]], task_id: str) -> list[str]:
    rows = [
        row for row in events
        if row.get("event_type") == "PORTAL_REQUEST_COMPLETED" and row.get("task_id") == task_id
    ]
    if any(row.get("http_status") != 200 for row in rows):
        raise RunnerError("a completed portal failure is a terminal result, not a resumable sample")
    return [cast(str, row["step"]) for row in rows]
def _remaining_calls(tasks: list[FrozenTask], events: list[dict[str, object]]) -> int:
    started = {
        (row.get("task_id"), row.get("step"))
        for row in events if row.get("event_type") == "PORTAL_REQUEST_STARTED"
    }
    return sum(
        step.model_call_upper_bound for task in tasks for step in _steps(task)
        if (task.task_id, step.name) not in started
    )
def _assert_boundary(snapshot: BoundarySnapshot, tasks: list[FrozenTask], events: list[dict[str, object]]) -> None:
    completed = _completed_tasks(events)
    remaining = _remaining_calls(tasks, events)
    if snapshot.event_sequence != len(events) or snapshot.completed_tasks != len(completed):
        raise BudgetBoundaryError("boundary snapshot does not bind the current recoverable evidence")
    if snapshot.planned_calls != remaining or snapshot.task_calls_used + remaining > MAX_CALLS:
        raise BudgetBoundaryError("the frozen remaining run does not fit the 300-call authorization")
    if snapshot.cumulative_calls + remaining > snapshot.cumulative_limit:
        raise BudgetBoundaryError("the remote cumulative model-call capacity is insufficient")
    if snapshot.planned_cost < snapshot.cost_planning_rate * remaining:
        raise BudgetBoundaryError("the boundary snapshot understates planned cost")
    if snapshot.task_cost_used + snapshot.planned_cost > MAX_COST_CNY:
        raise BudgetBoundaryError("the frozen remaining run does not fit the CNY 5 authorization")
def _cookie_directory(path: Path) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(REPOSITORY_ROOT.resolve())
    except ValueError:
        pass
    else:
        raise RunnerError("--cookie-dir must be outside the repository")
    if path.exists() and path.is_symlink():
        raise RunnerError("--cookie-dir cannot be a symlink")
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if stat.S_IMODE(path.stat().st_mode) & 0o077:
        raise RunnerError("--cookie-dir permissions must not grant group or other access")
    return path
def _create_cookie_file(path: Path) -> None:
    if path.exists():
        _validate_cookie_file(path)
        return
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(descriptor)
def _validate_cookie_file(path: Path) -> None:
    if path.is_symlink() or not path.is_file() or stat.S_IMODE(path.stat().st_mode) != 0o600:
        raise RunnerError("cookie jar must be a regular 0600 file")
def _credentials() -> Credentials:
    username = os.environ.get("DIYU_Q20_PORTAL_USERNAME", "")
    password = os.environ.get("DIYU_Q20_PORTAL_PASSWORD", "")
    if not username or len(password) < 12:
        raise RunnerError("portal credentials must be injected through DIYU_Q20_PORTAL_USERNAME/PASSWORD")
    return Credentials(username, password)
def _safe_answer_fields(answer: str, sensitive_values: tuple[str, ...]) -> tuple[dict[str, object], bool]:
    if any(value and value in answer for value in sensitive_values):
        return {"user_visible_answer_sha256": _sha256(answer.encode()), "answer_suppressed_for_credential": True}, False
    return {"user_visible_answer": answer}, True
def _replay_matches(pending: Mapping[str, object], task_id: str, step: str, digest: str, cookie_digest: str) -> bool:
    expected = (("task_id", task_id), ("step", step), ("request_sha256", digest),
                ("browser_cookie_sha256", cookie_digest))
    return pending.get("event_type") == "PORTAL_REQUEST_STARTED" and all(
        pending.get(key) == value for key, value in expected)
def _ensure_browser(client: PortalClient, pending: bool) -> tuple[dict[str, object], str]:
    options = client.options() if client._cookie_path and client._cookie_path.exists() else None
    if options is None:
        if pending:
            raise RunnerError("a pending request requires its still-valid persisted browser session")
        credentials = _credentials()
        try:
            options = client.login(credentials)
        finally:
            del credentials
    return options, client.save_cookie()
def _send_step(
    *, client: PortalClient, task: FrozenTask, step: PortalStep, snapshot: BoundarySnapshot, snapshot_digest: str,
    ledger: Path, events: list[dict[str, object]], calls_used: int, browser_digest: str,
) -> tuple[int, str]:
    request_digest = _sha256(_canonical(step.request))
    pending = _pending_event(events)
    replay = pending is not None
    if pending is not None:
        if not _replay_matches(pending, task.task_id, step.name, request_digest, browser_digest):
            raise RunnerError("pending request cannot be replayed safely")
    next_calls = calls_used + step.model_call_upper_bound
    incremental = next_calls - snapshot.task_calls_used
    if next_calls > MAX_CALLS or snapshot.cumulative_calls + incremental > snapshot.cumulative_limit:
        raise BudgetBoundaryError("the next exact portal request can exceed the call boundary")
    if snapshot.task_cost_used + snapshot.cost_planning_rate * incremental > MAX_COST_CNY:
        raise BudgetBoundaryError("the next exact portal request can exceed the cost boundary")
    credentials = _credentials()
    sensitive_values = (credentials.username, credentials.password)
    del credentials
    _append_event(
        ledger, events,
        {
            "event_type": "PORTAL_REQUEST_REPLAYED" if replay else "PORTAL_REQUEST_STARTED", "task_id": task.task_id,
            "step": step.name, "request_sha256": request_digest, "portal_endpoint": "/apps/v1/portal/chat",
            "browser_group": task.browser_group, "browser_cookie_sha256": browser_digest,
            "model_call_upper_bound": step.model_call_upper_bound, "model_provider": snapshot.provider,
            "model_name": snapshot.model, "model_config_sha256": snapshot.model_digest,
            "run_boundary_snapshot_sha256": snapshot_digest, "technical_replay": replay,
        },
    )
    try:
        result = client.chat(step.request)
    except RunnerError:
        _append_event(
            ledger, events, {"event_type": "PORTAL_TRANSPORT_INCOMPLETE", "task_id": task.task_id,
                             "step": step.name, "request_sha256": request_digest,
                             "error_type": "PORTAL_RESPONSE_INCOMPLETE"})
        raise
    answer = result.payload.get("answer")
    if not isinstance(answer, str) or not answer.strip():
        visible = result.payload.get("user_visible_text")
        answer = visible if isinstance(visible, str) else ""
    answer_fields, answer_is_safe = _safe_answer_fields(answer, sensitive_values)
    del sensitive_values
    _append_event(
        ledger, events,
        {
            "event_type": "PORTAL_REQUEST_COMPLETED", "task_id": task.task_id, "step": step.name,
            "request_sha256": request_digest, "http_status": result.status, "started_at": result.started_at,
            "ended_at": result.ended_at, "elapsed_ms": result.elapsed_ms, "browser_group": task.browser_group,
            "model_call_upper_bound": step.model_call_upper_bound, "cost_reconciliation": "REQUIRED_FROM_REMOTE_LEDGER",
            "publish_allowed": result.payload.get("publish_allowed"), "technical_replay": replay, **answer_fields,
        },
    )
    if not answer_is_safe:
        raise RunnerError("portal response contained an injected credential and was suppressed")
    if result.status != 200 or result.payload.get("simulation_only") is not True:
        raise RunnerError(f"portal step {step.name} failed with HTTP {result.status}")
    if result.payload.get("publish_allowed") is not False or not answer.strip():
        raise RunnerError("portal response violated the unpublished user-visible contract")
    return next_calls, client.save_cookie()
def _run_preflight(args: argparse.Namespace) -> int:
    policy = PortalPolicy(_base_url())
    client = PortalClient(policy, args.timeout_seconds)
    credentials = _credentials()
    logged_in = False
    try:
        login_options = client.login(credentials)
        logged_in = True
        options = client.options()
        if options is None or options != login_options:
            raise RunnerError("login and authenticated option contracts disagree")
    finally:
        del credentials
        if logged_in:
            client.logout()
    _write_json(
        args.output,
        {
            "schema": "diyu.q20.runner_preflight.v1", "captured_at": _utc_now(), "portal_base_url": policy.base_url,
            "https_only": True, "approved_root": "/apps", "model_calls_started": 0, "credentials_persisted": False,
            "cookie_persisted": False, "simulation_only": True, "automatic_publish": False,
            "content_account_count": len(cast(list[object], options["content_accounts"])),
            "topic_count": len(cast(list[object], options["topics"])), "content_formats": options["content_formats"],
        },
    )
    return 0
def _run_selftest() -> int:
    marker: dict[str, object] = {
        "task_id": "Q20-CP01-S1", "step": "FIRST_CANDIDATE_SET", "request_sha256": "a" * 64,
        "browser_cookie_sha256": "b" * 64,
    }
    started = {**marker, "event_type": "PORTAL_REQUEST_STARTED"}
    replayed = {**marker, "event_type": "PORTAL_REQUEST_REPLAYED"}
    completed = {**marker, "event_type": "PORTAL_REQUEST_COMPLETED"}
    if _pending_event([started, replayed, completed]) is not None:
        raise RunnerError("selftest: one exact replay did not close")
    try:
        _pending_event([started, replayed, replayed])
    except RunnerError:
        pass
    else:
        raise RunnerError("selftest: a second replay was accepted")
    if _replay_matches(started, cast(str, marker["task_id"]), cast(str, marker["step"]), "a" * 64, "c" * 64):
        raise RunnerError("selftest: a different browser cookie was accepted")
    safe_fields, safe = _safe_answer_fields("contains injected-password", ("injected-password",))
    if TASKS_PER_PROCESS != 1 or safe or "user_visible_answer" in safe_fields or (
        "user_visible_answer_sha256" not in safe_fields
    ):
        raise RunnerError("selftest: secret suppression or one-task pause invariant failed")
    tasks, _ = _load_tasks(DEFAULT_TASKS, DEFAULT_MANIFEST)
    blocked = BoundarySnapshot("provider", "model", "d" * 64, 208, 209, 0, Decimal("0"), Decimal("0.0187076"),
                               240, Decimal("4.489824"), 0, 0)
    try:
        _assert_boundary(blocked, tasks, [])
    except BudgetBoundaryError:
        pass
    else:
        raise RunnerError("selftest: insufficient capacity passed before credential access")
    LOGGER.info("offline runner selftest passed without network or credential access")
    return 0
def _run_official(args: argparse.Namespace) -> int:
    if not args.official:
        raise RunnerError("run mode requires the explicit --official switch")
    tasks, tasks_digest = _load_tasks(DEFAULT_TASKS, DEFAULT_MANIFEST)
    snapshot, snapshot_digest = _load_snapshot(args.boundary_snapshot)
    ledger = args.evidence_dir / "official_run_events.v1.jsonl"
    events = _load_events(ledger)
    _assert_boundary(snapshot, tasks, events)  # Must precede URL, cookie, credential and login access.
    completed = _completed_tasks(events)
    if completed != [task.task_id for task in tasks[: len(completed)]]:
        raise RunnerError("completed tasks are not an exact frozen-order prefix")
    policy = PortalPolicy(_base_url())
    cookie_dir = _cookie_directory(args.cookie_dir)
    if events:
        starts = [row for row in events if row.get("event_type") == "RUN_STARTED"]
        if len(starts) != 1:
            raise RunnerError("recoverable evidence has no unique run identity")
        run_id = cast(str, starts[0].get("run_id"))
        if not re.fullmatch(r"[0-9a-f]{20}", run_id):
            raise RunnerError("recoverable run identity is invalid")
    else:
        run_id = hashlib.sha256(os.urandom(32)).hexdigest()[:20]
        _append_event(
            ledger, events,
            {"event_type": "RUN_STARTED", "run_id": run_id, "frozen_tasks_sha256": tasks_digest},
        )
    contexts = {
        group: PortalClient(
            policy, args.timeout_seconds, cookie_dir / f"q20-{run_id}-{group}.cookies.txt"
        )
        for group in BROWSER_GROUPS
    }
    calls_used = snapshot.task_calls_used
    for task in tasks[len(completed) : len(completed) + TASKS_PER_PROCESS]:
        steps = _steps(task)
        done = _completed_steps(events, task.task_id)
        if done != [step.name for step in steps[: len(done)]]:
            raise RunnerError("completed portal steps are not an exact task-step prefix")
        pending = _pending_event(events)
        client = contexts[task.browser_group]
        options, cookie_digest = _ensure_browser(client, pending is not None)
        for step in steps:
            _validate_request_options(step.request, options)
        for step in steps[len(done) :]:
            if step.name == "SELECT_FIRST_CANDIDATE" and not any(
                row.get("event_type") == "BLIND_USER_SELECTION_RECORDED"
                and row.get("task_id") == task.task_id for row in events
            ):
                _append_event(
                    ledger, events,
                    {"event_type": "BLIND_USER_SELECTION_RECORDED", "task_id": task.task_id, "candidate_number": 1,
                     "selection_policy": "FIRST_AVAILABLE_WITHOUT_SCORE_OR_PRODUCT_ANSWER"},
                )
            calls_used, cookie_digest = _send_step(
                client=client, task=task, step=step, snapshot=snapshot, snapshot_digest=snapshot_digest,
                ledger=ledger, events=events, calls_used=calls_used, browser_digest=cookie_digest,
            )
        _append_event(
            ledger, events,
            {"event_type": "TASK_COMPLETED", "task_id": task.task_id, "task_ordinal": task.ordinal,
             "browser_group": task.browser_group, "browser_cookie_sha256": cookie_digest, "automatic_publish": False},
        )
    if len(completed) + TASKS_PER_PROCESS < len(tasks):
        _append_event(
            ledger, events, {"event_type": "RUN_PAUSED_FOR_LEDGER_REFRESH", "completed_tasks": len(completed) + 1})
        return 4
    for client in contexts.values():
        cookie_path = cast(Path, client._cookie_path)
        if cookie_path.exists() and client.options() is not None:
            client.logout()
        cookie_path.unlink(missing_ok=True)
    _append_event(
        ledger, events,
        {"event_type": "RUN_COMPLETED", "run_id": run_id, "completed_tasks": 100,
         "model_call_upper_bound": calls_used, "cost_reconciliation": "REQUIRED_FROM_REMOTE_LEDGER"},
    )
    return 0
def _base_url() -> str:
    if not (value := os.environ.get("DIYU_Q20_PORTAL_BASE_URL", "")):
        raise RunnerError("DIYU_Q20_PORTAL_BASE_URL is required")
    return value
def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout-seconds", type=int, default=180, choices=range(10, 601))
    modes = parser.add_subparsers(dest="mode", required=True)
    modes.add_parser("selftest", help="run offline boundary and recovery checks")
    preflight = modes.add_parser("preflight", help="read portal options without a model call")
    preflight.add_argument("--output", type=Path, required=True)
    run = modes.add_parser("run", help="run the exact frozen set through the portal")
    run.add_argument("--official", action="store_true")
    run.add_argument("--boundary-snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    run.add_argument("--evidence-dir", type=Path, default=DEFAULT_EVIDENCE_DIR)
    run.add_argument("--cookie-dir", type=Path, required=True)
    return parser
def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    args = _parser().parse_args()
    try:
        if args.mode == "selftest":
            return _run_selftest()
        return _run_preflight(args) if args.mode == "preflight" else _run_official(args)
    except BudgetBoundaryError as exc:
        LOGGER.error("official run refused at the authorized budget boundary: %s", exc)
        return 3
    except (RunnerError, OSError, ValueError) as exc:
        LOGGER.error("qualification runner stopped safely: %s", exc)
        return 2
if __name__ == "__main__":
    raise SystemExit(main())

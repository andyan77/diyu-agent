"""外部语义评审的窄适配器、日预算锁和可重放调用回执。"""

from __future__ import annotations

import json
import math
import os
import time
import urllib.error
import urllib.request
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping

from .canonical import digest_json
from .formulaic import AXES, verdict_from_axes


class ExternalJudgeError(RuntimeError):
    pass


class DailyBudgetExceeded(ExternalJudgeError):
    pass


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _closed(value: dict[str, Any], digest_field: str) -> dict[str, Any]:
    result = dict(value)
    result[digest_field] = ""
    unsigned = dict(result)
    unsigned.pop(digest_field)
    result[digest_field] = digest_json(unsigned)
    return result


def load_env_value(path: Path, key: str) -> str:
    """读取本地 env 文件；不修改进程环境，也不返回任何诊断副本。"""
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        if name.strip() == key and value.strip():
            return value.strip()
    raise ExternalJudgeError(f"missing local credential: {key}")


def validate_provider_rate_card(value: Mapping[str, Any]) -> list[str]:
    required = {
        "schema_version", "provider", "base_url", "model_revision",
        "captured_at", "currency", "input_cache_hit_per_million",
        "input_cache_miss_per_million", "output_per_million",
        "cny_per_usd_budget_conversion",
        "max_output_tokens_per_call", "source_url", "rate_card_digest",
    }
    errors: list[str] = []
    if set(value) != required:
        errors.append("provider_rate_card_field_set")
    if (value.get("schema_version") != "eval-spine-external-llm-rate-card-v1"
            or value.get("provider") != "DEEPSEEK"
            or value.get("base_url") != "https://api.deepseek.com"
            or value.get("currency") != "USD"):
        errors.append("provider_rate_card_fixed_fields")
    for field in ("model_revision", "captured_at", "source_url"):
        if not isinstance(value.get(field), str) or not value[field].strip():
            errors.append(f"provider_rate_card_{field}")
    for field in ("input_cache_hit_per_million",
                  "input_cache_miss_per_million", "output_per_million",
                  "cny_per_usd_budget_conversion"):
        number = value.get(field)
        if (not isinstance(number, (int, float)) or isinstance(number, bool)
                or not math.isfinite(float(number)) or float(number) <= 0):
            errors.append(f"provider_rate_card_{field}")
    maximum = value.get("max_output_tokens_per_call")
    if not isinstance(maximum, int) or isinstance(maximum, bool) or maximum <= 0:
        errors.append("provider_rate_card_max_output_tokens")
    unsigned = dict(value)
    supplied = unsigned.pop("rate_card_digest", None)
    if supplied != digest_json(unsigned):
        errors.append("provider_rate_card_digest")
    return sorted(errors)


def load_provider_rate_card(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_provider_rate_card(value)
    if errors:
        raise ExternalJudgeError("invalid provider rate card: " + ",".join(errors))
    return value


def validate_external_budget(value: Mapping[str, Any], *,
                             rate_card_digest: str) -> list[str]:
    required = {
        "schema_version", "contract_id", "approval_status", "approved_by",
        "approved_at", "currency", "daily_hard_ceiling_cny", "reset_timezone",
        "call_count_limit", "allowed_scope", "prohibited_scope",
        "rate_card_digest", "budget_digest",
    }
    errors: list[str] = []
    if set(value) != required:
        errors.append("external_budget_field_set")
    if (value.get("schema_version") != "eval-spine-external-llm-budget-v1"
            or value.get("contract_id") != "EAS-DEEPSEEK-DAILY-BUDGET-V1"
            or value.get("approval_status") != "APPROVED"
            or value.get("currency") != "CNY"
            or value.get("reset_timezone") != "UTC"
            or value.get("call_count_limit") is not None
            or value.get("rate_card_digest") != rate_card_digest):
        errors.append("external_budget_fixed_fields")
    for field in ("approved_by", "approved_at"):
        if not isinstance(value.get(field), str) or not value[field].strip():
            errors.append(f"external_budget_{field}")
    ceiling = value.get("daily_hard_ceiling_cny")
    if (not isinstance(ceiling, (int, float)) or isinstance(ceiling, bool)
            or not math.isfinite(float(ceiling)) or float(ceiling) != 30.0):
        errors.append("external_budget_daily_hard_ceiling")
    for field in ("allowed_scope", "prohibited_scope"):
        rows = value.get(field)
        if (not isinstance(rows, list) or not rows
                or any(not isinstance(row, str) or not row for row in rows)
                or len(rows) != len(set(rows))):
            errors.append(f"external_budget_{field}")
    unsigned = dict(value)
    supplied = unsigned.pop("budget_digest", None)
    if supplied != digest_json(unsigned):
        errors.append("external_budget_digest")
    return sorted(errors)


def load_external_budget(path: Path, *, rate_card_digest: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_external_budget(value, rate_card_digest=rate_card_digest)
    if errors:
        raise ExternalJudgeError("invalid external budget: " + ",".join(errors))
    return value


class DailySpendLedger:
    """用追加日志和进程锁预占最坏成本，跨进程执行每日硬上限。"""

    def __init__(self, path: Path, *, daily_budget_cny: float) -> None:
        self.path = path
        self.daily_budget_cny = float(daily_budget_cny)
        if not math.isfinite(self.daily_budget_cny) or self.daily_budget_cny <= 0:
            raise ValueError("daily_budget_cny must be positive")

    @contextmanager
    def _locked(self) -> Iterator[Any]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle = self.path.open("a+", encoding="utf-8")
        try:
            try:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            except ImportError as exc:  # pragma: no cover - Windows fallback must fail closed
                raise ExternalJudgeError("process-safe spend lock unavailable") from exc
            handle.seek(0)
            yield handle
        finally:
            try:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            except ImportError:
                pass
            handle.close()

    @staticmethod
    def _records(handle: Any) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for index, line in enumerate(handle.read().splitlines()):
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ExternalJudgeError(
                    f"spend ledger corruption at line {index + 1}") from exc
            if not isinstance(value, dict):
                raise ExternalJudgeError(
                    f"spend ledger non-object at line {index + 1}")
            if set(value) != {
                    "schema_version", "record_type", "reservation_id", "utc_day",
                    "recorded_at", "request_digest", "reserved_cost_cny",
                    "actual_cost_cny", "provider_call_id", "record_digest"}:
                raise ExternalJudgeError(
                    f"spend ledger field set mismatch at line {index + 1}")
            unsigned = dict(value)
            supplied = unsigned.pop("record_digest", None)
            if (value.get("schema_version") != "eval-spine-spend-ledger-record-v1"
                    or supplied != digest_json(unsigned)):
                raise ExternalJudgeError(
                    f"spend ledger digest mismatch at line {index + 1}")
            rows.append(value)
        return rows

    @staticmethod
    def _committed(rows: list[dict[str, Any]], day: str) -> float:
        reservations: dict[str, float] = {}
        settled: dict[str, float] = {}
        for row in rows:
            if row.get("utc_day") != day:
                continue
            reservation_id = str(row.get("reservation_id", ""))
            if row.get("record_type") == "RESERVATION":
                reservations[reservation_id] = float(row.get("reserved_cost_cny", 0))
            elif row.get("record_type") == "SETTLEMENT":
                settled[reservation_id] = float(row.get("actual_cost_cny", 0))
        return sum(settled.values()) + sum(
            cost for key, cost in reservations.items() if key not in settled)

    def reserve(self, *, request_digest: str, reserved_cost_cny: float,
                now: datetime | None = None) -> str:
        timestamp = now or _utc_now()
        day = timestamp.date().isoformat()
        if (not math.isfinite(float(reserved_cost_cny))
                or float(reserved_cost_cny) <= 0):
            raise ValueError("reserved_cost_cny must be positive")
        with self._locked() as handle:
            committed = self._committed(self._records(handle), day)
            if committed + float(reserved_cost_cny) > self.daily_budget_cny:
                raise DailyBudgetExceeded("external judge daily CNY ceiling reached")
            reservation_id = str(uuid.uuid4())
            record = _closed({
                "schema_version": "eval-spine-spend-ledger-record-v1",
                "record_type": "RESERVATION", "reservation_id": reservation_id,
                "utc_day": day, "recorded_at": timestamp.isoformat(),
                "request_digest": request_digest,
                "reserved_cost_cny": round(float(reserved_cost_cny), 12),
                "actual_cost_cny": None, "provider_call_id": None,
            }, "record_digest")
            handle.seek(0, os.SEEK_END)
            handle.write(json.dumps(record, ensure_ascii=False,
                                    sort_keys=True, separators=(",", ":")) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
            return reservation_id

    def settle(self, *, reservation_id: str, request_digest: str,
               actual_cost_cny: float, provider_call_id: str,
               now: datetime | None = None) -> None:
        timestamp = now or _utc_now()
        with self._locked() as handle:
            rows = self._records(handle)
            reservation = next((row for row in rows
                                if row.get("record_type") == "RESERVATION"
                                and row.get("reservation_id") == reservation_id), None)
            if reservation is None or reservation.get("request_digest") != request_digest:
                raise ExternalJudgeError("unknown or mismatched spend reservation")
            day = str(reservation["utc_day"])
            if any(row.get("record_type") == "SETTLEMENT"
                   and row.get("reservation_id") == reservation_id for row in rows):
                raise ExternalJudgeError("spend reservation already settled")
            reserved = float(reservation["reserved_cost_cny"])
            if (not math.isfinite(float(actual_cost_cny)) or actual_cost_cny < 0
                    or actual_cost_cny > reserved + 1e-9):
                raise ExternalJudgeError("actual external cost exceeds reservation")
            record = _closed({
                "schema_version": "eval-spine-spend-ledger-record-v1",
                "record_type": "SETTLEMENT", "reservation_id": reservation_id,
                "utc_day": day, "recorded_at": timestamp.isoformat(),
                "request_digest": request_digest,
                "reserved_cost_cny": reserved,
                "actual_cost_cny": round(float(actual_cost_cny), 12),
                "provider_call_id": provider_call_id,
            }, "record_digest")
            handle.seek(0, os.SEEK_END)
            handle.write(json.dumps(record, ensure_ascii=False,
                                    sort_keys=True, separators=(",", ":")) + "\n")
            handle.flush()
            os.fsync(handle.fileno())


Transport = Callable[[str, dict[str, str], dict[str, Any], float], dict[str, Any]]


def _urllib_transport(url: str, headers: dict[str, str], payload: dict[str, Any],
                      timeout_seconds: float) -> dict[str, Any]:
    request = urllib.request.Request(
        url, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError,
            json.JSONDecodeError) as exc:
        raise ExternalJudgeError(f"external judge transport failed: {type(exc).__name__}") from exc


def _estimate_cost_usd(usage: Mapping[str, Any], rate_card: Mapping[str, Any]) -> float:
    prompt = int(usage.get("prompt_tokens", 0))
    if "prompt_cache_hit_tokens" in usage:
        cached = int(usage.get("prompt_cache_hit_tokens", 0))
        cache_miss = int(usage.get("prompt_cache_miss_tokens", 0))
        if cached + cache_miss != prompt:
            raise ExternalJudgeError("provider cache-token usage does not sum to prompt")
    else:
        details = usage.get("prompt_tokens_details", {})
        cached = (int(details.get("cached_tokens", 0))
                  if isinstance(details, Mapping) else 0)
    cached = min(max(cached, 0), prompt)
    completion = int(usage.get("completion_tokens", 0))
    if prompt < 0 or completion < 0:
        raise ExternalJudgeError("provider returned negative token usage")
    return ((cached * float(rate_card["input_cache_hit_per_million"])
             + (prompt - cached) * float(rate_card["input_cache_miss_per_million"])
             + completion * float(rate_card["output_per_million"])) / 1_000_000)


def validate_formulaic_response(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {
            "axes", "necessary_grammar_exception_id", "evidence_notes"}:
        raise ExternalJudgeError("formulaic judge response field set mismatch")
    axes = value.get("axes")
    if not isinstance(axes, dict) or set(axes) != set(AXES):
        raise ExternalJudgeError("formulaic judge axes field set mismatch")
    exception_id = value.get("necessary_grammar_exception_id")
    if exception_id is not None and (
            not isinstance(exception_id, str) or not exception_id.strip()):
        raise ExternalJudgeError("invalid necessary grammar exception id")
    notes = value.get("evidence_notes")
    if (not isinstance(notes, list) or not notes
            or any(not isinstance(note, str) or not note.strip() for note in notes)):
        raise ExternalJudgeError("formulaic judge evidence notes required")
    verdict = verdict_from_axes(axes, exception_id)
    return {"axes": axes, "necessary_grammar_exception_id": exception_id,
            "evidence_notes": notes, "derived_verdict": verdict}


class DeepSeekFormulaicJudge:
    def __init__(self, *, api_key: str, rate_card: Mapping[str, Any],
                 external_budget: Mapping[str, Any], ledger: DailySpendLedger,
                 transport: Transport = _urllib_transport,
                 timeout_seconds: float = 60.0) -> None:
        errors = validate_provider_rate_card(rate_card)
        if errors:
            raise ExternalJudgeError("invalid provider rate card: " + ",".join(errors))
        if not api_key:
            raise ExternalJudgeError("missing DeepSeek API credential")
        budget_errors = validate_external_budget(
            external_budget, rate_card_digest=str(rate_card["rate_card_digest"]))
        if (budget_errors or ledger.daily_budget_cny
                != float(external_budget.get("daily_hard_ceiling_cny", -1))):
            raise ExternalJudgeError(
                "invalid external budget binding: " + ",".join(budget_errors))
        self._api_key = api_key
        self.rate_card = dict(rate_card)
        self.external_budget = dict(external_budget)
        self.ledger = ledger
        self.transport = transport
        self.timeout_seconds = timeout_seconds

    def judge(self, *, left_id: str, left_text: str, right_id: str,
              right_text: str, family_id: str, reviewer_identity: str,
              prompt_revision: str, max_output_tokens: int = 800) -> dict[str, Any]:
        if (not all(isinstance(value, str) and value.strip() for value in
                    (left_id, left_text, right_id, right_text, family_id,
                     reviewer_identity, prompt_revision))
                or left_id == right_id):
            raise ValueError("formulaic judge inputs must be non-empty and distinct")
        maximum = int(self.rate_card["max_output_tokens_per_call"])
        if not isinstance(max_output_tokens, int) or not 1 <= max_output_tokens <= maximum:
            raise ValueError("max_output_tokens outside frozen limit")
        rubric = (
            "你是独立的套路构念评审。只比较两条文本的修辞动作，不按字面相似度下结论。"
            "逐轴输出 SAME/DIFFERENT/UNCLEAR/NECESSARY_GRAMMAR；transformation_depth "
            "只能输出 SURFACE_ONLY/STRUCTURAL_CHANGE/UNCLEAR/NECESSARY_GRAMMAR。"
            "本次未提供必要语法例外注册表，所以六轴都不得输出 NECESSARY_GRAMMAR，"
            "necessary_grammar_exception_id 必须为 null。"
            "返回且只返回 JSON object，字段为 axes、necessary_grammar_exception_id、"
            "evidence_notes。axes 必须且只能包含 argument_spine、evidence_progression、"
            "limitation_function、viewpoint_anchor、closing_function、"
            "transformation_depth 六个键；不要把六轴放到顶层。evidence_notes 至少一条、"
            "只写可核对的简短理由。")
        payload = {
            "model": self.rate_card["model_revision"],
            "messages": [
                {"role": "system", "content": rubric},
                {"role": "user", "content": json.dumps({
                    "family_id": family_id,
                    "left": {"id": left_id, "text": left_text},
                    "right": {"id": right_id, "text": right_text},
                    "prompt_revision": prompt_revision,
                }, ensure_ascii=False, sort_keys=True)},
            ],
            "thinking": {"type": "disabled"},
            "response_format": {"type": "json_object"},
            "max_tokens": max_output_tokens, "stream": False,
        }
        request_view = {"provider": "DEEPSEEK", "payload": payload,
                        "reviewer_identity": reviewer_identity}
        request_digest = digest_json(request_view)
        input_token_upper_bound = 2 * len(json.dumps(
            payload["messages"], ensure_ascii=False).encode("utf-8"))
        reserved_usd = (
            input_token_upper_bound
            * float(self.rate_card["input_cache_miss_per_million"])
            + max_output_tokens * float(self.rate_card["output_per_million"])) / 1_000_000
        reserved_cny = reserved_usd * float(
            self.rate_card["cny_per_usd_budget_conversion"])
        reservation_id = self.ledger.reserve(
            request_digest=request_digest,
            reserved_cost_cny=max(reserved_cny, 1e-12))
        started = time.monotonic()
        response = self.transport(
            self.rate_card["base_url"].rstrip("/") + "/chat/completions",
            {"Content-Type": "application/json",
             "Authorization": "Bearer " + self._api_key},
            payload, self.timeout_seconds)
        elapsed = time.monotonic() - started
        try:
            provider_call_id = str(response["id"])
            usage = response["usage"]
            if not provider_call_id or not isinstance(usage, Mapping):
                raise ExternalJudgeError("provider identity or usage missing")
        except (KeyError, TypeError) as exc:
            raise ExternalJudgeError("provider accounting contract mismatch") from exc
        actual_usd = _estimate_cost_usd(usage, self.rate_card)
        actual_cny = actual_usd * float(
            self.rate_card["cny_per_usd_budget_conversion"])
        self.ledger.settle(
            reservation_id=reservation_id, request_digest=request_digest,
            actual_cost_cny=actual_cny, provider_call_id=provider_call_id)
        validation_errors: list[str] = []
        parsed: dict[str, Any] | None = None
        try:
            choice = response["choices"][0]
            content = choice["message"]["content"]
            if choice.get("finish_reason") != "stop":
                raise ExternalJudgeError("provider response did not finish normally")
            parsed = validate_formulaic_response(json.loads(content))
        except (KeyError, IndexError, TypeError, json.JSONDecodeError,
                ExternalJudgeError, ValueError) as exc:
            validation_errors.append(str(exc))
        receipt = {
            "schema_version": "eval-spine-external-judge-receipt-v1",
            "call_status": "VALID" if parsed is not None else "INVALID_RESPONSE",
            "validation_errors": validation_errors,
            "provider": "DEEPSEEK", "provider_call_id": provider_call_id,
            "model_revision": response.get("model", self.rate_card["model_revision"]),
            "reviewer_identity": reviewer_identity,
            "prompt_revision": prompt_revision,
            "prompt_digest": digest_json(payload["messages"]),
            "request_digest": request_digest,
            "response_digest": digest_json(response),
            "rate_card_digest": self.rate_card["rate_card_digest"],
            "budget_digest": self.external_budget["budget_digest"],
            "reservation_id": reservation_id,
            "usage": dict(usage), "cost_usd": round(actual_usd, 12),
            "cost_cny_budget_basis": round(actual_cny, 12),
            "wall_clock_seconds": round(elapsed, 6),
            "formulaic_result": parsed, "receipt_digest": "",
        }
        return _closed(receipt, "receipt_digest")


__all__ = [
    "DailyBudgetExceeded", "DailySpendLedger", "DeepSeekFormulaicJudge",
    "ExternalJudgeError", "load_env_value", "load_external_budget",
    "load_provider_rate_card", "validate_external_budget",
    "validate_formulaic_response", "validate_provider_rate_card",
]

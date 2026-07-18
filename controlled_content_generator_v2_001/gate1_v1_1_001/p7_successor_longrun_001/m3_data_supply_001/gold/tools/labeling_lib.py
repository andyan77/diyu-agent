#!/usr/bin/env python3
"""金标建标共享库：headless 标注叫、模板摘要核对、会话登记（协议 §1/§2 载体纪律）。"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

# M3 载体裁决 2026-07-17（journal seq41）：Anthropic 侧载体 claude-fable-5 → claude-opus-4-8。
# 起因 Fable 5 使用窗口 429 硬阻；发起人授权豁免切换。跨模型双盲仍成立（A=Codex-GPT/B=Opus-4.8，
# 两供应商）；QUAL 面构造全量 Opus 重建以统一来源。载体等价裁定见 ROLE_MODEL_MATRIX_ADDENDUM.M3.v2.json。
MODEL = "claude-opus-4-8"
NEUTRAL_CWD = Path(os.environ.get("TMPDIR", "/tmp/claude-1000")) / "m3_neutral"


def sha_text(t: str) -> str:
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def load_template(spec_path: Path, key: str) -> str:
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    entry = spec["prompt_templates"][key]
    if sha_text(entry["text"]) != entry["sha256"]:
        raise SystemExit(f"prompt template {key} digest drift — refuse to run")
    return entry["text"]


def run_headless(prompt: str, timeout: int = 1500) -> dict:
    NEUTRAL_CWD.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env["CLAUDE_CODE_DISABLE_AUTO_MEMORY"] = "1"
    proc = subprocess.run(
        ["claude", "-p", "--model", MODEL, "--output-format", "json", "--max-turns", "1"],
        input=prompt, capture_output=True, text=True, env=env,
        cwd=str(NEUTRAL_CWD), timeout=timeout)
    if proc.returncode != 0:
        raise RuntimeError(f"claude exit {proc.returncode}: {proc.stderr[-300:]}")
    return json.loads(proc.stdout.strip().splitlines()[-1])


def run_codex_headless(prompt: str, timeout: int = 420) -> dict:
    """席位 A 载体（scope v1.1）：codex exec 全新 ephemeral 线程，只读沙箱，仓外目录。"""
    import tempfile
    import time
    NEUTRAL_CWD.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    with tempfile.NamedTemporaryFile("r", suffix=".last.txt", dir=str(NEUTRAL_CWD),
                                     delete=False) as tf:
        last_path = tf.name
    proc = subprocess.run(
        ["codex", "exec", "-", "--json", "-o", last_path, "--ephemeral",
         "--skip-git-repo-check", "-s", "read-only"],
        input=prompt, capture_output=True, text=True,
        cwd=str(NEUTRAL_CWD), timeout=timeout)
    if proc.returncode != 0:
        raise RuntimeError(f"codex exit {proc.returncode}: {proc.stderr[-300:]}")
    thread_id, usage = None, None
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("type") == "thread.started":
            thread_id = ev.get("thread_id")
        elif ev.get("type") == "turn.completed":
            usage = ev.get("usage")
    result = Path(last_path).read_text(encoding="utf-8")
    Path(last_path).unlink(missing_ok=True)
    return {"session_id": thread_id or "UNKNOWN", "result": result,
            "total_cost_usd": 0.0, "provider": "codex-gpt",
            "model_config": "gpt-5.6-sol", "usage": usage,
            "duration_ms": int((time.time() - t0) * 1000), "num_turns": 1}


def call(carrier: str, prompt: str, timeout: int = 1500) -> dict:
    # Opus-4.8（席 B/构造/仲裁）单批含 1M 上下文+推理，实测仲裁批深权衡10条分歧偶超900s；给1500s余量，
    # 减少边缘慢批被误判超时（真超时仍由 attempt_call 捕获标 FAILED，不掀翻整流）
    if carrier == "codex":
        return run_codex_headless(prompt, timeout)
    return run_headless(prompt, timeout)


def parse_json_array(result_text: str) -> list | None:
    text = result_text.strip()
    if text.startswith("```"):
        text = text[text.find("["):text.rfind("]") + 1]
    try:
        rows = json.loads(text)
    except json.JSONDecodeError:
        try:
            rows = json.loads(text[text.find("["):text.rfind("]") + 1])
        except Exception:
            return None
    return rows if isinstance(rows, list) else None


def register(registry_path: Path, row: dict) -> None:
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    with open(registry_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def attempt_call(prompt: str, expected_check, raw_dir: Path, stem: str,
                 registry_path: Path, reg_meta: dict,
                 carrier: str = "claude") -> list | None:
    """一次叫 + 一次重试；每次都留 raw + 登记。expected_check(rows)->bool。"""
    rows = None
    raw_dir.mkdir(parents=True, exist_ok=True)
    for attempt in (1, 2):
        # 单次调用的超时/非零退出不得掀翻整条长流：捕获 → 登记失败尝试 → 重试/收尾标 FAILED
        try:
            res = call(carrier, prompt)
        except (subprocess.TimeoutExpired, RuntimeError) as e:
            register(registry_path, {**reg_meta, "attempt": attempt,
                                     "carrier": carrier, "model": (None if carrier == "codex" else MODEL),
                                     "call_error": type(e).__name__ + ": " + str(e)[:200],
                                     "usage": None, "cost_usd": None})
            continue
        raw_path = raw_dir / f"{stem}.raw.try{attempt}.json"
        raw_path.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
        register(registry_path, {**reg_meta, "attempt": attempt,
                                 "carrier": carrier,
                                 "model": (res.get("model_config") if carrier == "codex"
                                           else MODEL),
                                 "usage": res.get("usage"),
                                 "session_id": res.get("session_id"),
                                 "raw_output_path": raw_path.name,
                                 "cost_usd": res.get("total_cost_usd"),
                                 "duration_ms": res.get("duration_ms"),
                                 "num_turns": res.get("num_turns")})
        cand = parse_json_array(res.get("result", ""))
        if cand is not None and expected_check(cand):
            rows = cand
            break
    return rows


def registry_cost(registry_path: Path) -> dict:
    # 高并发追加（多标注/仲裁流同写一册）偶留撕裂/空字节行：跳过不可解析行，勿因单坏行崩溃
    rows, skipped = [], 0
    if registry_path.is_file():
        for l in open(registry_path, encoding="utf-8"):
            if not l.strip():
                continue
            try:
                rows.append(json.loads(l))
            except (json.JSONDecodeError, ValueError):
                skipped += 1
    return {"calls": len(rows),
            "total_usd": round(sum(r.get("cost_usd") or 0 for r in rows), 4),
            "total_wall_clock_ms": sum(r.get("duration_ms") or 0 for r in rows),
            "corrupt_rows_skipped": skipped}

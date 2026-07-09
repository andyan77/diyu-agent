# 08 · Batch Unlock Reconciliation (GRC Legacy Lock Retirement)

任务 / task: `GKB-GRC-LEGACY-LOCK-RETIRE-AND-GOVERNED-UNLOCK-001`（账本 step `P6R`）
= 原合并任务 `GKB-LEGACY-LOCK-RETIRE-AND-3600-STRUCTURED-DRAFT-MICROBATCH-GENERATION-001` 的 **Phase A**（founder 拆包裁定：先落 Phase A，Phase B 改真实增量微批，另行授权）。

## 一句话 / TL;DR

旧 semantic-pilot 失败线（44 cross-type / holdout-14 / 20-regen / v3–v4.7）**已失败并被 GRC 新线取代**。本目录把它们**登记为 superseded_failed_line（不删证据、不翻案、不改 PASS）**，并把 GRC 新线 **P4 canary-40 / P5 proposition_pack_v1 / P6 dual-gate briefing** 记录为当前**有效的受治理解锁依据**，建立一个**路线级**受治理增量微批解锁（范围 `mkc_007..mkc_046`）。**本任务零生成、零授权生成**；真实 3600 一条未产。`direct_3600_generation` / one-shot / `generate_without_grc_pilot` 仍 forbidden；P0-00（`mkc_001..006`）保持 held。

## 文件 / files

| 文件 | 作用 |
|---|---|
| `grc_legacy_pilot_reconciliation.v0.1.yaml` | 核心对账：旧线 superseded_failed（各 `use_as_p7_evidence: false`）+ GRC 证据 + 解锁范围/形态 + 诚实 caveat |
| `grc_batch_unlock_decision.v0.1.yaml` | 受治理解锁决定（路线级）：`governed_microbatch_generation_allowed_under_grc: true`，one-shot 仍禁，零生成/零授权，下一步=batch-001 另行授权 |
| `legacy_lock_surface_inventory.v0.1.yaml` | 全部锁面清单：02_brief_pack（4 顶层 + 14 batch brief）+ project-infra（**discovered count**，非硬编 10）+ 合约层（immutable preserved）|
| `legacy_failed_line_provenance_index.v0.1.yaml` | 失败线证据溯源（保留不删、无一翻案）|
| `grc_unlock_evidence_index.v0.1.yaml` | P4/P5/P6 证据索引（旧 20-regen / 旧线不作证据）|
| `p0_00_hold_decision.v0.1.yaml` | P0-00 `mkc_001..006` held，不进 GKB 正文、不进解锁范围 |

## 边界 / what this is NOT

- **不是**解除 one-shot 3600 禁令（合约层 `direct_3600_generation_allowed: false` 原样保留，碰都没碰）。
- **不是**授权生成（`generation_allowed` / `generation_eligible` 仍 false；无 `07_microbatch_runs/`；无草稿）。
- **不是**把旧失败线翻案（各 `rewritten_as_pass: false`；证据文件 immutable）。
- **不是**改 `project-infra/current_workspace_status.yaml` 或 `02_generation_brief_pack/**`（中央取代：路线权威在账本 + 本目录；旧锁按 legacy-read-only 登记）。
- **不是** CandidatePack / Four-Gate / KE / Serving / RAG / DIFY / production。

## 路线权威 / route authority

`10_execution_progress/grc_3600_execution_plan_status.v0.1.yaml`（primary）+ `08_batch_unlock_reconciliation/**`。
`project-infra/current_workspace_status.yaml` = legacy_read_only_not_active_route_authority。

## 校验 / checker

`ci/checkers/check_grc_legacy_lock_retire_and_governed_unlock.py`（独立重算、fail-closed、`--live` / `--selftest`；`python -O` 退出 2）。

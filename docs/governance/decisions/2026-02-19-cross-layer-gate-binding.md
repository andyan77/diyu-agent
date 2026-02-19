# 决议摘要：跨层验证节点与 Gate 绑定

日期：2026-02-19  
状态：Proposed（待 gate review 采纳）  
关联证据：`evidence/governance-reviews/cross-layer-integration-gap-v1.3-20260219.md`

## 背景

跨层验证节点（X/XF/XM）已在治理矩阵中定义，但机读 gate 通过 `delivery/milestone-matrix.yaml` + `scripts/verify_phase.py` 执行时，未建立节点 ID 级绑定，导致节点无法被机器追踪到通过/失败状态。

## 关键结论

1. 规划层完备：Section 4 定义 50 个跨层节点。
2. 执行层缺口：缺少以 X/XF/XM 为主键的独立集成装配任务卡。
3. Gate 层缺口：`exit_criteria` 与 X/XF/XM 无显式 ID 绑定。

## 拟采纳动作

1. 新增 `INT-*` 集成装配任务卡（映射 X/XF/XM）。
2. 在 `delivery/milestone-matrix.yaml` 增加节点绑定检查项。
3. 新增节点到 gate 覆盖校验脚本并纳入 CI。
4. 在 gate 证据中增加 Controlled-Pending 裁决状态。
5. 修正 `docs/governance/milestone-matrix.md` 中 XF 编号范围与横切文档不一致问题。

## 实施计划

- 子计划: `2026-02-19-cross-layer-gate-binding-impl-v1.0.md` (Dim-B 详细实施规格)
- 统一计划: `2026-02-19-production-delivery-gate-plan-v1.0.md` (Dim-A+B+C 三维度)

## 本文档边界

本文档仅记录决议摘要与后续动作，不替代审查证据正文。审查细节以证据文件为准。

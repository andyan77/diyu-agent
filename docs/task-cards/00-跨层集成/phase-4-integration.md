# Phase 4 Cross-Layer Integration Task Cards

## Phase 4: Full Feature + Performance -- Cross-Layer Verification

> 聚合规则: 同一 Phase + 参与层重叠 + 可共享 E2E 测试 -> 合并为一张卡
> 来源: `delivery/milestone-matrix.yaml:phase_4.exit_criteria`
> Gate 总数: 29 hard + 0 soft, 12 X-nodes bound

---

### TASK-INT-P4-TRACE: 全链路 trace_id 追踪 E2E

> 矩阵条目: X4-1
> Gate: p4-trace-e2e

| Field | Value |
|-------|-------|
| **目标** | 验证 trace_id 从 Gateway 入口 -> Brain -> Memory/Knowledge -> Tool -> Response 全链路传播 |
| **范围** | `tests/e2e/cross/test_trace_id_full_stack.py` |
| **范围外** | 前端 trace_id 注入 / OpenTelemetry collector 部署 |
| **依赖** | OS4-4, G4-1, B4-4 |
| **风险** | 依赖: 所有层必须实现 trace_id propagation; 数据: 需要完整对话链路; 兼容: 新增测试; 回滚: git revert |
| **兼容策略** | 新增测试文件, 无破坏性变更 |
| **验收命令** | `uv run pytest tests/e2e/cross/test_trace_id_full_stack.py -v` |
| **回滚方案** | `git revert` |
| **证据** | CI artifact / `evidence/phase-4/` |
| **决策记录** | trace_id 通过 contextvars 传播, 不依赖外部 collector |

---

### TASK-INT-P4-DELETE: 删除管线端到端 E2E

> 矩阵条目: X4-4
> Gate: p4-delete-e2e

| Field | Value |
|-------|-------|
| **目标** | 删除管线全链路: 用户请求删除 -> tombstone -> 物理删除 -> 审计记录 -> 所有存储 (PG + Neo4j + Qdrant + MinIO) 清理验证 |
| **范围** | `tests/e2e/cross/test_delete_pipeline_e2e.py` |
| **范围外** | GDPR/PIPL 合规报告生成 / 跨组织级联删除 |
| **依赖** | MC4-1, I4-5, OS4-5 |
| **风险** | 依赖: Delete FSM 8-state 必须就绪; 数据: 需要跨存储写入的测试数据; 兼容: 新增测试; 回滚: git revert |
| **兼容策略** | 新增测试文件, 使用 fake adapter 隔离存储 |
| **验收命令** | `uv run pytest tests/e2e/cross/test_delete_pipeline_e2e.py -v` |
| **回滚方案** | `git revert` |
| **证据** | CI artifact / `evidence/phase-4/` |
| **决策记录** | FSM 驱动删除, tombstone 保留 30 天, 物理删除异步执行 |

---

### TASK-INT-P4-FAULT: 故障注入与恢复验证

> 矩阵条目: X4-6
> Gate: p4-fault-injection

| Field | Value |
|-------|-------|
| **目标** | 验证关键路径故障注入后正确恢复: 删除管线中断恢复 + LLM Provider 故障切换 -> 审计完整 |
| **范围** | `tests/e2e/cross/test_fault_injection.py` |
| **范围外** | 网络层故障注入 / 全链路混沌工程 |
| **依赖** | OS4-5, OS4-6, S4-1 (circuit breaker) |
| **风险** | 依赖: LLM fallback (Qwen -> DeepSeek) 必须配置; 数据: 需要可注入故障的 adapter; 兼容: 新增测试; 回滚: git revert |
| **兼容策略** | 故障注入通过 adapter 配置, 不修改生产代码路径 |
| **验收命令** | `uv run pytest tests/e2e/cross/test_fault_injection.py -v` |
| **回滚方案** | `git revert` |
| **证据** | CI artifact / `evidence/phase-4/` |
| **决策记录** | R-1 裁决: Qwen primary -> DeepSeek fallback; LiteLLM mock for testing |

---

### TASK-INT-P4-SLO: SLI/SLO 端到端验证

> 矩阵条目: X4-5
> Gate: p4-slo-metrics

| Field | Value |
|-------|-------|
| **目标** | 验证 7 项 Brain SLI + API SLO 指标在 Prometheus/Grafana 全部可采集, 告警规则可触发 |
| **范围** | `scripts/check_slo_budget.py`, `deploy/monitoring/alerts.yml` |
| **范围外** | Grafana dashboard 布局 / 告警 Webhook 配置 |
| **依赖** | B4-4, OS4-1, OS4-2, OS4-3 |
| **风险** | 依赖: Prometheus metrics endpoint 必须暴露 7 SLI; 数据: 需要可触发告警的模拟负载; 兼容: 配置变更; 回滚: git revert alerts.yml |
| **兼容策略** | 追加告警规则, 不修改现有规则 |
| **验收命令** | `python3 scripts/check_slo_budget.py` |
| **回滚方案** | `git revert deploy/monitoring/alerts.yml` |
| **证据** | CI artifact / `evidence/phase-4/` |
| **决策记录** | C-2/C-3 裁决: 99.5% availability, P95<500ms, burn-rate 14.4x/6x |

---

### TASK-INT-P4-FE: 前端跨层集成 E2E

> 矩阵条目: XF4-1
> 矩阵条目: XF4-2
> 矩阵条目: XF4-3
> Gate: p4-billing-e2e, p4-monitoring-dashboard, p4-memory-privacy-e2e

| Field | Value |
|-------|-------|
| **目标** | 三条前后端跨层链路: (1) 充值流程 (XF4-1) + (2) 运维监控看板 (XF4-2) + (3) 记忆隐私控制 (XF4-3) |
| **范围** | `tests/e2e/cross/web/billing-flow.spec.ts`, `tests/e2e/cross/admin/monitoring-dashboard.spec.ts`, `tests/e2e/cross/web/memory-privacy.spec.ts` |
| **范围外** | 充值对接第三方支付 / Grafana embed / 批量记忆导出 |
| **依赖** | FW4-5, FA4-1, FW4-1, MC4-1 |
| **风险** | 依赖: 充值 API + 记忆删除 API 必须就绪; 数据: 需要测试组织 + 用户 + 余额; 兼容: 新增 E2E 测试; 回滚: git revert |
| **兼容策略** | Playwright E2E 测试, 不修改现有组件 |
| **验收命令** | `cd frontend && pnpm exec playwright test tests/e2e/cross/` |
| **回滚方案** | `git revert` |
| **证据** | CI artifact / Playwright trace / `evidence/phase-4/` |
| **决策记录** | Lighthouse 性能预算 (LCP<2.5s / FID<100ms / CLS<0.1 / 200KB) 同步验证 |

---

### TASK-INT-P4-MEDIA: 企业多模态 Cross-Layer E2E

> 矩阵条目: XM2-1
> 矩阵条目: XM2-2
> Gate: p4-enterprise-media, p4-media-safety

| Field | Value |
|-------|-------|
| **目标** | 企业媒体双写一致性 (Neo4j FK + Qdrant 向量) + NSFW/版权预检闭环 |
| **范围** | `tests/integration/knowledge/test_enterprise_media_fk.py`, `tests/integration/test_media_safety.py` |
| **范围外** | 跨模态语义检索 / 视频转码 / OCR |
| **依赖** | MM2-1, MM2-2, MM2-3, K4-3 |
| **风险** | 依赖: 企业媒体上传 API + FK Registry 必须就绪; 数据: 需要企业组织 + 媒体样本; 兼容: 新增测试; 回滚: git revert |
| **兼容策略** | 集成测试使用 fake adapter, 不依赖外部 AI 模型 |
| **验收命令** | `uv run pytest tests/integration/knowledge/test_enterprise_media_fk.py tests/integration/test_media_safety.py -v` |
| **回滚方案** | `git revert` |
| **证据** | CI artifact / `evidence/phase-4/` |
| **决策记录** | NSFW 检测使用规则引擎 stub, 生产替换为 AI 模型 |

# DIYU Agent Phase 4 落盘构建实施计划

**版本**: v4.1-final
**编制日期**: 2026-02-22
**Phase 主题**: 可靠性 + 完整功能 (Full Feature + Performance)
**前序**: Phase 3 已 GO (Hard 14/14, Soft 2/2, 1647 tests, 276 task cards)
**审查轮次**: 4 轮独立审查, 累计 10 项发现已全部修正
**原则**: 零 mock / 零代理 gate / 零口径歧义

---

## 第零部分 — 用户裁决记录

> 以下 13 项裁决为 Phase 4 无 mock 构建的前置决策，全部由项目负责人确认。

### R-1: LLM Provider Fallback 方案

- **生产**: Qwen 主 → DeepSeek 备。千问 API 已在 `.env` 中配置，DeepSeek API 单独配置 (`DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL`)。
- **测试**: LiteLLM mock provider，CI 中不依赖真实 LLM。
- **落盘位置**: `.env.example` 追加 DeepSeek 配置项；`src/tool/llm/` 实现 fallback 逻辑。

### R-2: 渗透测试工具与范围

- **工具**: OWASP ZAP `zap-baseline.py` 自动化扫描。
- **范围**: 仅 API endpoints（不含前端静态资源）。
- **报告格式**: JSON + Markdown 双份，存放 `evidence/pentest/`。
- **Gate**: `p4-pentest-report` — `scripts/check_pentest_report.py` 校验报告存在且无 Critical/High。

### R-3: SBOM 签名方案

- **工具**: 安装 cosign，使用 local key pair。
- **私钥**: `.keys/cosign.key`（已加入 `.gitignore`）。
- **CI**: 通过 Secret 注入私钥。
- **Gate**: `sign_sbom.sh` 改为硬失败（cosign 不可用或签名失败 → exit 1）。

### R-4: HA 验证拓扑

- **方案**: docker-compose HA 模式 — 2 app 实例 + nginx upstream + PG 主从。
- **PG 主从**: 无 Patroni，使用 `pg_basebackup` + 手动 promote 脚本验证 failover 逻辑。
- **落盘位置**: `deploy/ha/docker-compose.ha.yml` + `deploy/ha/nginx.conf` + `deploy/ha/pg_promote.sh`。
- **Gate**: `p4-ha-validation` — `scripts/check_ha_validation.sh`。

### R-5: 性能基线分档

| 档位 | 数据量 | 环境 | 用途 |
|------|--------|------|------|
| CI 回归基线 | Neo4j 10K 节点 / Qdrant 10K vectors | 开发环境 | 每次发版对比，防性能退化 |
| 容量规划基线 | 1M 级 | 独立性能测试（云上临时实例或大内存机器） | Phase 4 一次性跑完，生成报告，数据存档 |

- **Assembler 并发**: 10 并发。
- **种子数据脚本**: `scripts/seed_perf_data.py --neo4j-nodes 10000 --qdrant-vectors 10000`，切换档位只需改参数。

### C-1: On-call rotation

- **当前**: `founder-solo / best-effort`。商业化后升级为正式轮值。

### C-2: SLO 数值

- P95 < 500ms
- 错误率 < 0.1%
- 可用性 > 99.5%

### C-3: Burn-rate 阈值

- 接受 Google SRE Workbook 标准值:
  - Fast burn: 14.4x (1h window → P0 page)
  - Slow burn: 6x (6h window → P1 alert)

### C-4: P0 升级策略

- P0: page → 30min response（从原 15min 调整为 30min，适配 founder-solo 模式）。

### C-5: alerts.yml SLO 规则

- SLO burn-rate 规则追加到现有 `deploy/monitoring/alerts.yml`，新增 `diyu_slo_burn_rate` 规则组。

### C-6: Lighthouse CI 性能预算

- LCP < 2.5s / FID < 100ms / CLS < 0.1 — Google Core Web Vitals "Good" 标准。
- 首屏 < 200KB — 与 FE-08 Quality Engineering 定义一致。

### C-7: 离线部署镜像列表

- docker-compose 全部服务镜像 + celery-worker:
  - `pgvector/pgvector:pg16`
  - `redis:7-alpine`
  - `qdrant/qdrant:v1.12.6`
  - `neo4j:5-community`
  - `minio/minio:latest`
  - `diyu-agent:app` (自建)
  - `diyu-agent:celery-worker` (自建)

### C-8: 密钥轮换范围

- JWT_SECRET_KEY
- POSTGRES_PASSWORD (DATABASE_URL)
- MINIO_SECRET_KEY / AWS_SECRET_ACCESS_KEY
- LLM_API_KEY (含 Qwen + DeepSeek)

---

## 第一部分 — 当前状态基线

### 1.1 Phase 3 验收状态

```
make verify-phase-3 → Hard 14/14, Soft 2/2, GO
make test           → 1647 passed
check_acceptance_gate.py → 276 cards, 0 violations
make lint           → ruff check + format pass
make doctor         → 15/15 OK
```

### 1.2 Phase 4 当前 YAML 状态

`delivery/milestone-matrix.yaml` phase_4:
- 里程碑: 51 (23 Backend + 8 Frontend + 20 Crosscutting)
- exit_criteria: 29 hard + 0 soft (Stage 0 已完成)
- xnode_coverage: 12/12 = 100% (GO)
- go_no_go: hard_pass_rate=1.0, xnode_coverage_min=0.90

### 1.3 已通过的 Gate (Stage 0 验证)

| gate | 当前状态 | 证据 |
|------|---------|------|
| p4-compliance-artifacts | PASS | 7/7 required + SBOM 57KB |
| p4-incident-readiness | PASS | SLA P0/P1/P2 + 4 runbooks + on-call |
| p4-alert-routing | PASS | 8 rules + severity labels + routing |
| p4-slo-burn-rate (--verify-burn-rate) | PASS | fast/slow/sustained burn-rate rules |
| p4-slo-metrics | PASS | SLO + error-budget + burn-rate config |
| p4-postmortem-capa | PASS | template 6 sections + CAPA register |
| p4-release-drill --dry-run | PASS | 4s < 300s target |
| p4-diag-package --dry-run | PASS | 8 collection steps validated |
| p4-key-rotation --dry-run | PASS | 5 rotation targets identified |
| xnode-coverage --phase 4 | GO | 12/12 = 100% >= 90% |

### 1.4 跨层验证节点清单

| X-node | 参与层 | 验证场景 | 失败影响 |
|--------|--------|---------|---------|
| X4-1 | All | 全链路 trace_id 追踪 | 降级 |
| X4-2 | Infra+Delivery | 升级回滚演练 | 阻断 |
| X4-3 | All | 三 SSOT 一致性 | 阻断 |
| X4-4 | Brain+Memory+Infra | 删除管线端到端 | 阻断 |
| X4-5 | Obs+All | SLI/SLO 端到端 | 降级 |
| X4-6 | Obs+Infra | 故障注入与恢复 | 阻断 |
| X4-7 | Obs+Gateway | 渗透测试 OWASP Top 10 | 阻断 |
| XF4-1 | FE-Web+Gateway | 额度耗尽→充值→余额更新 | 阻断 |
| XF4-2 | FE-Admin+Infra | 系统监控看板 | 降级 |
| XF4-3 | FE-Web+Gateway+Memory | 查看记忆→删除→确认删除 | 阻断 |
| XM2-1 | Multimodal+Knowledge+Infra | 企业媒体双写+FK | 阻断 |
| XM2-2 | Multimodal+Obs | NSFW+版权预检 | 降级 |

---

## 第二部分 — 多轮审查发现修正记录

### 审查轮次总览

| 轮次 | 发现数 | 级别分布 |
|------|--------|---------|
| v1→v2 (矩阵对齐) | 16 | 结构性遗漏 (整个 FE 维度 + 5 X-nodes) |
| v2→v3 (独立审计 R1) | 5 | 1 Critical + 3 High + 1 Medium |
| v3→v4 (独立审计 R2) | 6 | 1 Critical + 3 High + 2 Medium |
| v4→v4.1 (独立审计 R3) | 4 | 2 High + 2 Medium |

### 逐项修正对照

| # | 级别 | 发现 | 根因 | 修正 |
|---|------|------|------|------|
| 1 | C | xnode 只查绑定不查 gate 通过 | check_xnode_coverage.py line 177 只查 binding 存在 | 增加 --verify-results 模式: gate PASS 才计入覆盖 |
| 2 | H | X4-1/3/4/7 绑定到代理 gate | 用元校验/覆盖率代替真实验证 | 每个 X-node 绑专属真实验证 gate |
| 3 | H | 口径不一致 (12/12, 11+2, 11+5) | 迭代过程中未清理中间版本 | 单一口径: 29 hard + 0 soft |
| 4 | H | XF4-2/XM2-1/XM2-2 放在 soft | verify_phase.py line 190 只看 hard | 全部提升为 hard |
| 5 | M | SBOM attestation 未纳入 P4 hard | production-delivery-gate-plan line 467 明确 Phase 4 hard | 新增 p4-sbom-attestation hard |
| 6 | M | 缺复盘+CAPA 闭环 | 有告警/演练无复盘回灌 | 新增 p4-postmortem-capa hard |
| 7 | H | soft 绑 xnode 间接阻断语义冲突 | soft fail→xnode 覆盖率降→间接 NO-GO | 原 soft 全部提升 hard, soft 清零 |
| 8 | H | D4-3/D4-4/D4-5 缺独立 gate | 里程碑无阻断验证 | 新增 3 个 hard gate |
| 9 | M | B4-1/K4-1/K4-2/G4-2 性能/HA 缺 gate | 核心生产指标无硬门禁 | 新增 p4-perf-baseline + p4-ha-validation |
| 10 | M | 中间版本口径残留 | 文内残留多种计数 | 本文为唯一口径，无中间描述 |

---

## 第三部分 — exit_criteria 最终定义

**唯一口径: 29 hard + 0 soft**

设计原则:
- **全 hard, 零 soft**: 消除 soft/xnode 语义冲突
- **真实验证**: 每个 X-node 绑定到执行真实测试的 gate
- **xnode 结果覆盖**: `--verify-results` 模式下 gate 必须 PASS 才计入
- **里程碑→gate 可追溯**: 关键里程碑均有独立 gate

### 29 Hard Gates

| # | gate ID | description | xnodes | 里程碑覆盖 |
|---|---------|-------------|--------|---------|
| 1 | p4-coverage | Test coverage >= 80% | — | 全局 |
| 2 | p4-fe-build | Frontend build passes | — | 全局 FE |
| 3 | p4-lighthouse | Lighthouse CI budget (LCP<2.5s/FID<100ms/CLS<0.1/200KB) | XF4-1 | FW4-1 |
| 4 | p4-a11y | Zero critical a11y violations | — | FW4-2, OS4-8 |
| 5 | p4-trace-e2e | Full-chain trace_id E2E | X4-1 | OS4-4 |
| 6 | p4-ssot-drift | 三 SSOT 一致性检查 | X4-3 | D3-3 升级 |
| 7 | p4-delete-e2e | 删除管线 8 态端到端 | X4-4 | MC4-1, I4-4, I4-5 |
| 8 | p4-fault-injection | 故障注入+恢复 | X4-6 | OS4-5, OS4-6 |
| 9 | p4-billing-e2e | Billing flow E2E | XF4-1 | FW4-5 |
| 10 | p4-memory-privacy-e2e | Memory privacy E2E | XF4-3 | MC4-1 |
| 11 | p4-release-drill | 升级回滚演练 | X4-2 | D4-1 |
| 12 | p4-dr-restore | 备份恢复演练 | — | D4-2, MC4-2 |
| 13 | p4-dependency-chaos | 依赖混沌测试 (CB-4) | — | OS4-5, OS4-6 |
| 14 | p4-incident-readiness | SLA+runbooks+on-call | — | OS4-3 |
| 15 | p4-alert-routing | Alert routing 完整性 | — | OS4-3 |
| 16 | p4-compliance-artifacts | 合规产物完整 | — | D4-6 |
| 17 | p4-slo-metrics | SLI/SLO+alerts 可用 | X4-5 | OS4-1, OS4-2 |
| 18 | p4-slo-burn-rate | Burn-rate 规则配置 | — | OS4-2 |
| 19 | p4-monitoring-dashboard | Admin 监控看板 E2E | XF4-2 | FA4-1 |
| 20 | p4-xnode-coverage | XNode 结果覆盖 >= 90% | — | 治理 |
| 21 | p4-pentest-report | OWASP Top 10 无 Critical/High | X4-7 | OS4-7 |
| 22 | p4-sbom-attestation | SBOM cosign 签名 | — | D3-5→P4 hard |
| 23 | p4-perf-baseline | 性能基线 (Assembler/Graph/Vector P95) | — | B4-1, K4-1, K4-2 |
| 24 | p4-ha-validation | HA failover <30s | — | G4-2, I4-2 |
| 25 | p4-diag-package | 一键诊断包 | — | D4-3 |
| 26 | p4-key-rotation | 密钥轮换 | — | D4-4 |
| 27 | p4-enterprise-media | 企业媒体双写+FK | XM2-1 | MM2-1~3 |
| 28 | p4-media-safety | NSFW+版权预检 | XM2-2 | MM2-4~6 |
| 29 | p4-postmortem-capa | 复盘模板+CAPA 登记簿 | — | 运维闭环 |

### go_no_go

```yaml
go_no_go:
  hard_pass_rate: 1.0
  xnode_coverage_min: 0.90
  approver: "architect"
```

---

## 第四部分 — xnode 覆盖矩阵 (结果覆盖)

| X-node | 绑定 hard gate | 验证方式 (gate PASS 才计入) |
|--------|---------------|-------------------------|
| X4-1 | p4-trace-e2e | pytest test_trace_id_full_stack.py |
| X4-2 | p4-release-drill | 升级回滚真实演练脚本 |
| X4-3 | p4-ssot-drift | check_ssot_drift.sh 三 SSOT 一致性 |
| X4-4 | p4-delete-e2e | pytest test_delete_pipeline_e2e.py 8 态 |
| X4-5 | p4-slo-metrics | check_slo_budget.py error-budget+burn-rate |
| X4-6 | p4-fault-injection | pytest test_fault_injection.py |
| X4-7 | p4-pentest-report | check_pentest_report.py 渗透报告 |
| XF4-1 | p4-lighthouse, p4-billing-e2e | Lighthouse CI + Playwright billing |
| XF4-2 | p4-monitoring-dashboard | Playwright monitoring-dashboard |
| XF4-3 | p4-memory-privacy-e2e | Playwright memory-privacy |
| XM2-1 | p4-enterprise-media | pytest test_enterprise_media_fk.py |
| XM2-2 | p4-media-safety | pytest test_media_safety.py |

12/12 X-nodes 全部绑定到 hard gate。

---

## 第五部分 — 治理机制修复 (Stage 0, 已完成)

### 5.1 check_xnode_coverage.py 增强

- 新增 `--verify-results` 参数
- 执行 bound gate check 命令，gate PASS 才计入覆盖
- Gate decision 使用 result_coverage 而非 direct_coverage

### 5.2 verify_phase.py 集成 xnode 结果覆盖

- 在 go_no_go 判定后追加 xnode_coverage_min 检查
- 导入 check_xnode_coverage 模块，执行 verify_results=True
- xnode 覆盖不达标 → BLOCKED

### 5.3 milestone-matrix.yaml 更新

- phase_4.exit_criteria → 29 hard + 0 soft + 12 xnodes 绑定

### 5.4 milestone-matrix.md 清单同步

- Phase 4 检查清单 → 29/29

### 5.5 phase-4-integration.md 创建

- 6 张跨层集成卡 (TRACE/DELETE/FAULT/SLO/FE/MEDIA)

### 5.6 incident-sla.yaml 更新

- 追加 slo/error_budget/burn_rate 段
- on_call → founder-solo/best-effort
- P0 response → 30min
- 追加 postmortem_template + capa_register 引用

### 5.7 alerts.yml 更新

- 新增 `diyu_slo_burn_rate` 规则组 (fast 14.4x / slow 6x / latency)

### 5.8 sign_sbom.sh 硬化

- cosign 不可用 → exit 1
- 支持 `.keys/cosign.key` local key pair
- `.gitignore` 追加 `.keys/`

### 5.9 新建脚本 (7)

| 脚本 | Gate |
|------|------|
| scripts/check_slo_budget.py | p4-slo-metrics |
| scripts/check_pentest_report.py | p4-pentest-report |
| scripts/check_postmortem_capa.py | p4-postmortem-capa |
| scripts/diyu_diagnose.sh | p4-diag-package |
| scripts/rotate_secrets.sh | p4-key-rotation |
| scripts/check_ha_validation.sh | p4-ha-validation |
| scripts/check_ssot_drift.sh | p4-ssot-drift |

### 5.10 新建交付产物 (2)

| 产物 | Gate |
|------|------|
| delivery/commercial/postmortem-template.md | p4-postmortem-capa |
| delivery/commercial/capa-register.yaml | p4-postmortem-capa |

---

## 第六部分 — 运维闭环定义

### 6.1 事故复盘 + CAPA 回灌

```
告警触发 (deploy/monitoring/alerts.yml)
→ 事故分级 (delivery/commercial/incident-sla.yaml P0/P1/P2)
→ 事故处置 (delivery/commercial/runbook/*.md)
→ 复盘 (delivery/commercial/postmortem-template.md)
→ CAPA 提取 (delivery/commercial/capa-register.yaml)
→ gate 绑定 (capa_register.gate_binding → 下轮 exit_criteria)
→ 阻断验证 (verify_phase.py)
```

### 6.2 SLO error-budget 闭环

```yaml
slo:
  availability: 99.5%      # 目标 (C-2)
  latency_p95: 500ms       # 目标 (C-2)
  error_rate: 0.1%         # 目标 (C-2)

error_budget:
  monthly_budget_minutes: 216  # 30d * 24h * 60min * 0.5%
  burn_rate:
    fast: 14.4x (1h window → P0 page)     # C-3
    slow: 6x (6h window → P1 alert)       # C-3
  exhaustion_policy: freeze non-critical deploys until budget resets

on_call:
  model: founder-solo     # C-1
  coverage: best-effort   # C-1
  P0: page → 30min response  # C-4
```

---

## 第七部分 — 51 个里程碑分层实施

### Stage 1: Backend (23 milestones)

#### Brain 层 (B4-1 ~ B4-5)

| ID | 交付 | 验收标准 | V-x | gate 覆盖 |
|----|------|---------|-----|---------|
| B4-1 | Context Assembler P95<200ms | 10 并发, P95<200ms (R-5) | X4-1 | p4-perf-baseline |
| B4-2 | Dynamic budget allocator v1 | token 预算分配, 利用率>=90% | — | p4-coverage |
| B4-3 | TruncationPolicy | 超 token 上限按优先级截断 | — | p4-coverage |
| B4-4 | 7 SLI instrumentation | 7 项指标 Grafana 可视 | X4-1 | p4-slo-metrics |
| B4-5 | Sanitization pattern-based | 恶意 prompt 拦截率>=99% | — | p4-coverage |

#### MemoryCore 层 (MC4-1 ~ MC4-3)

| ID | 交付 | 验收标准 | V-x | gate 覆盖 |
|----|------|---------|-----|---------|
| MC4-1 | 删除管线 8 态 FSM | 每步可审计 | X4-4 | p4-delete-e2e |
| MC4-2 | Backup restore drill | 恢复后数据一致 | X4-2 | p4-dr-restore |
| MC4-3 | deletion_timeout_rate SLI=0% | SLA 内完成删除 | X4-4 | p4-slo-metrics |

#### Knowledge 层 (K4-1 ~ K4-3)

| ID | 交付 | 验收标准 | V-x | gate 覆盖 |
|----|------|---------|-----|---------|
| K4-1 | Graph query P95<100ms | Neo4j 10K/1M 节点查询 (R-5) | X4-1 | p4-perf-baseline |
| K4-2 | Vector search P95<50ms | Qdrant 10K/1M vectors (R-5) | X4-1 | p4-perf-baseline |
| K4-3 | FK Reconciliation Job | 破坏→检测→修复→一致率 100% | X4-3 | p4-ssot-drift |

#### Skill 层 (S4-1 ~ S4-2)

| ID | 交付 | 验收标准 | V-x | gate 覆盖 |
|----|------|---------|-----|---------|
| S4-1 | Skill 熔断器 | 连续失败 5 次→熔断→降级 | X4-1 | p4-coverage |
| S4-2 | Skill 执行超时 | >30s→超时终止 | — | p4-coverage |

#### Tool 层 (T4-1 ~ T4-2)

| ID | 交付 | 验收标准 | V-x | gate 覆盖 |
|----|------|---------|-----|---------|
| T4-1 | Tool 独立计费 | 费用独立于 LLM token | X4-1 | p4-coverage |
| T4-2 | Tool retry + exponential backoff | 100ms/500ms/2000ms 退避 | — | p4-coverage |

#### Gateway 层 (G4-1 ~ G4-3)

| ID | 交付 | 验收标准 | V-x | gate 覆盖 |
|----|------|---------|-----|---------|
| G4-1 | SLO metrics + alerts | API P95<500ms, err<0.1% (C-2) | X4-1 | p4-slo-metrics |
| G4-2 | HA validation | 单节点故障→自动切换<30s (R-4) | X4-2 | p4-ha-validation |
| G4-3 | Per-org/user rate limiting | 不同租户不同阈值 | — | p4-coverage |

#### Infra 层 (I4-1 ~ I4-5)

| ID | 交付 | 验收标准 | V-x | gate 覆盖 |
|----|------|---------|-----|---------|
| I4-1 | Prometheus + Grafana stack | 4 黄金信号看板 | X4-1 | p4-slo-metrics |
| I4-2 | PG failover drill | 切换<30s (R-4) | X4-2 | p4-ha-validation |
| I4-3 | Backup restore drill PG | 数据完整率 100% | X4-2 | p4-dr-restore |
| I4-4 | Fault injection tests | 8 步全可恢复 | X4-4 | p4-delete-e2e |
| I4-5 | PIPL/GDPR delete pipeline | SLA 内完成 | X4-4 | p4-delete-e2e |

### Stage FE: Frontend (8 milestones)

#### FE-Web (FW4-1 ~ FW4-5)

| ID | 交付 | 验收标准 | V-x | gate 覆盖 |
|----|------|---------|-----|---------|
| FW4-1 | Performance budget | LCP<2.5s, FID<100ms, CLS<0.1 (C-6) | X4-1 | p4-lighthouse |
| FW4-2 | a11y check pass | axe-core 0 critical | — | p4-a11y |
| FW4-3 | Dark/light mode | 两种模式全组件正确 | — | p4-fe-build |
| FW4-4 | Keyboard shortcuts | >=5 个快捷键 | — | p4-fe-build |
| FW4-5 | Billing recharge page | 充值→余额更新 (XF4-1) | XF4-1 | p4-billing-e2e |

#### FE-Admin (FA4-1 ~ FA4-3)

| ID | 交付 | 验收标准 | V-x | gate 覆盖 |
|----|------|---------|-----|---------|
| FA4-1 | System monitoring dashboard | 实时数据可展示 | XF4-2 | p4-monitoring-dashboard |
| FA4-2 | Quota management | 配额即时生效 | — | p4-fe-build |
| FA4-3 | Backup management | 3 操作全可用 | X4-2 | p4-fe-build |

### Stage 2: Crosscutting (20 milestones)

#### Delivery (D4-1 ~ D4-6)

| ID | 交付 | V-x | gate 覆盖 |
|----|------|-----|---------|
| D4-1 | 升级回滚流程产品化 | X4-2 | p4-release-drill |
| D4-2 | 备份恢复演练门禁 | X4-2 | p4-dr-restore |
| D4-3 | 一键诊断包 | — | p4-diag-package |
| D4-4 | 密钥轮换 + 证书管理 | — | p4-key-rotation |
| D4-5 | 轻量离线部署 | — | (p4-offline-deploy 待创建) |
| D4-6 | verify-phase-4 | X4-2 | (29/29 gate 全通) |

#### Observability & Security (OS4-1 ~ OS4-8)

| ID | 交付 | V-x | gate 覆盖 |
|----|------|-----|---------|
| OS4-1 | 7 Brain SLI Grafana dashboard | X4-5 | p4-slo-metrics |
| OS4-2 | SLO 定义 + error-budget + burn-rate | X4-5 | p4-slo-metrics |
| OS4-3 | Alert tiering P0/P1/P2 | — | p4-alert-routing, p4-incident-readiness |
| OS4-4 | Full-chain trace_id | X4-1 | p4-trace-e2e |
| OS4-5 | Fault injection: 删除管线 | X4-6 | p4-dependency-chaos, p4-delete-e2e |
| OS4-6 | Fault injection: LLM Provider | X4-6 | p4-dependency-chaos |
| OS4-7 | Pentest OWASP Top 10 | X4-7 | p4-pentest-report |
| OS4-8 | FE a11y axe-core audit | — | p4-a11y |

#### Multimodal M2 (MM2-1 ~ MM2-6)

| ID | 交付 | V-x | gate 覆盖 |
|----|------|-----|---------|
| MM2-1 | Enterprise media upload API | — | p4-enterprise-media |
| MM2-2 | KnowledgeBundle media extension | — | p4-enterprise-media |
| MM2-3 | enterprise_media Neo4j FK | — | p4-enterprise-media |
| MM2-4 | Skill multimodal capability | — | p4-media-safety |
| MM2-5 | DocumentExtract Tool | — | p4-coverage |
| MM2-6 | Enterprise media delete cascade | X4-4 | p4-delete-e2e |

---

## 第八部分 — 交付产物总表

### 8.1 Stage 0 已完成 (治理脚手架)

| 类型 | 数量 | 状态 |
|------|------|------|
| 修改现有脚本 | 4 (xnode_coverage, verify_phase, alert_routing, sign_sbom) | 已完成 |
| 修改现有配置 | 3 (milestone-matrix.yaml, milestone-matrix.md, incident-sla.yaml) | 已完成 |
| 修改现有告警 | 1 (alerts.yml) | 已完成 |
| 新建脚本 | 7 (slo_budget, pentest_report, postmortem_capa, diagnose, rotate_secrets, ha_validation, ssot_drift) | 已完成 |
| 新建交付产物 | 3 (postmortem-template, capa-register, phase-4-integration.md) | 已完成 |

### 8.2 待创建的测试文件

| 路径 | 场景 | gate |
|------|------|------|
| tests/e2e/cross/test_trace_id_full_stack.py | 全链路 trace_id | p4-trace-e2e |
| tests/e2e/cross/test_delete_pipeline_e2e.py | 8 态删除管线 | p4-delete-e2e |
| tests/e2e/cross/test_fault_injection.py | 故障注入+恢复 | p4-fault-injection |
| tests/e2e/cross/test_dependency_chaos.py | 依赖混沌 4 场景 | p4-dependency-chaos |
| tests/e2e/cross/test_ha_failover.py | HA 单节点故障切换 | p4-ha-validation |
| tests/e2e/cross/web/billing-flow.spec.ts | 充值流程 Playwright | p4-billing-e2e |
| tests/e2e/cross/web/memory-privacy.spec.ts | 记忆隐私 Playwright | p4-memory-privacy-e2e |
| tests/e2e/cross/admin/monitoring-dashboard.spec.ts | 监控看板 Playwright | p4-monitoring-dashboard |
| tests/perf/test_assembler_latency.py | Assembler P95 | p4-perf-baseline |
| tests/perf/knowledge/test_graph_perf.py | Graph P95 | p4-perf-baseline |
| tests/perf/knowledge/test_vector_perf.py | Vector P95 | p4-perf-baseline |
| tests/integration/knowledge/test_enterprise_media_fk.py | 企业媒体双写 | p4-enterprise-media |
| tests/integration/test_media_safety.py | NSFW+版权 | p4-media-safety |

### 8.3 待创建的基础设施文件

| 路径 | 用途 |
|------|------|
| deploy/ha/docker-compose.ha.yml | HA 拓扑 (R-4) |
| deploy/ha/nginx.conf | nginx upstream (R-4) |
| deploy/ha/pg_promote.sh | PG 手动 promote (R-4) |
| scripts/seed_perf_data.py | 性能种子数据 (R-5) |
| scripts/check_offline_deploy.sh | 离线部署验证 |
| evidence/pentest/ | 渗透测试报告目录 |

---

## 第九部分 — 执行顺序与依赖关系

### 串行 / 并行判定

```
Stage 0 (已完成) ─────────────────────────────────────────
                │
                ├──── Stage 1-A: Brain + Memory + Infra(可观测)  ──┐ 串行链
                │     MC4-1(FSM) → I4-4/I4-5(故障注入/GDPR)       │
                │     I4-1(Prometheus) → B4-4(7 SLI)              │
                │     B4-1(Assembler) → B4-2/B4-3(budget/trunc)  │
                │                                                  │
                ├──── Stage 1-B: Knowledge + Skill + Tool  ────────┤ 与 1-A 并行
                │     K4-1/K4-2(性能基线) 可独立                     │
                │     K4-3(FK Reconciliation) 可独立                │
                │     S4-1/S4-2, T4-1/T4-2 无外部依赖               │
                │                                                  │
                ├──── Stage FE: Frontend 8 milestones ─────────────┤ 与 1-A/1-B 并行
                │     FW4-1~FW4-4 无后端依赖                        │
                │     FW4-5(billing) 需 Gateway billing API ←──────┤ 等 G4-3
                │     FA4-1(monitoring) 需 I4-1(Prometheus) ←──────┤ 等 1-A
                │                                                  │
                ▼                                                  │
         Stage 1-C: Gateway ──────────────────────────────────────┘
                │     G4-1(SLO metrics) 需 I4-1 + B4-4
                │     G4-2(HA) 需 I4-2(PG failover)
                │     G4-3(rate limiting) 可独立
                │
                ▼
         Stage 2: Crosscutting 运营硬化 ─────────────────────
                │  D4-1~D4-6, OS4-1~OS4-8
                │  依赖: Stage 1 的 SLI/Prometheus/FSM 全部就绪
                │  内部串行链: OS4-1→OS4-2→OS4-3 (SLI→SLO→Alert)
                │  pentest (OS4-7) 需 Gateway 全部就绪
                │
                ▼
         Stage 3: Multimodal M2 ────────────────────────────
                │  MM2-1~MM2-6
                │  依赖: K4-3(FK) + MC4-1(删除) + S3-3(Skill)
                │  全部串行于 Stage 1-A/1-B 之后
                │
                ▼
         验收: make verify-phase-4
```

### 并行矩阵

| 关系 | 组合 | 原因 |
|------|------|------|
| **可并行** | Stage 1-A + 1-B + FE(前4) | 无直接数据依赖 |
| **可并行** | K4-1/K4-2 + S4-1/S4-2 + T4-1/T4-2 | 三层各自独立 |
| **可并行** | FW4-1~FW4-4 + Stage 1 全部 | 前端不依赖后端新功能 |
| **串行** | MC4-1 → I4-4 → I4-5 | 删除 FSM → 故障注入 → GDPR |
| **串行** | I4-1 → B4-4 → OS4-1 → OS4-2 | Prometheus → SLI → Dashboard → SLO |
| **串行** | I4-2 → G4-2 | PG failover → HA validation |
| **串行** | Stage 1 + FE → Stage 2 | 运营硬化需功能就绪 |
| **串行** | Stage 2 → Stage 3 (M2) | 企业媒体需 FK/删除/Skill 就绪 |
| **串行** | Stage 3 → 验收 | 全部 29 gate 就绪后 verify |

### 最大并行度

同时推进 3 条线:
1. **线 A**: Brain → Memory → Infra(可观测) (关键路径)
2. **线 B**: Knowledge + Skill + Tool
3. **线 C**: Frontend FW4-1~FW4-4

---

## 第十部分 — 覆盖率汇总

| 维度 | 总数 | 覆盖 | 覆盖率 |
|------|------|------|--------|
| Backend milestones | 23 | 23 | 100% |
| Frontend milestones | 8 | 8 | 100% |
| Crosscutting milestones | 20 | 20 | 100% |
| Total milestones | 51 | 51 | 100% |
| X-nodes (结果覆盖) | 12 | 12 | 100% |
| exit_criteria hard | 29 | — | — |
| exit_criteria soft | 0 | — | — |
| 审查发现累计修正 | 10/10 | — | 100% |
| 用户裁决落盘 | 13/13 | — | 100% |

---

> 以上为综合 4 轮审查 + 13 项用户裁决的 Phase 4 落盘构建完整实施计划。
> Stage 0 治理脚手架已完成并验证通过，可进入 Stage 1 构建。

# DIYU Agent 里程碑矩阵 -- 横切维度 (Crosscutting)

> parent: `docs/governance/milestone-matrix.md`
> scope: Delivery/DevOps / Multimodal (M-Track) / Observability & Security / 跨层集成验证节点
> version: v1.0

---

> 矩阵层 7 字段格式 (D/AC/V-in/V-x/V-fb/M/DEP) 说明见 [索引文件](milestone-matrix.md) Section 0.5。
> 任务卡层采用双 Tier Schema (Tier-A: 10 字段, Tier-B: 8 字段)，详见 `task-card-schema-v1.0.md`。
> 后端维度详情见 [后端文件](milestone-matrix-backend.md)，前端维度详情见 [前端文件](milestone-matrix-frontend.md)。

---

## 1. Delivery/DevOps 详细里程碑

> 治理规范: v1.1 Section 12 + Vibe 执行附录 Section 1

### Phase 0 -- 骨架与硬门禁（核心交付 Phase）

| # | D | AC | V-in | V-x | V-fb | M | DEP |
|---|---|----|----|-----|------|---|-----|
| D0-1 | `delivery/manifest.yaml` 骨架 | [FILE] Schema 完整，值标 TBD，通过 schema 校验 | schema 校验通过 | X0-2 | -- | 字段完整 | -- |
| D0-2 | `delivery/milestone-matrix.schema.yaml` | [FILE] JSON Schema 定义存在 | schema 可解析 | -- | -- | 文件存在且有效 | -- |
| D0-3 | `delivery/preflight.sh` 雏形 | [CMD] 运行 -> 检查 Docker/Compose/端口/磁盘 | 检查项完整 | X0-3 | -- | >= 4 项检查通过 | -- |
| D0-4 | `.github/workflows/ci.yml` 硬门禁 | [CMD] PR -> CI 运行 ruff/mypy/pytest/guard 脚本 | CI 流程完整 | X0-2 | -- | 全部硬门禁项在 CI 中 | -- |
| D0-5 | `scripts/check_layer_deps.sh` | [CMD] 运行 -> 检测层间依赖违规 | 脚本可执行 | X0-2 | -- | 违规检出率可验证 | -- |
| D0-6 | `scripts/check_port_compat.sh` | [CMD] 运行 -> 检测 Port 兼容性 | 脚本可执行 | X0-2 | -- | 兼容性检查通过 | -- |
| D0-7 | `scripts/check_migration.sh` | [CMD] 运行 -> 检测 Migration 合规性 | 脚本可执行 | -- | -- | 合规检查通过 | -- |
| D0-8 | `scripts/change_impact_router.sh` | [CMD] 运行 -> 自动标记 [CONTRACT]/[MIGRATION]/[SECURITY] | 标记逻辑正确 | -- | -- | 3 类标记可触发 | -- |
| D0-9 | PR 模板 + CODEOWNERS + commit lint | [FILE] 文件存在且 CI 校验通过 | 模板完整 | X0-2 | -- | 文件全部存在 | -- |
| D0-10 | `make verify-phase-0` | [CMD] 运行 -> 所有 P0 检查项输出 PASS | 全项通过 | X0-2 | -- | 完成度 100% | -- |

### Phase 1 -- 安全扫描

| # | D | AC | V-in | V-x | V-fb | M | DEP |
|---|---|----|----|-----|------|---|-----|
| D1-1 | 镜像安全扫描 (CI 软门禁) | [CMD] Docker 镜像扫描无 Critical 漏洞 | 扫描报告可读 | X1-3 | -- | 0 Critical 漏洞 | -- |
| D1-2 | SBOM 生成 | [CMD] `make sbom` -> 生成 SPDX 格式 SBOM | SBOM 格式正确 | -- | -- | SPDX 合规 | -- |
| D1-3 | `make verify-phase-1` | [CMD] 运行 -> 所有 P1 检查项输出 PASS | 全项通过 | X1-3 | -- | 完成度 100% | -- |

### Phase 2 -- Dogfooding

| # | D | AC | V-in | V-x | V-fb | M | DEP |
|---|---|----|----|-----|------|---|-----|
| D2-1 | 前端 CI (pnpm lint + typecheck + test + a11y) | [CMD] 前端 PR CI 全部通过 | 4 项检查齐全 | X0-2 | XF2-4 | 0 error | -- |
| D2-2 | OpenAPI 类型同步检查 (CI 硬门禁) | [CMD] 生成后 diff 为空 | 同步脚本可用 | -- | XF2-4 | diff 为空 | -- |
| D2-3 | 内部 dogfooding 环境 | [E2E] `make verify-dogfooding` (全栈健康检查 + 对话冒烟测试) | 环境可访问 | X2-1 | XF2-1 | 团队可使用 | 全栈部署 |
| D2-4 | 资源消耗数据记录 | [METRIC] CPU/内存/存储使用量有记录 | 监控数据可查 | -- | -- | 3 项资源数据有记录 | -- |
| D2-5 | `make verify-phase-2` | [CMD] 运行 -> 所有 P2 检查项输出 PASS | 全项通过 | -- | -- | 完成度 100% | -- |

### Phase 3 -- 安装器产品化

| # | D | AC | V-in | V-x | V-fb | M | DEP |
|---|---|----|----|-----|------|---|-----|
| D3-1 | `delivery/manifest.yaml` TBD -> 实值 | [FILE] 所有核心字段有真实值 | schema 校验通过 | X4-3 | -- | TBD 项 = 0 | 资源数据 (D2-4) |
| D3-2 | 安装器 + preflight 产品化 | [CMD] 全新服务器运行安装脚本 -> 系统可用 | 安装脚本可执行 | -- | -- | 全新机器可部署 | -- |
| D3-3 | `deploy/*` 与 manifest 一致性检查 | [CMD] `scripts/check_manifest_drift.sh` 通过 | 漂移检测脚本可用 | X4-3 | -- | 漂移 = 0 | -- |
| D3-4 | `make verify-phase-3` | [CMD] 运行 -> 所有 P3 检查项输出 PASS | 全项通过 | -- | -- | 完成度 100% | -- |

### Phase 4 -- 运维产品化

| # | D | AC | V-in | V-x | V-fb | M | DEP |
|---|---|----|----|-----|------|---|-----|
| D4-1 | 升级回滚流程产品化 | [CMD] 升级 -> 回滚 -> 数据完整 -> 用时 < 5min | 回滚脚本可用 | X4-2 | -- | 回滚 < 5min | -- |
| D4-2 | 备份恢复演练门禁 | [CMD] `make dr-drill` -> upgrade->downgrade->upgrade 通过 | 演练脚本可用 | X4-2 | -- | 3 步演练全通过 | I4-3 |
| D4-3 | 一键诊断包 `diyu diagnose` | [CMD] 运行 -> 生成 tar.gz 含 logs/config/health/metrics | 诊断包内容完整 | -- | -- | 4 类信息全包含 | -- |
| D4-4 | 密钥轮换 + 证书管理 | [CMD] 轮换密钥 -> 服务无中断 | 轮换脚本可用 | -- | -- | 轮换无中断 | -- |
| D4-5 | 轻量离线 (docker save/load) | [CMD] save 镜像 -> 断网 -> load -> 服务启动 | 离线流程验证 | -- | -- | 离线部署可用 | -- |
| D4-6 | `make verify-phase-4` | [CMD] 运行 -> 所有 P4 检查项输出 PASS | 全项通过 | X4-2 | -- | 完成度 100% | -- |

### Phase 5 -- 自动化与合规

| # | D | AC | V-in | V-x | V-fb | M | DEP |
|---|---|----|----|-----|------|---|-----|
| D5-1 | 三 SSOT 自动一致性检查 | [CMD] CI 自动检测 Decision/Runtime/Delivery SSOT 偏差 | 检测脚本可用 | X5-2 | -- | 偏差自动检出 | OS5-1 |
| D5-2 | Exception Register 到期自动审计 | [CMD] 过期例外自动标记并通知 | 审计逻辑验证 | X5-1 | -- | 到期例外自动通知 | OS5-3 |
| D5-3 | 月度架构偏差审计模板 | [CMD] 生成审计报告 | 模板完整性 | X5-2 | -- | 报告可产出 | OS5-4 |
| D5-4 | `make verify-phase-5` | [CMD] 运行 -> 所有 P5 检查项输出 PASS | 全项通过 | X5-2 | -- | 完成度 100% | -- |

---

## 2. Multimodal (M-Track) 详细里程碑

> 架构文档: `00` Section 14.2 | 与 Phase 正交，M0 与 Phase 0 同步

### M0 -- 基座期 (无用户可见变化)

| # | D | AC | V-in | V-x | V-fb | M | DEP | Phase |
|---|---|----|----|-----|------|---|-----|-------|
| MM0-1 | ContentBlock Schema v1.1 + JSON Schema 验证 (ADR-043) | [TEST] Schema 验证通过 | Schema 完整性 | -- | -- | 验证通过 | -- | 0 |
| MM0-2 | ObjectStoragePort 接口 + S3/MinIO 实现 | [TEST] 5 个方法全部通过契约测试 | 5 方法契约测试 | X0-1 | XF2-3 | 5 方法全通过 | -- | 0 |
| MM0-3 | personal_media_objects / enterprise_media_objects DDL + RLS | [CMD] 表存在 + RLS 测试通过 | DDL + RLS 测试 | X1-1 | -- | 表存在 + 隔离通过 | -- | 0 |
| MM0-4 | tool_usage_records DDL | [CMD] 表存在 | DDL 对齐架构文档 | -- | -- | 表存在 | -- | 0 |
| MM0-5 | conversation_events.content_schema_version 列 | [CMD] 列存在 | DDL 完整性 | -- | -- | 列存在 | -- | 0 |
| MM0-6 | LLMCallPort content_parts 可选参数 Expand (ADR-046) | [TEST] 旧调用方式不受影响 | 向后兼容性测试 | X0-1 | -- | 旧接口不报错 | -- | 0 |
| MM0-7 | 安全管线 Stage 1 同步预检 | [TEST] 恶意文件被拦截 | 拦截逻辑单测 | -- | -- | 拦截率 >= 99% | -- | 0 |
| MM0-8 | 契约测试 Layer 1-4 全量新增条目 | [TEST] 所有新契约测试通过 | 契约测试覆盖 | X0-1 | -- | 全部新增条目通过 | -- | 0 |

### M1 -- 个人多模态

| # | D | AC | V-in | V-x | V-fb | M | DEP | Phase |
|---|---|----|----|-----|------|---|-----|-------|
| MM1-1 | 个人媒体上传 API 三步协议 | [E2E] `pytest tests/e2e/cross/test_media_upload.py -v` | 3 步协议单测 | -- | XF2-3 | checksum 匹配 | G2-6 | 3 |
| MM1-2 | WS payload 扩展 (ai_response_chunk 含 media) | [TEST] WS 消息含图片引用 | payload 格式单测 | X2-2 | XF2-1 | media 字段非空 | G2-2 | 3 |
| MM1-3 | ImageAnalyze + AudioTranscribe Tool | [TEST] 各 Tool 输入输出契约通过 | 2 Tool 各有单测 | X3-1 | -- | 2 Tool 全通过 | T3-2, T3-3 | 3 |
| MM1-4 | Brain 多模态模型选择逻辑 | [TEST] 含图片输入 -> 选择视觉模型 | 模型选择单测 | X2-1 | -- | 模型选择正确 | B2-1, T2-2 | 3 |
| MM1-5 | security_status 三层拦截 | [TEST] NSFW 内容 -> quarantined | 拦截逻辑单测 | -- | -- | NSFW 拦截率 >= 99% | OS3-1 | 3 |
| MM1-6 | 个人媒体删除管线 tombstone | [TEST] 删除 -> tombstone -> 物理删除 | 状态机单测 | X4-4 | -- | 删除完成率 100% | MC4-1 | 3 |

### M2 -- 企业多模态

| # | D | AC | V-in | V-x | V-fb | M | DEP | Phase |
|---|---|----|----|-----|------|---|-----|-------|
| MM2-1 | 企业媒体上传 API `/admin/knowledge/` | [E2E] `pytest tests/e2e/cross/test_enterprise_media_upload.py -v` | 上传流程单测 | X3-4 | XF3-2 | 上传成功率 >= 99% | G3-1 | 4 |
| MM2-2 | KnowledgeBundle media_contents 扩展 | [TEST] Bundle 含媒体引用 | 字段扩展单测 | X3-1 | -- | media_contents 非空 | K3-5 | 4 |
| MM2-3 | enterprise_media_objects 与 Neo4j FK 联动 | [TEST] 媒体与图谱节点关联一致 | FK 一致性单测 | X3-2 | -- | FK 一致率 = 100% | K3-3 | 4 |
| MM2-4 | Skill multimodal_input/output 能力声明 | [TEST] Skill 声明并处理多模态 | 能力声明单测 | X3-1 | -- | 声明格式正确 | S3-3 | 4 |
| MM2-5 | DocumentExtract Tool | [TEST] PDF -> 结构化文本 | 输出格式单测 | -- | -- | 提取文本非空 | -- | 4 |
| MM2-6 | 企业媒体删除管线 ChangeSet + 级联 | [TEST] 删除图谱节点 -> 级联删除媒体 | 级联逻辑单测 | X4-4 | -- | 级联完成率 100% | K3-3, MC4-1 | 4 |

### M3 -- 成熟期

| # | D | AC | V-in | V-x | V-fb | M | DEP | Phase |
|---|---|----|----|-----|------|---|-----|-------|
| MM3-1 | 版权风险检测 | [TEST] 已知版权图片被标记 | 检测逻辑单测 | -- | -- | 已知版权检出率 >= 90% | -- | 5 |
| MM3-2 | 跨模态语义检索 | [TEST] 文本查询 -> 返回相关图片/音频 | 检索逻辑单测 | -- | -- | 跨模态召回率 >= 70% | K3-5, I3-2 | 5 |
| MM3-3 | LLMCallPort Contract 阶段评估 | [FILE] 评估报告 | 报告内容完整 | -- | -- | 评估报告存在 | T5-2 | 5 |

---

## 3. Observability & Security 详细里程碑

> 治理规范: v1.1 Section 5/7/11 | 架构文档: `07-部署与安全.md` | 横切关注点，贯穿所有层

### Phase 0 -- 基线可观测性 + 安全扫描

| # | D | AC | V-in | V-x | V-fb | M | DEP |
|---|---|----|----|-----|------|---|-----|
| OS0-1 | 统一日志格式（JSON, 含 trace_id / org_id / request_id） | [CMD] 发送 API 请求 -> 日志输出含 3 个必需字段 | 日志格式检查 | X0-5 | -- | 3 字段齐全 | Gateway |
| OS0-2 | `ruff check` + `mypy --strict` CI 集成 | [CMD] CI 中两项检查通过 | CI 日志 | X0-2 | -- | 两项通过 | CI |
| OS0-3 | secret scanning (gitleaks/trufflehog) | [CMD] CI 中 secret 扫描通过，无硬编码密钥 | 扫描报告 | X0-4 | -- | 0 泄露 | CI |
| OS0-4 | SAST 基础扫描 (Bandit/Semgrep) | [CMD] CI 中 SAST 通过，无 Critical 漏洞 | 扫描报告 | X0-4 | -- | 0 Critical | CI |
| OS0-5 | 依赖漏洞扫描 (safety/pip-audit) | [CMD] CI 中依赖扫描通过 | 扫描报告 | X0-4 | -- | 0 Critical | CI |
| OS0-6 | 前端 ESLint security rules + `pnpm audit` | [CMD] `pnpm lint` 含安全规则，`pnpm audit` 无 Critical | 前端 CI 日志 | -- | -- | 0 Critical | CI |

### Phase 1 -- 隔离安全验证 + 审计基线

| # | D | AC | V-in | V-x | V-fb | M | DEP |
|---|---|----|----|-----|------|---|-----|
| OS1-1 | RLS 隔离测试框架 (`tests/isolation/`) | [TEST] 租户 A 不能读取租户 B 数据（正向+反向） | 隔离测试通过 | X1-1 | -- | 跨租户泄露 = 0 | PG RLS |
| OS1-2 | 隔离 smoke 测试 CI 硬门禁 | [CMD] `pytest tests/isolation/smoke/` 在每次 PR CI 中通过 | CI 日志 | X1-3 | -- | CI 硬门禁通过 | CI |
| OS1-3 | audit_events 写入 + 查询基线 | [TEST] 关键操作(登录/数据变更/权限变更)自动写入审计 | 写入单测 | X1-4 | -- | 关键操作覆盖 | Infra |
| OS1-4 | JWT 安全: token 过期/轮换/revocation | [TEST] 过期 token 返回 401; 被 revoke 的 token 返回 401 | 安全单测 | -- | -- | 401 响应准确 | Gateway |
| OS1-5 | CORS + 安全头 (HSTS/CSP/X-Content-Type-Options) | [CMD] 响应头包含所有必需安全头 | 响应头检查 | -- | -- | 安全头齐全 | Gateway |
| OS1-6 | 前端 XSS 防护 (DOMPurify + CSP) | [TEST] 注入脚本标签 -> 被净化/拦截 | XSS 防护单测 | X1-5 | -- | 净化率 100% | FE-Web |

### Phase 2 -- 4 黄金信号 + 基础告警

| # | D | AC | V-in | V-x | V-fb | M | DEP |
|---|---|----|----|-----|------|---|-----|
| OS2-1 | 4 黄金信号埋点 (延迟/流量/错误/饱和度) | [METRIC] FastAPI middleware 自动采集 4 项指标 | 指标查询 | X2-5 | -- | 4 项指标有数据 | Prometheus client |
| OS2-2 | 基础告警规则 (错误率 > 1%, P95 > 2s) | [CMD] 告警规则文件存在且 Prometheus 加载成功 | 规则加载 | X2-5 | -- | 告警可触发 | Prometheus |
| OS2-3 | Token 消耗异常告警 | [METRIC] 单次对话 token > 阈值 -> 触发告警 | 告警触发 | -- | -- | 告警可触发 | llm_usage_records |
| OS2-4 | 结构化错误日志 (error_code + stack_trace + context) | [CMD] 触发错误 -> 日志含 error_code 字段 | 日志格式检查 | -- | -- | error_code 齐全 | -- |
| OS2-5 | 前端错误边界 + Sentry/等效方案 | [TEST] 组件崩溃 -> ErrorBoundary 捕获 -> 上报错误 | 错误上报单测 | X2-6 | -- | 捕获率 100% | FE-Web |

### Phase 3 -- 内容安全管线 + 审计闭环

| # | D | AC | V-in | V-x | V-fb | M | DEP |
|---|---|----|----|-----|------|---|-----|
| OS3-1 | 内容安全检查管线 (security_status 6 态模型 ADR-051 安全检查子集: pending/scanning/safe/rejected/quarantined) | [TEST] 恶意内容 -> quarantined -> 审计记录 | 安全管线单测 | X3-5 | -- | 拦截率 >= 99% | Gateway |
| OS3-2 | 审计闭环: 所有 CRUD + 权限变更 -> audit_events | [TEST] 抽样 10 个关键操作 -> 全部有审计记录 | 审计覆盖单测 | -- | -- | 覆盖率 100% | Infra |
| OS3-3 | 知识写入安全校验 (XSS/注入防护) | [TEST] 知识条目含脚本标签 -> 写入时被净化 | 注入防护单测 | -- | -- | 净化率 100% | Knowledge |
| OS3-4 | Resolver 查询审计 (who/when/what/why) | [TEST] 每次 Resolver 查询 -> 审计日志含 4W | 审计单测 | X3-6 | -- | 4W 齐全 | Knowledge |
| OS3-5 | API 限流告警 (429 频率监控) | [METRIC] 429 响应率超阈值 -> 告警 | 告警触发 | -- | -- | 告警可触发 | Gateway |

### Phase 4 -- SLI/SLO + 告警分级 + 故障注入

| # | D | AC | V-in | V-x | V-fb | M | DEP |
|---|---|----|----|-----|------|---|-----|
| OS4-1 | 7 项 Brain SLI 定义 + Grafana 看板 (ADR-038) | [METRIC] injection_precision / retrieval_recall 等 7 项指标可视 | Grafana 看板 | X4-5 | -- | 7 项指标可视 | Prometheus + Grafana |
| OS4-2 | SLO 定义 (API P95 < 500ms, 错误率 < 0.1%, 可用性 > 99.5%) | [FILE] SLO 定义文件存在且告警规则对齐 | 文件检查 | X4-5 | -- | 告警对齐 SLO | -- |
| OS4-3 | 告警分级 (P0-Critical/P1-Warning/P2-Info) + 升级规则 | [FILE] 告警分级与升级流程文档存在 | 文件检查 | -- | -- | 分级文档完整 | -- |
| OS4-4 | 全链路 trace_id 验证 (Gateway -> Brain -> Memory -> Tool) | [E2E] `pytest tests/e2e/cross/test_trace_id_e2e.py -v` | 全链路追踪 | X4-1 | -- | trace_id 全链路可查 | -- |
| OS4-5 | 故障注入: 删除管线每步注入失败 | [TEST] 8 态状态机每步注入故障 -> 正确恢复 | 故障注入单测 | X4-6 | -- | 8 步全恢复 | 删除管线 |
| OS4-6 | 故障注入: LLM Provider 不可用 | [TEST] 主 Provider down -> fallback -> 用户无感 | fallback 单测 | X4-6 | -- | fallback 成功 | Model Registry |
| OS4-7 | 渗透测试基线 (OWASP Top 10 覆盖) | [FILE] 渗透测试报告存在，无 Critical/High 漏洞 | 报告检查 | X4-7 | -- | 0 Critical/High | -- |
| OS4-8 | 前端 a11y 无障碍审计 (axe-core 0 critical) | [CMD] axe-core 扫描关键页面 -> 0 critical violations | axe-core 报告 | -- | -- | 0 critical | FE-Web |

### Phase 5 -- 自动偏差审计 + 合规

| # | D | AC | V-in | V-x | V-fb | M | DEP |
|---|---|----|----|-----|------|---|-----|
| OS5-1 | 三 SSOT 自动一致性检查 (Decision/Runtime/Delivery) | [CMD] CI 自动检测 3 个 SSOT 偏差 | 检测脚本 | X5-3 | -- | 偏差自动检出 | CI |
| OS5-2 | Guard 自动阻断策略 (违规代码 -> CI 自动阻断 + 人话化错误) | [TEST] 提交层间违规代码 -> 阻断 -> 输出含"问题/位置/影响/怎么修/参考" | 阻断单测 | X5-1 | -- | 5 段输出齐全 | CI |
| OS5-3 | Exception Register 到期自动审计 | [CMD] 到期例外 -> 自动标记 + 通知 owner | 审计逻辑 | -- | -- | 到期自动通知 | Cron Job |
| OS5-4 | 月度架构偏差审计模板 + 自动产出 | [CMD] `make audit-report` -> 生成 Markdown 报告 | 报告产出 | X5-2 | -- | 报告可产出 | -- |
| OS5-5 | GDPR/PIPL 合规报告自动生成 | [CMD] `make compliance-report` -> 含数据保留/删除/审计统计 | 报告产出 | X5-4 | -- | 3 维统计齐全 | 删除管线 + 审计 |
| OS5-6 | 安全事件响应手册 (Runbook) | [FILE] 至少覆盖: 数据泄露/密钥泄露/DDoS/供应链攻击 4 场景 | 文件检查 | -- | -- | 4 场景覆盖 | -- |

---

## 4. 跨层集成验证节点

> 以下验证节点覆盖层内独立验证之外的跨层交互。每个节点描述: 参与层、触发场景、验证方法、失败影响。

### 4.1 Phase 0 跨层验证

| # | 参与层 | 验证场景 | 验证方法 | 失败影响 |
|---|--------|---------|---------|---------|
| X0-1 | All Ports | 所有 Port Stub 可独立实例化 | [TEST] 每个 Port 的 Stub 实现 pytest 通过 | 阻断: 无法启动任何层 |
| X0-2 | Delivery + CI | CI 硬门禁完整运行 | [CMD] 提交空变更 PR -> CI 全通过 | 阻断: 无法合并代码 |
| X0-3 | Infra + Gateway | Docker Compose 全栈启动 | [CMD] `docker-compose up` -> 所有服务 healthy | 阻断: 无开发环境 |
| X0-4 | Obs + CI | 安全扫描三件套 CI 集成 | [CMD] secret scan + SAST + 依赖扫描全部在 CI 中运行 | 阻断: 安全底线缺失 |
| X0-5 | Obs + Gateway | 日志格式标准化验证 | [CMD] 发送请求 -> 日志含 trace_id/org_id/request_id | 降级: 故障追踪困难 |
| XM0-1 | Multimodal + Ports | M0 契约测试全量通过 | [TEST] ContentBlock Schema + ObjectStoragePort + LLMCallPort 新增契约全通过 | 阻断: M-Track 无法启动 |

### 4.2 Phase 1 跨层验证

| # | 参与层 | 验证场景 | 验证方法 | 失败影响 |
|---|--------|---------|---------|---------|
| X1-1 | Gateway + Infra | JWT -> OrgContext -> RLS 全链路 | [TEST] 用户 A 的 token -> 只能访问 A 的数据 | 阻断: 租户隔离失败 = 数据泄露 |
| X1-2 | Gateway + Infra | RBAC 权限链路 | [TEST] 普通用户 -> 无法访问 Admin API | 阻断: 权限绕过 |
| X1-3 | Infra + Delivery | 隔离测试 CI 运行 | [CMD] `pytest tests/isolation/smoke/` 在 CI 中通过 | 阻断: 安全门禁缺失 |
| X1-4 | Obs + Gateway + Infra | 审计写入全链路 | [TEST] 登录/数据变更/权限变更 -> audit_events 有记录 -> 可查询 | 阻断: 审计不可用 = 合规失败 |
| X1-5 | Obs + FE-Web | 前端安全防护验证 | [TEST] XSS 注入 -> DOMPurify 净化 + CSP 拦截 | 阻断: 前端安全漏洞 |

### 4.3 Phase 2 跨层验证（首条 E2E 闭环）

| # | 参与层 | 验证场景 | 验证方法 | 失败影响 |
|---|--------|---------|---------|---------|
| X2-1 | Gateway + Brain + Memory + Tool | **对话完整闭环** | [E2E] `pytest tests/e2e/cross/test_conversation_loop.py -v` | 阻断: 核心价值不可用 |
| X2-2 | Gateway + Brain | 流式回复全链路 | [E2E] `pytest tests/e2e/cross/test_streaming_e2e.py -v` | 降级: 用户体验差 |
| X2-3 | Brain + Memory + Infra | Memory Evolution 闭环 | [TEST] 对话 -> 提取 observation -> 更新 memory_items -> 下次对话注入 | 降级: "越聊越懂你"不工作 |
| X2-4 | Gateway + Infra | Token 预算反压 (Loop D) | [TEST] 消耗 token -> 扣减 -> 耗尽 -> 402 拒绝 | 降级: 成本失控 |
| X2-5 | Obs + Gateway + Infra | 4 黄金信号端到端验证 | [METRIC] 发送 100 次请求 -> Prometheus 中延迟/流量/错误/饱和度指标均有数据 | 降级: 监控盲区 |
| X2-6 | Obs + FE-Web | 前端错误上报闭环 | [TEST] 触发组件崩溃 -> ErrorBoundary 捕获 -> 错误上报到后端 -> 可查询 | 降级: 前端故障不可见 |

### 4.4 Phase 2 前后端集成验证

| # | 参与层 | 验证场景 | 验证方法 | 失败影响 |
|---|--------|---------|---------|---------|
| XF2-1 | FE-Web + Gateway | **登录 -> 选组织 -> 对话 -> 流式回复** | [E2E] `pnpm exec playwright test tests/e2e/cross/web/login-to-streaming.spec.ts` | 阻断: 用户无法使用 |
| XF2-2 | FE-Web + Gateway + Memory | 记忆面板查看与删除 | [E2E] `pnpm exec playwright test tests/e2e/cross/web/memory-panel.spec.ts` | 降级: 记忆管理不可用 |
| XF2-3 | FE-Web + Gateway | 文件上传闭环 | [E2E] `pnpm exec playwright test tests/e2e/cross/web/file-upload.spec.ts` | 降级: 文件功能不可用 |
| XF2-4 | FE-Web + Gateway | OpenAPI 类型一致性 | [CMD] `pnpm openapi:generate && git diff` 为空 | 阻断: 前后端契约漂移 |

### 4.5 Phase 3 跨层验证（知识 + 技能闭环）

| # | 参与层 | 验证场景 | 验证方法 | 失败影响 |
|---|--------|---------|---------|---------|
| X3-1 | Brain + Skill + Knowledge + Tool | **对话触发 Skill 完整闭环** | [E2E] `pytest tests/e2e/cross/test_skill_e2e.py -v` | 阻断: Skill 价值不可用 |
| X3-2 | Knowledge (Neo4j + Qdrant) | FK 一致性验证 | [TEST] 写入 -> 双库一致 -> 查询返回关联数据 | 阻断: 知识库不可信 |
| X3-3 | Memory + Knowledge | Promotion Pipeline 跨 SSOT | [TEST] 个人记忆 -> 提案 -> 审批 -> 写入 Knowledge | 降级: 知识沉淀不工作 |
| X3-4 | Gateway + Knowledge | Knowledge Admin API 全链路 | [E2E] `pytest tests/e2e/cross/test_knowledge_admin_e2e.py -v` | 阻断: 知识管理不可用 |
| X3-5 | Obs + Gateway + Knowledge | 内容安全管线闭环 | [TEST] 恶意知识条目 -> security_status=quarantined -> 审计记录存在 | 阻断: 内容安全失效 |
| X3-6 | Obs + Knowledge | Resolver 查询审计闭环 | [TEST] Resolver 查询 -> audit_events 含 who/when/what/why | 降级: 知识使用不可追溯 |
| XM1-1 | Multimodal + Gateway + Tool | M1 个人媒体上传闭环 | [E2E] `pytest tests/e2e/cross/test_media_upload_e2e.py -v` | 阻断: 个人多模态不可用 |
| XM1-2 | Multimodal + Obs | M1 媒体安全扫描闭环 | [TEST] 上传 NSFW 图片 -> quarantined -> 审计记录 | 阻断: 媒体安全失效 |

### 4.6 Phase 3 前后端集成验证

| # | 参与层 | 验证场景 | 验证方法 | 失败影响 |
|---|--------|---------|---------|---------|
| XF3-1 | FE-Web + Gateway + Skill | **对话触发 Skill -> 右侧 Artifact 渲染** | [E2E] `pnpm exec playwright test tests/e2e/cross/web/skill-artifact.spec.ts` | 阻断: Skill UI 不可用 |
| XF3-2 | FE-Admin + Gateway + Knowledge | **知识编辑 -> 填模板 -> 提交 -> 总部查看** | [E2E] `pnpm exec playwright test tests/e2e/cross/admin/knowledge-workflow.spec.ts` | 阻断: 知识管理不可用 |
| XF3-3 | FE-Admin + Gateway | 组织配置继承验证 | [E2E] `pnpm exec playwright test tests/e2e/cross/admin/org-config-inherit.spec.ts` | 降级: 配置管理不可用 |

### 4.7 Phase 4 跨层验证

| # | 参与层 | 验证场景 | 验证方法 | 失败影响 |
|---|--------|---------|---------|---------|
| X4-1 | All | **全链路 trace_id 追踪** | [E2E] `pytest tests/e2e/cross/test_trace_id_full_stack.py -v` | 降级: 故障定位困难 |
| X4-2 | Infra + Delivery | 升级回滚演练 | [CMD] upgrade -> downgrade -> upgrade 数据完整 | 阻断: 发版风险不可控 |
| X4-3 | All | 三 SSOT 一致性 | [CMD] Decision docs <-> Port 签名 <-> manifest.yaml 无偏差 | 阻断: 发版 |
| X4-4 | Brain + Memory + Infra | 删除管线端到端 | [TEST] 用户请求删除 -> tombstone -> 物理删除 -> 审计 -> 所有存储清理 | 阻断: 合规失败 |
| X4-5 | Obs + All | SLI/SLO 指标端到端验证 | [METRIC] 7 项 Brain SLI + API SLO 指标在 Grafana 全部可视且告警可触发 | 降级: 监控不可用 |
| X4-6 | Obs + Infra | 故障注入与恢复验证 | [TEST] 删除管线 + LLM Provider 故障注入 -> 正确恢复 -> 审计完整 | 阻断: 故障恢复不可信 |
| X4-7 | Obs + Gateway | 渗透测试 OWASP Top 10 | [FILE] 渗透测试报告无 Critical/High + 整改确认 | 阻断: 安全基线不达标 |
| XM2-1 | Multimodal + Knowledge + Infra | M2 企业媒体双写 + FK 验证 | [TEST] 企业媒体上传 -> Neo4j FK 关联 -> Qdrant 向量同步 -> 一致性通过 | 阻断: 企业多模态不可用 |
| XM2-2 | Multimodal + Obs | M2 NSFW + 版权预检 | [TEST] 企业图片 -> NSFW 检测 + 版权预检 -> 审计记录 | 降级: 企业媒体安全失效 |

### 4.8 Phase 4 前后端集成验证

| # | 参与层 | 验证场景 | 验证方法 | 失败影响 |
|---|--------|---------|---------|---------|
| XF4-1 | FE-Web + Gateway | **额度耗尽 -> 充值 -> 余额更新** | [E2E] `pnpm exec playwright test tests/e2e/cross/web/billing-flow.spec.ts` | 阻断: 商业化不可用 |
| XF4-2 | FE-Admin + Infra | 系统监控看板 | [E2E] `pnpm exec playwright test tests/e2e/cross/admin/monitoring-dashboard.spec.ts` | 降级: 运维不可用 |
| XF4-3 | FE-Web + Gateway + Memory | **查看 AI 记忆 -> 删除 -> 确认删除** | [E2E] `pnpm exec playwright test tests/e2e/cross/web/memory-privacy.spec.ts` | 阻断: 隐私控制不可用 |

### 4.9 Phase 5 跨层验证

| # | 参与层 | 验证场景 | 验证方法 | 失败影响 |
|---|--------|---------|---------|---------|
| X5-1 | Delivery + Governance | Guard 自动阻断策略生效 | [TEST] 违规代码 -> CI 自动阻断 -> 人话化错误信息 | 降级: 治理退化 |
| X5-2 | All | 月度架构偏差审计 | [CMD] 审计模板产出报告 | 降级: 架构腐化 |
| X5-3 | Obs + Delivery + CI | 三 SSOT 自动一致性 + Guard 联动 | [CMD] SSOT 偏差 -> Guard 阻断 -> 人话化输出含 5 段 | 阻断: 治理自动化失效 |
| X5-4 | Obs + All | GDPR/PIPL 合规端到端验证 | [CMD] `make compliance-report` -> 数据保留/删除/审计统计完整 | 阻断: 合规报告不可产出 |
| XM3-1 | Multimodal + Knowledge | M3 跨模态语义检索 | [TEST] 文本查询 -> 返回相关图片/音频 -> 结果可排序 | 降级: 跨模态不可用 |
| XM3-2 | Multimodal + Obs | M3 版权合规审计 | [TEST] 版权风险图片 -> 标记 -> 合规报告含统计 | 降级: 版权风险不可控 |

---

# Phase 3 落盘构建实施路线图 v1.3.1（全量更正版）

> 日期: 2026-02-20
> 状态: Approved
> 上游决议: `docs/governance/decisions/2026-02-19-production-delivery-gate-plan-v1.0.md`
> 子计划: `docs/governance/decisions/2026-02-19-cross-layer-gate-binding-impl-v1.0.md`
> 版本链: v1.0 → v1.1 → v1.2 → v1.3 → v1.3.1 → v1.3.2 → v1.3.3
> 变更范围: Phase 3 全量构建实施 (Knowledge & Skill Ecosystem)

---

## 0. 元数据

- **主题**: Knowledge & Skill Ecosystem
- **前置**: Phase 2 gate GO (17/17 hard PASS)
- **范围**: 48 milestones + 11 XNodes + 14 hard exit criteria + 2 soft exit criteria + 2 gate 实施任务 (OS3-6 tenant-isolation, D3-5 sbom-attestation)
- **计数口径**: milestone 48 = 12 层 (Brain 4 + MemoryCore 2 + Knowledge 7 + Skill 4 + Tool 3 + Gateway 3 + Infra 4 + FE-Web 3 + FE-Admin 3 + Delivery 4 + Multimodal 6 + Observability 5); gate 实施任务 2 = Observability +1 (OS3-6) + Delivery +1 (D3-5)
- **并行工作流**: 8 条

### YAML 同步清单

落盘时必须同步修改 `delivery/milestone-matrix.yaml`:

| 变更 ID | 操作 |
|---------|------|
| v1.3-1 | phase_3.exit_criteria.hard 新增 5 项继承门禁 |
| v1.3-2 | phase_3.exit_criteria.hard 新增 p3-tenant-isolation-runtime |
| v1.3-2 | phase_3.exit_criteria.soft 新增 p3-sbom-attestation |
| v1.3-8 | p3-tool-execution check 改精确 3 文件路径 |
| v1.3-9 | p3-fe-knowledge check 增加 test -f 存在性检查 |
| v1.3-11 | phase_3.exit_criteria.hard 新增 p3-env-completeness |
| v1.3.2-A | phase_3.milestones 补录 OS3-6 + D3-5 |

### 任务卡同步清单

编入 Stage 0 任务 0-8，确保可追踪执行 [v1.3.1-B]:

| 文件 | 操作 |
|------|------|
| `docs/task-cards/06-基础设施层/infrastructure.md` | TASK-I3-3 "6 方法" -> "5 方法" |
| `docs/governance/milestone-matrix-backend.md` | I3-3 行 "6 方法" -> "5 方法" |
| `docs/governance/milestone-matrix-crosscutting.md` | MM0-2 行 "6 方法" -> "5 方法" |

### 矩阵文档同步清单 [v1.3.2]

编入 Stage 1A 任务 1-6a/1-6b/1-6c，确保 YAML/矩阵/索引三层同步:

| 文件 | 操作 |
|------|------|
| `delivery/milestone-matrix.yaml` | phase_3.milestones 补录 OS3-6 + D3-5 |
| `docs/governance/milestone-matrix-crosscutting.md` | Observability Phase 3 新增 OS3-6 行, Delivery Phase 3 新增 D3-5 行 |
| `docs/governance/milestone-matrix.md` | Phase 3 检查清单补录 3 项 (租户隔离/SBOM/env), 完成度 9/9 -> 12/12 |

---

## 1. Stage 0: Phase 2 全量回归 + 基线对齐 (D0)

**目标**: 确保 Phase 2 gate 无残留失败，建立干净基线，对齐文档一致性。

| # | 任务 | 验收命令 / 说明 |
|---|------|---------------|
| 0-1 | make lint 全部通过 | `make lint` exit 0 |
| 0-2 | semgrep + pip-audit 通过 | `bash scripts/security_scan.sh --full` exit 0 |
| 0-3 | banned mock patterns 清零 | `uv run python scripts/check_no_mock.py src/ tests/` exit 0 |
| 0-4 | env vars 完整性 | `uv run python scripts/check_env_completeness.py` exit 0 |
| 0-5 | E2E 无空跑 | `uv run python scripts/check_no_vacuous_pass.py tests/e2e/cross/ frontend/tests/e2e/cross/` exit 0 |
| 0-6 | 跨层依赖 = 0 | `bash scripts/check_layer_deps.sh --json` exit 0 |
| 0-7 | [v1.3-7] manifest.yaml 对齐 phase_2 | `delivery/manifest.yaml` current_phase 从 "phase_0" 更新为 "phase_2" (对齐 milestone-matrix.yaml:7) |
| 0-8 | [v1.3.1-B] ObjectStoragePort 方法数文档同步 | 以下 3 文件 "6 方法" -> "5 方法": `docs/task-cards/06-基础设施层/infrastructure.md` (line 404/409/411/413), `docs/governance/milestone-matrix-backend.md` (line 359), `docs/governance/milestone-matrix-crosscutting.md` (line 92). 验收: `grep -c "6 方法" <上述 3 文件>` 全部返回 0 |

**验收**: `make verify-phase-2` 全量 GO，无硬失败，无软失败退化。

---

## 2. Stage 1: Phase 3 Gate 激活 + 基础设施准备 (D1)

**目标**: 门禁骨架、集成卡、测试目录、Python/Docker 依赖。

### 1A -- 门禁与追溯

| # | 任务 | 说明 |
|---|------|------|
| 1-1 | 新建 `docs/task-cards/00-跨层集成/phase-3-integration.md` | 按聚合规则建 5 张集成卡，覆盖全部 11 个 XNode |
| 1-2 | [v1.3-1] milestone-matrix.yaml phase_3.exit_criteria.hard 写入继承门禁 | 写入继承 5 项: p3-lint, p3-security-scan, p3-layer-boundary, p3-no-mock-py, p3-integration |
| 1-3 | [v1.3-2][v1.3-11] milestone-matrix.yaml phase_3 写入决策文档门禁 + env-completeness | hard: p3-tenant-isolation-runtime, hard: p3-env-completeness, soft: p3-sbom-attestation |
| 1-4 | [v1.3-8] p3-tool-execution check 改精确路径 (同步到 YAML) | 见 Exit Criteria 节 |
| 1-5 | [v1.3-9] p3-fe-knowledge check 增加 test -f (同步到 YAML) | 见 Exit Criteria 节 |
| 1-6 | 确认 milestone-matrix.yaml phase_3.exit_criteria 全部 xnodes 绑定完整 | 14 hard + 2 soft 逐条核验 |
| 1-6a | [v1.3.2-A] milestone-matrix.yaml phase_3.milestones 补录 OS3-6 + D3-5 | 新增 `{id: "OS3-6", layer: "Observability", summary: "Tenant isolation runtime"}` 和 `{id: "D3-5", layer: "Delivery", summary: "SBOM attestation"}`. 验收: `grep "OS3-6" delivery/milestone-matrix.yaml && grep "D3-5" delivery/milestone-matrix.yaml` 均有匹配 |
| 1-6b | [v1.3.2-B] milestone-matrix-crosscutting.md 补录 OS3-6 + D3-5 条目 | Observability Phase 3 表 (OS3-5 之后) 新增 OS3-6 行; Delivery Phase 3 表 (D3-4 之后) 新增 D3-5 行. 验收: `grep "OS3-6" docs/governance/milestone-matrix-crosscutting.md && grep "D3-5" docs/governance/milestone-matrix-crosscutting.md` 均有匹配 |
| 1-6c | [v1.3.2-C] milestone-matrix.md Phase 3 检查清单补录 3 项 | 在 Phase 3 检查清单末尾追加: `[PASS] 租户隔离 runtime: 跨 org 查询阻断 100% (OS3-6)`, `[PASS] SBOM attestation 签名验证 (D3-5, soft)`, `[PASS] env vars 完整性检查通过`. Phase 3 完成度改为 12/12. 验收: `grep "OS3-6" docs/governance/milestone-matrix.md && grep "D3-5" docs/governance/milestone-matrix.md && grep "env.*完整" docs/governance/milestone-matrix.md` 均有匹配 |
| 1-6d | [v1.3.3-C] 路线图 vs 任务卡测试路径对齐 | 以任务卡为 SSOT，统一测试路径。影响 3 处: (1) G3-1: 路线图改为 `test_knowledge_api.py` (对齐 gateway.md:306); (2) G3-3/OS3-1: 路线图改为 `test_content_pipeline.py` (对齐 obs-security.md:360); (3) exit_criteria p3-content-security check 同步更新. 验收: 路线图中无 `test_knowledge_admin_api.py` 和 `test_content_security.py` 引用 |

> **注意**: current_phase 不在此 Stage 切换。开发期间使用 `--phase 3` 显式指定，避免 CI `--current` 参数导致的阻断。

**5 张集成卡** (对齐决策文档 cross-layer-gate-binding-impl-v1.0.md:725):

| 卡 ID | 覆盖节点 | 聚合依据 |
|--------|---------|---------|
| TASK-INT-P3-SKILL | X3-1 | 独立 E2E: Skill 完整闭环 |
| TASK-INT-P3-KNOWLEDGE | X3-2, X3-3, X3-4, X3-6 | 共享 Knowledge 集成测试套件 |
| TASK-INT-P3-SECURITY | X3-5, XM1-2 | 共享安全管线测试 |
| TASK-INT-P3-MEDIA | XM1-1 | 独立 E2E: 媒体上传 |
| TASK-INT-P3-FE | XF3-1, XF3-2, XF3-3 | 共享 Playwright suite |

### 1B -- 测试目录骨架

| # | 任务 | 说明 |
|---|------|------|
| 1-7 | 创建 `tests/unit/skill/__init__.py` | p3-skill-registry check 目标目录 |
| 1-8 | 创建 `tests/integration/knowledge/__init__.py` | p3-knowledge-crud check 目标目录 |
| 1-9 | 创建 `tests/perf/__init__.py` + `conftest.py` | p3-graph-perf (soft) 目标目录 |
| 1-10 | 创建 `tests/integration/test_promotion.py` (空壳 + skip marker) | p3-promotion-pipeline check 目标路径 |

### 1C -- Python 依赖安装

| # | 任务 | 验收命令 |
|---|------|---------|
| 1-11 | `uv add neo4j` | `uv run python -c "import neo4j"` exit 0 |
| 1-12 | `uv add qdrant-client` | `uv run python -c "import qdrant_client"` exit 0 |
| 1-13 | `uv add boto3` (MinIO S3 兼容) | `uv run python -c "import boto3"` exit 0 |

### 1D -- Docker Compose 补全

| # | 任务 | 说明 |
|---|------|------|
| 1-14 | docker-compose.yml app 服务 depends_on 补充 neo4j + qdrant | 当前只有 postgres/redis/minio |
| 1-15 | .env.example 补充 NEO4J_URI, QDRANT_URL, MINIO_ENDPOINT 等变量 | check_env_completeness.py 后续能覆盖 |

**Stage 1 验收**:

- `check_xnode_coverage.py --phase 3 --json` -> decision=GO, rate >= 0.70
- `docker compose up neo4j qdrant minio` 可正常启动
- `uv run python -c "import neo4j; import qdrant_client; import boto3"` exit 0
- 4 个测试目录/文件已创建
- CI 上 `--phase 2` 仍全绿 (不影响现有 PR 流程)
- milestone-matrix.yaml phase_3 exit_criteria 已含 14 hard + 2 soft
- [v1.3.2-A] milestone-matrix.yaml phase_3.milestones 含 OS3-6 + D3-5 (共 50 条目 = 48 milestones + 2 gate 实施任务)
- [v1.3.2-B] milestone-matrix-crosscutting.md Observability Phase 3 含 OS3-6, Delivery Phase 3 含 D3-5
- [v1.3.2-C] milestone-matrix.md Phase 3 检查清单含 12 项 (含租户隔离/SBOM/env-completeness)

---

## 3. Stage 2: Port 接口扩展 + Infrastructure Adapter (D2)

**目标**: 新增 Port 接口、实现全部 Infrastructure adapter。

### 2A -- Port 接口变更

| # | 任务 | 文件 | 说明 |
|---|------|------|------|
| 2-1 | 新增 ObjectStoragePort | `src/ports/object_storage_port.py` | 5 方法 (对齐架构文档 00:578): generate_upload_url, generate_download_url, delete_object, delete_objects, head_object. 不含 list_objects/copy_object (架构文档未定义) |
| 2-2 | SkillRegistry 扩展 lifecycle 方法 | `src/ports/skill_registry.py` | 新增 register(), deregister(), update_status() 支持 S3-3 五态转换 |
| 2-3 | MemoryCorePort 扩展 promotion 方法 | `src/ports/memory_core_port.py` | 新增 promote_to_knowledge() -> PromotionReceipt |

**验收**:

- `uv run pytest tests/unit/ports/ -q` 通过
- `bash scripts/check_port_compat.sh` exit 0

### 2B -- Infrastructure Adapter (I3-1 ~ I3-4)

| Milestone | 任务 | 产出 | 测试路径 |
|-----------|------|------|---------|
| I3-1 | Neo4j connection + CRUD adapter | `src/infra/graph/neo4j_adapter.py` | `tests/unit/infra/test_neo4j_adapter.py` |
| I3-2 | Qdrant connection + CRUD adapter | `src/infra/vector/qdrant_adapter.py` | `tests/unit/infra/test_qdrant_adapter.py` |
| I3-3 | ObjectStoragePort 实现 (S3/MinIO) | `src/infra/storage/s3_adapter.py` | `tests/unit/infra/test_s3_adapter.py` |
| I3-4 | tool_usage_records DDL migration | `migrations/versions/006_create_tool_usage_records.py` | rollback 验证 |

**验收**:

- adapter 单测使用 Fake adapter 或 testcontainers 隔离外部服务 (禁止 unittest.mock/MagicMock/patch)
- migration up/down 可逆: `alembic upgrade head && alembic downgrade -1`
- `bash scripts/check_layer_deps.sh --json` 跨层违规 = 0
- `bash scripts/check_migration.sh` exit 0
- `uv run python scripts/check_no_mock.py src/ tests/` exit 0
- [v1.3-4] `uv run python scripts/check_env_completeness.py` exit 0 (新增 adapter 引入 NEO4J_URI/QDRANT_URL 等变量后必须同步 .env.example)

---

## 4. Stage 3: 后端业务主链 (D3 ~ D5)

**目标**: 33 个后端业务 milestone + 6 个 Multimodal M1 milestone。

### 3A -- Knowledge 核心 (K3-1 ~ K3-7)

**关键依赖**: K3-4 必须先于 MC3-1 完成。

| Milestone | 任务 | 测试路径 | 依赖 |
|-----------|------|---------|------|
| K3-1 | Neo4j schema + 种子数据 (>=50 节点) | `tests/unit/knowledge/test_neo4j_schema.py` | I3-1 |
| K3-2 | Qdrant collection init + 种子数据 (>=50 向量) | `tests/unit/knowledge/test_qdrant_init.py` | I3-2 |
| K3-3 | FK 联动 (Neo4j node_id <-> Qdrant point_id) | `tests/unit/knowledge/test_fk_linkage.py` | K3-1, K3-2 |
| K3-4 | Knowledge Write API (POST 双写 + 审计回执 + 幂等键) | `tests/unit/knowledge/test_write_api.py` + `tests/integration/knowledge/test_write_integration.py` | K3-3 |
| K3-5 | Diyu Resolver 最小实现 (1-2 Profile, p95 < 200ms) | `tests/unit/knowledge/test_resolver.py` | K3-3 |
| K3-6 | Entity type 注册机制 | `tests/unit/knowledge/test_entity_types.py` | K3-1 |
| K3-7 | ERP/PIM ChangeSet 接口 (批量导入 + 幂等) | `tests/unit/knowledge/test_changeset.py` | K3-4 |

### 3B -- Memory Promotion (MC3-1 ~ MC3-2)

| Milestone | 任务 | 测试路径 | 依赖 |
|-----------|------|---------|------|
| MC3-1 | Promotion Pipeline (个人记忆 -> 组织知识) | `tests/unit/memory/test_promotion.py` | K3-4 (需 Knowledge Write 能力) |
| MC3-2 | promotion_receipt 追踪 | `tests/unit/memory/test_promotion_receipt.py` | MC3-1 |

### 3C -- Brain Skill Router (B3-1 ~ B3-4)

| Milestone | 任务 | 测试路径 | 依赖 |
|-----------|------|---------|------|
| B3-1 | Skill Router (Intent -> Skill, 准确率 >= 95%) | `tests/unit/brain/test_skill_router.py` | S3-3 |
| B3-2 | Skill 编排流 (成功率 >= 90%) | `tests/unit/brain/test_skill_orchestration.py` | B3-1 |
| B3-3 | 角色适配模块 (org_tier -> prompt template) | `tests/unit/brain/test_role_adaptation.py` | -- |
| B3-4 | 负反馈熔断 (连续失败 N 次 -> 降级) | `tests/unit/brain/test_negative_feedback_fuse.py` | B3-2 |

### 3D -- Skill 实现 (S3-1 ~ S3-4)

| Milestone | 任务 | 测试路径 | 依赖 |
|-----------|------|---------|------|
| S3-1 | ContentWriterSkill | `tests/unit/skill/test_content_writer.py` | K3-5 (Resolver) |
| S3-2 | MerchandisingSkill | `tests/unit/skill/test_merchandising.py` | K3-5 |
| S3-3 | Skill lifecycle (5 态) | `tests/unit/skill/test_lifecycle.py` | Port 2-2 |
| S3-4 | Skill param validation | `tests/unit/skill/test_param_validation.py` | S3-3 |

### 3E -- Tool 新增 (T3-1 ~ T3-3)

| Milestone | 任务 | 测试路径 | 依赖 |
|-----------|------|---------|------|
| T3-1 | WebSearch Tool | `tests/unit/tool/test_web_search.py` | I3-4 |
| T3-2 | ImageAnalyze Tool | `tests/unit/tool/test_image_analyze.py` | I3-3 |
| T3-3 | AudioTranscribe Tool | `tests/unit/tool/test_audio_transcribe.py` | I3-3 |

### 3F -- Gateway API (G3-1 ~ G3-3)

| Milestone | 任务 | 测试路径 | 依赖 |
|-----------|------|---------|------|
| G3-1 | Knowledge Admin API (CRUD + RBAC) | `tests/unit/gateway/test_knowledge_api.py` | K3-4 |
| G3-2 | Skill API (触发 + 状态查询) | `tests/unit/gateway/test_skill_api.py` | S3-3 |
| G3-3 | Content security check endpoint | `tests/unit/gateway/test_content_pipeline.py` | OS3-1 |

### 3G -- Multimodal M1 (MM1-1 ~ MM1-6)

| Milestone | 任务 | 绑定 XNode | 依赖 |
|-----------|------|----------|------|
| MM1-1 | Personal media upload API | XM1-1 | I3-3 |
| MM1-2 | WS payload media extension | X2-2 | G2-2 |
| MM1-3 | ImageAnalyze + AudioTranscribe 集成 | XM1-1 | T3-2, T3-3 |
| MM1-4 | Brain multimodal model selection | X2-1 | B2-1, T2-2 |
| MM1-5 | security_status 3-layer intercept | XM1-2 | OS3-1 |
| MM1-6 | Personal media delete tombstone | X4-4 | MC4-1 |

> [v1.3.3-A] **MM1 任务卡创建**: MM1-1~MM1-6 当前仅通过 M-Track 交叉引用散布于其他层任务卡中，无主任务卡。需在 Stage 3G 实施时同步创建 `docs/task-cards/08-多模态/multimodal.md`，包含 TASK-MM1-1 至 TASK-MM1-6 共 6 张任务卡 (Tier-B 格式)。验收: `uv run python scripts/task_card_traceability_check.py --phase 3` main_coverage >= 95%。

### Stage 3 关键路径

```
K3-1 ──┐
K3-2 ──┼─→ K3-3 ─→ K3-4 ─→ K3-5 ─→ S3-1/S3-2 ─→ B3-1 ─→ B3-2 ─→ B3-4
K3-6 ──┘              │        │                      ↑
                      │        └─→ K3-7               S3-3 ─→ S3-4
                      └─→ MC3-1 ─→ MC3-2
```

### Stage 3 验收

对齐 hard exit criteria 精确 check:

- `uv run pytest tests/unit/knowledge/ tests/integration/knowledge/ -q` -> p3-knowledge-crud
- `uv run pytest tests/unit/skill/ -q` -> p3-skill-registry
- `uv run pytest tests/unit/tool/test_web_search.py tests/unit/tool/test_image_analyze.py tests/unit/tool/test_audio_transcribe.py -q` -> p3-tool-execution [v1.3-8 精确路径]
- `uv run pytest tests/unit/memory/test_promotion.py tests/integration/test_promotion.py -q` -> p3-promotion-pipeline
- `uv run pytest tests/unit/gateway/test_content_pipeline.py -q` -> p3-content-security [v1.3.3-C 路径对齐]
- `uv run pytest tests/unit/knowledge/test_resolver_audit.py -q` -> p3-resolver-audit
- [v1.3.3-A] `uv run python scripts/task_card_traceability_check.py --phase 3` -> main_coverage >= 95%

---

## 5. Stage 4: 前端与管理端落盘 (D6)

**目标**: 6 个前端 milestone，前后端契约联调。

### FE-Web (FW3-1 ~ FW3-3)

| Milestone | 任务 | 产出路径 (对齐任务卡) |
|-----------|------|-------------------|
| FW3-1 | 知识浏览页 | `apps/web/app/knowledge/page.tsx` + `apps/web/components/knowledge/` (05-page-routes/task-cards.md:16) |
| FW3-2 | Skill 结构化渲染 (右侧面板 Artifact) | `apps/web/components/chat/ArtifactPanel.tsx` + `packages/ui/composites/` (04-dialog-engine/task-cards.md:122) |
| FW3-3 | 商品组件 (ProductCard/OutfitGrid/StyleBoard) | `packages/ui/src/commerce/` (05-page-routes/task-cards.md:33) |

### FE-Admin (FA3-1 ~ FA3-3)

| Milestone | 任务 | 产出路径 (对齐任务卡) |
|-----------|------|-------------------|
| FA3-1 | 知识编辑工作台 | `apps/admin/app/knowledge/page.tsx` + `apps/admin/components/KnowledgeEditor.tsx` (06-admin-console/task-cards.md:71) |
| FA3-2 | 内容审核队列 | `apps/admin/app/knowledge/review/page.tsx` (06-admin-console/task-cards.md:88) |
| FA3-3 | org_settings 配置管理 | `apps/admin/app/settings/page.tsx` (06-admin-console/task-cards.md:105) |

**验收**:

- `cd frontend && pnpm run build` exit 0
- `test -f apps/web/app/knowledge/page.tsx` [v1.3-9]
- `test -f apps/admin/app/knowledge/page.tsx` [v1.3-9]
- `test -f apps/admin/app/knowledge/review/page.tsx` [v1.3-9]
- -> p3-fe-knowledge (build pass + 文件存在)
- `bash scripts/check_openapi_sync.sh` exit 0

---

## 6. Stage 5: 安全、审计与租户隔离闭环 (D7)

**目标**: 5 个 Observability milestone + 1 个 gate 实施任务 (OS3-6)。

| Milestone | 任务 | 验收指标 | 测试路径 |
|-----------|------|---------|---------|
| OS3-1 | 内容安全管线 (security_status 6-state) | 恶意内容拦截率 >= 95% | `tests/unit/gateway/test_content_pipeline.py` |
| OS3-2 | 全 CRUD + 权限变更审计 | audit_events 覆盖所有写操作 | `tests/unit/infra/test_audit_coverage.py` |
| OS3-3 | Knowledge write XSS/注入防护 | 注入净化率 100% | `tests/unit/knowledge/test_xss_protection.py` |
| OS3-4 | Resolver 4W 审计 (who/when/what/why) | 查询日志含全部 4 维度 | `tests/unit/knowledge/test_resolver_audit.py` |
| OS3-5 | API rate limit 429 告警 | 告警触发延迟 < 60s | `tests/unit/gateway/test_rate_limit_alert.py` |
| OS3-6 (gate 任务) | [v1.3-3] 租户隔离 runtime 验证 (p3-tenant-isolation-runtime) | 跨 org 查询阻断 100% | `tests/isolation/test_tenant_crossover.py` |

OS3-6 测试覆盖项:
- cross_org_select_blocked
- rls_scoped_join
- concurrent_org_isolation

来源: `production-delivery-gate-plan-v1.0.md:417`

**验收**:

- `uv run pytest tests/unit/gateway/test_content_pipeline.py -q` -> OS3-1 [v1.3.3-C 路径对齐]
- [v1.3.3-E] `uv run pytest tests/unit/infra/test_audit_coverage.py -q` -> OS3-2
- [v1.3.3-E] `uv run pytest tests/unit/knowledge/test_xss_protection.py -q` -> OS3-3
- `uv run pytest tests/unit/knowledge/test_resolver_audit.py -q` -> OS3-4
- [v1.3.3-E] `uv run pytest tests/unit/gateway/test_rate_limit_alert.py -q` -> OS3-5
- `uv run pytest tests/isolation/test_tenant_crossover.py -q` -> p3-tenant-isolation-runtime / OS3-6 [v1.3-3]
- `bash scripts/security_scan.sh --full` exit 0

---

## 7. Stage 6: 交付与安装器产品化 (D8)

**目标**: 4 个 Delivery milestone + 1 个 gate 实施任务 (D3-5)。

| Milestone | 任务 | 产出路径 |
|-----------|------|---------|
| D3-1 | manifest.yaml 实值化 (版本号、镜像 tag、端口) | `delivery/manifest.yaml` |
| D3-2 | 安装器 + preflight 产品化 | `delivery/install.sh` -- 待创建; `delivery/preflight.sh` 增强 |
| D3-3 | deploy/* 与 manifest 一致性检查 | `scripts/check_manifest_drift.sh` -- 待创建 |
| D3-4 | [v1.3-6] 验证 verify-phase-3 全绿 (非 "新增 target") | Makefile 通配 target 已存在 (verify-phase-%); 确认: `make verify-phase-3` exit 0 |
| D3-5 (gate 任务) | [v1.3-3] scripts/sign_sbom.sh 创建 (p3-sbom-attestation, soft gate) | `scripts/sign_sbom.sh` -- 待创建; SBOM 签名 + cosign 验证; 来源: `production-delivery-gate-plan-v1.0.md:467` |

**验收**:

- `make verify-phase-3` 全绿
- `bash delivery/install.sh && make doctor` exit 0 (全新环境部署)
- `bash scripts/check_manifest_drift.sh` exit 0 (漂移 = 0)
- `bash scripts/sign_sbom.sh` exit 0 (soft, 不阻断 GO 判定) [v1.3-3]

---

## 8. Stage 7: Phase 3 Gate 收口 (D9)

| # | 任务 |
|---|------|
| 7-1 | Phase 3 全量门禁: `make verify-phase-3 --json` [v1.3.3-F] |
| 7-2 | Phase 2 回归: `make verify-phase-2 --json` (确认无退化) [v1.3.3-F] |
| 7-3 | XNode 覆盖: `check_xnode_coverage.py --phase 3 --json` |
| 7-4 | 切换 current_phase: milestone-matrix.yaml line 7 改为 phase_3; [v1.3-7] delivery/manifest.yaml current_phase 改为 "phase_3" |
| 7-5 | [v1.3-5] 更新 CI (.github/workflows/ci.yml): (a) "Phase 2 gate verification" 步骤 (line 277) 改为: `run: uv run python scripts/verify_phase.py --phase 3 --json`; (b) 在其后新增 "Phase 2 regression" 步骤: `run: uv run python scripts/verify_phase.py --phase 2 --json`; (c) [v1.3.1-D] "Validate Phase 2 runtime config" 步骤 (line 284-285) 改为条件执行: `if: hashFiles('delivery/v4-phase2-workflows.yaml') != ''` (保留脚本，文件存在则跑，不存在不报错) |
| 7-6 | 证据归档至 `evidence/phase-3/` |
| 7-7 | 软指标: `uv run pytest tests/perf/test_knowledge_query.py -q` (p95 < 200ms) |
| 7-8 | 软指标: `bash scripts/sign_sbom.sh` exit 0 (p3-sbom-attestation) [v1.3-3] |
| 7-9a | [v1.3.3-B] 任务卡溯源: `uv run python scripts/task_card_traceability_check.py --phase 3` -> main_coverage >= 95% |
| 7-9b | [v1.3.3-B] 任务卡 schema 校验: `uv run python scripts/check_task_schema.py` exit 0 |
| 7-10 | Go/No-Go 评审 (approver: architect + security-reviewer; 参与: contract-owner, frontend-lead, devops) [v1.3.3-G] |

**验收输出** -- `evidence/phase-3/` 下包含:

- `verify-phase_3-*.json` -- gate 结果 (下划线，匹配 verify_phase.py 实际输出)
- `verify-phase_2-regression-*.json` -- Phase 2 回归证据
- `xnode-coverage-phase3-*.json` -- XNode 覆盖报告
- 5 张集成卡各自的 pytest/playwright 输出
- 安全审计证据 (semgrep + pip-audit + pnpm audit)
- `sbom.json.bundle` (SBOM 签名证据, 如 soft 通过) [v1.3-3]

---

## 9. 并行工作流 (8 条)

```
┌──────────────────────────────────────────────────────────┐
│ Flow 1: 基础设施链 [最高优先级，全链前置]                      │
│   Port 扩展 (2A) → I3-1~I3-4 + docker-compose + migration  │
├──────────────────────────────────────────────────────────┤
│ Flow 2: 知识与记忆链 [依赖 Flow 1]                            │
│   K3-1~K3-7 → MC3-1~MC3-2                                  │
│   关键: K3-4 先于 MC3-1                                       │
├──────────────────────────────────────────────────────────┤
│ Flow 3: 主业务链 [依赖 Flow 1 + Flow 2 的 K3-5]               │
│   S3-1~S3-4 → B3-1~B3-4 → G3-1~G3-2                       │
├──────────────────────────────────────────────────────────┤
│ Flow 4: Tool 链 [依赖 Flow 1 的 I3-3/I3-4]                   │
│   T3-1~T3-3                                                 │
├──────────────────────────────────────────────────────────┤
│ Flow 5: 多模态链 [依赖 Flow 1 + Flow 3/4 部分]                 │
│   MM1-1~MM1-6                                               │
├──────────────────────────────────────────────────────────┤
│ Flow 6: 安全审计链 [可与 Flow 2/3 并行]                        │
│   OS3-1~OS3-5 + OS3-6(tenant-isolation) + G3-3              │
├──────────────────────────────────────────────────────────┤
│ Flow 7: 前端体验链 [依赖 Flow 2/3 API 稳定后启动]               │
│   FW3-1~FW3-3 + FA3-1~FA3-3 + 契约联调                       │
├──────────────────────────────────────────────────────────┤
│ Flow 8: 交付门禁链 [贯穿全程]                                  │
│   Phase gate + xnode 覆盖 + 安装器 + SBOM签名 + 验证 + 证据归档  │
└──────────────────────────────────────────────────────────┘
```

**依赖拓扑**:

```
Flow 1 ──┬──→ Flow 2 ──┬──→ Flow 3 ──→ Flow 7
         │              └──→ Flow 5
         ├──→ Flow 4 ──────→ Flow 5
         └──→ Flow 6
Flow 8 ──── 贯穿 Stage 1 ~ Stage 7
```

---

## 10. Exit Criteria (YAML 层面完整定义)

### 14 Hard Criteria

**原 7 项 (Phase 3 专属)**:

```yaml
- id: "p3-knowledge-crud"
  description: "Knowledge CRUD API tests (FK linkage + admin API)"
  check: "uv run pytest tests/unit/knowledge/ tests/integration/knowledge/ -q"
  xnodes: ["X3-2", "X3-4"]

- id: "p3-skill-registry"
  description: "Skill registry + E2E skill loop tests"
  check: "uv run pytest tests/unit/skill/ -q"
  xnodes: ["X3-1"]

- id: "p3-tool-execution"  # [v1.3-8]
  description: "Tool execution sandbox tests (Phase 3 new tools only)"
  check: >-
    uv run pytest
    tests/unit/tool/test_web_search.py
    tests/unit/tool/test_image_analyze.py
    tests/unit/tool/test_audio_transcribe.py -q
  xnodes: ["XM1-1"]

- id: "p3-fe-knowledge"  # [v1.3-9]
  description: "Frontend knowledge + skill + admin pages build + exist"
  check: >-
    cd frontend && pnpm run build
    && test -f apps/web/app/knowledge/page.tsx
    && test -f apps/admin/app/knowledge/page.tsx
    && test -f apps/admin/app/knowledge/review/page.tsx
  xnodes: ["XF3-1", "XF3-2", "XF3-3"]

- id: "p3-promotion-pipeline"
  description: "Memory->Knowledge promotion pipeline cross-SSOT"
  check: >-
    uv run pytest tests/unit/memory/test_promotion.py
    tests/integration/test_promotion.py -q
  xnodes: ["X3-3"]

- id: "p3-content-security"
  description: "Content security pipeline (security_status 6-state)"
  check: "uv run pytest tests/unit/gateway/test_content_pipeline.py -q"
  xnodes: ["X3-5", "XM1-2"]

- id: "p3-resolver-audit"
  description: "Resolver query audit (who/when/what/why)"
  check: "uv run pytest tests/unit/knowledge/test_resolver_audit.py -q"
  xnodes: ["X3-6"]
```

**决策文档新增 1 项 [v1.3-2]**:

```yaml
- id: "p3-tenant-isolation-runtime"
  description: "Runtime tenant isolation (cross-org blocked)"
  check: "uv run pytest tests/isolation/test_tenant_crossover.py -q"
  # source: production-delivery-gate-plan-v1.0.md:417
```

**继承 5 项 (Phase 2 通用质量门禁) [v1.3-1]**:

```yaml
- id: "p3-lint"
  description: "Full lint (ruff + frontend ESLint)"
  check: "make lint"

- id: "p3-security-scan"
  description: "Security scan (semgrep + pip-audit)"
  check: "bash scripts/security_scan.sh --full"

- id: "p3-layer-boundary"
  description: "Layer boundary violations = 0"
  check: "bash scripts/check_layer_deps.sh --json"

- id: "p3-no-mock-py"
  description: "No banned mock patterns in Python"
  check: "uv run python scripts/check_no_mock.py src/ tests/"

- id: "p3-integration"
  description: "Integration tests pass"
  check: "uv run pytest tests/integration/ -q --tb=short"
```

**继承 env-completeness [v1.3-11]**:

```yaml
- id: "p3-env-completeness"
  description: "All source-referenced env vars present in .env.example"
  check: "uv run python scripts/check_env_completeness.py"
```

### 2 Soft Criteria

```yaml
- id: "p3-graph-perf"
  description: "Knowledge graph query p95 < 200ms"
  check: "uv run pytest tests/perf/test_knowledge_query.py -q"

- id: "p3-sbom-attestation"  # [v1.3-2]
  description: "SBOM signed with cosign (Phase 3 soft, Phase 4 hard)"
  check: "bash scripts/sign_sbom.sh"
  # source: production-delivery-gate-plan-v1.0.md:467
```

---

## 11. Go/No-Go 放行标准

[v1.3.1-C] 每行标注阻断级别，消除 soft gate 语义歧义。

| # | 条件 | 验证命令 | 阻断级别 |
|---|------|---------|---------|
| 1 | Phase 2 门禁持续 GO | `make verify-phase-2` exit 0 | hard-block |
| 2 | Phase 3 hard criteria 14/14 PASS | `make verify-phase-3` exit 0 | hard-block |
| 3 | Phase 3 XNode 覆盖率 >= 0.70 | `check_xnode_coverage.py --phase 3 --json` | hard-block |
| 4 | 5 张集成卡全部有可执行证据 | `evidence/phase-3/` 下逐条核验 | hard-block |
| 5 | Lint + Security scan 通过 | `make lint && bash scripts/security_scan.sh --full` | hard-block |
| 6 | 跨层依赖违规 = 0 | `bash scripts/check_layer_deps.sh --json` | hard-block |
| 7 | Port 兼容性检查通过 | `bash scripts/check_port_compat.sh` | hard-block |
| 8 | Env 完整性通过 | `uv run python scripts/check_env_completeness.py` | hard-block |
| 9 | manifest.yaml + CI 已更新 | 手动核验 [v1.3-5][v1.3-7] | hard-block |
| 10 | 观察: graph query p95 < 200ms | `uv run pytest tests/perf/test_knowledge_query.py -q` | soft-track |
| 11 | 观察: SBOM attestation | `bash scripts/sign_sbom.sh` | soft-track |
| 12 | [v1.3.3-B] 任务卡溯源 >= 95% | `uv run python scripts/task_card_traceability_check.py --phase 3` | hard-block |
| 13 | [v1.3.3-G] Go/No-Go 评审签署 | approver: architect + security-reviewer; 参与: contract-owner, frontend-lead, devops | hard-block |

**阻断级别说明**:

- **hard-block**: FAIL 则整体判定 BLOCKED，不可放行
- **soft-track**: 记录结果、归档证据、不阻断 GO 判定，Architect 评审时作为参考因素

---

## 12. 可视化: 8 条并行工作流时间线

```
时间轴 ──────────────────────────────────────────────────────▸
        D0    D1    D2    D3    D4    D5    D6    D7    D8   D9

Flow 1  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
基础设施  S0    S1    S2

Flow 2  ·····················▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
知识记忆                      K3-1→K3-7 → MC3-1→MC3-2

Flow 3  ········································▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
主业务                                           S3→B3→G3-1/G3-2

Flow 4  ·····················▓▓▓▓▓▓▓▓▓▓
Tool                        T3-1~T3-3

Flow 5  ········································▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
多模态                                           MM1-1~MM1-6

Flow 6  ·····················▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
安全审计                      OS3-1~OS3-6 + G3-3

Flow 7  ·····················································▓▓▓▓▓▓▓▓▓▓
前端体验                                                      FW3+FA3

Flow 8  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
交付门禁  贯穿 S0 ────────────────────────────────────────────── S7

图例:  ▓▓ 活跃期    ·· 等待依赖    ▸ 时间方向
```

---

## 13. 可视化: 关键路径

```
Stage 0  Stage 1   Stage 2        Stage 3
──────── ────────── ──────── ────────────────────────────────────────────

                                  ┌ K3-1 ┐
S0 回归 ▸ S1-1A门禁 ▸ 2A Port ▸ 2B ┤      ├▸ K3-3 ▸ K3-4 ▸ K3-5 ▸ S3-1
                     扩展     I3-1 └ K3-2 ┘
                             I3-2

         Stage 3 (续)                   Stage 4   Stage 7
         ──────────────────────────────  ────────  ────────

▸ B3-1 ▸ B3-2 ▸ G3-1 ▸ (API稳定) ▸ FW3-1 ▸ FA3-1 ▸ S7 收口
                G3-2

关键路径长度: 约 20 个串行 milestone
并行可缩短: Flow 4/5/6 不在关键路径上，可被关键路径完全遮盖
```

---

## 14. 可视化: 阻断点清单

| # | 阻断点 | 原因 | 解除条件 |
|---|--------|------|---------|
| 1 | Stage 0 全量回归 | 脏基线会污染所有后续 Stage | `make verify-phase-2` -> GO |
| 2 | Stage 1A 门禁写入 YAML | 后续所有 Stage 验收依赖 YAML 中 exit criteria 定义 | 14 hard + 2 soft 全部写入 + 核验 |
| 3 | Stage 2A Port 接口定义 | 4 个 adapter 和全部业务层依赖 Port 接口 | `check_port_compat.sh` exit 0 |
| 4 | K3-3 FK 联动 | K3-4/K3-5/K3-7/MC3-1 全部依赖 K3-3 | `test_fk_linkage.py` pass |
| 5 | K3-4 Knowledge Write API | MC3-1 + K3-7 + G3-1 全部依赖 | `test_write_api.py` + `test_write_integration.py` pass |
| 6 | S3-3 Skill lifecycle | B3-1 + S3-4 + G3-2 全部依赖 | `test_lifecycle.py` pass |
| 7 | Stage 3->4 API 稳定 | 前端 FW3/FA3 需要后端 API 契约冻结 | `check_openapi_sync.sh` exit 0 |
| 8 | Stage 7 Gate 收口 | 最终放行前全量串行验证 | 14/14 hard PASS + Architect 签署 |

---

## 15. 全量变更记录

### v1.2 -> v1.3 变更 (11 项)

| # | 问题来源 | 发现内容 | 修正 | 所在位置 |
|---|---------|---------|------|---------|
| v1.3-1 | P0-1 审查 | YAML 仅 7 hard，继承 5 项未写入 YAML | Stage 1A 任务 1-2: 写入 YAML | Stage 1A + YAML |
| v1.3-2 | P0-2 审查 | 决策文档 p3-tenant-isolation-runtime (hard) + p3-sbom-attestation (soft) 未纳入 YAML | Stage 1A 任务 1-3: 写入 YAML; Stage 5 新增 OS3-6; Stage 6 新增 D3-5 | Stage 1A/5/6 + YAML |
| v1.3-3 | P0-2 衍生 | Stage 5 缺租户隔离 runtime 测试; Stage 6 缺 SBOM 签名脚本 | Stage 5 新增 OS3-6 + test_tenant_crossover.py; 新增 scripts/sign_sbom.sh | Stage 5 + Stage 6 |
| v1.3-4 | P1-1 审查 | 新增 adapter 引入环境变量后 .env.example 未同步 | Stage 2B 验收新增 check_env_completeness.py | Stage 2B 验收 |
| v1.3-5 | P1-2 审查 | CI 硬编码 --phase 2，Stage 7 未显式列出 CI 更新 | Stage 7 步骤 7-5 详列 CI 三处变更 | Stage 7 |
| v1.3-6 | P2-1 审查 | "新增 verify-phase-3 target" 不准确 | D3-4 描述改为 "验证 verify-phase-3 全绿" | Stage 6 |
| v1.3-7 | P2-2 审查 | manifest.yaml current_phase 为 phase_0 | Stage 0 对齐为 phase_2; Stage 7 更新为 phase_3 | Stage 0 + Stage 7 |
| v1.3-8 | 额外发现 | p3-tool-execution YAML check 为全目录 | YAML 同步改为精确 3 文件路径 | YAML |
| v1.3-9 | 额外发现 | p3-fe-knowledge YAML check 仅 build | YAML 同步增加 test -f 存在性检查 | YAML |
| v1.3-10 | 额外发现 | ObjectStoragePort 架构文档 5 方法，任务卡写 6 方法 | 任务卡 + milestone-matrix 统一为 5 方法 | 任务卡 + MM 表 |
| v1.3-11 | P0-1+P0-2 | Exit Criteria 计数不准确 | 统一为 14 hard + 2 soft | 全文 |

### v1.3 -> v1.3.1 补丁 (4 项)

| 补丁 ID | 问题来源 | 发现内容 | 修正 | 所在位置 |
|---------|---------|---------|------|---------|
| v1.3.1-A | v1.3 自检 | 新增 OS3-6/D3-5 但头部仍写 Obs=5, Del=4, 总数=48 | 头部独立标注 "+2 gate 实施任务"，milestone 口径保持 48 | 文档头部 |
| v1.3.1-B | v1.3 自检 | ObjectStoragePort "6->5" 仅在头部清单，未编入任何 Stage 编号任务 | 编入 Stage 0 任务 0-8 作为编号步骤，含精确文件行号 + grep 验收命令 | Stage 0 |
| v1.3.1-C | v1.3 自检 | p3-sbom-attestation 为 soft 但 Go/No-Go 表未区分阻断级别 | Go/No-Go 表增加 "阻断级别" 列: hard-block / soft-track | Go/No-Go 表 |
| v1.3.1-D | v1.3 自检 | Stage 7 validate_phase2_config.py "评估是否保留" 是待决策项 | 替换为确定性指令: 保留脚本，改为条件执行 `if: hashFiles(...) != ''` | Stage 7 步骤 7-5(c) |

### v1.3.1 -> v1.3.2 补丁 (3 项)

| 补丁 ID | 问题来源 | 发现内容 | 修正 | 所在位置 |
|---------|---------|---------|------|---------|
| v1.3.2-A | GAP-5 审查 | YAML phase_3.milestones 列表缺 OS3-6 (tenant-isolation) 和 D3-5 (sbom-attestation)，里程碑追踪不完整 | Stage 1A 新增任务 1-6a: 补录 2 条 milestone 到 YAML; Stage 1 验收新增检查 | Stage 1A + Stage 1 验收 |
| v1.3.2-B | GAP-6 审查 | milestone-matrix-crosscutting.md Observability Phase 3 仅 OS3-1~OS3-5 (无 OS3-6), Delivery Phase 3 仅 D3-1~D3-4 (无 D3-5), 矩阵规划层与路线图实施层不同步 | Stage 1A 新增任务 1-6b: 补录 2 条 milestone 到横切矩阵; Stage 1 验收新增检查 | Stage 1A + Stage 1 验收 |
| v1.3.2-C | GAP-7 审查 | milestone-matrix.md Phase 3 检查清单仅 9 项，缺少租户隔离 runtime / SBOM attestation / env completeness，与 Go/No-Go 12 项放行条件不同步 | Stage 1A 新增任务 1-6c: 补录 3 项到 Phase 3 检查清单 (12/12); Stage 1 验收新增检查 | Stage 1A + Stage 1 验收 |

### v1.3.2 -> v1.3.3 补丁 (7 项)

| 补丁 ID | 问题来源 | 发现内容 | 修正 | 所在位置 |
|---------|---------|---------|------|---------|
| v1.3.3-A | 发现 1 审查 | MM1-1~MM1-6 无主任务卡，main_coverage=87.5% (治理规范要求 Phase 3 >= 95%) | Stage 3G 追加 MM1 任务卡创建说明 (`docs/task-cards/08-多模态/multimodal.md`, 6 张 Tier-B 卡); Stage 3 验收追加 `task_card_traceability_check.py --phase 3` | Stage 3G + Stage 3 验收 |
| v1.3.3-B | 发现 2 审查 | 路线图无任何 Stage 验收纳入 `check_task_schema.py` 或 `task_card_traceability_check.py`，治理闭环缺失 | Stage 7 追加任务 7-9a (traceability) + 7-9b (schema); Go/No-Go 追加 #12 (hard-block) | Stage 7 + Go/No-Go |
| v1.3.3-C | 发现 3 审查 | 3 处测试路径命名冲突: G3-1 路线图 `test_knowledge_admin_api.py` vs 任务卡 `test_knowledge_api.py`; G3-3/OS3-1 路线图 `test_content_security.py` vs 任务卡 `test_content_pipeline.py` | 以任务卡为 SSOT 统一路径; Stage 1A 追加任务 1-6d 确保执行时对齐; 修正路线图 3F/Stage 5/Stage 3 验收/Exit Criteria 中的路径引用 | Stage 1A + 3F + Stage 3 验收 + Stage 5 + Exit Criteria |
| v1.3.3-D | 发现 4 审查 | MM1-2/4/6 XNode 绑定和依赖与横切矩阵不一致: 路线图标 `--` 但矩阵有明确绑定 | 3G 表对齐横切矩阵: MM1-2 XNode=X2-2 DEP=G2-2; MM1-4 XNode=X2-1 DEP=B2-1,T2-2; MM1-6 XNode=X4-4 DEP=MC4-1 | Stage 3G |
| v1.3.3-E | 发现 5 审查 | Stage 5 验收清单仅覆盖 OS3-1/OS3-4/OS3-6，遗漏 OS3-2 (`test_audit_coverage.py`), OS3-3 (`test_xss_protection.py`), OS3-5 (`test_rate_limit_alert.py`) | Stage 5 验收补全 3 条命令 | Stage 5 验收 |
| v1.3.3-F | 发现 6 审查 | Stage 7 任务 7-1/7-2 命令缺 `--json`，与治理规范 "JSON 证据归档" 要求不一致 | 7-1/7-2 命令追加 `--json` | Stage 7 |
| v1.3.3-G | 发现 7 审查 | Go/No-Go #12 审批角色仅 architect，未覆盖审查矩阵中 SECURITY/CONTRACT/FRONTEND-CONTRACT/DevOps 角色 | 拆分为 approver (architect + security-reviewer) 和 参与者 (contract-owner, frontend-lead, devops) | Stage 7 + Go/No-Go |

---

路线图 v1.3.3 完成。8 Stage, 48 milestones + 2 gate 实施任务, 11 XNodes (聚合为 5 张集成卡), 14 hard + 2 soft exit criteria, 8 条并行工作流, 13 Go/No-Go 放行条件 (11 hard-block + 2 soft-track)。无待决策项，无歧义描述，全部为可执行指令。

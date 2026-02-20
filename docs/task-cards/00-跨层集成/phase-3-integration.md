# Phase 3 Cross-Layer Integration Task Cards

## Phase 3: Knowledge & Skill Ecosystem -- Cross-Layer Verification

> 聚合规则: 同一 Phase + 参与层重叠 + 可共享 E2E 测试 -> 合并为一张卡
> 来源: `docs/governance/decisions/2026-02-19-cross-layer-gate-binding-impl-v1.0.md:725`

---

### TASK-INT-P3-SKILL: Skill 完整闭环 Cross-Layer E2E

> 矩阵条目: X3-1

| Field | Value |
|-------|-------|
| **目标** | 对话触发 Skill 完整闭环 (Intent -> Router -> Skill -> Tool -> Response) 通过 E2E 验证 |
| **范围** | `tests/e2e/cross/test_skill_e2e.py` |
| **范围外** | 前端 Artifact 渲染 / Skill A/B 测试 / 多模态 Skill |
| **依赖** | TASK-S3-3, TASK-B3-1, TASK-B3-2 |
| **风险** | 依赖: Brain Skill Router + Skill lifecycle 必须就绪; 数据: 需要已注册的 Skill 实例; 兼容: 新增测试; 回滚: git revert |
| **兼容策略** | 新增测试文件, 无破坏性变更 |
| **验收命令** | `uv run pytest tests/e2e/cross/test_skill_e2e.py -v` |
| **回滚方案** | `git revert` |
| **证据** | CI artifact / `evidence/phase-3/` |
| **决策记录** | Fake adapter 模式, 无外部服务依赖 |

---

### TASK-INT-P3-KNOWLEDGE: Knowledge 集成测试套件

> 矩阵条目: X3-2
> 矩阵条目: X3-3
> 矩阵条目: X3-4
> 矩阵条目: X3-6

| Field | Value |
|-------|-------|
| **目标** | Knowledge 四条跨层链路: FK 一致性 (X3-2) + Promotion 跨 SSOT (X3-3) + Admin API 全链路 (X3-4) + Resolver 审计闭环 (X3-6) |
| **范围** | `tests/integration/knowledge/`, `tests/unit/knowledge/test_resolver_audit.py`, `tests/integration/test_promotion.py` |
| **范围外** | Knowledge 性能基准 / 企业多模态 FK / 跨模态检索 |
| **依赖** | TASK-K3-3, TASK-K3-4, TASK-MC3-1, TASK-OS3-4 |
| **风险** | 依赖: Neo4j + Qdrant FK 联动必须就绪 (K3-3); 数据: Promotion 需要 Memory + Knowledge 双写能力; 兼容: 新增测试; 回滚: git revert |
| **兼容策略** | 新增测试文件, 无破坏性变更 |
| **验收命令** | `uv run pytest tests/integration/knowledge/ tests/unit/knowledge/test_resolver_audit.py tests/integration/test_promotion.py -v` |
| **回滚方案** | `git revert` |
| **证据** | CI artifact / `evidence/phase-3/` |
| **决策记录** | 四节点共享 Knowledge 集成测试套件, 降低测试维护成本 |

---

### TASK-INT-P3-SECURITY: 内容安全管线 Cross-Layer E2E

> 矩阵条目: X3-5
> 矩阵条目: XM1-2

| Field | Value |
|-------|-------|
| **目标** | 内容安全管线闭环 (恶意内容 -> quarantined -> 审计) + 媒体安全扫描闭环 |
| **范围** | `tests/unit/gateway/test_content_pipeline.py`, `tests/isolation/test_tenant_crossover.py` |
| **范围外** | NSFW 检测模型训练 / 版权检测 / 企业媒体安全 |
| **依赖** | TASK-OS3-1, TASK-OS3-6 |
| **风险** | 依赖: security_status 6-state 模型必须就绪; 数据: 需要恶意内容样本; 兼容: 新增测试; 回滚: git revert |
| **兼容策略** | 新增测试文件, 无破坏性变更 |
| **验收命令** | `uv run pytest tests/unit/gateway/test_content_pipeline.py tests/isolation/test_tenant_crossover.py -v` |
| **回滚方案** | `git revert` |
| **证据** | CI artifact / `evidence/phase-3/` |
| **决策记录** | 安全管线与租户隔离共享安全测试套件 |

---

### TASK-INT-P3-MEDIA: 个人媒体上传 Cross-Layer E2E

> 矩阵条目: XM1-1

| Field | Value |
|-------|-------|
| **目标** | 个人媒体上传三步协议闭环 (presigned URL -> upload -> confirm -> accessible) |
| **范围** | `tests/e2e/cross/test_media_upload.py` |
| **范围外** | 企业媒体上传 / 媒体安全扫描 / 媒体删除管线 |
| **依赖** | TASK-I3-3, TASK-MM1-1 |
| **风险** | 依赖: ObjectStoragePort (S3/MinIO) 必须就绪; 环境: 需要 MinIO 运行 [ENV-DEP]; 兼容: 新增测试; 回滚: git revert |
| **兼容策略** | 新增测试文件, 无破坏性变更 |
| **验收命令** | [ENV-DEP] `uv run pytest tests/e2e/cross/test_media_upload.py -v` |
| **回滚方案** | `git revert` |
| **证据** | CI artifact / `evidence/phase-3/` |
| **决策记录** | 独立 E2E, 不与其他安全/知识测试混合 |

---

### TASK-INT-P3-FE: 前端集成 Playwright Suite

> 矩阵条目: XF3-1
> 矩阵条目: XF3-2
> 矩阵条目: XF3-3

| Field | Value |
|-------|-------|
| **目标** | 前端三条集成链路: Skill Artifact 渲染 (XF3-1) + 知识编辑工作流 (XF3-2) + 组织配置继承 (XF3-3) |
| **范围** | `frontend/tests/e2e/cross/web/skill-artifact.spec.ts`, `frontend/tests/e2e/cross/admin/knowledge-workflow.spec.ts`, `frontend/tests/e2e/cross/admin/org-config-inherit.spec.ts` |
| **范围外** | 性能预算 / a11y 审计 / 移动端 |
| **依赖** | TASK-FW3-2, TASK-FA3-1, TASK-FA3-3 |
| **风险** | 环境依赖: 需要全栈运行 (Backend + Frontend) [ENV-DEP, E2E]; 测试稳定性: Playwright 超时; 认证: 需要 Admin 权限; 数据: 需要知识条目种子数据 |
| **兼容策略** | 新增测试文件, 无破坏性变更 |
| **验收命令** | [ENV-DEP, E2E] `cd frontend && pnpm exec playwright test tests/e2e/cross/web/skill-artifact.spec.ts tests/e2e/cross/admin/knowledge-workflow.spec.ts tests/e2e/cross/admin/org-config-inherit.spec.ts` |
| **回滚方案** | `git revert` |
| **证据** | Playwright trace + screenshots / `evidence/phase-3/` |
| **决策记录** | 三节点共享 Playwright suite, 按 web/admin 分组 |

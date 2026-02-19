# 治理验证与门禁体系补全计划 v1.0

# 生产级商业工程化交付 + 运维闭环落地

> 日期: 2026-02-19
> 状态: Approved (终审通过, Phase 2 范围已执行)
> 终审日期: 2026-02-20
> 上游决议: `docs/governance/decisions/2026-02-19-cross-layer-gate-binding.md`
> 子计划: `docs/governance/decisions/2026-02-19-cross-layer-gate-binding-impl-v1.0.md`
> 审查证据: `evidence/governance-reviews/cross-layer-integration-gap-v1.3-20260219.md`
> 变更范围: 工程验证链 + 跨层集成 + 运维闭环 (三维度统一)

---

## 0. 设计原则

1. **三维度统一**: 工程验证链 (Dim-A) + 跨层集成承接链 (Dim-B) + 运维闭环 (Dim-C)
2. **实现先于门禁**: 先补可执行对象, 再上 gate, 再固化运营证据
3. **按 Phase 渐进**: 不在同一 Phase 硬化全部项, 避免 gate 长期红灯
4. **CI 可验证做自动 gate**: 非 CI 可验证做人工 checklist, 不伪自动化
5. **不另建独立系统**: 在现有治理体系内增量补全
6. **向后兼容**: 新增字段/脚本不破坏现有 gate 语义
7. **覆盖率阈值渐进**: P2>=40%, P3>=70%, P4>=90%, P5=100% (Dim-B)
8. **Phase 0-1 不改历史 gate**: 仅做回溯审计 (Dim-B)
9. **运维项 Phase 4 前不设阻断 gate**: 避免前置项缺失导致假阻断 (Dim-C)
10. **双口径输出**: direct (gate 判定) + semantic (仅辅助) (Dim-B)

---

## 1. 范围定义

### 1.1 三维度缺口模型

```
Dimension A: 工程验证链硬化 (7 项, F1-F7)
  -- CI gate 实际不强制 / 覆盖率不检查 / 服务环境缺失 / 证据链断裂

Dimension B: 跨层集成承接链 (50 节点, G0-G7 + P2-P5)
  -- X/XF/XM 节点 0% gate 绑定率, 详见子计划

Dimension C: 运维闭环落地 (14 维度, A/B/C 三档)
  -- 发布/灾备/告警/事故/合规/供应链等运营能力缺 gate 硬化
```

### 1.2 上游决议与证据

| 文档 | 角色 |
|------|------|
| `2026-02-19-cross-layer-gate-binding.md` | 上游决议 (5 项动作) |
| `2026-02-19-cross-layer-gate-binding-impl-v1.0.md` | Dim-B 子计划 (v1.0.1, 详细实施规格) |
| `cross-layer-integration-gap-v1.3-20260219.md` | 审查证据 |
| `governance-optimization-plan.md` | 治理体系 v2.0 总纲 |
| `execution-plan-v1.0.md` | 执行计划基线 |

---

## 2. 缺口总览

### 2.1 Dimension A: 工程验证链 (7 项)

| ID | 缺口 | 严重度 | 证据 | Phase |
|----|------|--------|------|-------|
| F1 | 分支保护形同虚设 | CRITICAL | `ci.yml:33` REQUIRED 注释但未启用; pre-push hook 可 `--no-verify` 绕过 | P2 |
| F2 | CI 不运行覆盖率检查 | HIGH | `pyproject.toml:117` fail_under=80 存在; `ci.yml` 无 `--cov` (grep 0 matches) | P2 |
| F3 | CI 无服务容器 (PG/Redis) | HIGH | `ci.yml:151-158` bare ubuntu; `tests/integration/` 4 文件在 CI 不运行 | P2-3 |
| F4 | verify_phase.py shell=True 无白名单 | MEDIUM | `verify_phase.py:63` subprocess shell=True; `lint_workflow_checks.py` 不检查 milestone-matrix.yaml | P3 |
| F5 | Dockerfile 不存在, 容器化链为空 | MEDIUM | `docker-compose.yml:68` 引用不存在的 Dockerfile (glob 0 files) | P3 |
| F6 | 证据链 90 天过期, 无持久归档 | MEDIUM | `actions/upload-artifact` 默认 90 天; `evidence/` gitignored | P4 |
| F7 | 前端 Playwright E2E 不在 CI | LOW | `ci.yml` 无 playwright step; `turbo.json` test:e2e 未被 CI 调用 | P3-4 |

### 2.2 Dimension B: 跨层集成承接链 (50 节点)

详见子计划。摘要: 50 个 X/XF/XM 节点在 `milestone-matrix-crosscutting.md` Section 4
定义, `milestone-matrix.yaml` 中 0% 显式 ID 绑定 (grep 确认无 X/XF/XM 引用)。
通过 `xnodes` 元字段 + `check_xnode_coverage.py` 补全。

### 2.3 Dimension C: 运维闭环 (14 维度, 3 档)

| 档位 | Phase | 维度 | 当前状态 |
|------|-------|------|---------|
| A | P2-3 | 多租户安全运行时验证 | `check_rls.sh` 仅静态扫描; `tests/isolation/` CI 不运行 |
| A | P2-3 | Secrets 全生命周期 | `.env` + `docker-compose.yml:10` 硬编码 dev 密码; 无 Vault |
| A | P2-3 | 供应链签名 | `generate_sbom.sh` 生成 SPDX JSON; 无 cosign/sigstore |
| B | P4 | 发布治理 (灰度/回滚) | Dockerfile 不存在 (F5); 无发布管线 |
| B | P4 | 灾备连续性 (RTO/RPO) | `crosscutting.md:65-66` 有规划; 无 drill 脚本 |
| B | P4 | 告警到处置 | `deploy/monitoring/alerts.yml` 存在; 无值班/升级路径 |
| B | P4 | 事故管理 (MTTA/MTTR) | `delivery/commercial/runbook/` 5 个模板; 无目标和 gate |
| B | P4 | 合规法务 | `crosscutting.md:199-200` 有规划; 无可执行产物 |
| B | P4 | 外部依赖韧性 | Phase 4 X4-2/X4-3 规划; 无降级/熔断测试 |
| C | P5 | 计费闭环 | 业务逻辑, 非 CI gate 可验证 |
| C | P5 | 数据治理 | 文档+流程, 检查文件存在即可 |
| C | P5 | 容量与性能 | 需专用压测环境, 不适合 PR CI |
| C | P5 | 客户运维 | 状态页/支持SOP, 运营资产 |
| C | P5 | 商业化交付 | License/entitlement, 产品功能 |

---

## 3. 完整产物清单

### 3.1 Dimension A 产物

| # | 产物 | 路径 | 类型 | Phase |
|---|------|------|------|-------|
| FA-1 | 分支保护或等效强制机制 | `.github/workflows/ci.yml` + GitHub Settings | 修改 | P2 |
| FA-2 | CI 覆盖率 gate | `.github/workflows/ci.yml` test-backend job | 修改 | P2 |
| FA-3 | CI PG/Redis service container job | `.github/workflows/ci.yml` 新 job | 新建 | P2-3 |
| FA-4 | Phase gate 命令白名单扩展 | `scripts/lint_workflow_checks.py` | 修改 | P3 |
| FA-5 | Dockerfile (multi-stage) | `Dockerfile` | 新建 | P3 |
| FA-6 | 证据持久归档 CI step | `.github/workflows/ci.yml` | 修改 | P4 |
| FA-7 | 前端 Playwright CI job | `.github/workflows/ci.yml` 新 job | 新建 | P3-4 |

### 3.2 Dimension B 产物 (引用子计划)

| # | 产物 | 类型 | Phase |
|---|------|------|-------|
| G0 | 兼容前置修复包 (4 项) | 修改 | P2 |
| G1-G7 | 框架搭建 (schema + 脚本 + CI + 回溯) | 新建/修改 | P2 |
| P2-P5 | 各 Phase 集成任务卡 + E2E 测试 | 新建 | P2-5 |

详见: `2026-02-19-cross-layer-gate-binding-impl-v1.0.md`

### 3.3 Dimension C 产物

| # | 产物 | 路径 | 类型 | Phase |
|---|------|------|------|-------|
| CA-1 | 租户隔离运行时 gate | `tests/isolation/test_tenant_crossover.py` | 新建 | P3 |
| CA-2 | Secrets 完整性检查脚本 | `scripts/check_env_completeness.py` | 新建 | P2 |
| CA-3 | SBOM 签名 + attestation | `scripts/sign_sbom.sh` | 新建 | P3 |
| CB-1 | 发布回滚 runbook + drill | `delivery/commercial/runbook/release-rollback.md` + `scripts/drill_release.sh` | 新建 | P4 |
| CB-2 | 灾备恢复 runbook + drill | `delivery/commercial/runbook/dr-restore.md` + `scripts/drill_dr_restore.sh` | 新建 | P4 |
| CB-3 | 事故管理 SLA 定义 | `delivery/commercial/incident-sla.yaml` | 新建 | P4 |
| CB-4 | 依赖韧性 chaos 测试 | `tests/e2e/cross/test_dependency_chaos.py` | 新建 | P4 |
| CB-5 | 告警路由验证脚本 | `scripts/check_alert_routing.py` | 新建 | P4 |
| CB-6 | 合规产物检查脚本 | `scripts/check_compliance_artifacts.py` | 新建 | P4 |
| CC-1 | 上线前阻断清单 | `delivery/operations-readiness-checklist.md` | 新建 | P5 |
| CC-2 | 发版证据模板 | `evidence/release/template.json` | 新建 | P5 |
| CC-3 | 商业就绪检查 | `scripts/check_commercial_readiness.py` | 新建 | P5 |

---

## 4. Dimension A: 工程验证链硬化

### 4.1 [F1] 分支保护

**问题**: Private repo + GitHub Free plan, 原生分支保护不可用 (HTTP 403)。
`pre-push-guard.sh` 仅覆盖 4/14 CI 检查且可被 `--no-verify` 绕过。

**方案 A (推荐): 升级 GitHub Pro ($4/月)**

启用后配置:
```bash
gh api repos/{owner}/{repo}/branches/main/protection --method PUT \
  --field required_status_checks='{"strict":true,"contexts":[
    "L1: Security Scan","L1: Backend Lint","L1: Backend Tests",
    "L1: Backend Typecheck","L1: Frontend Tests","L1: Frontend Typecheck",
    "L3: Phase Gate"]}' \
  --field enforce_admins=true \
  --field required_pull_request_reviews='{"required_approving_review_count":1}'
```

**方案 B (零成本): CI merge-readiness + hook 自动安装**

ci.yml 增加 merge-readiness job:
```yaml
merge-readiness:
  name: "Merge Readiness"
  runs-on: ubuntu-latest
  needs: [security-scan, lint-backend, lint-frontend, typecheck-backend,
          typecheck-frontend, test-backend, test-frontend, semantic-checks]
  if: github.event_name == 'pull_request'
  steps:
    - run: echo "All required checks passed"
```

Makefile bootstrap target 增加 hook 自动安装:
```makefile
bootstrap:
	# ... existing steps ...
	@ln -sf ../../scripts/pre-push-guard.sh .git/hooks/pre-push
	@echo "[bootstrap] pre-push hook installed"
```

pre-push-guard.sh 增加安全扫描和类型检查 (从 4/4 升级到 6/6):
```bash
echo "  [5/6] mypy..."
uv run mypy src/ --no-error-summary || { echo "BLOCKED: type errors"; exit 1; }
echo "  [6/6] security scan (quick)..."
bash scripts/security_scan.sh --quick || { echo "BLOCKED: security findings"; exit 1; }
```

**验收**: 方案 A: `gh api .../branches/main/protection` 返回 200。
方案 B: merge-readiness job 在 PR 中可见; `make bootstrap` 自动安装 hook。

### 4.2 [F2] CI 覆盖率 gate

**问题**: `pyproject.toml:117` 定义 `fail_under = 80`, 但 `ci.yml` test-backend
job 仅运行 `pytest tests/unit/ -v --tb=short`, 不带 `--cov`。

**修复**: ci.yml test-backend job (line 137-139):

```yaml
      - run: |
          mkdir -p ${{ env.EVIDENCE_DIR }}
          uv run pytest tests/unit/ -v --tb=short \
            --cov=src --cov-report=xml:${{ env.EVIDENCE_DIR }}/coverage.xml \
            --cov-report=term-missing --cov-fail-under=80 \
            --junitxml=${{ env.EVIDENCE_DIR }}/test-results.xml
```

**验收**: 覆盖率 < 80% 的 PR -> CI test-backend job 红。

### 4.3 [F3] CI 服务容器

**问题**: 全部 CI job 在 bare ubuntu-latest 运行。`tests/integration/` (4 文件)
和 `tests/isolation/` 在 CI 中从不执行。

**修复**: ci.yml 新增 integration-tests job:

```yaml
  integration-tests:
    name: "L2: Integration Tests"
    runs-on: ubuntu-latest
    services:
      postgres:
        image: pgvector/pgvector:pg16
        env:
          POSTGRES_USER: diyu
          POSTGRES_PASSWORD: test_ci
          POSTGRES_DB: diyu_test
        ports: ['5432:5432']
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      redis:
        image: redis:7-alpine
        ports: ['6379:6379']
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv sync --dev --frozen
      - name: Run isolation tests (RLS runtime)
        env:
          DATABASE_URL: postgresql+asyncpg://diyu:test_ci@localhost:5432/diyu_test
          REDIS_URL: redis://localhost:6379/0
        run: uv run pytest tests/isolation/ -v --tb=short
      - name: Run integration tests
        env:
          DATABASE_URL: postgresql+asyncpg://diyu:test_ci@localhost:5432/diyu_test
          REDIS_URL: redis://localhost:6379/0
        run: uv run pytest tests/integration/ -v --tb=short
```

**分级**: Phase 2 informational (不加入 required checks); Phase 3 升级为 required。

**验收**: `tests/isolation/test_rls_isolation.py` 在 CI 中运行并 PASS。

### 4.4 [F4] Phase gate 命令白名单

**问题**: `verify_phase.py:63` 对 YAML check 字段执行 `shell=True`,
`lint_workflow_checks.py` 仅检查 `v4-workflows.yaml`, 不检查 `milestone-matrix.yaml`。

**修复**: 扩展 `lint_workflow_checks.py` 新增 `--field` 参数:

```bash
uv run python scripts/lint_workflow_checks.py \
  delivery/milestone-matrix.yaml --field exit_criteria
```

在 ci.yml guard-checks job 的 "Lint workflow check commands" step 中增加:
```yaml
- run: |
    for f in delivery/v4-workflows.yaml delivery/v4-phase2-workflows.yaml; do
      if [ -f "$f" ]; then uv run python scripts/lint_workflow_checks.py "$f"; fi
    done
    uv run python scripts/lint_workflow_checks.py delivery/milestone-matrix.yaml --field exit_criteria
```

**验收**: milestone-matrix.yaml 中的 check 命令全部通过白名单校验。

### 4.5 [F5] 容器化构建链

**问题**: `docker-compose.yml:68` 引用不存在的 Dockerfile。

**规格** (Phase 3 交付):
- Multi-stage Dockerfile: builder stage (uv + deps) -> runtime stage (slim, non-root)
- CI 新增 `build-image` job: `docker build` + `trivy image --exit-code 1 --severity HIGH,CRITICAL`
- 替换 Makefile `image-scan` target 中 soft warning 为 hard gate

**前置**: Phase 2 完成后, Phase 3 激活前。

**验收**: `docker build -t diyu-agent:test .` 成功; trivy 通过。

### 4.6 [F6] 证据链持久归档

**问题**: CI artifact 90 天过期; `evidence/` 被 gitignore; 无持久归档。

**修复** (Phase 4):

`.gitignore` 增加白名单:
```gitignore
!evidence/ci/
!evidence/ci/*.json
!evidence/ci/*.xml
!evidence/release/
!evidence/release/*.json
```

CI 关键 gate 证据写入 `evidence/ci/`:
```yaml
      - name: Archive gate evidence
        if: github.ref == 'refs/heads/main'
        run: |
          mkdir -p evidence/ci
          cp ${{ env.EVIDENCE_DIR }}/phase-gate.json evidence/ci/ 2>/dev/null || true
          cp ${{ env.EVIDENCE_DIR }}/coverage.xml evidence/ci/ 2>/dev/null || true
          cp ${{ env.EVIDENCE_DIR }}/security-scan.json evidence/ci/ 2>/dev/null || true
```

**验收**: `evidence/ci/` 下有最近一次 gate 通过的 JSON 证据; `git ls-files evidence/ci/` 非空。

### 4.7 [F7] 前端 Playwright CI job

**问题**: `turbo.json` 定义 `test:e2e` 但 CI 不调用。

**修复** (Phase 3-4, 与 F3 合并交付):

```yaml
  e2e-frontend:
    name: "L2: Frontend E2E"
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
        with:
          version: 9
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
      - run: cd frontend && pnpm install --frozen-lockfile
      - run: cd frontend && pnpm exec playwright install --with-deps
      - run: cd frontend && pnpm run test:e2e
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: playwright-results
          path: frontend/test-results/
```

**前置**: F5 Dockerfile 或本地 dev server 作为测试后端。

**验收**: Playwright 测试在 CI 运行, trace 作为 artifact 上传。

---

## 5. Dimension B: 跨层集成承接链

完整实施规格见子计划:
`docs/governance/decisions/2026-02-19-cross-layer-gate-binding-impl-v1.0.md` (v1.0.1)

**摘要**:

| 产物组 | 内容 |
|--------|------|
| G0 (4 项) | 兼容前置修复: traceability whitelist-only, check_task_schema `matrix_refs: list[str]`, .gitignore, schema_version 1.0->1.1 |
| G1 | YAML schema 扩展: `xnodes` array + `xnode_coverage_min` |
| G2-G3 | YAML exit_criteria xnodes 字段 + go_no_go 阈值 |
| G4 | `check_xnode_coverage.py` (双口径: direct + semantic) |
| G5 | Makefile target (check-xnode-coverage / check-xnode-coverage-% / check-xnode-coverage-all) |
| G6 | CI `milestone-check.yml` 新增 xnode-coverage job |
| G7 | Phase 0-1 回溯审计 (`evidence/retrospective/`) |
| P2-P5 | 各 Phase 集成任务卡 (Tier-A) + `tests/e2e/cross/` + `frontend/tests/e2e/cross/` |

**Phase 2 hard/soft 分级** (基于 CI 环境依赖):
- hard (2): p2-x2-1 (FakeSessionFactory), p2-xf2-4 (纯脚本)
- soft (5): p2-x2-3/x2-4 (PG), p2-xf2-1 (全栈), p2-x2-5 (Prometheus), p2-x2-6 (Frontend)

**--all 模式**: 硬编码 `sys.exit(0)`, 禁止条件分支 (code review red line)。

---

## 6. Dimension C: 运维闭环落地

### 6.1 A 档: Phase 2-3 硬化 (3 项)

#### CA-1: 租户隔离运行时 gate

**当前**: `check_rls.sh` 仅静态扫描 migration 中 RLS 语句, 不做运行时越权验证。

**与 F3 合并**: `integration-tests` job 中运行 `tests/isolation/` 即可覆盖基础场景。

**增强**: 新增 `tests/isolation/test_tenant_crossover.py`:

```python
"""Runtime tenant isolation verification.

Validates:
1. Org-A user cannot query Org-B data (SELECT boundary)
2. SET app.current_org_id correctly scopes all queries
3. JOIN across tables maintains RLS enforcement
4. Concurrent org contexts don't leak data
"""

@pytest.mark.isolation
class TestTenantCrossover:
    async def test_cross_org_select_blocked(self, db_session): ...
    async def test_rls_scoped_join(self, db_session): ...
    async def test_concurrent_org_isolation(self, db_session): ...
```

**gate ID**: `p3-tenant-isolation-runtime`
**分级**: Phase 2 不设 gate (F3 先行); Phase 3 hard gate。
**验收**: 测试在 CI integration-tests job 中 PASS。

#### CA-2: Secrets 完整性检查

**当前**: `.env.example` 存在但无自动校验; `docker-compose.yml:10` 硬编码 dev 密码。

**新建**: `scripts/check_env_completeness.py`

```python
"""Verify .env.example covers all runtime config keys referenced in source.

Scans: src/ for os.environ[], os.getenv(), settings.* references
Compares: .env.example defined keys
Outputs: missing keys (FAIL), extra keys (INFO)
Exit: 0 if all runtime keys covered, 1 if missing
"""
```

**gate ID**: `p2-env-completeness` (soft gate)
**验收**: `uv run python scripts/check_env_completeness.py` exit 0。
**Phase 4 增强**: 接入 Vault/KMS 后增加 `secret-rotation-check`
(验证密钥 TTL, 轮换策略, 吊销能力, 审计追踪)。

#### CA-3: SBOM 签名 + Attestation

**当前**: `generate_sbom.sh` 生成 SPDX 2.3 JSON (`delivery/sbom.json`), 无签名。

**新建**: `scripts/sign_sbom.sh`

```bash
#!/usr/bin/env bash
# SBOM generation + cosign keyless signing (Sigstore)
set -euo pipefail
bash scripts/generate_sbom.sh --validate
cosign sign-blob --yes delivery/sbom.json --bundle delivery/sbom.json.bundle
cosign verify-blob delivery/sbom.json --bundle delivery/sbom.json.bundle \
  --certificate-identity-regexp=".*" --certificate-oidc-issuer-regexp=".*"
echo "SBOM signed and verified"
```

**CI 集成**: `semantic-checks` job 增加 step:
```yaml
      - name: Install cosign
        uses: sigstore/cosign-installer@v3
      - name: SBOM sign and verify
        run: bash scripts/sign_sbom.sh
```

**gate ID**: `p3-sbom-attestation` (Phase 3 soft, Phase 4 hard)
**前置**: CI runner 需要 cosign (sigstore/cosign-installer action)
**验收**: `cosign verify-blob delivery/sbom.json --bundle delivery/sbom.json.bundle` exit 0。

### 6.2 B 档: Phase 4 硬化 (6 项)

#### CB-1: 发布回滚 runbook + drill

**前置**: F5 Dockerfile 完成。

**产物**:
- `delivery/commercial/runbook/release-rollback.md`: 灰度/金丝雀/全量/回滚步骤
- `scripts/drill_release.sh`: dry-run 回滚演练
  - 模拟部署新版本 -> 健康检查失败 -> 触发回滚 -> 验证回滚完成
  - 计时: 回滚 < 5 分钟为 PASS
  - 输出: JSON 证据 (步骤/耗时/结果)

**gate ID**: `p4-release-drill`
**验收**: `bash scripts/drill_release.sh --dry-run` exit 0, 回滚耗时 < 5min。

#### CB-2: 灾备恢复 runbook + drill

**产物**:
- `delivery/commercial/runbook/dr-restore.md`: RTO/RPO 定义, 跨环境恢复步骤
  - RTO 目标: 30 分钟 (基础服务恢复)
  - RPO 目标: 1 小时 (数据丢失上限)
- `scripts/drill_dr_restore.sh`: 备份 -> 恢复 -> 数据一致性验证 drill
  - 输出: JSON 证据归档到 `evidence/release/`

**gate ID**: `p4-dr-restore-drill`
**验收**: `bash scripts/drill_dr_restore.sh --dry-run` exit 0。

#### CB-3: 事故管理 SLA 定义

**产物**: `delivery/commercial/incident-sla.yaml`

```yaml
incident_levels:
  P0:
    response_time: "15min"
    resolution_target: "4h"
    escalation: ["on-call-engineer", "engineering-lead", "CTO"]
  P1:
    response_time: "30min"
    resolution_target: "8h"
    escalation: ["on-call-engineer", "engineering-lead"]
  P2:
    response_time: "4h"
    resolution_target: "3d"
    escalation: ["team-lead"]

metrics:
  mtta_target: "15min"
  mttr_target_p0: "4h"
  mttr_target_p1: "8h"

on_call:
  rotation: "weekly"
  coverage: "24x7"
  suppression_rules: "deploy/monitoring/alerts.yml#suppression"
```

**验证脚本**: `scripts/check_incident_readiness.py`
- 检查 `incident-sla.yaml` 存在且 schema 合法
- 检查 `deploy/monitoring/alerts.yml` 中每条 critical 规则有 routing label
- 检查 runbook 目录中存在 P0/P1 对应的响应文档

**gate ID**: `p4-incident-readiness`
**验收**: `uv run python scripts/check_incident_readiness.py` exit 0。

#### CB-4: 外部依赖韧性 (chaos gate)

**产物**: `tests/e2e/cross/test_dependency_chaos.py`

```python
"""External dependency resilience verification.

Tests:
1. LLM provider unavailable -> graceful degradation (non-500)
2. Redis disconnected -> fallback to direct mode
3. PG slow query -> timeout + circuit breaker + 503
4. Object storage (MinIO) unreachable -> upload queue with retry
"""

@pytest.mark.e2e
class TestDependencyChaos:
    async def test_llm_unavailable_graceful(self): ...
    async def test_redis_disconnect_fallback(self): ...
    async def test_pg_slow_circuit_breaker(self): ...
    async def test_storage_unreachable_retry(self): ...
```

**gate ID**: `p4-dependency-chaos`
**前置**: F3 CI 服务容器; 降级/熔断逻辑已实现。
**验收**: 测试在 CI 中 PASS。

#### CB-5: 告警路由验证

**产物**: `scripts/check_alert_routing.py`

```python
"""Validate alert routing completeness.

Checks:
1. Every rule in alerts.yml has severity label
2. Critical/Warning rules have routing destination
3. Suppression rules reference valid alert names
4. On-call schedule file exists and is non-empty
"""
```

**gate ID**: `p4-alert-routing`
**验收**: `uv run python scripts/check_alert_routing.py` exit 0。

#### CB-6: 合规产物检查

**产物**: `scripts/check_compliance_artifacts.py`

```python
"""Validate compliance artifact existence and non-emptiness.

Required artifacts:
- delivery/commercial/dpa-template.md (Data Processing Agreement)
- delivery/commercial/privacy-policy.md
- delivery/commercial/data-retention-policy.md
- delivery/commercial/data-deletion-proof-template.md
- delivery/commercial/runbook/data-breach-response.md [EXISTS]
- delivery/commercial/runbook/supply-chain-response.md [EXISTS]
"""
```

**gate ID**: `p4-compliance-artifacts`
**验收**: `uv run python scripts/check_compliance_artifacts.py` exit 0。

### 6.3 C 档: Phase 5 人工 checklist (5 项)

以下不做 CI 自动 gate, 纳入 `operations-readiness-checklist.md` 作为 Phase 5 人工审查:

| # | 维度 | checklist 项 | 验证方式 |
|---|------|-------------|---------|
| 1 | 计费闭环 | 双账本一致性 + 幂等扣费 + 日对账报告 | 业务测试报告 + 财务审计 |
| 2 | 数据治理 | 数据分类文档 + 保留策略 + 删除可证明 (evidence 归档) | 文档审查 |
| 3 | 容量与性能 | 压测基线报告 (k6/artillery) + 容量模型 + 扩缩容策略 | 专项压测证据 |
| 4 | 客户运维 | SLA 报告模板 + 状态页 + 支持 SOP | 运营审查 |
| 5 | 商业化交付 | License/entitlement + 版本兼容矩阵 + 升级策略 | 产品审查 |

### 6.4 补充治理件

#### CC-1: operations-readiness-checklist.md

**路径**: `delivery/operations-readiness-checklist.md`

Phase 5 上线前阻断清单。包含 B 档 6 项运营证据确认 + C 档 5 项人工审查。
每项含验证命令或证据引用, 全部勾选方可签署 Go-Live。

#### CC-2: evidence/release/ 发版证据模板

**路径**: `evidence/release/template.json`

```json
{
  "version": "",
  "release_date": "",
  "gate_evidence": {
    "phase_gate": "evidence/ci/phase-gate.json",
    "coverage": "evidence/ci/coverage.xml",
    "security_scan": "evidence/ci/security-scan.json",
    "sbom": "delivery/sbom.json",
    "sbom_signature": "delivery/sbom.json.bundle"
  },
  "drill_evidence": {
    "release_rollback": "",
    "dr_restore": ""
  },
  "sign_off": {
    "engineering": "",
    "security": "",
    "operations": ""
  }
}
```

`.gitignore` 白名单:
```gitignore
!evidence/release/
!evidence/release/*.json
!evidence/ci/
!evidence/ci/*.json
!evidence/ci/*.xml
```

#### CC-3: 缺失 runbook 补充

在 `delivery/commercial/runbook/` 下新增 (补全现有 5 个模板的缺口):
- `release-rollback.md` (发布回滚)
- `dr-restore.md` (灾备恢复)
- `billing-reconciliation.md` (计费对账)

---

## 7. 统一执行顺序

```
Step 0: 兼容前置修复 (Dim-B G0)
  0a. scripts/task_card_traceability_check.py (whitelist-only, 不改覆盖率分母)
  0b. scripts/check_task_schema.py (matrix_refs: list[str], 单 ID 一行)
  0c. .gitignore (retrospective + release + ci 白名单)
  0d. 验证: make check-schema && python3 scripts/task_card_traceability_check.py

Step 1: 工程链基础硬化 (Dim-A F1+F2)
  1a. [F1] 分支保护 或 CI merge-readiness job + bootstrap hook 自动安装
  1b. [F2] ci.yml test-backend 增加 --cov --cov-fail-under=80
  1c. 验证: 覆盖率 < 80% 的测试 PR -> CI 红

Step 2: 框架搭建 (Dim-B G1-G7 + Dim-C CA-2)
  2a. YAML schema 扩展 (G1) + schema_version 1.0 -> 1.1
  2b. check_xnode_coverage.py (G4)
  2c. check_env_completeness.py (CA-2)
  2d. Makefile targets (G5)
  2e. milestone-check.yml xnode-coverage job (G6)
  2f. Phase 0-1 回溯审计 (G7)
  2g. milestone-matrix.md:154 XF 范围修复
  2h. 验证: make check-xnode-coverage (Phase 2 direct_rate = 0.0)
      + uv run python scripts/check_env_completeness.py

Step 3: Phase 2 补全 (Dim-B P2)
  3a. 新建 docs/task-cards/00-跨层集成/phase-2-integration.md (5 张卡)
  3b. 新建 tests/e2e/cross/ + Phase 2 测试文件
  3c. milestone-matrix.yaml Phase 2 exit_criteria + go_no_go (G2, G3)
  3d. 验证: make check-xnode-coverage-2 (direct_rate >= 0.40)

Step 4: Phase 2 Gate Review
  4a. make verify-phase-2-archive
  4b. make check-xnode-coverage-2
  4c. 归档证据

Step 5: CI 服务环境 + Phase 3 准备 (Dim-A F3+F4+F5 + Dim-C CA-1+CA-3)
  5a. [F3] ci.yml 新增 integration-tests job (PG + Redis service)
  5b. [CA-1] tests/isolation/test_tenant_crossover.py
  5c. [F5] Dockerfile (multi-stage build)
  5d. [CA-3] sign_sbom.sh + cosign CI 集成
  5e. [F4] lint_workflow_checks.py 扩展到 milestone-matrix.yaml
  5f. 验证: CI integration-tests 绿; docker build 成功; SBOM 签名可验证

Step 6: Phase 3 激活 (Dim-B P3)
  6a. Phase 3 集成任务卡 + 测试文件
  6b. YAML Phase 3 exit_criteria + xnodes
  6c. tenant-isolation-runtime 从 soft 升级为 hard
  6d. sbom-attestation 设为 soft
  6e. 验证: check-xnode-coverage-3 >= 0.70

Step 7: Phase 4 激活 (Dim-B P4 + Dim-C CB-1~6 + Dim-A F6+F7)
  7a. [CB-1] release-rollback runbook + drill_release.sh
  7b. [CB-2] dr-restore runbook + drill_dr_restore.sh
  7c. [CB-3] incident-sla.yaml + check_incident_readiness.py
  7d. [CB-4] test_dependency_chaos.py
  7e. [CB-5] check_alert_routing.py
  7f. [CB-6] check_compliance_artifacts.py
  7g. [F6] 证据持久归档 CI step
  7h. [F7] Playwright CI job
  7i. Phase 4 集成任务卡 + 测试
  7j. 验证: check-xnode-coverage-4 >= 0.90; CB-1~6 gate 全部 PASS

Step 8: Phase 5 激活 (Dim-B P5 + Dim-C CC-*)
  8a. [CC-1] operations-readiness-checklist.md 全部项通过
  8b. [CC-2] evidence/release/template.json 填写
  8c. [CC-3] check_commercial_readiness.py
  8d. Phase 5 集成任务卡 + 测试
  8e. 验证: check-xnode-coverage-5 = 1.0; operations checklist 全部勾选
```

---

## 8. 验收标准矩阵

### 8.1 Dimension A 验收

| 检查项 | 命令 | 期望 |
|--------|------|------|
| 分支保护 | `gh api .../branches/main/protection` 或 CI merge-readiness | 200 或 job 存在 |
| 覆盖率 gate | CI test-backend with --cov | fail_under=80 生效 |
| 服务容器 | CI integration-tests job | tests/isolation/ 全部 PASS |
| 命令白名单 | `lint_workflow_checks.py` 覆盖 milestone-matrix.yaml | exit 0 |
| 容器化 | `docker build -t diyu-agent:test .` | 成功 + trivy 通过 |
| 证据归档 | `git ls-files evidence/ci/` | 非空 |
| 前端 E2E | CI e2e-frontend job | Playwright PASS |

### 8.2 Dimension B 验收

| 检查项 | 命令 | 期望 |
|--------|------|------|
| Schema 校验 | jsonschema validate | 无 error |
| 现有 gate 不退化 | `make verify-phase-current` | 全部 PASS |
| 可追溯性 | `python3 scripts/task_card_traceability_check.py` | 新卡不报 dangling |
| 任务卡 schema | `python3 scripts/check_task_schema.py --mode full` | Tier-A 通过 |
| xnode 覆盖率 | `make check-xnode-coverage-2` | direct_rate >= 0.40 |
| --all 不阻断 | `make check-xnode-coverage-all` | exit 0 (始终) |

### 8.3 Dimension C 验收

| 检查项 | 命令 | 期望 |
|--------|------|------|
| Secrets 完整性 | `python3 scripts/check_env_completeness.py` | exit 0 |
| 租户隔离运行时 | CI integration-tests: `pytest tests/isolation/` | 全部 PASS |
| SBOM 签名 | `bash scripts/sign_sbom.sh` | exit 0 |
| 发布 drill | `bash scripts/drill_release.sh --dry-run` | exit 0, < 5min |
| 灾备 drill | `bash scripts/drill_dr_restore.sh --dry-run` | exit 0 |
| 事故就绪 | `python3 scripts/check_incident_readiness.py` | exit 0 |
| 依赖韧性 | `pytest tests/e2e/cross/test_dependency_chaos.py` | 全部 PASS |
| 告警路由 | `python3 scripts/check_alert_routing.py` | exit 0 |
| 合规产物 | `python3 scripts/check_compliance_artifacts.py` | exit 0 |
| 运营就绪 | `operations-readiness-checklist.md` 全部勾选 | 人工确认 |

---

## 9. Phase 覆盖率阈值矩阵

| Phase | xnode_min (B) | CI 服务 (A) | 运维 gate (C) | 阻断级别 |
|-------|---------------|-------------|---------------|---------|
| P0-1 | 回溯审计 | 无变更 | 无 | -- |
| P2 | >= 0.40 | Fake only | CA-2 soft | informational |
| P3 | >= 0.70 | PG + Redis | CA-1 hard, CA-3 soft | P3 required |
| P4 | >= 0.90 | + Playwright | CB-1~6 hard | P4 required |
| P5 | = 1.00 | 全量 | CC-1 checklist | Go-Live blocking |

---

## 10. 14 维度可追溯矩阵

| # | 维度 | 计划项 | 档位 | Phase | gate ID |
|---|------|--------|------|-------|---------|
| 1 | 发布治理 | CB-1 + F5 | B | P4 | p4-release-drill |
| 2 | 生产配置 | CA-2 -> P4 Vault | A->B | P2->P4 | p2-env-completeness -> p4-secret-rotation |
| 3 | 灾备连续性 | CB-2 | B | P4 | p4-dr-restore-drill |
| 4 | 计费闭环 | CC-1 #1 | C | P5 | 人工审查 |
| 5 | 告警到处置 | CB-5 | B | P4 | p4-alert-routing |
| 6 | 事故管理 | CB-3 | B | P4 | p4-incident-readiness |
| 7 | 多租户安全 | CA-1 + F3 | A | P3 | p3-tenant-isolation-runtime |
| 8 | 合规法务 | CB-6 | B | P4 | p4-compliance-artifacts |
| 9 | 数据治理 | CC-1 #2 | C | P5 | 人工审查 |
| 10 | 供应链安全 | CA-3 | A | P3 | p3-sbom-attestation |
| 11 | 容量与性能 | CC-1 #3 | C | P5 | 人工审查 |
| 12 | 外部依赖韧性 | CB-4 | B | P4 | p4-dependency-chaos |
| 13 | 客户运维 | CC-1 #4 | C | P5 | 人工审查 |
| 14 | 商业化交付 | CC-1 #5 | C | P5 | 人工审查 |

---

## 11. 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0 | 2026-02-19 | 初始版本: 三维度统一计划 (Dim-A 7项 + Dim-B 引用子计划 + Dim-C 14维度3档) |
| v1.0.1 | 2026-02-20 | 终审落盘: Proposed → Approved; 补充终审记录与各维度实施进度 |

---

## 12. 终审记录

### 终审日期: 2026-02-20

### 各维度 Phase 2 实施进度

| 维度 | 计划项 (Phase 2 范围) | 实施状态 | 证据 |
|------|----------------------|---------|------|
| **Dim-A F1** | CI merge-readiness job | 已落盘 | ci.yml:491 merge-readiness job |
| **Dim-A F2** | CI 覆盖率 gate --cov-fail-under=80 | 已落盘 | ci.yml:140-141 |
| **Dim-A F3** | CI PG/Redis service container | 已落盘 | ci.yml integration-tests job |
| **Dim-B G0-G7** | 跨层集成框架全套 | 已落盘 | 见子计划终审记录 |
| **Dim-B P2** | Phase 2 集成任务卡 + E2E 测试 | 已落盘 | 22/22 tests PASS, 0 skip |
| **Dim-C CA-2** | check_env_completeness.py | 已落盘 | PASS (8/8 keys), 接入 CI + milestone-matrix |

### 后续 Phase 待实施项 (不阻断当前终审)

| 维度 | 计划项 | 目标 Phase |
|------|--------|-----------|
| Dim-A F4 | lint_workflow_checks.py 扩展 | P3 |
| Dim-A F5 | Dockerfile 多阶段构建 | P3 |
| Dim-A F6 | 证据持久归档 CI step | P4 |
| Dim-A F7 | 前端 Playwright CI job | P3-4 |
| Dim-C CA-1 | test_tenant_crossover.py | P3 |
| Dim-C CA-3 | sign_sbom.sh | P3 |
| Dim-C CB-1~6 | 运维 B 档 6 项 | P4 |
| Dim-C CC-1~3 | 运维 C 档 3 项 | P5 |

### Gate 验证结果

```
make verify-phase-0  → GO (10/10 hard, 2/2 soft)
make verify-phase-1  → GO (9/9 hard)
make verify-phase-2  → GO (17/17 hard, 6/6 soft)
check_xnode_coverage --phase 2 → GO (threshold 0.40)
check_env_completeness → PASS
check_no_vacuous_pass → PASS (8 files, 0 skip)
CI merge-readiness → 27/27 checks green (PR #26)
```

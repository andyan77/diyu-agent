# 跨层集成承接链补全 -- 实施计划 v1.0

> 日期: 2026-02-19
> 状态: Approved (终审通过, Phase 2 已落盘执行)
> 终审日期: 2026-02-20
> 上游决议: `docs/governance/decisions/2026-02-19-cross-layer-gate-binding.md`
> 审查证据: `evidence/governance-reviews/cross-layer-integration-gap-v1.3-20260219.md`
> 变更范围: 治理体系增强 (不另建系统)

---

## 0. 设计原则

1. 在现有治理体系内补一条"集成承接链" (X/XF/XM -> INT 任务卡 -> gate 命令)
2. 不另建独立系统; 不引入 xnode-gate-map.yaml 间接层
3. check_xnode_coverage.py 与 verify_phase.py 分职责, verify_phase.py 不改动
4. 按 Phase 拆分任务卡文件, 不做大一统巨文件
5. Phase 0-1 不改历史 gate, 只做回溯审计报告
6. 覆盖率阈值渐进收敛, 不一步到位
7. 双口径输出: direct (gate 判定) + semantic (仅辅助)

---

## 1. 产物清单

| # | 产物 | 路径 | 类型 |
|---|------|------|------|
| G0 | 兼容前置修复包 | 见 Section 2 | 修改 |
| G1 | YAML schema 扩展 | `delivery/milestone-matrix.schema.yaml` | 修改 |
| G2 | YAML exit_criteria 增加 xnodes 字段 | `delivery/milestone-matrix.yaml` | 修改 |
| G3 | YAML go_no_go 增加 xnode_coverage_min | `delivery/milestone-matrix.yaml` | 修改 |
| G4 | 覆盖率校验脚本 | `scripts/check_xnode_coverage.py` | 新建 |
| G5 | Makefile target | `Makefile` | 修改 |
| G6 | CI workflow | `.github/workflows/milestone-check.yml` | 修改 |
| G7 | Phase 0-1 回溯审计 | `evidence/retrospective/phase-0-1-xnode-audit.json` | 新建 |
| P2 | Phase 2 集成任务卡 | `docs/task-cards/00-跨层集成/phase-2-integration.md` | 新建 |
| P3 | Phase 3 集成任务卡 | `docs/task-cards/00-跨层集成/phase-3-integration.md` | 新建 (Phase 3 激活时) |
| P4 | Phase 4 集成任务卡 | `docs/task-cards/00-跨层集成/phase-4-integration.md` | 新建 (Phase 4 激活时) |
| P5 | Phase 5 集成任务卡 | `docs/task-cards/00-跨层集成/phase-5-integration.md` | 新建 (Phase 5 激活时) |
| T* | 跨层 E2E 测试文件 | `tests/e2e/cross/`, `frontend/tests/e2e/cross/` | 新建 (按 Phase 递增) |

---

## 2. G0: 兼容前置修复包 (必须在 G1-G7 之前完成)

所有后续步骤依赖此修复包先行落地, 否则现有门禁会对新格式产生假阳性阻断。

### 2.1 task_card_traceability_check.py -- 扩展 dangling_refs 白名单 (不改覆盖率分母)

**问题**: `load_milestone_ids()` (line 51-74) 仅从 `milestone-matrix.yaml` 的
`milestones[]` 数组提取 ID。新任务卡的 `> 矩阵条目: X2-1` 引用会被判为 `dangling_refs`。

**约束**: 不能将 X/XF/XM 节点并入 `milestone_ids` 集合, 否则会改变现有
覆盖率分母 (从 ~132 膨胀到 ~182), 导致现有 gate 语义退化。

**修复**: 新增 `load_xnode_ids()` 函数, 但仅用于 dangling_refs 白名单:

```python
XNODE_RE = re.compile(r"\|\s*(X[FM]?\d+-\d+)\s*\|")
CROSSCUTTING_PATH = Path("docs/governance/milestone-matrix-crosscutting.md")

def load_xnode_ids(*, crosscutting_path: Path | None = None) -> set[str]:
    """Extract X/XF/XM node IDs from crosscutting.md Section 4."""
    path = crosscutting_path or CROSSCUTTING_PATH
    if not path.exists():
        return set()
    ids: set[str] = set()
    in_section4 = False
    for line in path.read_text().splitlines():
        if line.startswith("## 4."):
            in_section4 = True
        elif line.startswith("## ") and not line.startswith("## 4."):
            if in_section4:
                break
        if in_section4:
            for m in XNODE_RE.finditer(line):
                ids.add(m.group(1))
    return ids
```

在 `compute_result()` (line 152-154) 中, 仅修改 dangling 判定逻辑:

```python
# 覆盖率分母: 仍然只用 milestone_ids (不变, 不并入 xnode_ids)
main_block = _coverage_block(milestone_ids, main_covered)
all_block = _coverage_block(milestone_ids, all_covered)

# dangling 判定: 扩展白名单, X/XF/XM 引用不再报假阳性
known_valid_ids = milestone_ids | xnode_ids
dangling = sorted(all_card_refs - known_valid_ids)
```

这样既防止 X 引用被报 dangling, 又不改变现有 milestone 覆盖率口径。

### 2.2 check_task_schema.py -- matrix_ref 数据结构升级 (单值 -> 列表)

**问题分析** (3 层):

1. **正则层**: `MATRIX_REF_RE = re.compile(r">\s*矩阵条目:\s*(\S+)")` (line 36) 只捕获
   单行中第一个非空 token。若在同一行写 `> 矩阵条目: X2-1, X2-2` 则捕获 `X2-1,`
   (含尾随逗号)。
2. **数据结构层**: `matrix_ref: str | None = None` (CardInfo line 95) 是单值字段;
   `matrix_ref = mat_match.group(1)` (line 168) 对每次匹配做覆盖而非追加。
   当一张卡有多行 `> 矩阵条目:` 时, 只保留最后一行的值。
3. **校验层**: `card.matrix_ref not in matrix_ids` (line 310) 按单值比较;
   若 matrix_ref 含逗号或空格则必定不在 matrix_ids 中, 产生假阳性。

仅改正则不够 -- 数据结构和校验逻辑必须同步修改。

**修复方案**: 采用 "单 ID 一行" 任务卡格式 + `matrix_ref` -> `matrix_refs: list[str]` 累积。

**Step 1 -- 数据结构** (CardInfo, line 86-97):

```python
@dataclass
class CardInfo:
    task_id: str
    title: str
    file: str
    line: int
    tier: str
    phase: int
    fields: dict = field(default_factory=dict)
    matrix_refs: list = field(default_factory=list)  # was: matrix_ref: str | None = None
    exceptions: list = field(default_factory=list)
    raw_lines: list = field(default_factory=list)
```

**Step 2 -- 解析** (parse_card, line 148-168):

```python
    matrix_refs = []  # was: matrix_ref = None
    ...
    mat_match = MATRIX_REF_RE.search(line)
    if mat_match:
        matrix_refs.append(mat_match.group(1))  # was: matrix_ref = mat_match.group(1)
```

正则本身不需要改 -- 每行仍然只捕获一个 `\S+` token。
多节点卡用多行 `> 矩阵条目:` 表达 (每行一个 ID), 示例:

```
> 矩阵条目: X2-1
> 矩阵条目: X2-2
> 矩阵条目: X2-3
```

**Step 3 -- 校验** (validate_card, line 297-325):

```python
    # matrix-orphan: 无矩阵引用
    if not card.matrix_refs:
        violations.append(...)

    # matrix-invalid: 任一引用不在合法集合中
    elif matrix_ids:
        for ref in card.matrix_refs:
            base_ref = ref.split()[0] if " " in ref else ref
            if base_ref not in matrix_ids:
                violations.append(
                    Violation(
                        card_id=card.task_id,
                        file=card.file,
                        line=card.line,
                        severity=Severity.BLOCK,
                        rule="matrix-invalid",
                        message=f"Matrix reference '{ref}' not found in milestone-matrix files",
                    )
                )
```

**Step 4 -- 向后兼容**: `collect_matrix_ids()` (line 224-232) 使用
`r"\b([A-Z]+\d+-\d+)\b"` 已能匹配 X2-1, XF2-4, XM0-1 等格式, 无需修改。

**受影响文件**: 仅 `scripts/check_task_schema.py` (约 15 行改动)。
现有任务卡全部是单行单 ID 格式, 升级后不影响已有卡的解析结果。

### 2.3 .gitignore -- 增加 retrospective 白名单

**问题**: `evidence/*` (line 67) 会忽略 `evidence/retrospective/`。

**修复**: 增加白名单:

```gitignore
# Evidence (CI-generated, not committed manually)
evidence/*
!evidence/governance-reviews/
!evidence/governance-reviews/*.md
!evidence/retrospective/              # <-- 新增
!evidence/retrospective/*.json        # <-- 新增
!evidence/v4-phase2/
evidence/v4-phase2/*
!evidence/v4-phase2/.gitkeep
```

### 2.4 schema_version bump: 1.0 -> 1.1

**问题**: 新增 `xnodes` 和 `xnode_coverage_min` 字段改变了 schema 语义。
虽然向后兼容, 但治理口径上应显式 minor bump。

**修复**:
- `delivery/milestone-matrix.schema.yaml` title 注释更新
- `delivery/milestone-matrix.yaml` line 6: `schema_version: "1.1"`
- `milestone-matrix.schema.yaml` properties.schema_version.pattern 保持 `"^\d+\.\d+$"` (已兼容)

---

## 3. G1: YAML Schema 扩展

**文件**: `delivery/milestone-matrix.schema.yaml`

在 `definitions.Criterion.properties` 中增加:

```yaml
      xnodes:
        type: array
        items:
          type: string
          pattern: "^X[FM]?\\d+-\\d+$"
        description: "Cross-layer verification nodes covered by this criterion"
```

在 `definitions.Phase.properties.go_no_go.properties` 中增加:

```yaml
      xnode_coverage_min:
        type: number
        minimum: 0
        maximum: 1
        description: "Minimum xnode coverage rate for Go decision (0.0 to 1.0)"
```

`Criterion` 的 `additionalProperties` 不设 false (当前 schema 未设, 已兼容)。

---

## 4. G2 + G3: milestone-matrix.yaml 变更

### 4.1 schema_version bump

```yaml
schema_version: "1.1"
```

### 4.2 Phase 2 exit_criteria 新增跨层 gate

**CI 环境约束**: 当前 `ci.yml` test-e2e job (line 151-158) 运行在 bare
`ubuntu-latest`, 无 PG/Redis service container。新增跨层 gate 按服务依赖分级:

- **hard**: 可用 Fake adapter / 纯脚本完成, 无外部服务依赖
- **soft**: 需要 PG/Redis/Prometheus 或全栈 (Backend+Frontend) 环境

满足 CI 可运行条件后, soft 可提升为 hard (需 PR + gate review 审批)。

```yaml
  phase_2:
    exit_criteria:
      hard:
        # ... 现有 13 条保持不变 ...

        # --- 跨层集成 gate (新增, hard = Fake adapter 可运行) ---
        - id: "p2-x2-1-conversation-loop"
          description: "Cross-layer: full conversation loop E2E (X2-1)"
          check: "uv run pytest tests/e2e/cross/test_conversation_loop.py -v --tb=short"
          xnodes: [X2-1]
          # 依据: 现有 tests/e2e/test_conversation_loop.py 已用 FakeSessionFactory,
          # 新 cross/ 版本可沿用同一模式, 无外部服务依赖

        - id: "p2-xf2-4-openapi-sync"
          description: "Cross-layer FE: OpenAPI type consistency (XF2-4)"
          check: "bash scripts/check_openapi_sync.sh"
          xnodes: [XF2-4]
          # 依据: 纯静态 diff 脚本, 无运行时依赖

      soft:
        # ... 现有 p2-streaming 保持不变 ...

        # --- 跨层集成 gate (新增, soft = 需外部服务或全栈环境) ---
        - id: "p2-x2-3-memory-evolution"
          description: "Cross-layer: memory evolution closed loop (X2-3)"
          check: "uv run pytest tests/e2e/cross/test_memory_evolution.py -v --tb=short"
          xnodes: [X2-3]
          # soft 原因: Memory evolution 依赖 PG pgvector 写入 [ENV-DEP: PG]
          # 提升条件: CI 增加 PG service container 后可升 hard

        - id: "p2-x2-4-token-backpressure"
          description: "Cross-layer: token budget backpressure (X2-4)"
          check: "uv run pytest tests/e2e/cross/test_token_backpressure.py -v --tb=short"
          xnodes: [X2-4]
          # soft 原因: 需要 token_billing 表 + PG [ENV-DEP: PG]

        - id: "p2-xf2-1-login-to-streaming"
          description: "Cross-layer FE: login -> org -> chat -> streaming (XF2-1/2/3)"
          check: "cd frontend && pnpm exec playwright test tests/e2e/cross/web/login-to-streaming.spec.ts"
          xnodes: [XF2-1, XF2-2, XF2-3]
          # soft 原因: Playwright 需全栈运行 (Backend + Frontend) [ENV-DEP: FULLSTACK]

        - id: "p2-x2-5-golden-signals"
          description: "Cross-layer: 4 golden signals e2e (X2-5)"
          check: "uv run pytest tests/e2e/cross/test_golden_signals.py -v --tb=short"
          xnodes: [X2-5]
          # soft 原因: 需要 Prometheus 可查询 [ENV-DEP: PROMETHEUS]

        - id: "p2-x2-6-fe-error-boundary"
          description: "Cross-layer: FE error boundary closed loop (X2-6)"
          check: "cd frontend && pnpm exec playwright test tests/e2e/cross/web/error-boundary.spec.ts"
          xnodes: [X2-6]
          # soft 原因: Playwright 需 Frontend dev server [ENV-DEP: FRONTEND]

    go_no_go:
      hard_pass_rate: 1.0
      xnode_coverage_min: 0.40
      approver: "architect"
```

**hard/soft 分级汇总 (Phase 2)**:

| gate | 分级 | 环境依赖 | 提升条件 |
|------|------|---------|---------|
| p2-x2-1 (conversation-loop) | hard | FakeSessionFactory | -- |
| p2-xf2-4 (openapi-sync) | hard | 纯脚本 | -- |
| p2-x2-3 (memory-evolution) | soft | PG + pgvector | CI 增加 PG service |
| p2-x2-4 (token-backpressure) | soft | PG | CI 增加 PG service |
| p2-xf2-1 (login-to-streaming) | soft | Backend + Frontend | CI 增加 fullstack job |
| p2-x2-5 (golden-signals) | soft | Prometheus | CI 增加 monitoring stack |
| p2-x2-6 (fe-error-boundary) | soft | Frontend dev server | CI 增加 frontend job |

### 4.3 Phase 3-5 go_no_go 阈值 (仅阈值, gate 条目在各 Phase 激活时补全)

```yaml
  phase_3:
    go_no_go:
      hard_pass_rate: 1.0
      xnode_coverage_min: 0.70
      approver: "architect"

  phase_4:
    go_no_go:
      hard_pass_rate: 1.0
      xnode_coverage_min: 0.90
      approver: "architect"

  phase_5:
    go_no_go:
      hard_pass_rate: 1.0
      xnode_coverage_min: 1.0
      approver: "architect"
```

### 4.4 Phase 3 exit_criteria 跨层 gate (Phase 3 激活时补全, 示例)

```yaml
  phase_3:
    exit_criteria:
      hard:
        # ... 现有 4 条保持不变 ...

        - id: "p3-x3-1-skill-e2e"
          description: "Cross-layer: skill full loop E2E (X3-1)"
          check: "uv run pytest tests/e2e/cross/test_skill_e2e.py -v --tb=short"
          xnodes: [X3-1]

        - id: "p3-x3-knowledge-integration"
          description: "Cross-layer: knowledge FK + promotion + admin + audit (X3-2/3/4/6)"
          check: "uv run pytest tests/e2e/cross/test_knowledge_integration.py -v --tb=short"
          xnodes: [X3-2, X3-3, X3-4, X3-6]

        - id: "p3-x3-5-content-security"
          description: "Cross-layer: content security pipeline (X3-5, XM1-2)"
          check: "uv run pytest tests/e2e/cross/test_content_security.py -v --tb=short"
          xnodes: [X3-5, XM1-2]

        - id: "p3-xf3-fe-integration"
          description: "Cross-layer FE: skill + knowledge + org config (XF3-1/2/3)"
          check: "cd frontend && pnpm exec playwright test tests/e2e/cross/"
          xnodes: [XF3-1, XF3-2, XF3-3]

      soft:
        # ... 现有 p3-graph-perf 保持不变 ...

        - id: "p3-xm1-1-media-upload"
          description: "Cross-layer: personal media upload E2E (XM1-1)"
          check: "uv run pytest tests/e2e/cross/test_media_upload.py -v --tb=short"
          xnodes: [XM1-1]
```

Phase 4/5 exit_criteria 跨层 gate 在各 Phase 激活时添加, 遵循同一模式。

---

## 5. G4: scripts/check_xnode_coverage.py

**职责**: 单一职责 -- 校验 X/XF/XM 节点被 exit_criteria 覆盖的程度。

**接口**:

```
Usage:
    python3 scripts/check_xnode_coverage.py --phase N [--json]
    python3 scripts/check_xnode_coverage.py --current [--json]
    python3 scripts/check_xnode_coverage.py --all [--json]

Exit codes:
    0 - Coverage meets threshold (or --all mode, which never blocks)
    1 - Coverage below threshold
    2 - Configuration error

Notes:
    --current: reads current_phase from YAML, applies xnode_coverage_min threshold
    --phase N: checks specific phase, applies xnode_coverage_min threshold
    --all: reports all phases, NEVER blocks (informational only)
```

**输入**:
- `docs/governance/milestone-matrix-crosscutting.md` Section 4 (节点定义源)
- `delivery/milestone-matrix.yaml` exit_criteria (xnodes 字段 + go_no_go.xnode_coverage_min)

**输出**: 双口径 JSON 报告。

```json
{
  "phase": "phase_3",
  "timestamp": "2026-02-19T...",
  "nodes": {
    "total": 11,
    "phase_nodes": ["X3-1", "X3-2", "..."]
  },
  "direct_coverage": {
    "rate": 0.72,
    "covered": ["X3-1", "X3-2", "X3-3", "X3-4", "X3-5", "X3-6", "XM1-2", "XF3-1"],
    "missing": ["XM1-1", "XF3-2", "XF3-3"]
  },
  "semantic_coverage": {
    "rate": 0.91,
    "additional": [
      {"node": "XM1-1", "matched_check": "p3-xm1-1-media-upload", "rule": "path_prefix"}
    ],
    "rules_applied": ["path_prefix"]
  },
  "validation": {
    "orphan_xnodes": [],
    "untagged_checks": ["p3-graph-perf"]
  },
  "gate": {
    "threshold": 0.70,
    "decision": "GO",
    "basis": "direct"
  }
}
```

**semantic 规则** (确定性, 可复现):

```python
SEMANTIC_RULES = [
    {
        "name": "path_prefix",
        "description": "check command test path shares prefix with node verification method path",
        "match": lambda check_path, node_path: (
            check_path and node_path and
            (check_path.startswith(node_path) or node_path.startswith(check_path))
        ),
    },
]
```

不做模糊语义匹配、不做关键词相似度、不做 LLM 推断。

**双向校验**:
- 正向: xnodes 中引用的 ID 必须存在于 crosscutting.md Section 4
- 反向: 输出未被任何 xnodes 引用的节点清单 (缺口)
- 告警: 有 check 但无 xnodes 的条目 (疑似漏标, 归入 untagged_checks)

**--all 模式约束 (STRICT)**:

`--all` exit code **必须硬编码为 0**, 禁止任何条件分支改变此行为:

```python
def main():
    ...
    if args.all:
        for phase in all_phases:
            report = check_phase(phase)
            reports.append(report)
        print(json.dumps(reports, indent=2))
        sys.exit(0)  # ALWAYS 0 -- --all is informational only, NEVER blocks
    ...
```

实现层强约束:
- `--all` 代码路径中禁止调用 `check_threshold()` 或任何返回非零的逻辑
- 仅 `--current` 和 `--phase N` 模式根据 `xnode_coverage_min` 阈值决定 exit code
- 原因: 未激活 Phase (P3-P5) 尚无 gate 条目, 若 `--all` 可阻断则 CI 永远红
- Code review 时此为必检项 (red line)

---

## 6. G5: Makefile target

在 Schema Validation section 中增加:

```makefile
check-xnode-coverage: ## Check X/XF/XM node coverage (current phase)
	@$(PYTHON) $(SCRIPTS)/check_xnode_coverage.py --current --json

check-xnode-coverage-%: ## Check xnode coverage for phase N (e.g., make check-xnode-coverage-3)
	@$(PYTHON) $(SCRIPTS)/check_xnode_coverage.py --phase $* --json

check-xnode-coverage-all: ## Report xnode coverage for all phases (informational)
	@$(PYTHON) $(SCRIPTS)/check_xnode_coverage.py --all --json
```

---

## 7. G6: CI workflow 变更

**文件**: `.github/workflows/milestone-check.yml`

变更: 增加 `xnode-coverage` job, 触发路径增加 crosscutting.md 和脚本。

```yaml
name: Milestone Check

on:
  pull_request:
    branches: [main, develop]
    paths:
      - "delivery/milestone-matrix.yaml"
      - "delivery/milestone-matrix.schema.yaml"
      - "docs/governance/milestone-matrix*.md"
      - "scripts/milestone_aggregator.py"
      - "scripts/check_acceptance_commands.sh"
      - "scripts/check_xnode_coverage.py"

jobs:
  # ... 现有 yaml-integrity, milestone-aggregation, acceptance-commands 保持不变 ...

  xnode-coverage:
    name: "XNode Coverage"
    runs-on: ubuntu-latest
    needs: yaml-integrity
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv sync --dev --frozen
      - name: Check xnode coverage (current phase, gated)
        run: uv run python scripts/check_xnode_coverage.py --current --json
      - name: Report xnode coverage (all phases, informational)
        run: uv run python scripts/check_xnode_coverage.py --all --json
        if: always()
```

**阻断策略**: Phase 2-3 期间 xnode-coverage 为 informational (不加入 required
status checks)。Phase 4 起根据阈值收敛情况升级为 required。

---

## 8. G7: Phase 0-1 回溯审计

**文件**: `evidence/retrospective/phase-0-1-xnode-audit.json`

**生成方式**: `python3 scripts/check_xnode_coverage.py --phase 0 --json` +
`python3 scripts/check_xnode_coverage.py --phase 1 --json` 输出合并。

**内容**: 标准双口径报告, 明确标注为事后分析:

```json
{
  "report_type": "retrospective_audit",
  "note": "Post-hoc analysis of completed phases. Not a gate modification.",
  "generated_at": "...",
  "phases": {
    "phase_0": {"direct_coverage": {"rate": 0.0, "...": "..."}, "semantic_coverage": {"...": "..."}},
    "phase_1": {"direct_coverage": {"rate": 0.0, "...": "..."}, "semantic_coverage": {"...": "..."}}
  }
}
```

**不做**: 不修改 Phase 0/1 的 exit_criteria / go_no_go; 不在 evidence/phase-0/
或 evidence/phase-1/ 中写入新文件。

---

## 9. P2: Phase 2 集成任务卡

**文件**: `docs/task-cards/00-跨层集成/phase-2-integration.md`

**遵循**: `task-card-schema-v1.0.md` Tier-A (Section 1.3: 跨层集成卡强制 Tier-A)

**矩阵引用格式约定**: 严格使用 "单 ID 一行" 格式:

```
> 矩阵条目: X2-1
> 矩阵条目: X2-2
> 矩阵条目: X2-3
```

此格式与 G0 Section 2.2 的 `matrix_refs: list[str]` 累积逻辑配合:
每行 `> 矩阵条目:` 匹配一次正则, append 到列表。
禁止逗号分隔 (如 `> 矩阵条目: X2-1, X2-2`), 避免正则不匹配或捕获含逗号字符串。

**聚合规则**: 同一 Phase + 参与层重叠 + 可共享 E2E 测试 -> 合并为一张卡

**Phase 2 卡清单 (5 张)**:

| 卡 ID | 覆盖节点 | 聚合依据 |
|--------|---------|---------|
| TASK-INT-P2-CONV | X2-1, X2-2, X2-3 | 共享对话闭环测试链路 |
| TASK-INT-P2-TOKEN | X2-4 | 独立: Token 反压链路 |
| TASK-INT-P2-OBS | X2-5, X2-6 | 共享可观测性测试 |
| TASK-INT-P2-FE | XF2-1, XF2-2, XF2-3 | 共享 Playwright suite |
| TASK-INT-P2-OPENAPI | XF2-4 | 复用现有 check, 仅增加 xnodes 绑定 |

### TASK-INT-P2-CONV

```
> 矩阵条目: X2-1
> 矩阵条目: X2-2
> 矩阵条目: X2-3

**目标**: 对话闭环 + 流式回复 + Memory Evolution 三条跨层链路通过 E2E 验证
**范围**: tests/e2e/cross/test_conversation_loop.py, tests/e2e/cross/test_memory_evolution.py
**范围外**: 前端 Playwright 测试 / 性能基准
**依赖**: TASK-B2-1, TASK-MC2-5, TASK-G2-2
**风险**:
  - 数据依赖: 需要 PG + Redis 全栈环境 [ENV-DEP]
  - 跨层耦合: Brain -> MemoryCore -> Gateway 三层交互
**兼容策略**: 新增测试, 无破坏性变更
**验收命令**:
  uv run pytest tests/e2e/cross/test_conversation_loop.py tests/e2e/cross/test_memory_evolution.py -v
  # 期望: 全部 PASS
**回滚方案**: git revert (仅测试文件, 无 DDL)
**证据**: CI artifact / evidence/phase-2/
**决策记录**: 采用 Fake adapter 而非完整外部服务, 降低 CI 环境依赖
```

### TASK-INT-P2-TOKEN

```
> 矩阵条目: X2-4

**目标**: Token 预算反压链路 (消耗 -> 扣减 -> 耗尽 -> 402) 通过 E2E 验证
**范围**: tests/e2e/cross/test_token_backpressure.py
**范围外**: 计费 UI / 充值流程
**依赖**: TASK-G2-4, TASK-I2-3
**风险**:
  - 数据依赖: 需要 token_billing 表有初始数据 [ENV-DEP]
**兼容策略**: 新增测试, 无破坏性变更
**验收命令**:
  uv run pytest tests/e2e/cross/test_token_backpressure.py -v --tb=short
**回滚方案**: git revert
**证据**: CI artifact
**决策记录**: --
```

### TASK-INT-P2-OBS

```
> 矩阵条目: X2-5
> 矩阵条目: X2-6

**目标**: 4 黄金信号端到端 + 前端错误上报闭环通过验证
**范围**: tests/e2e/cross/test_golden_signals.py, frontend/tests/e2e/cross/web/error-boundary.spec.ts
**范围外**: Grafana 看板 / 告警规则配置
**依赖**: TASK-OS2-1, TASK-OS2-5
**风险**:
  - 环境依赖: 需要 Prometheus 可查询 [ENV-DEP]
**兼容策略**: 新增测试
**验收命令**:
  uv run pytest tests/e2e/cross/test_golden_signals.py -v --tb=short
  cd frontend && pnpm exec playwright test tests/e2e/cross/web/error-boundary.spec.ts
**回滚方案**: git revert
**证据**: CI artifact
**决策记录**: --
```

### TASK-INT-P2-FE

```
> 矩阵条目: XF2-1
> 矩阵条目: XF2-2
> 矩阵条目: XF2-3

**目标**: 前后端集成三条链路 (登录->对话->流式 / 记忆面板 / 文件上传) Playwright E2E 通过
**范围**: frontend/tests/e2e/cross/web/login-to-streaming.spec.ts,
  frontend/tests/e2e/cross/web/memory-panel.spec.ts,
  frontend/tests/e2e/cross/web/file-upload.spec.ts
**范围外**: Admin 前端 / 移动端
**依赖**: TASK-FW2-1, TASK-FW2-4, TASK-FW2-6
**风险**:
  - 环境依赖: 需要全栈运行 (Backend + Frontend) [ENV-DEP, E2E]
**兼容策略**: 新增测试
**验收命令**:
  cd frontend && pnpm exec playwright test tests/e2e/cross/web/
**回滚方案**: git revert
**证据**: Playwright trace + screenshots
**决策记录**: --
```

### TASK-INT-P2-OPENAPI

```
> 矩阵条目: XF2-4

**目标**: OpenAPI 类型同步 (生成后 diff 为空) 作为跨层 gate 可追踪
**范围**: scripts/check_openapi_sync.sh (已有)
**范围外**: 新增 API 端点
**依赖**: TASK-D2-2
**风险**: 无新增风险 (复用现有脚本)
**兼容策略**: 仅增加 xnodes 标记, 不改脚本逻辑
**验收命令**:
  bash scripts/check_openapi_sync.sh
**回滚方案**: git revert xnodes 标记
**证据**: CI 输出
**决策记录**: 复用现有 check, 仅增加 xnodes 绑定
```

---

## 10. P3-P5: 后续 Phase 集成任务卡框架

每个 Phase 激活时建卡, 不提前写空壳。聚合规则:
同一 Phase + 参与层重叠 + 可共享 E2E 测试 -> 合并为一张卡。

### Phase 3 (11 节点 -> 5 张卡)

| 卡 ID | 覆盖节点 | 聚合依据 |
|--------|---------|---------|
| TASK-INT-P3-SKILL | X3-1 | 独立 E2E: Skill 完整闭环 |
| TASK-INT-P3-KNOWLEDGE | X3-2, X3-3, X3-4, X3-6 | 共享 Knowledge 集成测试套件 |
| TASK-INT-P3-SECURITY | X3-5, XM1-2 | 共享安全管线测试 |
| TASK-INT-P3-MEDIA | XM1-1 | 独立 E2E: 媒体上传 |
| TASK-INT-P3-FE | XF3-1, XF3-2, XF3-3 | 共享 Playwright suite |

### Phase 4 (12 节点 -> 5 张卡)

| 卡 ID | 覆盖节点 | 聚合依据 |
|--------|---------|---------|
| TASK-INT-P4-TRACE | X4-1 | 独立 E2E: 全链路 trace_id |
| TASK-INT-P4-RELIABILITY | X4-2, X4-3, X4-6 | 共享基础设施可靠性测试 |
| TASK-INT-P4-DELETE | X4-4 | 独立 E2E: 删除管线端到端 |
| TASK-INT-P4-OBS | X4-5, X4-7, XM2-2 | 共享可观测性验证 |
| TASK-INT-P4-MEDIA-FE | XM2-1, XF4-1, XF4-2, XF4-3 | 共享企业媒体 + 前端集成 |

### Phase 5 (6 节点 -> 3 张卡)

| 卡 ID | 覆盖节点 | 聚合依据 |
|--------|---------|---------|
| TASK-INT-P5-GOVERNANCE | X5-1, X5-2, X5-3 | 共享治理自动化验证 |
| TASK-INT-P5-COMPLIANCE | X5-4, XM3-2 | 共享合规验证 |
| TASK-INT-P5-MULTIMODAL | XM3-1 | 独立: 跨模态语义检索 |

---

## 11. 测试文件目录结构

```
tests/e2e/
  cross/                                  # 新建目录
    __init__.py
    # Phase 2
    test_conversation_loop.py             # X2-1 (从现有 tests/e2e/test_conversation_loop.py 迁移或引用)
    test_memory_evolution.py              # X2-3
    test_token_backpressure.py            # X2-4
    test_golden_signals.py                # X2-5
    # Phase 3 (Phase 3 激活时新建)
    test_skill_e2e.py                     # X3-1
    test_knowledge_integration.py         # X3-2, X3-3, X3-4, X3-6
    test_content_security.py              # X3-5, XM1-2
    test_media_upload.py                  # XM1-1
    # Phase 4, 5 同理

frontend/tests/e2e/cross/                 # 新建目录
  web/
    login-to-streaming.spec.ts            # XF2-1
    memory-panel.spec.ts                  # XF2-2
    file-upload.spec.ts                   # XF2-3
    error-boundary.spec.ts                # X2-6
  admin/
    # Phase 3+: knowledge-workflow.spec.ts, org-config-inherit.spec.ts, ...
```

---

## 12. 文档一致性修复 (附带)

| 修复项 | 文件 | 变更 |
|--------|------|------|
| XF 范围 | `docs/governance/milestone-matrix.md:154` | `XF0-x ~ XF3-x` -> `XF2-x ~ XF4-x` |
| 上游决议更新 | `docs/governance/decisions/2026-02-19-cross-layer-gate-binding.md` | 增加"实施计划已落盘"引用 |

---

## 13. 执行顺序

```
Step 0: 兼容前置修复包 (G0) -- 必须先行
  0a. 修改 scripts/task_card_traceability_check.py (2.1: 扩展合法引用源)
  0b. 修改 scripts/check_task_schema.py (2.2: 修复矩阵引用正则)
  0c. 修改 .gitignore (2.3: 增加 retrospective 白名单)
  0d. 验证: make check-schema && python3 scripts/task_card_traceability_check.py

Step 1: 框架搭建 (全局一次性)
  1a. 修改 delivery/milestone-matrix.schema.yaml (G1 + 2.4 version bump)
  1b. 新建 scripts/check_xnode_coverage.py (G4)
  1c. 修改 Makefile 增加 target (G5)
  1d. 修改 .github/workflows/milestone-check.yml (G6)
  1e. 生成 evidence/retrospective/phase-0-1-xnode-audit.json (G7)
  1f. 修复 milestone-matrix.md:154 XF 范围
  1g. 验证: make check-xnode-coverage (应输出 Phase 2 direct_rate = 0.0)

Step 2: Phase 2 补全 (当前阶段, 优先)
  2a. 新建 docs/task-cards/00-跨层集成/phase-2-integration.md (P2)
  2b. 新建 tests/e2e/cross/ 目录 + Phase 2 测试文件 (T*)
  2c. 修改 milestone-matrix.yaml Phase 2 exit_criteria + go_no_go (G2, G3)
  2d. 验证: make check-xnode-coverage-2 (应输出 direct_rate >= 0.40)
  2e. 裁决 Controlled-Pending A/B

Step 3: Phase 2 Gate Review
  3a. make verify-phase-2-archive
  3b. make check-xnode-coverage-2
  3c. 归档证据

Step 4: Phase 3 激活时同步 (不提前)
  4a. 新建 phase-3-integration.md
  4b. 新建 Phase 3 测试文件
  4c. 修改 YAML Phase 3 exit_criteria + xnodes
  4d. 重复 Step 3 模式

Step 5-6: Phase 4/5 同 Step 4 模式
```

---

## 14. 验收标准

| 检查项 | 命令 | 期望 |
|--------|------|------|
| Schema 校验通过 | `python3 -c "import yaml,jsonschema; ..."` | 无 validation error |
| 现有 gate 不受影响 | `make verify-phase-current` | 现有条目全部 PASS (无退化) |
| 可追溯性校验通过 | `python3 scripts/task_card_traceability_check.py` | 新卡引用不报 dangling |
| 任务卡 schema 校验 | `python3 scripts/check_task_schema.py --mode full` | 新卡通过 Tier-A 校验 |
| 覆盖率脚本可运行 | `make check-xnode-coverage-2` | JSON 输出, direct_rate >= 0.40 |
| CI 不阻断 | milestone-check workflow | xnode-coverage job 成功 |
| --all 不阻断 | `make check-xnode-coverage-all` | exit code = 0 (始终) |

---

## 15. 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0 | 2026-02-19 | 初始版本, 含兼容前置修复包 (G0) + 框架 (G1-G7) + Phase 2 补全 (P2) + Phase 3-5 框架 |
| v1.0.1 | 2026-02-19 | 修正 4 项兼容性问题: (1) 2.1 traceability whitelist-only; (2) 2.2 matrix_ref->list[str] 完整数据结构升级; (3) 4.2 Phase 2 hard/soft 分级 (CI 环境依赖); (4) --all 硬编码 exit(0) 强约束 |
| v1.0.2 | 2026-02-20 | 终审落盘: Proposed → Approved; 补充终审记录与实施证据链 |

---

## 16. 终审记录

| 步骤 | 产物 | 实施状态 | 证据 |
|------|------|---------|------|
| G0 兼容前置修复 (4项) | task_card_traceability_check.py, check_task_schema.py, .gitignore, schema 1.1 | 已落盘 | PR #25 |
| G1 YAML Schema xnodes | milestone-matrix.schema.yaml:85-89 | 已落盘 | PR #25 |
| G2-G3 xnodes 绑定+阈值 | milestone-matrix.yaml P2 7 criteria, P2=0.40 | 已落盘 | PR #25 |
| G4 check_xnode_coverage.py | 315 行, py3.10 兼容 (UTC=timezone.utc) | 已落盘 | PR #25 + #26 (UTC fix) |
| G5 Makefile targets | 3 targets: check-xnode-coverage / -% / -all | 已落盘 | PR #25 |
| G6 CI xnode-coverage job | milestone-check.yml:68-78 | 已落盘 | PR #25 |
| G7 Phase 0-1 回溯审计 | evidence/retrospective/phase-0-1-xnode-audit.json | 已落盘 | PR #25 |
| P2 集成任务卡 (5张) | docs/task-cards/00-跨层集成/phase-2-integration.md | 已落盘 | PR #25 |
| T-BE 后端 E2E (4文件) | tests/e2e/cross/ — 11 tests, 0 skip, 全部 PASS | 已落盘 | PR #26 |
| T-FE 前端 E2E (4文件) | frontend/tests/e2e/cross/web/ — 11 tests, 0 skip, 全部 PASS | 已落盘 | PR #26 |
| verify_phase.py shell 兼容 | shell 元字符支持 (&&, pipe, redirect) | 已落盘 | PR #26 |
| Makefile PYTHON 统一 | `PYTHON := uv run python` | 已落盘 | PR #26 |
| env completeness gate | p2-env-completeness + p2-no-vacuous-pass 接入 milestone-matrix | 已落盘 | PR #26 |
| Phase 0-2 证据归档 | evidence/ 同日新产证据 | 已落盘 | PR #27 |

### 终审 Gate 验证结果

```
make verify-phase-0  → GO (10/10 hard, 2/2 soft)
make verify-phase-1  → GO (9/9 hard)
make verify-phase-2  → GO (17/17 hard, 6/6 soft)
check_xnode_coverage --phase 2 → GO (threshold 0.40)
check_env_completeness → PASS (8/8 keys)
check_no_vacuous_pass → PASS (8 files, 0 skip)
Backend E2E cross  → 11 passed
Frontend E2E cross → 11 passed
```

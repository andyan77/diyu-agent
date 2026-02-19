# 审查论证报告：跨层集成任务卡遗漏分析（v1.3）

版本：v1.3（2026-02-19）  
审查边界：仅治理文档与里程碑矩阵，不含代码实现核查  
审查方式：独立复核（文档交叉对照 + 机读矩阵解析 + gate 执行器逻辑核验）

---

## 1. 审查对象与证据基线

审查文件：

- `docs/governance/milestone-matrix.md`
- `docs/governance/milestone-matrix-backend.md`
- `docs/governance/milestone-matrix-frontend.md`
- `docs/governance/milestone-matrix-crosscutting.md`
- `delivery/milestone-matrix.yaml`
- `docs/governance/execution-plan-v1.0.md`
- `docs/governance/task-card-schema-v1.0.md`
- `scripts/verify_phase.py`

关键证据点：

- `delivery/milestone-matrix.yaml:7`：`current_phase: "phase_2"`
- `delivery/milestone-matrix.yaml:332`、`delivery/milestone-matrix.yaml:414`、`delivery/milestone-matrix.yaml:499`：Phase 3/4/5 定义
- `docs/governance/milestone-matrix-crosscutting.md:204`：Section 4 跨层验证节点入口
- `scripts/verify_phase.py:4`、`scripts/verify_phase.py:102`、`scripts/verify_phase.py:107`、`scripts/verify_phase.py:122`：仅执行 YAML `exit_criteria`

---

## 2. 数字基线（复核后最终值）

### 2.1 Phase 3-5 里程碑数量（机读矩阵）

| Phase | 总数 |
|---|---:|
| Phase 3 | 48 |
| Phase 4 | 51 |
| Phase 5 | 33 |
| 合计 | 132 |

结论：`132`（非 127、非 138）。

### 2.2 跨层验证节点数量（Section 4）

| 分类 | 数量 |
|---|---:|
| X | 33 |
| XF | 10 |
| XM | 7 |
| 合计 | 50 |

结论：`50`（Section 4 全量）。

### 2.3 按小节分布（无遗漏清单）

| 小节 | 节点 | 数量 |
|---|---|---:|
| 4.1 | X0-1~X0-5, XM0-1 | 6 |
| 4.2 | X1-1~X1-5 | 5 |
| 4.3 | X2-1~X2-6 | 6 |
| 4.4 | XF2-1~XF2-4 | 4 |
| 4.5 | X3-1~X3-6, XM1-1~XM1-2 | 8 |
| 4.6 | XF3-1~XF3-3 | 3 |
| 4.7 | X4-1~X4-7, XM2-1~XM2-2 | 9 |
| 4.8 | XF4-1~XF4-3 | 3 |
| 4.9 | X5-1~X5-4, XM3-1~XM3-2 | 6 |
| 合计 |  | 50 |

---

## 3. 核心判断（v1.3）

### 3.1 规划层（矩阵）不是空白，已定义跨层验证体系

成立。`crosscutting.md` Section 4 明确给出 X/XF/XM 节点与验证方法。  
因此“规划层没有跨层定义”的说法不成立。

### 3.2 执行层（任务卡）缺少“独立集成装配卡”

成立。未发现 `TASK-X* / TASK-XF* / TASK-XM*` 独立任务卡。  
但“执行层完全没有跨层内容”不成立：跨层依赖散见于层内卡依赖字段。

示例：

- `docs/task-cards/01-对话Agent层-Brain/brain.md:232`
- `docs/task-cards/05-Gateway层/gateway.md:321`

### 3.3 Gate 层（YAML + verify_phase）与 X/XF/XM 未绑定

成立。`verify_phase.py` 只跑 YAML `exit_criteria`，并不读取 Section 4 节点。  
检索 `delivery/milestone-matrix.yaml` 未出现 `X*/XF*/XM*` 节点 ID（无显式绑定）。

---

## 4. 覆盖率矩阵（v1.3 更正口径）

> v1.3 采用严格口径，避免 v1.2 的“虚构 gate ID/过度语义映射”问题。  
> 覆盖定义：节点 ID（X/XF/XM）在 YAML exit criteria 中可被机器直接追踪（ID 级绑定）。

### 4.1 严格 ID 绑定覆盖率（客观可复现）

| Phase | 节点数 | YAML 检查项数(H+S) | 直接 ID 绑定数 | 覆盖率 |
|---|---:|---:|---:|---:|
| 0 | 6 | 12 | 0 | 0% |
| 1 | 5 | 9 | 0 | 0% |
| 2 | 10 | 14 | 0 | 0% |
| 3 | 11 | 5 | 0 | 0% |
| 4 | 12 | 5 | 0 | 0% |
| 5 | 6 | 4 | 0 | 0% |
| 总计 | 50 | 49 | 0 | 0% |

结论：机器 gate 对 X/XF/XM 的显式绑定覆盖率为 0%。

### 4.2 主题相关但未绑定（不计入覆盖率）

存在“主题相关”检查，但不是节点 ID 绑定：

- `p2-e2e-conversation-loop`（对话闭环）
- `p2-streaming`（流式，soft）
- `p4-billing`（计费流程，soft）
- `p5-full-e2e`（全量 Playwright，范围未细化）
- `p3-knowledge-crud` / `p3-skill-registry` / `p3-tool-execution`（部分场景相关）

结论：有场景相关检查，但缺“节点级机器可追踪映射”。

---

## 5. 三类对象边界（防止语义混用）

| 类别 | 定义 | 当前状态 |
|---|---|---|
| 跨层验证节点 | `crosscutting.md` 的 X/XF/XM 场景定义 | 已定义 50 个 |
| 集成装配任务卡 | 以 X/XF/XM 为主键的独立执行卡（负责人、命令、证据） | 缺失 |
| 机器 gate 命令 | YAML `exit_criteria` + `verify_phase.py` 执行 | 存在，但未与 X/XF/XM 建立 ID 绑定 |

传导链：`节点定义 -> 装配任务卡 -> gate 命令`  
当前断裂：`节点定义 -> 装配任务卡`。

---

## 6. Controlled-Pending 状态（文档内证据）

来源：`docs/governance/execution-plan-v1.0.md:828` 起 Section 10。

| 项 | 描述 | 截止 | 状态判断 |
|---|---|---|---|
| A | `/settings` 无矩阵条目 | Phase 2 gate review | 到期窗口（当前 phase=2） |
| B | SSE 通知中心 UI 条目待定 | Phase 2 gate review | 到期窗口（当前 phase=2） |
| C | Admin Model Registry/Pricing | Phase 3 gate review | 未到期 |
| D | Admin Plugin/Tool Management | Phase 3 gate review | 未到期 |

备注：A/B 是否已裁决，需 gate 审查证据文件佐证（本报告仅文档口径）。

---

## 7. 文档一致性问题（LOW）

### LOW-1：XF 编号范围声明不一致

- `docs/governance/milestone-matrix.md:154` 写 `XF0-x ~ XF3-x`
- 但 `docs/governance/milestone-matrix-crosscutting.md:284` 起已定义 `XF4-1~XF4-3`

建议：统一为 `XF2-x ~ XF4-x` 或至少 `XF0-x ~ XF4-x`。

### LOW-2：V-x/V-fb 非全量填写，需避免“100%引用”表述

反例：

- `docs/governance/milestone-matrix-frontend.md:61`（FW3-3）
- `docs/governance/milestone-matrix-backend.md:297`（G3-3）

---

## 8. 对“跨层遗漏”原命题的最终裁定

### 8.1 成立部分

- “缺少独立跨层集成装配任务卡”成立。
- “gate 未将跨层节点作为机器门禁对象”成立。

### 8.2 不成立/需修正部分

- “完全没有跨层定义”不成立（Section 4 已有 50 节点）。
- “执行层完全没有跨层实施内容”不成立（有跨层依赖，但无独立装配卡）。

### 8.3 最终根因（v1.3）

不是“规划设计盲区”，而是“规划层到执行层再到 gate 层的传导缺失”：

1. 规划层：有定义（50 节点）
2. 执行层：无独立装配卡承接
3. gate 层：无节点 ID 绑定，机器不可追踪

---

## 9. 补全建议（可执行）

1. 新增 `INT-*` 独立集成装配卡体系（按 X/XF/XM 一一映射）。
2. 在 `delivery/milestone-matrix.yaml` 新增节点绑定 gate：
   - 示例：`p3-x3-1-skill-e2e`、`p3-xf3-2-admin-knowledge-e2e`、`p4-x4-4-delete-pipeline-e2e`。
3. 增加“节点->gate 覆盖校验脚本”，纳入 CI：
   - 输入：Section 4 节点列表
   - 输出：绑定率、缺失节点清单、阻断阈值
4. Gate 证据中增加 Controlled-Pending 裁决状态字段，避免“到期未裁决”漂移。
5. 修正文档索引 XF 范围不一致问题。

---

## 10. v1.3 结论

本次独立复核结论：

- 数字基线已稳定：`Phase 3-5 = 132`、`X/XF/XM = 50`。
- 结构性问题已准确定义：跨层验证“有定义、无承接、弱门禁绑定”。
- 相比 v1.2，v1.3 已去除虚构 gate 映射，覆盖率口径可复现、可审计。

最终判定：  
跨层集成任务卡遗漏问题成立，但应精确表述为“传导断裂”而非“规划缺失”。

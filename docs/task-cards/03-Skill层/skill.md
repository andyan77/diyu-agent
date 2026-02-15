# Skill 层任务卡集

> 架构文档: `docs/architecture/03-Skill层.md`
> 里程碑来源: `docs/governance/milestone-matrix-backend.md` Section 4
> 影响门禁: `src/skill/**` -> check_layer_deps
> 渐进式组合 Step 3

---

## Phase 0 -- Port 定义

### TASK-S0-1: SkillProtocol 基类

| 字段 | 内容 |
|------|------|
| **目标** | 定义 Skill 层核心协议 (execute() / describe() / validate_params())，使所有 Skill 统一契约 |
| **范围 (In Scope)** | `src/skill/core/protocol.py` |
| **范围外 (Out of Scope)** | Brain 调度逻辑 / Knowledge Stores 内部实现 / Tool 内部实现 / Memory Core |
| **依赖** | -- |
| **兼容策略** | 纯新增协议定义 |
| **验收命令** | `mypy --strict src/skill/core/protocol.py && echo PASS` (3 个方法签名完整) |
| **回滚方案** | `git revert <commit>` |
| **证据** | mypy 通过日志 |
| **风险** | 依赖: N/A -- 无外部依赖 / 数据: N/A -- 纯协议定义 / 兼容: Protocol 一旦发布需保持稳定 (ADR-033) / 回滚: git revert |
| **决策记录** | 决策: SkillProtocol 统一 execute/describe/validate_params 签名 / 理由: 所有 Skill 统一契约, Brain Router 可按协议调度 / 来源: ADR-033, 架构文档 03 Section 2 |

> 矩阵条目: S0-1 | V-x: X0-1

### TASK-S0-2: SkillRegistry Stub

| 字段 | 内容 |
|------|------|
| **目标** | 空注册表 Stub，匹配任何请求返回"未找到"，使 Brain 在 Phase 0-2 可调用 |
| **范围 (In Scope)** | `src/skill/registry/stub.py`, `tests/unit/skill/test_stub.py` |
| **范围外 (Out of Scope)** | Brain 调度逻辑 / Knowledge Stores / Tool 层 / 真实注册表实现 |
| **依赖** | TASK-S0-1 |
| **兼容策略** | Stub 实现全部方法；Phase 3 被真实注册表替换 |
| **验收命令** | `pytest tests/unit/skill/test_stub.py -v` |
| **回滚方案** | `git revert <commit>` |
| **证据** | Stub 单测通过 |

> 矩阵条目: S0-2 | V-x: X0-1

---

## Phase 1-2 -- 无直接交付

---

## Phase 3 -- 核心 Skill 实现（核心交付 Phase）

### TASK-S3-1: ContentWriterSkill 内容写手

| 字段 | 内容 |
|------|------|
| **目标** | 给定品牌知识 + 人设 + 平台 -> 生成符合格式的营销内容 |
| **范围 (In Scope)** | `src/skill/implementations/content_writer.py`, `tests/unit/skill/test_content_writer.py` |
| **范围外 (Out of Scope)** | Brain 调度逻辑 / Knowledge Stores 内部实现 / LLM 模型选择 / 前端集成 |
| **依赖** | KnowledgeBundle (K3-5), LLMCallPort (T2-1) |
| **兼容策略** | 新增 Skill 实现；注册后才激活 |
| **验收命令** | `pytest tests/unit/skill/test_content_writer.py -v` (生成内容含必需字段) |
| **回滚方案** | `git revert <commit>` -- 从注册表移除该 Skill |
| **证据** | 输出格式校验单测通过 |
| **风险** | 依赖: K3-5 (KnowledgeBundle) + T2-1 (LLMCallPort) 双依赖 / 数据: LLM 输出需格式校验 / 兼容: 新增 Skill, 注册后才激活 / 回滚: 注册表移除 |
| **决策记录** | 决策: Skill 通过 execute(knowledge=KnowledgeBundle) 被动接收预组装知识 / 理由: Skill 不直接调用 Resolver (架构约束) / 来源: 架构文档 03 Section 2 |

> 矩阵条目: S3-1 | V-x: X3-1 | V-fb: XF3-1

### TASK-S3-2: MerchandisingSkill 搭配助手

| 字段 | 内容 |
|------|------|
| **目标** | 给定 SKU + 库存 -> 推荐搭配方案 + 兼容度评分 |
| **范围 (In Scope)** | `src/skill/implementations/merchandising.py`, `tests/unit/skill/test_merchandising.py` |
| **范围外 (Out of Scope)** | Brain 调度逻辑 / Neo4j 图谱内部实现 / 库存管理系统 / 前端集成 |
| **依赖** | StylingRule 图谱 (K3-1) |
| **兼容策略** | 新增 Skill 实现 |
| **验收命令** | `pytest tests/unit/skill/test_merchandising.py -v` (搭配方案 >= 1 个) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 评分逻辑单测通过 |
| **风险** | 依赖: K3-1 (StylingRule 图谱) 需有种子数据 / 数据: 搭配规则质量依赖图谱数据完整性 / 兼容: 新增 Skill / 回滚: git revert |
| **决策记录** | 决策: 搭配推荐基于 Neo4j StylingRule 图谱结构化查询 / 理由: 品类/搭配关系天然图结构 / 来源: 架构文档 03 Section 2 |

> 矩阵条目: S3-2 | V-x: X3-1 | V-fb: XF3-1

### TASK-S3-3: Skill 生命周期管理

| 字段 | 内容 |
|------|------|
| **目标** | 注册 -> 启用 -> 执行 -> 禁用 -> 重新启用，5 态转换全覆盖 |
| **范围 (In Scope)** | `src/skill/registry/lifecycle.py`, `tests/unit/skill/test_lifecycle.py` |
| **范围外 (Out of Scope)** | Brain Router 匹配逻辑 / Knowledge Stores / Tool 层 / 具体 Skill 实现 |
| **依赖** | TASK-S0-1 |
| **兼容策略** | 替换 Stub Registry 为真实实现；Port 接口不变 |
| **验收命令** | `pytest tests/unit/skill/test_lifecycle.py -v` (5 态转换全覆盖) |
| **回滚方案** | 配置切回 Stub (`SKILL_REGISTRY=stub`) |
| **证据** | 状态转换单测通过 |
| **风险** | 依赖: S0-1 (SkillProtocol) / 数据: 状态转换需持久化 / 兼容: 替换 Stub, Port 接口不变 / 回滚: SKILL_REGISTRY=stub |
| **决策记录** | 决策: Skill 状态机 draft->active->deprecated->disabled 四态 + 重启用 / 理由: 生命周期管理支持灰度发布和安全下线 / 来源: 架构文档 03 Section 8 |

> 矩阵条目: S3-3

### TASK-S3-4: Skill 参数校验

| 字段 | 内容 |
|------|------|
| **目标** | 缺失必填参数返回明确错误，错误消息含缺失字段名 |
| **范围 (In Scope)** | `src/skill/core/validation.py`, `tests/unit/skill/test_validation.py` |
| **范围外 (Out of Scope)** | Brain 调度逻辑 / 具体 Skill 业务逻辑 / Knowledge Stores / 前端集成 |
| **依赖** | TASK-S0-1 |
| **兼容策略** | 新增校验层，不影响已有 Skill 实现 |
| **验收命令** | `pytest tests/unit/skill/test_validation.py -v` |
| **回滚方案** | `git revert <commit>` |
| **证据** | 校验逻辑单测通过 |
| **风险** | 依赖: S0-1 (SkillProtocol) / 数据: N/A -- 纯校验逻辑 / 兼容: 新增校验层 / 回滚: git revert |
| **决策记录** | 决策: SkillProtocol.validate_params() 统一参数校验 / 理由: 错误前移, 避免无效调用进入执行链 / 来源: 架构文档 03 Section 2 |

> 矩阵条目: S3-4

---

## Phase 4 -- 可靠性

### TASK-S4-1: Skill 熔断器

| 字段 | 内容 |
|------|------|
| **目标** | Skill 连续失败 5 次 -> 自动熔断 -> 优雅降级回复 |
| **范围 (In Scope)** | `src/skill/resilience/circuit_breaker.py`, `tests/unit/skill/test_circuit_breaker.py` |
| **范围外 (Out of Scope)** | Brain 降级对话逻辑 / Tool 重试机制 / Knowledge Stores / 前端集成 |
| **依赖** | TASK-S3-3 |
| **兼容策略** | 新增熔断层；熔断后降级为纯对话回复 |
| **验收命令** | `pytest tests/unit/skill/test_circuit_breaker.py -v` (熔断后降级成功率 100%) |
| **回滚方案** | `git revert <commit>` -- 移除熔断层 |
| **证据** | 熔断逻辑单测通过 |
| **风险** | 依赖: S3-3 (生命周期管理) / 数据: N/A -- 纯逻辑层 / 兼容: 新增熔断层, 可配置阈值 / 回滚: git revert |
| **决策记录** | 决策: Skill 级熔断器 (连续失败 5 次触发) / 理由: 防止故障 Skill 持续消耗资源 / 来源: 架构文档 03 Section 8 |

> 矩阵条目: S4-1 | V-x: X4-1

### TASK-S4-2: Skill 执行超时

| 字段 | 内容 |
|------|------|
| **目标** | Skill 执行超过 30s -> 超时终止 -> 返回 timeout 错误 |
| **范围 (In Scope)** | `src/skill/resilience/timeout.py`, `tests/unit/skill/test_timeout.py` |
| **范围外 (Out of Scope)** | Brain 调度逻辑 / Tool 超时机制 / Knowledge Stores / 前端集成 |
| **依赖** | TASK-S3-3 |
| **兼容策略** | 新增超时层；可配置超时阈值 |
| **验收命令** | `pytest tests/unit/skill/test_timeout.py -v` (超时终止响应 < 1s) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 超时逻辑单测通过 |
| **风险** | 依赖: S3-3 (生命周期管理) / 数据: N/A -- 纯逻辑层 / 兼容: 新增超时层, 可配置阈值 / 回滚: git revert |
| **决策记录** | 决策: Skill 执行超时 30s 硬上限 / 理由: 防止长时间阻塞对话响应 / 来源: 架构文档 03 Section 8 |

> 矩阵条目: S4-2

---

## Phase 5 -- 高级能力

### TASK-S5-1: Skill A/B Testing

| 字段 | 内容 |
|------|------|
| **目标** | 同一 Skill 两个版本按流量比例执行，偏差 < 5%；支持 guardrail-based 自动回滚 |
| **范围 (In Scope)** | `src/skill/experiment/ab_test.py`, `src/skill/experiment/guardrail.py`, `tests/unit/skill/test_ab.py` |
| **范围外 (Out of Scope)** | Brain 调度逻辑 / Knowledge 检索策略实验 / 前端集成 / 统计分析引擎 |
| **依赖** | TASK-S3-3 |
| **兼容策略** | 新增实验层；配置关闭则默认版本 |
| **验收命令** | `pytest tests/unit/skill/test_ab.py -v` (流量比例偏差 < 5% + guardrail 触发回滚) |
| **回滚方案** | 配置关闭 A/B 测试 |
| **证据** | 流量分配单测通过 + guardrail 回滚单测通过 |
| **风险** | 依赖: S3-3 (生命周期管理) / 数据: 实验数据需隔离, 避免污染生产指标 / 兼容: 新增实验层, 配置关闭即回退 / 回滚: 配置关闭 A/B |
| **决策记录** | 决策: Experiment Engine 5 维度 (流量分配/租户分层/collision/guardrail/实验卡片) / 理由: 安全灰度发布 + 自动回滚 (ADR-023) / 来源: ADR-023, 架构文档 03 Section 4 |

> 矩阵条目: S5-1
> 参考: ADR-023 (实验引擎 5 维度: 流量分配 / 租户分层 / collision management / guardrail 回滚 / 实验卡片 7 字段)

### TASK-S5-2: Skill multimodal 能力声明 [M-Track M2]

| 字段 | 内容 |
|------|------|
| **目标** | Skill 声明 multimodal_input/output 支持 (03 Section 2) |
| **范围 (In Scope)** | `src/skill/core/protocol.py` (扩展), `tests/unit/skill/test_multimodal_declare.py` |
| **范围外 (Out of Scope)** | 多模态 Tool 实现 / LLMCallPort 扩展 / Brain 调度 / 前端集成 |
| **依赖** | MM2-4 |
| **兼容策略** | 向后兼容 -- multimodal 字段可选，不声明默认为纯文本 |
| **验收命令** | `pytest tests/unit/skill/test_multimodal_declare.py -v` (声明可解析) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 声明格式单测通过 |
| **风险** | 依赖: MM2-4 里程碑依赖 / 数据: N/A -- 纯声明扩展 / 兼容: 向后兼容, multimodal 字段可选 (ADR-046) / 回滚: git revert |
| **决策记录** | 决策: Expand-Contract 模式扩展 multimodal 能力声明 / 理由: 渐进式多模态支持, 不破坏现有 Skill (ADR-046) / 来源: ADR-046, 架构文档 03 Section 2 |

> 矩阵条目: S5-2 | M-Track: MM2-4

---

> **维护规则:** 里程碑矩阵条目变更时同步更新对应任务卡。

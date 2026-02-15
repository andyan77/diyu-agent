# Tool 层任务卡集

> 架构文档: `docs/architecture/04-Tool层.md`
> 里程碑来源: `docs/governance/milestone-matrix-backend.md` Section 5
> 影响门禁: `src/tool/**` -> check_layer_deps + check_port_compat
> 渐进式组合 Step 2

---

## Phase 0 -- Port 定义

### TASK-T0-1: LLMCallPort 接口定义

| 字段 | 内容 |
|------|------|
| **目标** | 定义 LLM 调用契约 (model_id, messages, temperature 等参数)，使 Brain 层可基于 Port 编程 |
| **范围 (In Scope)** | `src/ports/llm_call_port.py` |
| **范围外 (Out of Scope)** | Skill 实现 / Brain 调度逻辑 / LLM Gateway 路由 / 前端集成 |
| **依赖** | -- |
| **兼容策略** | 纯新增接口定义 |
| **验收命令** | `mypy --strict src/ports/llm_call_port.py && echo PASS` |
| **回滚方案** | `git revert <commit>` |
| **证据** | mypy 通过日志 |
| **风险** | 依赖: N/A / 数据: N/A -- 纯接口定义 / 兼容: Port 接口一旦发布需保持稳定 / 回滚: git revert |
| **决策记录** | 决策: LLMCallPort 统一 LLM 调用契约 / 理由: Brain 基于 Port 编程, 与具体 LLM provider 解耦 / 来源: 架构文档 04 Section 2 |

> 矩阵条目: T0-1 | V-x: X0-1

### TASK-T0-2: LLMCallPort Stub

| 字段 | 内容 |
|------|------|
| **目标** | 返回固定文本 "stub response" 的 Stub，使 Brain 在无 LLM 环境下测试 |
| **范围 (In Scope)** | `src/tool/llm/stub.py`, `tests/unit/tool/test_llm_stub.py` |
| **范围外 (Out of Scope)** | Skill 实现 / Brain 调度逻辑 / LLM Gateway / 真实 LLM provider |
| **依赖** | TASK-T0-1 |
| **兼容策略** | Stub 实现全部方法；Phase 2 被真实实现替换 |
| **验收命令** | `pytest tests/unit/tool/test_llm_stub.py -v` |
| **回滚方案** | `git revert <commit>` |
| **证据** | Stub 单测通过 |

> 矩阵条目: T0-2 | V-x: X0-1

### TASK-T0-3: ToolProtocol 基类

| 字段 | 内容 |
|------|------|
| **目标** | 定义 Tool 层统一协议 (execute() / describe() 签名) |
| **范围 (In Scope)** | `src/tool/core/protocol.py` |
| **范围外 (Out of Scope)** | Skill 实现 / Brain 调度逻辑 / 具体 Tool 实现 / 前端集成 |
| **依赖** | -- |
| **兼容策略** | 纯新增协议定义 |
| **验收命令** | `mypy --strict src/tool/core/protocol.py && echo PASS` |
| **回滚方案** | `git revert <commit>` |
| **证据** | mypy 通过日志 |
| **风险** | 依赖: N/A / 数据: N/A -- 纯协议定义 / 兼容: Protocol 一旦发布需保持稳定 / 回滚: git revert |
| **决策记录** | 决策: ToolProtocol 统一 execute/describe 签名, 无状态单一职责 / 理由: Tool 底层可替换, 不绑定具体实现 / 来源: 架构文档 04 Section 2 |

> 矩阵条目: T0-3

### TASK-T0-4: LLMCallPort content_parts 可选参数 Expand (ADR-046) [M-Track M0]

| 字段 | 内容 |
|------|------|
| **目标** | LLMCallPort 新增 content_parts 可选参数，旧调用方式 (纯 text messages) 不受影响 |
| **范围 (In Scope)** | `src/ports/llm_call_port.py` (扩展), `tests/unit/tool/test_llm_port_compat.py` |
| **范围外 (Out of Scope)** | Skill 多模态实现 / Brain 调度逻辑 / LLM Gateway 内部 / 前端集成 |
| **依赖** | TASK-T0-1 (LLMCallPort 基础接口) |
| **兼容策略** | Expand-Contract: content_parts 为可选字段，不传则退化为纯文本调用 (ADR-046) |
| **验收命令** | `pytest tests/unit/tool/test_llm_port_compat.py -v` (旧接口不报错 + 新接口可传 content_parts) |
| **回滚方案** | `git revert <commit>` -- content_parts 字段移除，旧接口不受影响 |
| **证据** | 向后兼容性测试通过 |
| **风险** | 依赖: T0-1 (LLMCallPort 基础接口) / 数据: N/A -- 纯接口扩展 / 兼容: Expand-Contract 模式, 旧接口不受影响 (ADR-046) / 回滚: git revert, 字段移除 |
| **决策记录** | 决策: Expand-Contract 迁移 content_parts 参数 / 理由: 渐进式多模态扩展, v1.x Expand -> v1.x+1 Migrate -> v2.0 Contract / 来源: ADR-046, 架构文档 05 Section 9 |

> 矩阵条目: MM0-6 | M-Track: MM0-6
> 主卡归属: Tool (Port 定义) | 引用层: Brain (调用方), Gateway (LLM 路由)

---

## Phase 1 -- 无直接交付

---

## Phase 2 -- LLMCall 真实实现

### TASK-T2-1: LLMCallPort -> LLM Gateway 真实实现

| 字段 | 内容 |
|------|------|
| **目标** | 调用 LiteLLM -> 收到 LLM 回复 -> token 计量记录写入，调用成功率 >= 99% |
| **范围 (In Scope)** | `src/tool/llm/gateway_adapter.py`, `tests/integration/tool/test_llm_gateway.py` |
| **范围外 (Out of Scope)** | Skill 实现 / Brain 调度逻辑 / LLM provider 内部 / 前端集成 |
| **依赖** | LLM Gateway (G2-3), LiteLLM |
| **兼容策略** | 替换 Stub；Port 接口不变 |
| **验收命令** | [ENV-DEP] `pytest tests/integration/tool/test_llm_gateway.py -v` (调用成功率 >= 99%) |
| **回滚方案** | 配置切回 Stub (`LLM_BACKEND=stub`) |
| **证据** | 集成测试通过 |
| **风险** | 依赖: G2-3 (LLM Gateway) + LiteLLM 外部库 / 数据: token 计量需准确 / 兼容: 替换 Stub, Port 不变 / 回滚: LLM_BACKEND=stub |
| **决策记录** | 决策: LiteLLM 作为 LLM 统一路由层 (不独立部署代理服务) / 理由: 统一多 provider 接口 + 计费 + 审计 / 来源: 架构文档 05 Section 5 |

> 矩阵条目: T2-1 | V-x: X2-1

### TASK-T2-2: Model Registry + Fallback

| 字段 | 内容 |
|------|------|
| **目标** | 主模型 down -> 自动 fallback 到备选模型，延迟 < 2s |
| **范围 (In Scope)** | `src/tool/llm/model_registry.py`, `tests/unit/tool/test_fallback.py` |
| **范围外 (Out of Scope)** | Skill 实现 / Brain 调度逻辑 / LLM provider 内部 / 前端集成 |
| **依赖** | TASK-T2-1 |
| **兼容策略** | 新增 fallback 层；单模型配置下退化为直接调用 |
| **验收命令** | `pytest tests/unit/tool/test_fallback.py -v` (fallback 延迟 < 2s) |
| **回滚方案** | `git revert <commit>` -- 回退为单模型 |
| **证据** | fallback 逻辑单测通过 |
| **风险** | 依赖: T2-1 (LLM Gateway 真实实现) / 数据: N/A -- 纯路由逻辑 / 兼容: 新增 fallback 层, 单模型退化 / 回滚: git revert |
| **决策记录** | 决策: Model Registry + 断路器 + 降级链 fallback / 理由: LLM provider 不稳定需自动切换 / 来源: 架构文档 05 Section 5.4 |

> 矩阵条目: T2-2 | V-x: X2-1

### TASK-T2-3: Token 计量写入 llm_usage_records

| 字段 | 内容 |
|------|------|
| **目标** | 每次 LLM 调用后写入 prompt/completion tokens，计量缺失率 = 0% |
| **范围 (In Scope)** | `src/tool/llm/usage_tracker.py`, `tests/unit/tool/test_usage.py` |
| **范围外 (Out of Scope)** | Skill 实现 / Brain 调度逻辑 / 计费结算逻辑 / 前端集成 |
| **依赖** | TASK-T2-1 |
| **兼容策略** | 纯追加写入，不影响 LLM 调用逻辑 |
| **验收命令** | `pytest tests/unit/tool/test_usage.py -v` (计量缺失率 = 0%) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 计量准确性单测通过 |
| **风险** | 依赖: T2-1 (LLM Gateway) / 数据: 计量数据需准确, 丢失不可恢复 / 兼容: 纯追加写入 / 回滚: git revert |
| **决策记录** | 决策: llm_usage_records 与 tool_usage_records 分离计量 / 理由: LLM token 和 Tool 调用分别计费 / 来源: 架构文档 04 Section 5 |

> 矩阵条目: T2-3 | V-x: X2-4

---

## Phase 3 -- 扩展 Tool

### TASK-T3-1: WebSearch Tool

| 字段 | 内容 |
|------|------|
| **目标** | 搜索关键词 -> 返回结构化搜索结果 |
| **范围 (In Scope)** | `src/tool/implementations/web_search.py`, `tests/unit/tool/test_web_search.py` |
| **范围外 (Out of Scope)** | Skill 实现 / Brain 调度逻辑 / 搜索引擎内部 / 前端集成 |
| **依赖** | -- |
| **兼容策略** | 新增 Tool，注册后才激活 |
| **验收命令** | `pytest tests/unit/tool/test_web_search.py -v` (结果非空) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 输出格式单测通过 |
| **风险** | 依赖: 外部搜索 API 可用性 / 数据: 搜索结果需脱敏处理 / 兼容: 新增 Tool, 注册后激活 / 回滚: git revert |
| **决策记录** | 决策: Tool 底层实现可替换 (搜索引擎从 Bing -> Google) / 理由: ToolProtocol 抽象, 不绑定具体实现 / 来源: 架构文档 04 Section 2 |

> 矩阵条目: T3-1 | V-x: X3-1

### TASK-T3-2: ImageAnalyze Tool [M-Track M1]

| 字段 | 内容 |
|------|------|
| **目标** | 输入图片 -> 返回描述文本 |
| **范围 (In Scope)** | `src/tool/implementations/image_analyze.py`, `tests/unit/tool/test_image_analyze.py` |
| **范围外 (Out of Scope)** | Skill 实现 / Brain 调度逻辑 / 对象存储内部 / 前端集成 |
| **依赖** | ObjectStoragePort (I3-3) |
| **兼容策略** | 新增 Tool |
| **验收命令** | `pytest tests/unit/tool/test_image_analyze.py -v` (描述文本长度 > 0) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 输入校验单测通过 |
| **风险** | 依赖: I3-3 (ObjectStoragePort) 未就绪时阻塞 / 数据: 图片需安全扫描 / 兼容: 新增 Tool / 回滚: git revert |
| **决策记录** | 决策: ImageAnalyze 为 M1 多模态 Tool / 理由: 视觉理解是核心多模态能力 / 来源: 架构文档 04 Section 3 |

> 矩阵条目: T3-2 | V-x: X3-1 | M-Track: MM1-3

### TASK-T3-3: AudioTranscribe Tool [M-Track M1]

| 字段 | 内容 |
|------|------|
| **目标** | 输入音频 -> 返回转写文本 |
| **范围 (In Scope)** | `src/tool/implementations/audio_transcribe.py`, `tests/unit/tool/test_audio_transcribe.py` |
| **范围外 (Out of Scope)** | Skill 实现 / Brain 调度逻辑 / 对象存储内部 / 前端集成 |
| **依赖** | ObjectStoragePort (I3-3) |
| **兼容策略** | 新增 Tool |
| **验收命令** | `pytest tests/unit/tool/test_audio_transcribe.py -v` (转写文本长度 > 0) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 输入校验单测通过 |
| **风险** | 依赖: I3-3 (ObjectStoragePort) / 数据: 音频需安全扫描 / 兼容: 新增 Tool / 回滚: git revert |
| **决策记录** | 决策: AudioTranscribe 为 M1 多模态 Tool / 理由: 语音输入是核心交互模态 / 来源: 架构文档 04 Section 3 |

> 矩阵条目: T3-3 | V-x: X3-1 | M-Track: MM1-3

### TASK-T3-4: DocumentExtract Tool [M-Track M2]

| 字段 | 内容 |
|------|------|
| **目标** | 输入 PDF/DOCX 文件 -> 返回结构化文本，提取文本非空 |
| **范围 (In Scope)** | `src/tool/implementations/document_extract.py`, `tests/unit/tool/test_document_extract.py` |
| **范围外 (Out of Scope)** | Skill 实现 / Brain 调度逻辑 / Knowledge 入库逻辑 / 前端集成 |
| **依赖** | ObjectStoragePort (I3-3) |
| **兼容策略** | 新增 Tool，注册后才激活 |
| **验收命令** | `pytest tests/unit/tool/test_document_extract.py -v` (提取文本非空 + 格式保留) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 输出格式单测通过 |
| **风险** | 依赖: I3-3 (ObjectStoragePort) / 数据: 文档内容需安全扫描 / 兼容: 新增 Tool, 注册后激活 / 回滚: git revert |
| **决策记录** | 决策: DocumentExtract 为 M2 文档理解 Tool / 理由: 企业文档入库需结构化提取 / 来源: 架构文档 04 Section 3 |

> 矩阵条目: MM2-5 | M-Track: MM2-5
> 主卡归属: Tool | 引用层: Knowledge (企业文档入库)

---

## Phase 4 -- 可靠性

### TASK-T4-1: Tool 独立计费 (ADR-047)

| 字段 | 内容 |
|------|------|
| **目标** | Tool 调用费用独立于 LLM token 费用计量 |
| **范围 (In Scope)** | `src/tool/billing/tool_billing.py`, `tests/unit/tool/test_billing.py` |
| **范围外 (Out of Scope)** | LLM token 计费 / Skill 实现 / Brain 调度 / 结算系统 |
| **依赖** | tool_usage_records (I3-4) |
| **兼容策略** | 新增计费维度，不影响现有 token 计费 |
| **验收命令** | `pytest tests/unit/tool/test_billing.py -v` (计费独立且准确) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 计费逻辑单测通过 |
| **风险** | 依赖: I3-4 (tool_usage_records 表) / 数据: 计费数据需准确, 丢失影响收入 / 兼容: 新增计费维度 / 回滚: git revert |
| **决策记录** | 决策: Tool 独立计费 (ADR-047) / 理由: Tool 调用成本独立于 LLM token, 需分开计量 / 来源: ADR-047, 架构文档 04 Section 5 |

> 矩阵条目: T4-1 | V-x: X4-1

### TASK-T4-2: Tool 重试 + 指数退避

| 字段 | 内容 |
|------|------|
| **目标** | 失败后 100ms/500ms/2000ms 重试 |
| **范围 (In Scope)** | `src/tool/resilience/retry.py`, `tests/unit/tool/test_retry.py` |
| **范围外 (Out of Scope)** | Skill 熔断机制 / Brain 调度逻辑 / 外部 API 实现 / 前端集成 |
| **依赖** | -- |
| **兼容策略** | 新增重试层；可配置关闭 |
| **验收命令** | `pytest tests/unit/tool/test_retry.py -v` (重试间隔符合预期) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 退避逻辑单测通过 |
| **风险** | 依赖: N/A / 数据: N/A -- 纯逻辑层 / 兼容: 新增重试层, 可配置关闭 / 回滚: git revert |
| **决策记录** | 决策: 指数退避重试 (100ms/500ms/2000ms) / 理由: 外部 API 瞬时失败常见, 重试可提高成功率 / 来源: 架构文档 04 Section 5 |

> 矩阵条目: T4-2

---

## Phase 5 -- 治理

### TASK-T5-1: Tool 成本看板

| 字段 | 内容 |
|------|------|
| **目标** | 按 Tool 类型和租户维度展示成本 |
| **范围 (In Scope)** | Grafana dashboard JSON, `src/tool/billing/dashboard.py` |
| **范围外 (Out of Scope)** | LLM token 看板 / Skill 看板 / Grafana 基础设施 / 前端集成 |
| **依赖** | Grafana (I4-1) |
| **兼容策略** | 纯新增看板 |
| **验收命令** | [ENV-DEP] `curl -s localhost:3000/api/datasources \| python3 -c "import sys,json; ds=json.load(sys.stdin); assert len(ds)>=2"` staging: Grafana 看板数据源验证 (2 维度数据可查) |
| **回滚方案** | 删除看板 JSON |
| **证据** | 看板截图 |
| **风险** | 依赖: I4-1 (Grafana) / 数据: 看板数据源需与 tool_usage_records 对齐 / 兼容: 纯新增看板 / 回滚: 删除看板 JSON |
| **决策记录** | 决策: Tool 成本看板按类型+租户双维度 / 理由: 运营需按维度分析 Tool 使用成本 / 来源: 架构文档 04 Section 5 |

> 矩阵条目: T5-1

### TASK-T5-2: LLMCallPort Contract 阶段评估 (ADR-046)

| 字段 | 内容 |
|------|------|
| **目标** | 评估报告: 是否可移除 content_parts 兼容层 [M-Track M3] |
| **范围 (In Scope)** | `docs/evaluations/llm_contract_review.md` |
| **范围外 (Out of Scope)** | 实际代码变更 / Skill 实现 / Brain 调度 / 前端集成 |
| **依赖** | MM3-3 |
| **兼容策略** | 纯文档产出 |
| **验收命令** | `test -f docs/evaluations/llm_contract_review.md && grep -qc "content_parts" docs/evaluations/llm_contract_review.md && echo PASS` |
| **回滚方案** | 不适用 |
| **证据** | 评估报告 |
| **风险** | 依赖: MM3-3 里程碑依赖 / 数据: N/A -- 纯评估文档 / 兼容: N/A -- 不涉及代码变更 / 回滚: 不适用 |
| **决策记录** | 决策: Expand-Contract v2.0 Contract 阶段前需评估报告 / 理由: 确认所有调用方已迁移后才可移除兼容层 (ADR-046) / 来源: ADR-046, 架构文档 05 Section 9 |

> 矩阵条目: T5-2 | V-x: X5-2 | M-Track: MM3-3

---

> **维护规则:** 里程碑矩阵条目变更时同步更新对应任务卡。

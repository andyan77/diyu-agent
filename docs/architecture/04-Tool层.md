# Tool 层（原子级可执行能力）

> **所属层:** 能力层（四肢的末端执行器）  
> **依赖性:** 可逐个替换，底层实现可换（如搜索引擎从 Bing -> Google）  
> **版本:** v3.6
> **验证标准:** Tool 无状态、单一职责；底层实现可替换不影响 Skill 调用方  

---

## 1. Tool 的本质

```
Tool = 原子级可执行能力
+-- 无状态，单一职责
+-- 由 Skill 调用（Brain 仅通过 LLMCall Tool 直接调用 LLM）
+-- 可计量，可管控
+-- 底层实现可替换（如搜索引擎从 Bing -> Google）

调用方向约束:
  Brain -> Skill -> Tool    [允许]
  Brain -> LLMCall Tool     [允许，Brain 的唯一直接 Tool 调用]
  Tool -> Skill             [禁止，Tool 不知道 Skill 的存在]
  Tool -> Tool              [禁止，Tool 间不互调]
```

---

## 2. ToolProtocol

```python
class ToolProtocol:
    name: str
    version: str
    description: str
    input_schema: JSONSchema
    output_schema: JSONSchema
    required_permissions: Set[str]
    billable: bool
    rate_limit: Optional[RateLimit]

    async def execute(self, params: Dict, org_context: OrganizationContext) -> ToolResult
```

---

## 3. Tool 清单

| Tool | 状态 | 说明 | 计费 |
|------|------|------|------|
| **LLMCall** | **Day 1** | 统一 LLM 调用入口 | 按 Token |
| ImageGenerate | 远期 | 图片生成 | 按张 |
| ImageAnalyze | M1 | 图片理解 | 按 Token |
| AudioTranscribe | M1 | 语音转文字 | 按分钟 |
| DocumentExtract | M2 | 文档解析 | 按次 |
| WebSearch | 占位 | 联网搜索 | 按次 |
| WebScrape | 占位 | 网页抓取 | 按次 |
| CodeSandbox | 占位 | 代码执行 | 按次 |
| ExternalAPI | 占位 | 外部系统对接 | 按次 |

> **[裁决]** Day 1 只实现 LLMCall。M1/M2 多模态 Tool 按分期实现。其余定义好接口，stub 实现。预留 MCP 适配器。

**v3.6 Tool 计量对齐:**

```
多模态 Tool 计量 (与 LLMCall 分离):
  每次调用写入 tool_usage_records (非 llm_usage_records)
  字段对齐 Section 5: tool_name, tool_version, org_id, user_id, skill_id,
                       input_summary(脱敏), duration_ms, cost_amount, billing_unit, status
  tool_usage_records DDL 定义见 06-基础设施层.md Section 9
  预算校验: Loop D Pre-check 同时检查 budget_tool_amount (见 05-Gateway层.md Section 8.4)
```

---

## 4. MCP 适配器（预留）

```python
class MCPToolAdapter(ToolProtocol):
    """将 MCP Server 的 Tool 包装为 Diyu ToolProtocol"""
    def __init__(self, mcp_server_url, tool_definition): ...
    async def execute(self, params, org_context): ...
```

> **[裁决]** 自定义 ToolProtocol，预留 MCP 适配器。不绑定 MCP 协议。

---

## 5. Tool 的计量与管控

```
每次 Tool 调用记录:
+-- tool_name, tool_version
+-- org_id, user_id
+-- skill_id（调用方 Skill）
+-- input_summary（脱敏后的输入摘要）
+-- output_summary（脱敏后的输出摘要）
+-- duration_ms
+-- cost（如适用）
+-- status: success | error | rate_limited

管控:
+-- 按 org_tier 控制可用 Tool
+-- 按 skill_whitelist 控制 Skill 可调用的 Tool
+-- Rate Limit 按 org + tool 维度
+-- Budget 消耗纳入 Token Billing Service 统一管理
```

---

> **验证方式:** 1) Tool 实现替换（如 WebSearch 从 Bing 换 Google）不影响 Skill 调用; 2) Tool 无状态验证: 相同输入始终相同输出; 3) MCP 适配器可将外部 MCP Tool 注册为 Diyu Tool; 4) [v3.6] 多模态 Tool 调用记录写入 tool_usage_records 而非 llm_usage_records; 5) [v3.6] AudioTranscribe/DocumentExtract 按 billing_unit 正确计量。

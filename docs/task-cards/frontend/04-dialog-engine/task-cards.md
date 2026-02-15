# 前端对话引擎 任务卡集

> 架构文档: `docs/frontend/04-dialog-engine.md`
> 里程碑来源: `docs/governance/milestone-matrix-frontend.md` Section 1 (Phase 2)
> 影响门禁: `apps/web/app/chat/**`, `apps/web/components/chat/**` -> pnpm test

---

## Phase 2 -- 对话主界面（核心交付 Phase）

### TASK-FW2-1: 对话界面 /chat 双栏布局

| 字段 | 内容 |
|------|------|
| **目标** | 左栏历史列表 + 右栏对话区域，响应式布局 |
| **范围 (In Scope)** | `apps/web/app/chat/page.tsx`, `apps/web/components/chat/Layout.tsx` |
| **范围外 (Out of Scope)** | 后端 API / 数据库 / DevOps / 对话业务逻辑 |
| **依赖** | -- |
| **兼容策略** | 纯新增页面 |
| **验收命令** | `pnpm exec playwright test tests/e2e/web/chat/layout.spec.ts` (双栏正确渲染) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 布局响应式截图 |
| **风险** | 依赖: N/A -- 纯 UI 布局 / 数据: N/A / 兼容: 纯新增页面 / 回滚: git revert |
| **决策记录** | 决策: /chat 双栏布局 (左历史+右对话) / 理由: 标准对话 UI 模式 / 来源: FE-04 Section 1 |

> 矩阵条目: FW2-1 | V-fb: XF2-1

### TASK-FW2-2: 流式消息渲染 (SSE/WS)

| 字段 | 内容 |
|------|------|
| **目标** | 发消息 -> 看到逐字流式回复 -> Markdown 渲染，首字节渲染 < 500ms |
| **范围 (In Scope)** | `apps/web/components/chat/StreamMessage.tsx`, `apps/web/lib/ws/` |
| **范围外 (Out of Scope)** | 后端 LLM 调用 / Gateway WS 实现 / 数据库 / DevOps |
| **依赖** | Gateway WS (G2-2), TASK-FW2-7 |
| **兼容策略** | 新增流式组件 |
| **验收命令** | `pnpm exec playwright test tests/e2e/web/chat/streaming.spec.ts` (首字节渲染 < 500ms) |
| **回滚方案** | `git revert <commit>` |
| **证据** | Markdown 渲染截图 |
| **风险** | 依赖: G2-2 (Gateway WS) + FW2-7 (WS 连接) / 数据: 流式消息断裂需重连补偿 / 兼容: 新增流式组件 / 回滚: git revert |
| **决策记录** | 决策: SSE/WS 流式消息 + Markdown 渲染 / 理由: 首字节 <500ms 用户体验 / 来源: FE-04 Section 2 |

> 矩阵条目: FW2-2 | V-x: X2-2 | V-fb: XF2-1

### TASK-FW2-3: 对话历史管理

| 字段 | 内容 |
|------|------|
| **目标** | 新建/重命名/删除/搜索对话 |
| **范围 (In Scope)** | `apps/web/components/chat/History.tsx` |
| **范围外 (Out of Scope)** | 后端对话存储 / Memory Core / 数据库 / DevOps |
| **依赖** | TASK-FW2-1 |
| **兼容策略** | 新增组件 |
| **验收命令** | `pnpm exec playwright test tests/e2e/web/chat/history.spec.ts` (4 操作全通过) |
| **回滚方案** | `git revert <commit>` |
| **证据** | CRUD 逻辑单测通过 |
| **风险** | 依赖: FW2-1 (Chat 布局) / 数据: 删除操作不可逆 / 兼容: 新增组件 / 回滚: git revert |
| **决策记录** | 决策: 对话历史 CRUD (新建/重命名/删除/搜索) / 理由: 对话管理基础功能 / 来源: FE-04 Section 2 |

> 矩阵条目: FW2-3 | V-fb: XF2-1

### TASK-FW2-4: 记忆面板 (Memory Context Panel)

| 字段 | 内容 |
|------|------|
| **目标** | Cmd+Shift+M -> 查看 AI 对你的记忆 -> 删除某条记忆 |
| **范围 (In Scope)** | `apps/web/components/chat/MemoryPanel.tsx` |
| **范围外 (Out of Scope)** | 后端 Memory Core / Brain 调度 / 数据库 / DevOps |
| **依赖** | Memory Core API (MC2-3) |
| **兼容策略** | 新增面板 |
| **验收命令** | `pnpm exec playwright test tests/e2e/web/chat/memory-panel.spec.ts` (记忆列表可加载 + 删除可操作) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 面板交互 E2E 通过 |
| **风险** | 依赖: MC2-3 (Memory Core API) / 数据: 记忆删除需用户确认 / 兼容: 新增面板 / 回滚: git revert |
| **决策记录** | 决策: Cmd+Shift+M 记忆面板 / 理由: 用户可查看和管理 AI 记忆 / 来源: FE-04 Section 3 |

> 矩阵条目: FW2-4 | V-x: X2-3 | V-fb: XF2-2

### TASK-FW2-5: 消息操作 (复制/重试/反馈)

| 字段 | 内容 |
|------|------|
| **目标** | 复制 -> 剪贴板包含内容; 重试 -> 重新生成; 反馈 -> 记录 |
| **范围 (In Scope)** | `apps/web/components/chat/MessageActions.tsx` |
| **范围外 (Out of Scope)** | 后端消息处理 / LLM 重试逻辑 / 数据库 / DevOps |
| **依赖** | TASK-FW2-2 |
| **兼容策略** | 新增操作组件 |
| **验收命令** | `pnpm exec playwright test tests/e2e/web/chat/message-actions.spec.ts` (3 操作全可用) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 操作逻辑单测通过 |
| **风险** | 依赖: FW2-2 (流式消息) / 数据: 反馈数据需持久化 / 兼容: 新增操作组件 / 回滚: git revert |
| **决策记录** | 决策: 消息操作 (复制/重试/反馈) / 理由: 对话交互基础功能 / 来源: FE-04 Section 2 |

> 矩阵条目: FW2-5

### TASK-FW2-6: 文件上传 (拖拽 + 进度条) [M-Track M1]

| 字段 | 内容 |
|------|------|
| **目标** | 拖文件到输入框 -> 上传进度 -> 上传完成 -> AI 处理，成功率 >= 99% |
| **范围 (In Scope)** | `apps/web/components/chat/FileUpload.tsx` |
| **范围外 (Out of Scope)** | 后端上传 API / ObjectStorage / 安全扫描 / 数据库 |
| **依赖** | 三步上传协议 (G2-6) |
| **兼容策略** | 新增上传组件 |
| **验收命令** | `pnpm exec playwright test tests/e2e/web/chat/file-upload.spec.ts` (上传成功率 >= 99%) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 上传流程 E2E 通过 |
| **风险** | 依赖: G2-6 (三步上传协议) / 数据: 文件上传需安全预检 / 兼容: 新增上传组件 / 回滚: git revert |
| **决策记录** | 决策: 拖拽文件上传 + 进度条 / 理由: 多模态交互入口 (M-Track M1) / 来源: FE-04 Section 4 |

> 矩阵条目: FW2-6 | V-fb: XF2-3 | M-Track: MM1-1

---

## Phase 3 -- 知识与 Skill (对话视角)

### TASK-FW3-2: Skill 结构化渲染 (右侧面板 Artifact)

| 字段 | 内容 |
|------|------|
| **目标** | 对话触发 Skill -> 右侧显示结构化内容 (产品卡片/搭配方案)；未知 tool_output type 降级为 JsonViewer 不崩溃 |
| **范围 (In Scope)** | `apps/web/components/chat/ArtifactPanel.tsx`, `packages/ui/composites/` (Component Registry) |
| **范围外 (Out of Scope)** | 后端 Skill 执行 / Tool 调用 / Knowledge Stores / 数据库 |
| **依赖** | Skill API (G3-2) |
| **兼容策略** | 新增面板；Component Registry 对未知类型降级 (FE-04 Section 4) |
| **验收命令** | `pnpm exec playwright test tests/e2e/web/knowledge/skill-artifact.spec.ts` (结构化内容正确渲染) + `pnpm test --filter web -- --grep JsonViewer` (unknown type -> JsonViewer fallback) |
| **回滚方案** | `git revert <commit>` |
| **证据** | Artifact 渲染 E2E 通过 + JsonViewer fallback 单测通过 |
| **风险** | 依赖: G3-2 (Skill API) / 数据: 未知 tool_output type 降级为 JsonViewer / 兼容: 新增面板 + Component Registry / 回滚: git revert |
| **决策记录** | 决策: Skill 结构化渲染 + Component Registry fallback / 理由: 可扩展渲染, 未知类型安全降级 / 来源: FE-04 Section 4 |

> 矩阵条目: FW3-2 | V-x: X3-1 | V-fb: XF3-1

---

> **维护规则:** 里程碑矩阵条目变更时同步更新对应任务卡。

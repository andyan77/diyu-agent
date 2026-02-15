# 前端页面路由 任务卡集

> 架构文档: `docs/frontend/05-page-routes.md`
> 里程碑来源: `docs/governance/milestone-matrix-frontend.md` (Phase 3-5)
> 影响门禁: `apps/web/app/**` -> pnpm test

---

## Phase 3 -- 知识与商品页面

### TASK-FW3-1: 知识浏览页 /knowledge

| 字段 | 内容 |
|------|------|
| **目标** | 搜索知识 -> 查看详情 -> 预览内容 |
| **范围 (In Scope)** | `apps/web/app/knowledge/page.tsx`, `apps/web/components/knowledge/` |
| **范围外 (Out of Scope)** | 后端 Knowledge API / 知识存储 / 数据库 / DevOps |
| **依赖** | Knowledge API (G3-1) |
| **兼容策略** | 纯新增页面 |
| **验收命令** | `pnpm exec playwright test tests/e2e/web/knowledge/browse.spec.ts` (搜索结果可展示) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 搜索逻辑 E2E 通过 |
| **风险** | 依赖: G3-1 (Knowledge API) / 数据: N/A -- 只读浏览 / 兼容: 纯新增页面 / 回滚: git revert |
| **决策记录** | 决策: /knowledge 知识浏览页 / 理由: 用户可搜索和预览知识内容 / 来源: FE-05 Section 1 |

> 矩阵条目: FW3-1 | V-x: X3-4 | V-fb: XF3-1

### TASK-FW3-3: 商品组件 (ProductCard/OutfitGrid/StyleBoard)

| 字段 | 内容 |
|------|------|
| **目标** | 3 个商品组件在 Storybook 中可预览 |
| **范围 (In Scope)** | `packages/ui/src/commerce/` |
| **范围外 (Out of Scope)** | 后端商品数据 / Knowledge Stores / 数据库 / DevOps |
| **依赖** | packages/ui (FW0-3) |
| **兼容策略** | 新增组件 |
| **验收命令** | `pnpm storybook` (3 组件全可预览) |
| **回滚方案** | `git revert <commit>` |
| **证据** | Storybook 截图 |
| **风险** | 依赖: FW0-3 (packages/ui) / 数据: N/A -- 纯 UI 组件 / 兼容: 新增组件 / 回滚: git revert |
| **决策记录** | 决策: 3 商品组件 (ProductCard/OutfitGrid/StyleBoard) / 理由: 时尚行业核心展示组件 / 来源: FE-05 Section 1 |

> 矩阵条目: FW3-3

---

## Phase 4 -- 完整功能

### TASK-FW4-3: 暗色/亮色模式

| 字段 | 内容 |
|------|------|
| **目标** | 切换主题 -> 所有组件颜色正确 |
| **范围 (In Scope)** | `apps/web/providers/ThemeProvider.tsx`, `packages/ui/` (主题变量) |
| **范围外 (Out of Scope)** | 后端 API / 数据库 / DevOps / 可观测性 |
| **依赖** | packages/ui |
| **兼容策略** | 新增主题系统 |
| **验收命令** | `pnpm exec playwright test tests/e2e/web/settings/theme.spec.ts` (两种模式全组件正确) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 主题切换 E2E 通过 |
| **风险** | 依赖: packages/ui / 数据: 主题偏好需持久化 / 兼容: 新增主题系统 / 回滚: git revert |
| **决策记录** | 决策: 暗色/亮色模式 ThemeProvider / 理由: 用户体验个性化 / 来源: FE-05 Section 2 |

> 矩阵条目: FW4-3

### TASK-FW4-4: 键盘快捷键 (Cmd+K/N/Shift+M 等)

| 字段 | 内容 |
|------|------|
| **目标** | >= 5 个快捷键可用 |
| **范围 (In Scope)** | `apps/web/lib/hotkeys.ts` |
| **范围外 (Out of Scope)** | 后端 API / 数据库 / DevOps / 可观测性 |
| **依赖** | -- |
| **兼容策略** | 新增快捷键系统 |
| **验收命令** | `pnpm exec playwright test tests/e2e/web/settings/keyboard-shortcuts.spec.ts` (>= 5 个快捷键触发对应功能) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 快捷键映射 E2E 通过 |
| **风险** | 依赖: N/A / 数据: N/A -- 纯前端快捷键 / 兼容: 新增快捷键系统 / 回滚: git revert |
| **决策记录** | 决策: Cmd+K/N/Shift+M 等快捷键 / 理由: 提升操作效率 / 来源: FE-05 Section 2 |

> 矩阵条目: FW4-4

### TASK-FW4-5: 积分充值页 /billing

| 字段 | 内容 |
|------|------|
| **目标** | 选择套餐 -> 支付 -> 余额更新 |
| **范围 (In Scope)** | `apps/web/app/billing/page.tsx` |
| **范围外 (Out of Scope)** | 后端计费逻辑 / 支付集成 / 数据库 / DevOps |
| **依赖** | 计费 API (I2-3) |
| **兼容策略** | 纯新增页面 |
| **验收命令** | `pnpm exec playwright test tests/e2e/web/billing/recharge.spec.ts` (充值 -> 余额更新) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 支付流程 E2E 通过 |
| **风险** | 依赖: I2-3 (计费 API) / 数据: 支付操作需安全验证 / 兼容: 纯新增页面 / 回滚: git revert |
| **决策记录** | 决策: /billing 积分充值页 / 理由: 用户自助充值入口 / 来源: FE-05 Section 2 |

> 矩阵条目: FW4-5 | V-x: X2-4 | V-fb: XF4-1

---

## Phase 5 -- 高级体验

### TASK-FW5-1: 语音交互 [M-Track M1]

| 字段 | 内容 |
|------|------|
| **目标** | 点击麦克风 -> 语音转文字 -> AI 回复 -> 语音播放 |
| **范围 (In Scope)** | `apps/web/components/chat/VoiceInput.tsx` |
| **范围外 (Out of Scope)** | 后端 AudioTranscribe Tool / LLM 调用 / 数据库 / DevOps |
| **依赖** | AudioTranscribe Tool (T3-3) |
| **兼容策略** | 新增语音组件；不支持时隐藏 |
| **验收命令** | `pnpm exec playwright test tests/e2e/web/voice/interaction.spec.ts` (语音转文字可用) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 语音流程 E2E 通过 |
| **风险** | 依赖: T3-3 (AudioTranscribe Tool) / 数据: 语音数据需脱敏 / 兼容: 新增语音组件, 不支持时隐藏 / 回滚: git revert |
| **决策记录** | 决策: 语音交互 (录音->转文字->AI回复->播放) / 理由: 多模态交互入口 (M-Track M1) / 来源: FE-05 Section 3 |

> 矩阵条目: FW5-1 | M-Track: MM1-3 (AudioTranscribe Tool 依赖)

### ~~TASK-FW5-2: PWA 离线支持~~ [Closed]

> **架构决策**: 00-architecture-overview.md L242 明确关闭 PWA ("Not needed. No PWA planned.")
> **关闭时间**: L1 SSOT 设计阶段
> **原矩阵条目**: FW5-2 (已标注 [Closed])

---

> **维护规则:** 里程碑矩阵条目变更时同步更新对应任务卡。

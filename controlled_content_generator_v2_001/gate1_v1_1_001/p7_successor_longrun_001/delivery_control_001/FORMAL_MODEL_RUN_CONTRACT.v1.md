# 正式模型运行合同 v1（FORMAL_MODEL_RUN_CONTRACT）

> 适用：M2–M7 每一个由监督器启动的里程碑会话，以及其中一切正式模型运行。
> P2–P7 模板逐字引用本合同；模板内的里程碑专属条款只能加严不能放宽。

## 1. 会话身份（硬门）

- 每个里程碑 = 一个**全新、非 fork、非 resume 的 Fable 5 顶层会话**；主负责人实际模型必须为 Fable 5 系列，否则 `STOP_MODEL_OR_CONTEXT_IDENTITY_INVALID`。
- 启动只能由**会话外监督器**（`tools/launcher.py`）完成；子代理伪装顶层会话 = 启动记录无效。
- 会话开始即落 `SESSION_IDENTITY.<M>.v1.json`（requested/actual model、session ID、run ID 或 UNAVAILABLE 三元组、版本、记忆来源盘点）。
- `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` 由监督器在 spawn 时注入并在会话内验证。
- **同一会话内跨里程碑续跑 = 停**（v2.5 §七）；里程碑关闭即退出。

## 2. 状态承载（硬门）

- 跨里程碑状态完全由 Git + manifest + 证据包 + HANDOFF + RUN_JOURNAL 承担；禁止用聊天摘要替代磁盘工件。
- 任何业务修改前追加 RUN_JOURNAL 记录；上下文压缩/恢复后必须重读 `SOURCE_LOCK`、`ACTIVE_CONTRACT_SET`、`RUN_JOURNAL`、当前 `MILESTONE_CONTRACT` 与最后绿色提交。
- journal 缺失、损坏或与 Git 矛盾 → `STOP_RUN_JOURNAL_INVALID`；从最后绿色提交幂等恢复，不凭会话记忆接位。

## 3. 写面与 Git（硬门）

- 只写启动记录冻结的 allowlist；暂存与提交只用显式路径清单；禁 `git add -A`、reset、clean、checkout--、stash 覆盖、rebase、force-push、tag、merge master。
- 每个胶囊至少一个边界清晰的提交；断言门控提交（断言不过，add/commit 物理上不执行）。
- 推送仅限既有 origin 任务分支；新产品仓/远程仅 M5/M7 依 D0 边界执行并登记。

## 4. 正式模型运行与签字

- 角色-模型分配以 `ROLE_MODEL_MATRIX` 为准；Codex-GPT 用途以 `GPT_CODEX_SCOPE_CONTRACT` 为准；DeepSeek 30 元/日窄门不变。
- 一切签字按 `schema/signer_receipt.v1.schema.json`：**缺任一必填字段 = 未签**；提供方不公开字段写 UNAVAILABLE 三元组；禁止伪造模型修订号或调用 ID。
- 作者不得签自身工作；正式审核 = 全新只读非 fork 会话 + 隔离声明。
- 修复使候选提交 / 输出 manifest / 证据摘要变化 → 既有审核自动失效，两份审核对新候选重跑。
- 外部调用先预占后结算、失败也结算留回执；成本事件全量记账（24 字段），记账缺失=停。

## 5. 密封与数据（硬门）

- 凡接触密封载荷明文的任何会话：全新非 fork + 自动记忆禁用 + 会话结束登记（v2.5 §三 3.7′）；保全角色只见数量/摘要/回执。
- 密封载荷明文不进作者可读 Git 历史；密封摘要 denylist 撞库命中 = 停。
- 真实客户数据零输入；`.env*`/密钥零读取零入库。

## 6. 关闭

- 出口只能是 `PASS / DIAGNOSTIC_FINAL / FAIL / HONEST_STOP / INTERRUPTED_RESUMABLE`；`IMPLEMENTATION_COMPLETE_REVIEW_READY` 仅为中间态。
- 关闭时产出八件套（P1 §二十三）+ 附件；PASS 需两份彼此独立、绑定同一候选的审核（Fable 对抗审查 + Codex-GPT 复算签字）。
- checker `--mode FINAL` 通过是任何 PASS 宣告的前置；checker 不修改状态、不签自身。
- 停止线触发：先写 RUN_JOURNAL、STOP_LEDGER、Git 状态、最后绿色提交、可复算证据、typed 回执，再停并上报发起人。

## 7. 停止线（全程有效）

v2.5 §七全集 + P1 §二十五全集；未分类新事项 = 停 + 报发起人（唯一升级通道）。
不属于停止线：普通代码错误、测试失败、依赖安装、内部审核意见、命名、实现方法、子代理失败。

## 8. 仍需发起人（永不默认授权）

部署；正式发布；Release/tag；merge master；强推/重写历史；真实客户数据；降低 V1.1 或阶段验收标准；重开九项冻结裁决；自行处理停止线；擅自解释未分类新事项。

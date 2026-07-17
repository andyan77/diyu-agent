# GPT-via-Codex Scope + 回执合同 v1

> 真源：v2.3 §壹-1/2（THIRD_MODEL_FAMILY 裁决 + 落地纪律 2）、v2.3 §四 P0 新增 3、v2.5 §三 3.9-2。
> 授权源：发起人 2026-07-16 裁决（SIGNATURE_AUTHORITY_SOURCE=Sponsor authorization；HUMAN_OR_LEGAL_SIGNER_REQUIRED=NO）。
> 现行 `external_llm_budget.v1.json` 只覆盖 DeepSeek 套路轴；本合同补齐 Codex-GPT 的 scope 与回执约定。

## 1. 角色

| 角色 | 代号 | 说明 |
|---|---|---|
| 独立裁决者 | INDEPENDENT_ADJUDICATOR | 从冻结原始事件独立复算并裁决 |
| 审查签字方 | EXTERNAL_REVIEW_SIGNER | 对候选提交+manifest 出具接受/拒绝签字 |

## 2. 允许用途（allowlist，穷尽式）

1. 独立裁决 / 独立复算（对冻结输入从磁盘重算）；
2. 实现与方法学复核（只读）；
3. 审查签字（按 `schema/signer_receipt.v2.schema.json`）；
4. 盲锚题复核（M4 及之后，按当时里程碑合同）。

## 3. 禁止用途（denylist）

1. 批量内容生成（生成 240/60/120 或任何交付内容）；
2. 替代密封资格运行主体；
3. 读取密封载荷明文（QUAL-A/B、隐藏 40）——除非当时里程碑合同显式将其列为该角色可见材料；
4. 写入仓库（Codex 会话只读；签字回执由执行侧按 Codex 输出落盘并绑定原始输出摘要）；
5. 承担与作者相同 scope 的实现工作后再签字（作者不得自签的镜像约束）。

## 4. 记账

- Codex 订阅制调用：**只记账不设门**（v2.3 §壹-4）；每次正式调用登记：时间、用途、输入摘要、输出摘要、退出状态。
- 登记处：当时里程碑 `EVIDENCE_MANIFEST` + 调用回执文件（内容寻址命名，见 §5）。

## 5. 回执纪律

- 回执文件名含其内容 sha256 前缀，**内容寻址、禁覆盖**；同名冲突 = 停止并调查。
- 签字回执必须满足 `signer_receipt.v2.schema.json` 全部必填字段；**缺任一必填字段 = 该签字无效（视为未签）**。
- 提供方不公开的字段写 `{value: UNAVAILABLE, unavailable_reason, evidence_ref}`；**禁止伪造内部模型修订号或调用 ID**。
- 验证方式：checker `FINAL` 模式复算回执摘要、schema 校验、绑定的 input_commit/manifest 摘要一致性、隔离声明有效性；任一不过 = 未签。

## 6. 隔离

- 全新 Codex 会话/线程；非作者会话 resume/fork；
- 输入仅限：冻结候选提交内容、manifest、审查请求文书；
- 回执含 `session_isolation_attestation`；无效 = 未签。

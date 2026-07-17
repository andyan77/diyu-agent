# 锚内容修正说明 v1（R5 关闭后当场自纠）

## 缺陷（关闭后工作流产物层，非候选代码层）

首个 R5 锚提交 `10e5b0b`（父=首个关闭提交 `caa489f`）内的 `ORIGIN_ANCHOR.v2.json`
把 `closeout_artifact_digests` 建成了「milestones/M1 树内全部文件」——包括已被
SUPERSESSION_LEDGER §5 声明取代的 R3 遗留 v1 工件。`closure.py verify_closure`
在该表上按序选取 `HANDOFF.*`/`CLOSEOUT_RECEIPT.*` 做交叉核验时命中了 v1 遗留件
（绑定 R3 候选 11b71e9）→ 主会话收尾自验当场失败（fail-closed 生效，未放行）。

被审候选 `de83d92` 的代码与全部关闭工件（v2 解析集）无缺陷：三断言门
（HANDOFF 全引用复算 / 八件套 / FINAL 三域）在关闭提交前后均 PASS。

## 修正（零历史改写、零候选变更）

- 锚工件表语义修正为「本轮活跃闭包集」：v2 解析集 + 签字回执 + 出口证据 +
  审查报告/事件/请求 + 快照；排除存在 v2 同基名的 v1 遗留件与锚自身。
- 依「锚提交第一父 == 锚内 closeout_commit」规则，以本说明所在提交为
  **有效关闭提交 K2**（其树完整继承 `caa489f` 的全部关闭工件，字节不变），
  其直接子提交携带修正后 `ORIGIN_ANCHOR.v2.json` 为**有效锚提交**。
  首个 K/A（`caa489f`/`10e5b0b`）作废封存，本文件即其 supersession 登记。
- `closure.py --verify M1` 必须在修正锚上零外部知识重建全链通过后，
  会话方可关闭。

# M3 里程碑关闭 · 独立审核请求 (v1)

**里程碑**：M3（数据供给与逻辑解耦）
**候选提交 candidate_commit**：`84f8fc503e487d4291411f5b9b616595467c138e`
**产品域 product_scope**：`SHARED`
**输入提交 input_commit**：`5ce595de7eb48fcf04178651f84400b0411134be`

## 绑定摘要（审核须逐项复算一致）
- `input_manifest_digest` = `29de0b8bb3d77c67…`（milestones/M3/INPUT_MANIFEST.v1.json 的 canonical 自摘要）
- `output_manifest_digest` = `8ebc581fccaa1c32…`（OUTPUT_MANIFEST.v1.json）
- `evidence_manifest_digest` = `0eee0c1873cfc9ff…`（EVIDENCE_MANIFEST.v1.json）

## M3 交付主张（须验证）
1. **六胶囊全交付**：①分格供需审计+向量容量表+抽样框/排除日志 ②标注协议冻结+小试回执 ③G1 参考金标（跨模型双审）④G2 开发金标（493 用例，dev_manifest 物化）⑤QUAL-A/B 双密封 ⑥逻辑核解耦（LOGICAL_CORE_SEPARATED）。
2. **QUAL 六步硬序**：A1_FACE_FROZEN→B1→B2→A2→A3→B3，seq 1-6 严格单调、集内序 A1<A2<A3 / B1<B2<B3；金标 A=725 面 / B=701 面；qual_order 校验 PASS 零违规（tools/qual_order.py）。
3. **密封纪律**：`sealed_custody_001/` 全程 gitignore、git 面零出现；保全回执仅计数/摘要（SEALED_CUSTODY_RECEIPT）；SEALED_PAYLOAD_DENYLIST 注册 A/B 金标摘要；主编排会话零接触密封明文。
4. **跨模型双盲**：A 席=Codex-GPT(gpt-5.6-sol) vs B 席=Opus-4.8；仲裁=Opus（同 B 席披露）；分歧 QUAL-A 0.4166/QUAL-B 0.4494 全经仲裁终裁，金标零未决。
5. **载体裁决等价**：Fable-5 撞 429 使用窗口 → 发起人授权豁免换 claude-opus-4-8；等价裁定 EQUIVALENT_IN_ALL_VALIDITY_BEARING_PROPERTIES（ROLE_MODEL_MATRIX_ADDENDUM.M3.v2.json）；不动冻结 ACS（set_digest 516fe73b）。
6. **family-wise 假通过率预算**预登记，落盘早于任何金标可见（FAMILY_WISE_FALSE_PASS_BUDGET.v1.json）。

## 审核须做（read-only，零仓写）
- 运行 `python3 checker/p7_master_check.py --milestone M3 --mode PRE_REVIEW`，确认送审条件三域通过 + ARTIFACT_INTEGRITY。
- 复算三 manifest 的 canonical 自摘要与本请求绑定一致；抽验 OUTPUT/EVIDENCE 条目 sha256。
- 复算 QUAL_ORDER_EVENTS 六步序（tools/qual_order.py 零违规）；核金标计数 725/701 与回执一致。
- 对抗探针：git 面搜 `sealed_custody_001/`（须零命中）；核 SEALED_PAYLOAD_DENYLIST 含 A/B 摘要；核载体等价裁定的诚实残留披露。
- 核 candidate_manifest（release/candidate_manifest.v1.json）verify passed、无 drift。

## 裁决
返回结构化 JSON：`{"verdict":"ACCEPT"|"REJECT","reviewer_role":"METHODOLOGY"|"IMPLEMENTATION","findings":[{"severity":"P0|P1|P2|ADVISORY","status":"OPEN|RESOLVED","note":"…"}],"recompute_notes":"…"}`。
任何 P0/P1 OPEN 阻断项 → REJECT。仅当全部主张成立、无阻断项时 ACCEPT。

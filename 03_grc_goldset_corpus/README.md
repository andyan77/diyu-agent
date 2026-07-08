# GRC Goldset Corpus (canonical)

任务 / task: `GKB-GRC-CORPUS-LOCK-AND-NORMALIZATION-001`

本目录把原先散落在 `tmp/` 的 GRC 语料，从**临时导入状态**锁定为仓库内 **canonical GRC corpus**。
锁定之后，下游任务（judge / canary / generation）一律消费本目录，不得再直接读 `tmp/`。

大白话：`tmp/` 就像刚卸货堆在门口的箱子——本任务把每一箱**原样搬进仓库货架、贴上台账**，
之后取货只看货架和台账，不再回门口翻箱子。搬运是**逐字节复制**，一个字都没改。

## 边界 / boundary（本任务只做归档，不生产知识）

- 只读 `tmp/` 源，**不修改 / 不删除 / 不移动**任何 `tmp/` 文件。
- `normalized/` 下全部 32 个文件是源文件的**逐字节副本**（sha256 与源一致）。
- 不生成任何新知识、不做 canary / 3600 / CandidatePack、不跑 Four-Gate。
- 不写 KE / Serving / RAG / DIFY，不改 `01_generation_contracts` / `02_generation_brief_pack`。
- **不解决** `EvidencePolicyOutbox` enum gap——只记进 `blocking_gap_ledger.v0.1.yaml`。
- 所有 readiness 保持 `false`（见每个 manifest 的 `readiness:` 块）。

## 目录结构 / layout

| 文件 / file | 作用 / role |
|---|---|
| `corpus_registry.v0.1.yaml` | 语料总台账；引用每个 normalized 文件恰好一次；声明 corpus 已锁定 |
| `source_digest_manifest.v0.1.yaml` | 32 个源文件的 sha256 / 字节数 / 源路径 → canonical 路径映射 |
| `formal_120_manifest.v0.1.yaml` | formal_120 精确清单：120 例、40 簇（mkc_007..mkc_046）、每簇 3 例、40/40/40 分布 |
| `p0_00_control_plane_manifest.v0.1.yaml` | P0-00 控制面清单：18 例、mkc_001..mkc_006、**不计入 formal_120** |
| `expert_review_13_manifest.v0.1.yaml` | 13 批专家评审 TXT 的 canonical ASCII 清单（原文逐字节保留，不改判） |
| `normalization_map.v0.1.yaml` | 规范化记录：中文名→ASCII 名、cluster_count 派生、case_id 格式差异观测 |
| `blocking_gap_ledger.v0.1.yaml` | EvidencePolicyOutbox / evidence_policy_candidate gap（15 例，记录不解决）|
| `schema/*.json` | 5 个结构 schema，checker 用它们校验 normalized 产物 |
| `normalized/**` | 32 个源文件的 canonical ASCII 副本（逐字节复制）|

## 规范化规则 / normalization

- **canonical 机器路径必须 ASCII**。唯一非 ASCII 源名 `tmp/13个批次专家评审.txt`
  规范为 `normalized/expert_review/expert_review_13_batches.v0.1.txt`。
  中文源路径只允许作为 `source_path` / `provenance_path` / `digest_input` 出现，
  **绝不**作为 canonical 机器路径。
- 各 batch 的 `cluster_count` 源里未显式给出，由 `selected_clusters` 长度**派生**，
  派生记录在 `normalization_map.v0.1.yaml`。
- 各 batch 的 `case_id` 格式不一致（如 P0-01 `GRC-P001-MKC007-POS-001`、
  P0-05 `GRC-P0-05-PRODUCT-NARRATIVE-001-MKC_044-POS-001`）——**原样保留，不改写**，
  仅在 `normalization_map` 记录观测。

## 校验 / checker

```bash
python3 ci/checkers/check_grc_corpus_registry.py --live --report-out ci/reports/grc_corpus_registry_report.v0.1.json
python3 ci/checkers/check_grc_corpus_registry.py --selftest
```

checker 对 counts / clusters / EvidencePolicy gap **独立重算**（不复用 manifest 自报数），
fail-closed（`python -O` 拒跑，异常即非零退出）。

## 下一步 / next（本任务不解锁）

`generation_unlocked: false`。EvidencePolicy gap 阻断 canary / 3600 / CandidatePack，
下一步真实动作是 `GKB-GRC-EVIDENCEPOLICY-OWNER-CONTRACT-DELTA-AND-ALIGNMENT-001`。

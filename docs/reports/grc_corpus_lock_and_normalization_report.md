# GRC Corpus Lock and Normalization — Delivery Report

任务 / task: `GKB-GRC-CORPUS-LOCK-AND-NORMALIZATION-001`
阶段 / phase: GRC corpus canonicalization（judge / canary / generation 之前的基础设施）
下一步 / next real action: `GKB-GRC-EVIDENCEPOLICY-OWNER-CONTRACT-DELTA-AND-ALIGNMENT-001`

## 1. 一句话结论 / TL;DR

把 `tmp/` 里的 P0-00、GRC-P0-01..05、13 批专家评审，从临时导入状态**逐字节**锁定为仓库内
canonical GRC corpus（`03_grc_goldset_corpus/`），并新增一个**独立重算、fail-closed** 的 checker，
杜绝后续任务再直接消费 `tmp/`。**未生成任何新知识，未解锁任何 generation，readiness 全 false。**

## 2. repo_after

| 字段 | 值 |
|---|---|
| branch | master |
| head_before | `09fdb37ce4e47f1d277420f606a44395e5b4132a` |
| head_after | 见本次 commit（`git rev-parse HEAD`）；本报告与 receipt 一并进该 commit |
| worktree_after | clean（断言门控提交保证）|

## 3. files_written（add-only，59 文件，0 修改，0 删除）

| 区域 | 数量 | 说明 |
|---|---|---|
| `03_grc_goldset_corpus/*.yaml` + `README.md` + `schema/*.json` | 13 | 7 manifest + README + 5 schema |
| `03_grc_goldset_corpus/normalized/**` | 32 | 32 源文件的逐字节 ASCII 副本 |
| `03_grc_goldset_corpus/.gitattributes` | 1 | `normalized/** -text`，保证 git 存储字节级不变（见 §11）|
| `ci/checkers/check_grc_corpus_registry.py` | 1 | 独立重算 + fail-closed checker |
| `ci/fixtures/grc_corpus_registry/**` | 9 | positive + 8 negative |
| `ci/reports/grc_corpus_registry_report.v0.1.json` | 1 | checker --live 产物 |
| `docs/reports/grc_corpus_lock_and_normalization_{report.md,receipt.json}` | 2 | 本报告 + 机器回执 |

未修改任何 tracked 文件；`tmp/` 未被触碰；`01_generation_contracts` / `02_generation_brief_pack` /
`00_source_inputs` / `project-infra/current_workspace_status.yaml` / `README.md`（仓库根）均未改。

## 4. corpus_counts（checker 独立重算，非抄 manifest 自报数）

| 计数 | 值 |
|---|---|
| p0_00_case_count | 18 |
| formal_120_case_count | 120 |
| positive_gold / anti_gold / borderline_repair | 40 / 40 / 40 |
| formal_cluster_count | 40（mkc_007..mkc_046）|
| formal_cluster_exactness | 每簇恰好 3 例 |
| p0_00_cluster_range | mkc_001..mkc_006 |
| p0_00 计入 formal_120 | **否** |

## 5. normalization

| 项 | 值 |
|---|---|
| source_files_count | 32（P0-00:5, P0-01:6, P0-02..05:20, 专家评审 TXT:1）|
| normalized_files_count | 32（逐字节副本，sha256 与源一致）|
| source_digest_count | 32（覆盖全部源，含 sha256 / 字节数）|
| chinese_filename_replaced_by_ascii | 1（`13个批次专家评审.txt` → `expert_review_13_batches.v0.1.txt`）|
| cluster_count_derived_count | 5（各 batch 由 `selected_clusters` 长度派生，记入 normalization_map）|
| case_id_rewrite / judgment_rewrite | 均 **false**（case_id 格式差异原样保留，专家评审原文不改判）|

**case_id 格式差异观测**（保留不改写）：P0-01 `GRC-P001-MKC007-POS-001`、
P0-02..04 `GRC-P0-0X-MKCyyy-...`、P0-05 `GRC-P0-05-PRODUCT-NARRATIVE-001-MKC_044-POS-001`。

## 6. blocking_gap_ledger — EvidencePolicyOutbox enum gap（只记录，不解决）

| 项 | 值 |
|---|---|
| evidence_policy_outbox_case_count | 15 |
| evidence_policy_candidate_case_count | 15（与 outbox 为**同一** 15 例）|
| 簇 | mkc_021 / mkc_026 / mkc_027 / mkc_028（P0-03，12 例）+ mkc_044（P0-05，3 例）|
| silently_mapped_to_GeneralKnowledgeBase | **false**（未偷映射）|
| resolved_in_this_task | **false**（本任务禁止解决）|
| blocks | canary_generation / 3600_generation / CandidatePack / Four_Gate |
| does_not_block | corpus_lock / normalization / digest_manifest |
| requires_next_task | `GKB-GRC-EVIDENCEPOLICY-OWNER-CONTRACT-DELTA-AND-ALIGNMENT-001` |

大白话：现有严格 schema 的枚举**不认** `EvidencePolicyOutbox` / `evidence_policy_candidate` 这两个值。
这不影响"把语料搬上货架"，但会挡住"开始生产内容"。本任务只把这 15 条**登记在案**，
不硬贴、不偷改成 `GeneralKnowledgeBase`，留给下一任务用正式契约 delta 解决。

## 7. checks

| 检查 | 结果 |
|---|---|
| checker --live | PASS（exit 0）|
| checker --selftest | PASS（8/8 negative fail-closed）|
| checker `python -O`（防 assert 绕过）| exit 2，打印 `FAIL-CLOSED` |
| schema 校验 normalized 产物 | PASS（20 batch 文件 + 120 case）|
| byte-identity（normalized == source）| 32/32 一致 |
| readiness_false | 全 false（`readiness_all_false: true`）|
| forbidden_scope_clean | KE/Serving/RAG/DIFY/CandidatePack 目录均未创建/触碰 |
| no_generation_created | 无 generated-knowledge 目录 |
| add-only | 无 tracked 文件被修改，`tmp/` 未动 |

## 8. checker 反自审假绿设计（E12 对齐）

checker 的 ground truth **独立重算**，不复用 manifest 自报数：

- formal_120 计数 / 簇覆盖 / 每簇例数 / case_id 唯一性 —— 直接解析
  `normalized/formal_120/p0_0X/gold_reference_cases.yaml` 重算，再**反向**断言 manifest 自报值一致。
- EvidencePolicy 15 例 —— 独立扫描 `storage_target` / `artifact_kind` 标记重算 case_id 集，
  与 `blocking_gap_ledger` 双向比对；并断言这些 case 的 normalized 副本**未**被路由到 `GeneralKnowledgeBase`。
- 32 源文件 —— 独立枚举 `tmp/GRC-P0-0*` + 专家评审 TXT，断言 digest 恰好覆盖，且逐文件 sha256 一致。
- normalized 注册 —— 独立 walk `normalized/` 目录，断言 registry 恰好一次引用每个文件。

同一套纯核心 `validate_corpus_model` 同时判 live 语料与 8 个 negative fixture，
保证 fixture 真正走被测逻辑（非旁路装饰）。

## 9. declared_status / readiness

```
grc_corpus_canonicalized: true
formal_120_corpus_locked: true
p0_00_control_plane_corpus_locked: true
expert_review_13_source_locked: true
generation_unlocked: false

readiness: candidatepack_ready / KE_ready / RAG_ready / DIFY_ready /
           production_ready / generation_allowed = false（readiness_all_false: true）
```

## 10. next_real_action_unlocked

`GKB-GRC-EVIDENCEPOLICY-OWNER-CONTRACT-DELTA-AND-ALIGNMENT-001`
（**不是**直接进 canary / 3600 / CandidatePack —— 这些被 EvidencePolicy gap 阻断）。

## 11. CRLF 字节精确性修正（founder 授权扩 allowed writes 一个 config 文件）

**发现**：首次提交后核对 git 存储，发现仓库 `core.autocrlf=input` 在**入库时**把 6 个 CRLF 源文件
（5 个 P0-00 文件 + 专家评审 TXT）静默改写成 LF —— 工作树副本仍是 CRLF（checker 读工作树，照常 PASS），
但**已提交的 blob 与 manifest 记录的 sha256 不一致**，破坏"字节级锁"（fresh clone 会对不上 digest）。

**大白话**：这份锁本该是"每份文件的复印件 + 指纹"。磁盘上 32 份指纹全对；但 git 有个"自动换行转换"
的设置，把 6 份 Windows 换行的文件在**入库那一刻**悄悄换成了 Unix 换行 —— 于是仓库里存的那 6 份复印件
和它自己登记的指纹对不上了。

**处置**（founder 裁定 Option A）：新增 `03_grc_goldset_corpus/.gitattributes`（`normalized/** -text`），
令 git 对 verbatim 副本**零换行转换**、按字节原样存储，再 `git add --renormalize` + `--amend` 重提交。
结果：**32/32 已提交 blob 的 sha256 == manifest == 源字节**。这是对 §5 allowed writes 的一处最小扩展
（1 个 config 文件），已经 founder 显式批准。tmp/ 未动，无逻辑代码改动，readiness 仍全 false。

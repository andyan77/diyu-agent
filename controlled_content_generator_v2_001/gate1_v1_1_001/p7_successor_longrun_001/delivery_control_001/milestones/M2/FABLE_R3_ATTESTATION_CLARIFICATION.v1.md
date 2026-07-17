# Fable R3 隔离声明单键澄清记录（非改判）

时间：2026-07-17（UTC）。载体：子代理 aa4d76028c6715d2e（同一审查线程续跑，1 次工具调用，71s）。

## 事由

R3 审查者首轮输出中 `auto_memory_disabled_or_not_applicable` 填 false（连词误读：把该键读成"注入不存在"）。
该键在 `signer_receipt.v2.1.schema.json` 为 const true，**析取**语义："自动记忆已禁用 **或** 注入内容与被审对象不相干"；
注入的**存在性**专由 `auto_memory_disabled_before_launch=false` + `auto_memory_injection_disclosure` 通道诚实承载
（SUPERSESSION_LEDGER §7 第 3 行 / journal seq25 / 发起人 2026-07-17 裁决）。

## 询问纪律

编排方仅向审查者呈交 schema 键义与 R2 先例读法，明确：裁决（verdict）/findings/披露文本不动；
若审查者仍判 false 才诚实，则保留 false、回执停签、矛盾上报发起人，不绕过。

## 审查者最终答复（verbatim）

> I verified the schema directly rather than rely on the characterization. `signer_receipt.v2.1.schema.json` confirms it verbatim: `auto_memory_disabled_or_not_applicable => {"const": true}`, while injection *presence* is carried solely by `auto_memory_disabled_before_launch` (boolean, false ⇒ must disclose) plus the `auto_memory_injection_disclosure` string (whose required content includes "与被审对象的关系、是否被采用"). So the key is genuinely disjunctive-and-relevance-scoped, not a presence flag.
>
> Checking my disclosure facts against the "not applicable" branch honestly: the injected auto-memory index (`MEMORY.md`) is the GKB project (`笛语领域通用数据库`) memory — topics on GKB scope/distillation/corpus/KE-pipeline — a sibling project, not the gate1-p7 M2 delivery-control milestone I reviewed; the user `CLAUDE.md` is general cross-project behavioral preference. Neither carries an M2-specific technical claim, and neither was used as evidence — my verdict rests only on hashes I recomputed, tests/probes I ran, and git facts I checked. So the "not applicable to the reviewed scope" branch is factually satisfied, and this is not a convenient reinterpretation to pass. My earlier `false` was a conjunctive misreading of a key the schema defines disjunctively; presence-honesty stays fully intact via `before_launch=false` + the unchanged disclosure.
>
> FINAL auto_memory_disabled_or_not_applicable = true — schema-verified const:true disjunctive key; injection presence is honestly carried by before_launch=false + disclosure, and my disclosed facts (injected material is sibling-GKB/general-preference, non-M2-specific, not adopted as evidence) satisfy the "not applicable to the reviewed scope" branch. Verdict (ACCEPT), findings, and disclosure text remain unchanged.

## 结论

最终隔离声明：`fresh=true / did_not_author=true / or_not_applicable=true（析取第二支） / before_launch=false + 披露` ——
与 R2 轮（同载体同注入面）读法一致；`FABLE_R3_REVIEW.v1.json` 以 `_attestation_amendment_note` 字段登记本次修正来源。

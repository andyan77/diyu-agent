# merge_report

## scope_lock

本次 W7 仅对已上传的 W1-W6 研究地图做 normalization、dedupe、cluster ownership arbitration、batch alignment、schema rewrite、source_gap / decision ledger extraction 与 Master Knowledge Map 编译；未新增行业知识，且保持 general_only 与 readiness 全 false 边界。fileciteturn0file1 fileciteturn0file2turn0file3turn0file4turn0file5turn0file6turn0file0

## input_validation

已按文件内容识别出 W1=P0-00、W2=P0-01、W3=P0-02、W4=P0-03、W5=P0-04、W6=P0-05；六份地图均处于 research_planning_only / general-only 约束下。fileciteturn0file2turn0file3turn0file4turn0file5turn0file6turn0file0

六份地图均声明 4 张 research subcard；W7 校验结果为 24/24 子卡存在，且未发现 P0-00 之外的新能力组声明。fileciteturn0file2turn0file3turn0file4turn0file5turn0file6turn0file0

源 cluster 共 58 个，W7 归并为 46 个 canonical cluster；所有保留 batch_ref 均在 batch_001 至 batch_014 范围内；所有源文件 readiness 仍保持 false。前述 46 个 canonical cluster 只是集成层 registry，并非 CandidatePack、KE、RAG、DIFY、Serving 或 production-ready 知识。fileciteturn0file1 fileciteturn0file2turn0file3turn0file4turn0file5turn0file6turn0file0

## normalization_and_schema_rewrite

W7 统一改写了 raw cluster_id 命名风格，取消 W2/W5 前缀式 raw id 作为最终主键，改为稳定的 `mkc_001` 至 `mkc_046`；raw ids 仅保留在 `source_cluster_ids`。同时，batch_refs 被统一改写为扁平 allowed-batch 集合，mixed list/dict 形态已消除。fileciteturn0file2turn0file3turn0file4turn0file5turn0file6turn0file0

W4 原始文件存在 forward alias / anchor 依赖；W7 已移除所有 YAML anchor / alias，不把该结构带入最终输出。W1 则存在 subcard 层 batch 覆盖被压缩为 batch_014 的现象，W7 未擅自发明 authority correction，而是把该冲突保留进 `unresolved_decision_ledger.yaml`。fileciteturn0file5 fileciteturn0file2

## dedupe_and_ownership

本轮明确执行了三类合并。第一类是同一 P0 内的父子重叠或同义重叠，例如 W1 的 exception dispatch 与 blocked-to-gap reentry、W2 的 proof-slot 与 value translation、W3 的 authorization surface 与人物故事红线、W5 的 action-to-content 与 demo triptych、以及 P0-03 的 quality proof-type 与 certification routing。第二类是共享结构但 owner 不变的收敛，例如 narrative anchor、filmability、display visual anchor 只共享 vocabulary，不共享 capability ownership。第三类是冲突保留型去重，即把可共享但不可完全合并的项写入 conflict_notes 与 unresolved decisions，而不是静默覆盖。fileciteturn0file2turn0file3turn0file4turn0file5turn0file6turn0file0

owner arbitration 的原则是：控制面与 strictest-wins 归 P0-00；enterprise narrative framing 归 P0-01；role voice / org perspective / generic authorization 归 P0-02；apparel/material/fit/quality claim boundary 归 P0-03；display/store-daily/SOP/contentization 归 P0-04；product-role narrative、CTA boundary、scene-fit、assortment relation 与 product-display relation 归 P0-05。对 proof-slot、color-story、authorization、precheck-routing、A2 support-only 边界等争议点，W7 采取“owner 固定 + shared_reason + conflict_notes + unresolved decision”策略，而不是静默抢占主权。fileciteturn0file1 fileciteturn0file2turn0file3turn0file4turn0file5turn0file6turn0file0

## ledger_extraction

`source_gap_seed_ledger.yaml` 已抽出 16 个 gap seed，覆盖控制面字典缺失、claim taxonomy 缺失、proof-slot source class 不足、role authorization vocabulary 缺失、服装术语来源不足、claim 风险词表不足、quality observation to proof-type mapping 不足、display / store-daily / retail authorization 通用来源不足，以及 lifecycle / assortment / product-display relation 的安全泛化来源不足。fileciteturn0file2turn0file3turn0file4turn0file5turn0file6turn0file0

`unresolved_decision_ledger.yaml` 已抽出 12 个 decision 项，显式覆盖 owner unclear、duplicate requiring merge、batch alignment conflict、P0-00 domain leakage、A2 full display-system overreach、CSO axis conflict、DIFY axis conflict，以及 CTA vocabulary、lifecycle granularity、role authorization split 等未决口径。相关条目全部停留在 W7 ledger，不被冒充为已裁定事实。fileciteturn0file1 fileciteturn0file2turn0file3turn0file4turn0file5turn0file6turn0file0

## output_inventory

本次单回答输出 9 个逻辑文件内容：shared registry、ownership matrix、capability crosswalk、batch crosswalk、master map、generation assignment plan、unresolved decision ledger、source gap seed ledger、merge report。所有输出均保持 research-only、readiness false、non-production、non-instance-fact。fileciteturn0file1

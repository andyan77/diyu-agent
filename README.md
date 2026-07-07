# 笛语领域通用数据库

本工作区是笛语领域通用数据库 Codex 知识生成准备工作区。

当前边界：

- 当前不是 KE truth source。
- 当前不是 CandidatePack。
- 当前不是 RAG 或 DIFY 工作区。
- 当前不允许 production、release、generation readiness 被置为 true。
- W7 知识地图已完成并迁移为 canonical input copy。
- 当前下一步是 `CODEX-KNOWLEDGE-GENERATION-CONTRACT-LOCK-001`。

后续顺序：

1. contract lock
2. brief pack
3. pilot
4. microbatch generation
5. quality / dedupe / alignment
6. CandidatePack eligibility split

本工作区只承载 Codex 知识生成准备线的 source input copy、契约、brief、pilot、microbatch draft、质量对齐报告和 CandidatePack eligibility split 输出。它不拥有 KE truth source、Serving Projection、RAG context_bundle、DIFY workflow、runtime ledger 或 production release。

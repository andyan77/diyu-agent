# DIYU Agent -- Frontend Architecture Documents

> **contract_version**: 1.0.0
> **min_compatible_version**: 1.0.0
> **status**: Active
> **source**: Extracted from `docs/reviews/frontend_design.md` v2.0 (Frozen Snapshot)

---

## Document Map

| ID | Layer | Document | Owner | Status |
|----|-------|----------|-------|--------|
| FE-00 | Architecture Overview | [00-architecture-overview.md](./00-architecture-overview.md) | Frontend Architecture Lead | Active |
| FE-01 | Monorepo Infrastructure | [01-monorepo-infrastructure.md](./01-monorepo-infrastructure.md) | Frontend Architecture Lead | Active |
| FE-02 | Transport Layer | [02-transport-layer.md](./02-transport-layer.md) | Frontend Platform Lead | Active |
| FE-03 | Auth & Permission | [03-auth-permission.md](./03-auth-permission.md) | Frontend Security Lead | Active |
| FE-04 | Dialog Engine | [04-dialog-engine.md](./04-dialog-engine.md) | Frontend AI Experience Lead | Active |
| FE-05 | Page Routes & Features | [05-page-routes.md](./05-page-routes.md) | Frontend Product Lead | Active |
| FE-06 | Admin Console | [06-admin-console.md](./06-admin-console.md) | Frontend Admin Lead | Active |
| FE-07 | Deployment & CI/CD | [07-deployment.md](./07-deployment.md) | Frontend DevOps Lead | Active |
| FE-08 | Quality Engineering | [08-quality-engineering.md](./08-quality-engineering.md) | Frontend QA Lead | Active |

---

## Cross-Document Contracts (Port Owner Table)

Each cross-document contract has exactly ONE owner document. Other documents reference but do not redefine.

| Contract | Owner | Consumers |
|----------|-------|-----------|
| DEPLOY_MODE enum (saas/private/hybrid) | FE-07 | FE-00, FE-01, FE-02, FE-03 |
| AuthStrategy interface | FE-03 | FE-02, FE-04 |
| OrgContext type | FE-03 | FE-04, FE-05, FE-06 |
| TierGate rules | FE-03 | FE-05, FE-06 |
| WS message types (uplink/downlink) | FE-02 | FE-04 |
| WS connection state machine | FE-02 | FE-04, FE-05 |
| WS close codes | FE-02 | FE-04 |
| SSE event types | FE-02 | FE-05, FE-06 |
| REST rate-limit headers | FE-02 | FE-05, FE-06 |
| Component Registry interface | FE-04 | FE-05 |
| DiyuChatRuntime interface | FE-04 | FE-05 |
| Chat State (AI SDK useChat) | FE-04 | FE-05 |
| packages/ui module boundary | FE-01 | FE-04, FE-05, FE-06 |
| packages/shared exports | FE-01 | FE-03, FE-04, FE-05, FE-06 |
| packages/api-client exports | FE-01 | FE-02, FE-03, FE-04 |
| ADR registry (FE-001 ~ FE-016) | FE-00 | all |
| Performance budget | FE-08 | FE-07 |

---

## Dependency Graph (Batch Construction Order)

```
Batch A (no dependencies):  FE-00, FE-01, FE-07, FE-08
Batch B (depends on A):     FE-02, FE-03, FE-06
Batch C (depends on A+B):   FE-04, FE-05(non-chat subdomain)
Batch C' (depends on C):    FE-05(chat subdomain)

Note: FE-05 is split into two subdomains with different dependency profiles:
  - Non-Chat subdomain (auth, memory, history, knowledge-edit, store-dashboard, settings,
    bookmarks, training) depends only on FE-01/02/03, can parallel with FE-04
  - Chat subdomain (chat, content, merchandising, search) depends on FE-04,
    must wait for FE-04 completion
```

---

## Cross-Document Verification Loops

| Loop | Scope | Owner |
|------|-------|-------|
| F-A | Auth flow: FE-03 <-> FE-02 <-> FE-07 | FE-03 |
| F-B | Dialog flow: FE-04 <-> FE-02 <-> FE-05 | FE-04 |
| F-C | Billing flow: FE-06 <-> FE-05 <-> FE-02 | FE-06 |
| F-D | Permission flow: FE-03 <-> FE-05 <-> FE-06 | FE-03 |
| F-E | Knowledge edit flow: FE-05 <-> FE-06 <-> FE-02 | FE-06 |

---

## Structure Deviation Note

The final document numbering diverges from the initial V2 splitting proposal:

| V2 Proposal | Final Allocation | Rationale |
|-------------|-----------------|-----------|
| FE-03 = Design System | FE-03 = Auth & Permission | Design system is a package concern (covered in FE-01 packages/ui); Auth/Permission is a standalone cross-cutting domain needing its own owned contracts (AuthStrategy, OrgContext, TierGate) |
| FE-08 = Appendix & ADR | FE-08 = Quality Engineering | ADR registry moved to FE-00 (architecture overview, natural home); Quality (testing, a11y, security, performance budget) is a standalone engineering domain |

All content from the original proposal is covered; only the grouping boundaries shifted for better contract ownership isolation.

---

## Source Document

The original monolithic document `docs/reviews/frontend_design.md` (v2.0) is preserved as a **Frozen Snapshot**. It serves as the single-source-of-truth baseline for all extracted modules. No further edits should be made to the frozen document; all changes go to the module documents.

---

> **Breaking Change Policy**: Expand-Contract. New fields/types are added first (expand); old fields are deprecated with `@deprecated` annotation; removal happens only after all consumers migrate (contract).

# Task Card Schema Rules Reference

> Source: `docs/governance/task-card-schema-v1.0.md` (Frozen)

## Tier-A (10 fields)

Required for Phase 2+ cards, cross-layer dependency cards, and OS-prefixed cards.

| # | Field | Notes |
|---|-------|-------|
| 1 | 目标 | Must contain result keyword |
| 2 | 范围 (In Scope) | Must use labeled format |
| 3 | 范围外 (Out of Scope) | Must be non-empty |
| 4 | 依赖 | Cross-layer refs trigger Tier-A |
| 5 | 风险 | 4 categories: 依赖/数据/兼容/回滚 |
| 6 | 兼容策略 | Expand-Contract for Port changes |
| 7 | 验收命令 | Executable or tagged |
| 8 | 回滚方案 | Must exist |
| 9 | 证据 | CI link or TBD with deadline |
| 10 | 决策记录 | 决策/理由/来源 referencing ADR |

## Tier-B (8 fields)

Default for Phase 0-1 single-layer cards without cross-layer deps.

Fields 1-4, 6-9 from Tier-A (no 风险, no 决策记录).

## Exception Mechanism

```
> EXCEPTION: EXC-XXX | Field: <field> | Owner: <owner> | Deadline: <date> | Alt: <alternative>
```

- Owner must not be TBD
- All 5 fields required
- Deadline must be a real date

## Acceptance Command Tags

| Tag | Meaning |
|-----|---------|
| `[ENV-DEP]` | Requires external environment (DB, API) |
| `[E2E]` | Requires browser/E2E test framework |
| `[MANUAL-VERIFY]` | Cannot be automated; must include alt description (>= 5 chars) |

## L1 Architecture Doc Mapping

| Layer Prefix | Architecture Doc |
|-------------|-----------------|
| B (Brain) | `docs/architecture/01-对话Agent层-Brain.md` |
| MC (MemoryCore) | `docs/architecture/01-对话Agent层-Brain.md` |
| K (Knowledge) | `docs/architecture/02-Knowledge层.md` |
| S (Skill) | `docs/architecture/03-Skill层.md` |
| T (Tool) | `docs/architecture/04-Tool层.md` |
| G (Gateway) | `docs/architecture/05-Gateway层.md` |
| I (Infrastructure) | `docs/architecture/06-基础设施层.md` |
| D (Delivery) | `docs/architecture/07-部署与安全.md` |
| OS (Observability) | `docs/architecture/07-部署与安全.md` |

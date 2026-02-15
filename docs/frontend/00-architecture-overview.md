# FE-00 Architecture Overview

> **contract_version**: 1.0.0
> **min_compatible_version**: 1.0.0
> **breaking_change_policy**: Expand-Contract
> **owner**: Frontend Architecture Lead
> **source_sections**: frontend_design.md Sections 1, 2, 3, 13, 16, 18, 19, 20, 21

---

## 1. Overview

This document defines the architectural overview of the **DIYU Agent** platform frontend. The frontend is the system's **external consumer** (00 Section 12.2 Step 8/9), interacting with the system exclusively through Gateway-exposed API contracts without modifying any internal layer.

Coverage:
- `apps/web` -- User-facing application (Step 8)
- `apps/admin` -- Admin console (Step 9)
- `packages/*` -- Shared infrastructure

---

## 2. Core Principles

1. **Strict Decoupling (Type A)**: Frontend only consumes Gateway API contracts (`/api/v1/*`, `/ws/conversations/{conversation_id}`, `/events/*`). Zero awareness of Brain internals, Memory Core Schema, or Skill implementations.
2. **Component-Driven**: Shared design system (`packages/ui`) ensures consistency across user-facing and admin apps.
3. **Generative UI**: Supports rendering dynamic structured content returned by Skills (product cards, outfit plans, data charts), not limited to plain text.
4. **Optimistic Updates & Real-time**: Chat interactions respond instantly. WebSocket carries conversations, SSE carries notifications.
5. **Secure by Design**: SaaS uses HttpOnly Cookie + BFF (anti-XSS); Private degrades to in-memory Bearer Token (security via network isolation). See FE-03 Section 2.
6. **Dual-Pane Workspace**: Inspired by Claude.ai Artifacts pattern for content production scenarios, kept lightweight through a standard component library.
7. **Degradation-First**: When any non-hard-dependency backend component is unavailable, frontend shows degraded UI rather than crashing.
8. **Deployment Adaptation**: DEPLOY_MODE env var adapts to SaaS/Private/Hybrid deployment modes (ADR FE-001). See FE-07.

---

## 3. Backend Architecture Context

DIYU backend is a 7-layer + dual-SSOT decoupled architecture, v3.6 finalized:

```
Level 0 (Inseparable Core Pair): Brain + Memory Core (hard dependency)
Level 1 (Port-coupled Function Layer): Knowledge / Skill / Tool / Gateway
Level 2 (Pluggable Environment Layer): Infrastructure / Deployment
---
External Consumer (Step 8/9): Frontend UI / Admin Console
```

Key backend constraints and frontend impact:

| Backend Constraint | Frontend Impact |
|-------------------|-----------------|
| Type A interface-level full decoupling | Frontend only consumes Gateway API contracts, zero awareness of Brain/Memory/Knowledge |
| WebSocket /ws/conversations/{conversation_id} as primary interaction | Frontend must use WS streaming as core communication mode |
| Skill returns structured data | Frontend needs Generative UI / Component Registry to render dynamic content |
| Multi-tenant 5-level org tree + RBAC | Frontend needs fine-grained permission control + org switching |
| CP/DP partitioning | User-facing and admin apps consume different API subsets |
| Port evolution Expand-Contract | Frontend must gracefully handle unknown fields/message types |
| Memory Core auto-evolution + PIPL/GDPR deletion rights | Frontend needs memory visualization + deletion request tracking |
| Soft-dependency degradation (degraded_reason) | Frontend needs to display degraded state, hide unavailable features |
| Experiment Engine canary | Frontend needs Feature Flag conditional rendering + experiment variant indicators |
| Three deployment modes (SaaS/Private/Hybrid) | Frontend build artifacts must adapt to multiple deployment environments (FE-001) |

### 3.1 Industry Best Practices Survey

| Platform | Frontend Stack | Core Pattern | Key Insight |
|----------|---------------|-------------|-------------|
| Dify | React + Custom | Workflow Canvas + Prompt IDE | Visual orchestration + BaaS thinking |
| Coze Studio | React + TS (Rush.js monorepo) + @coze/coze-design | DDD + No-code Builder | Custom UI lib + strict dependency control |
| Claude.ai | React | Chat + Artifacts dual-pane | Content preview + lightweight code execution |
| ChatGPT | React + Next.js | Chat-first + Canvas | Multimodal + real-time collaboration |
| LobeChat | Next.js + Zustand + Ant Design + tRPC | Full-stack AI platform | Frontend-as-platform (different positioning from DIYU) |
| LangSmith | React | Dashboard + Trace Viewer | Observability-first |

Key distinction: Claude.ai / LobeChat are "frontend-as-AI-platform" (frontend includes model management, knowledge base, Agent orchestration). DIYU frontend is a "thin client" (all intelligence resides in the backend 7-layer architecture; frontend only handles display and interaction). Cannot directly fork or lighten these platforms; should borrow UX patterns + build custom adaptation architecture.

Technology trends (2025-2026):

1. Vercel AI SDK 6 has become the de facto standard for React AI applications: useChat / streamText / Generative UI / Tool Loop
2. assistant-ui (YC-backed) as new standard for AI Chat component layer, natively supporting AI SDK + shadcn/ui
3. Turborepo + pnpm is the mature solution for Multi-app Monorepo
4. Feature-Sliced Design (FSD) gaining wide adoption in large frontend projects
5. React Server Components for Admin data-intensive pages, reducing client-side JS

---

## 4. Backward Compatibility Strategy

Three principles for frontend backward compatibility (aligned with backend Expand-Contract):

```
1. Unknown message type tolerance:
   - Received unknown tool_output.type -> Component Registry finds no match -> JsonViewer (no crash)
   - Received unknown field -> ignore (TypeScript uses Record<string, unknown> as fallback)
   - Received new version Schema -> only use known fields
   - DiyuChatRuntime receives unknown WS message type -> log warning, do not interrupt stream

2. Feature Flags first:
   - New features controlled by Feature Flag in org_settings
   - Frontend hides entry when Flag=false, does not request new API
   - Backend upgrades -> turns on Flag -> frontend automatically displays
   - packages/shared/feature-flags.ts provides unified evaluation interface

3. API version awareness:
   - api-client layer adapts /api/v1/ and future /api/v2/
   - Version switching completed inside api-client, does not affect upper-layer components
   - Uses OpenAPI to generate types, diff checks for breaking changes on upgrade
```

---

## 5. Trade-off Analysis

### 5.1 Framework Selection

| Option | Pros | Cons | Decision |
|--------|------|------|----------|
| Next.js 15 (App Router) | Good RSC performance, native AI SDK support, SSR/SSG, mature ecosystem | Private deployment needs Node.js or static export degradation | **Selected**, private mode resolved via FE-001 |
| Vite + React SPA | Ultra-fast HMR, lightweight, pure static deployment | No SSR, AI SDK integration requires extra work, need custom routing | Not selected |
| Remix | Excellent data loading model, Progressive Enhancement | Weak AI SDK integration, small ecosystem | Not selected |

### 5.2 AI Chat Component Strategy

| Option | Pros | Cons | Decision |
|--------|------|------|----------|
| assistant-ui + AI SDK + Custom Runtime | Professional Chat UX, streaming/retry built-in, shadcn native | Need custom DiyuChatRuntime adapter (~1-2 person-weeks) | **Selected**, adaptation cost << custom Chat UI cost |
| Custom Chat UI (referencing AI SDK Data Stream Protocol) | Full control, no external dependency | Large engineering effort (6-8 person-weeks), easy to miss edge cases | Fallback (FE-009 degradation plan) |
| CopilotKit | Full-featured AI interaction framework | Too heavy, invasive, conflicts with DIYU architecture | Not selected |

### 5.3 UI Library Strategy

| Option | Pros | Cons | Decision |
|--------|------|------|----------|
| shadcn/ui (Web) + shadcn/ui + Ant Design hybrid (Admin) | Best tool for each scenario; Chat lightweight customization, Admin enterprise out-of-box | Admin two UI libs need style isolation | **Selected**, engineering pragmatism |
| Global shadcn/ui | Unified consistency | Admin enterprise components (Tree/Cascader/Steps) need ~3-5 person-weeks to build | Not selected (unless team has ample frontend capacity) |
| Global Ant Design | Enterprise components complete | Inconsistent with assistant-ui/Tailwind ecosystem, Chat UI customization limited | Not selected |

### 5.4 State Management Strategy

| Option | Pros | Cons | Decision |
|--------|------|------|----------|
| Zustand + TanStack Query + AI SDK + RHF | Four state sources each handle their domain, no redundancy, type-safe | 4 state sources need coordination | **Selected** |
| Redux Toolkit | Unified model, strong DevTools | Too much boilerplate, too heavy for AI Chat scenarios | Not selected |
| Jotai/Recoil | Atomic, fine-grained | Overlaps with TanStack Query functionality | Not selected |

### 5.5 Monorepo Strategy

| Option | Pros | Cons | Decision |
|--------|------|------|----------|
| Turborepo + pnpm | Incremental builds, remote caching, simple config | Fewer features than Nx | **Selected** |
| Nx | Most features, dependency graph analysis | Complex config, steep learning curve | Not selected |
| Rush.js (Coze model) | Validated at scale | Complex config, relatively small community | Not selected |

### 5.6 Real-time Communication Strategy

| Option | Pros | Cons | Decision |
|--------|------|------|----------|
| WebSocket (Chat) + SSE (Events) + REST (CRUD) | Each protocol matches scenario, aligned with backend contracts | Need to maintain 3 client types | **Selected** |
| All WebSocket | Unified protocol | CRUD via WS unnatural, caching difficult | Not selected |
| All REST + Polling | Simple | High latency, poor experience | Not selected |

### 5.7 Auth Strategy

| Option | Pros | Cons | Decision |
|--------|------|------|----------|
| Auth Strategy Factory (SaaS: Cookie+BFF / Private: Bearer) | Security optimized per deployment mode; upper-layer code unaware | Two auth logic sets to maintain | **Selected** (FE-010) |
| Global HttpOnly Cookie + BFF | Highest security | BFF unavailable under output:'export' | Not selected (conflicts with FE-001) |
| Global Bearer Token | Simple and unified | XSS risk on SaaS public network exposure | Not selected |

---

## 6. Design Decision Record (ADR)

| ADR | Decision | Rationale |
|-----|----------|-----------|
| FE-001 | Next.js 15 App Router + DEPLOY_MODE dual-mode build | SaaS: full RSC; Private: output:'export' pure static, nginx deployment, zero Node.js dependency |
| FE-002 | assistant-ui (not custom Chat UI), custom Hook as degradation fallback | Professional AI Chat component, saves 6-8 person-weeks; retains full control fallback |
| FE-003 | Four-state-source separation (Zustand + TanStack + AI SDK + RHF) | Each handles its domain, avoids single-solution compromises |
| FE-004 | Component Registry (not hardcoded switch) | New Skills register components instead of modifying code, aligned with backend "extension through registration" |
| FE-005 | Web/Admin independent applications (not unified SPA) | Security isolation, independent deployment, different permission models |
| FE-006 | WebSocket + SSE + REST three-protocol parallel use | Aligned with Gateway contracts, each protocol matches its scenario |
| FE-007 | TypeScript strict + Zod runtime dual validation | Compile-time + runtime double insurance |
| FE-008 | Admin hybrid UI library (shadcn/ui base + Ant Design enterprise components) | Engineering pragmatism: Chat scenario shadcn/ui for customization, Admin scenario Ant Design for out-of-box; CSS prefix isolation |
| FE-009 | AI SDK Custom Runtime adapting DIYU WebSocket (fallback: backend API Route / custom Hook) | Prioritize frontend adaptation (~1-2 person-weeks); if blocked, degrade to backend adding /api/v1/chat HTTP endpoint or custom Hook |
| FE-010 | Auth Strategy Factory (SaaS: Cookie+BFF / Private: Bearer) | Resolves BFF + output:'export' compatibility conflict; security optimized per deployment mode; upper-layer code unaware |
| FE-011 | Append-Only client WS constraint | Protects backend KV cache stable prefix, aligned with Brain Context Engineering |
| FE-012 | Suggestion Chips backend-driven (static list degradation) | Context-aware priority, inspired by Manus token logits masking |
| FE-013 | Artifact persistence (IndexedDB + backend history query) | Reduces redundant queries, inspired by Manus filesystem external memory |
| FE-014 | Tier-Aware navigation + feature exposure matrix | org_tier drives menu/feature visibility, packages/shared/org-tiers.ts provides constants; aligned with 06 Section 1.1 tier definitions |
| FE-015 | Platform-Ops route group (Phase 0 skeleton + Phase 2 implementation) | Phased delivery: skeleton doesn't depend on backend new APIs; global model registry waits for backend model_registry API |
| FE-016 | Settings Constraints frontend enum (LAW/RULE/BRIDGE) | packages/shared/settings-constraints.ts syncs with 06 Section 1.6; expand-contract compatible |

---

## 7. Backend Alignment Table

| Frontend Decision | Backend Architecture | Relationship |
|-------------------|---------------------|-------------|
| Type A decoupling (frontend zero awareness of Brain/Memory) | Backend 7-layer architecture Step 8/9 positioning | Aligned |
| Component Registry | Skill framework "extension through registration" | Aligned |
| DiyuChatRuntime | Gateway WebSocket /ws/conversations/{conversation_id} contract | Adaptation layer, bridging AI SDK with DIYU protocol |
| Degradation state display | Soft-dependency degradation degraded_reason | Aligned, frontend consumes backend degradation signals |
| Memory transparency panel | injection_receipt 5-tuple + utilized | Visualization, leveraging existing backend data |
| PIPL deletion tracking | tombstone + deletion_event + legal_profile | Aligned, frontend displays backend deletion pipeline status |
| Feature Flags | Experiment Engine canary | Aligned, org_settings driven |
| OrgContext throughout | Gateway OrgContext assembly | Aligned, frontend includes org_id in every request |
| DEPLOY_MODE dual-mode | Three deployment modes (SaaS/Private/Hybrid) | Adaptation, resolving Next.js private deployment constraints |
| Admin Ant Design hybrid | 5-level ltree org tree + three-level review workflow | Pragmatic choice, matching enterprise management scenario complexity |
| Append-Only WS constraint | Brain Context Engineering KV cache | Aligned, frontend does not interfere with backend context management |
| Auth Strategy Factory | Gateway JWT auth + three deployment modes | Adaptation, SaaS/Private security strategy differentiation |
| Tier-Aware navigation + feature exposure matrix | 06 Section 1.1 five-level org_tier definition | Aligned, frontend constants same-source as backend enum |
| Platform-Ops route group | 06 Section 1.3 platform-level permissions | Aligned, PlatformGuard validates org_tier |
| Settings Constraints enum (25 items) | 06 Section 1.6 LAW/RULE/BRIDGE classification | Aligned, frontend enum syncs with backend classification |
| Model config brand-level UI | 05 Section 4.2 OrganizationContext.model_access | Consumes, reuses existing org_settings API |
| Model registry global CRUD | 05 Section 5.2 ModelDefinition schema | Depends, requires backend model_registry CRUD API |
| Knowledge visibility partitioning | 02 Section 5.3 KnowledgeEntry.visibility | Consumes, reuses existing field |
| Notification center | 05 Section 1 SSE /events/* | Consumes, frontend subscribes to backend event push |
| Multi-session management | 05 Section 7.1 WebSocket per-session connection | Aligned, frontend session management semantically consistent with backend |

---

## 8. Constraints & Boundaries

```
1. Frontend is thin client: All intelligence (LLM/Memory/Knowledge/Skill) in backend, frontend only handles display and interaction
2. Frontend permissions are UX-level: Real security validation at Gateway RLS, frontend only hides unauthorized elements
3. Privacy hard boundary: Admin Console does not display Memory Core raw data, only manages Knowledge Stores (ref: ADR-018)
4. No frontend AI logic: No memory retrieval/ranking/confidence calculation in frontend; those are backend Context Assembler's responsibilities
5. Progressive launch: Phase 0-4 progressive delivery, each Phase independently acceptance-testable
6. DEPLOY_MODE dual-build: CI produces both SaaS and Private artifacts simultaneously, ensuring private clients have zero Node.js dependency
7. No new Ports: Frontend does not modify Step 1~7 layers, does not introduce new backend Ports
8. org_tier constants same-source: packages/shared/org-tiers.ts is frontend's sole tier definition source, syncs with 06 Section 1.1
9. settings-constraints same-source: packages/shared/settings-constraints.ts is frontend's sole LAW/RULE/BRIDGE enum, syncs with 06 Section 1.6
10. expand-contract compatible: Frontend graceful degradation when receiving unknown org_tier or unknown config items, no crashes
```

---

## 9. Open Questions (All Resolved)

| # | Question | Decision | Status |
|---|----------|----------|--------|
| 1 | Brand design spec (color palette, fonts, spacing) | Reference Claude.ai homepage design, full replication for DIYU branding | **Closed** |
| 2 | PWA / Service Worker offline support? | Not needed. Offline = unavailable, acceptable. No PWA planned | **Closed** |
| 3 | Admin Console Phase 0 scope | Scope confirmed; delivery phased across Phase 0-4. Phase 0: skeleton + TierGate (FA0-1~FA0-3). Phase 2: user/org/audit (FA2-1~FA2-3). Phase 3: knowledge/review/config (FA3-1~FA3-3). Phase 4: ops/quota/backup (FA4-1~FA4-3). Billing via Web FW4-5, not Admin. | **Closed** |
| 4 | Multilingual support? | Chinese only. No i18n, remove next-intl pre-embedding | **Closed** |
| 5 | Private mode WS Token method | Method 1: reuse login access_token directly. No backend changes needed | **Closed** |
| 6 | Suggestion Chips before backend implementation | Frontend uses static fixed buttons as degradation; auto-switches to dynamic backend-driven chips when available | **Closed** |
| 7 | effective-settings API for Phase 0 | Phase 0 frontend builds shell with mock data first; backend API connects when ready | **Closed** |
| 8 | RBAC permission code naming | **RESOLVED**: Backend 06-Infrastructure lines 108-120 defines 11 permission codes. Frontend adopted exact backend naming in FE-03 Section 1.1. No "suggested naming" remains. | **Closed** |

---

## 10. Frontend Backend Backlog Summary

> Frontend does not introduce new Ports, but the following features require backend to provide new APIs or extend existing APIs. This table is for backend team scheduling reference.

| # | Backend Need | Frontend Consumer | Frontend Phase | Backend Layer | Notes |
|---|-------------|------------------|---------------|---------------|-------|
| B1 | GET /api/v1/admin/effective-settings | Config management enhancement (FE-06 9.4.11) | Phase 0 | Gateway / 06 Infrastructure | Returns merged config after inheritance chain |
| B2 | model_registry CRUD API | Global model registry (FE-06 9.4.9) | Phase 2 | 05 Gateway / LLM Gateway | ModelDefinition CRUD |
| B3 | SSE event type extensions (config change/review request/quota alert) | Notification center (FE-06 9.4.13) | Phase 2 | 05 Gateway / SSE | Existing /events/* endpoint, need new event type definitions |
| B4 | Session list + archive API | Multi-session management (FE-06 4.14) | Phase 2 | 05 Gateway / Session | Session CRUD + archive semantics |
| B5 | org_settings.branding field extension | Brand theme customization (Phase 3) | Phase 3 | 06 Infrastructure | New RULE config items: theme color/logo/font |
| B6 | Onboarding wizard completion status API | Onboarding wizard (FE-06 9.4.12) | Phase 2 | 06 Infrastructure | Persist onboarding step completion status |
| B7 | RBAC permission code final naming confirmation | Tier-Aware navigation (FE-03) | Phase 0 | 06 Infrastructure | **RESOLVED**: Backend 11 permission codes adopted exactly in FE-03 Section 1.1 |
| B8 | Knowledge entry visibility filter API parameter | Knowledge visibility partitioning (FE-06 9.4.10) | Phase 2 | 02 Knowledge | Whether existing API supports visibility filter parameter |

---

> **Document essence:** The frontend is the display extension of the backend Gateway, not a second brain. All complexity has been resolved in the backend 7-layer architecture; the frontend's responsibility is to elegantly present solutions to users.

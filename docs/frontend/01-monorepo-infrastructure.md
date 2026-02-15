# FE-01 Monorepo Infrastructure

> **contract_version**: 1.0.0
> **min_compatible_version**: 1.0.0
> **breaking_change_policy**: Expand-Contract
> **owner**: Frontend Architecture Lead
> **source_sections**: frontend_design.md Sections 4, 5.1, 5.2, 8.9

---

## 1. Tech Stack

| Layer | Selection | Rationale |
|-------|-----------|-----------|
| **Framework** | **Next.js 15 (App Router)** | RSC improves FCP, native AI SDK support, industry standard for AI apps; private mode degrades via output:'export' (ADR FE-001) |
| **Language** | **TypeScript 5.x (strict)** | Non-negotiable |
| **Monorepo** | **Turborepo + pnpm** | Incremental builds, remote caching, parallel tasks, dependency isolation |
| **Styling** | **Tailwind CSS v4** | Atomic, AI-friendly, theme system |
| **UI Base (Chat/General)** | **shadcn/ui (Radix Primitives)** | Code ownership, accessibility, AI-maintainable; for apps/web and packages/ui |
| **UI Supplement (Admin Enterprise)** | **Ant Design 5 (tree-shakeable)** | 5-level org tree, cascader, complex form layouts, approval workflows -- enterprise out-of-box; only in apps/admin (ADR FE-008) |
| **AI Chat Components** | **assistant-ui** | Professional AI Chat UX, native AI SDK integration, streaming/retry/interrupt; degrade to custom Hook if stability/customization insufficient (ADR FE-009) |
| **AI SDK** | **Vercel AI SDK 6** | useChat / Generative UI / Tool Loop; via Custom Runtime adapting DIYU WebSocket (ADR FE-009) |
| **State (Server)** | **TanStack Query v5** | Cache invalidation, optimistic updates, background refetch |
| **State (Client)** | **Zustand** | Minimal, TypeScript-first, no boilerplate |
| **Forms** | **React Hook Form + Zod** | Type-safe validation, excellent performance |
| **Markdown** | **react-markdown + rehype-highlight** | AI replies contain markdown, need safe rendering + code highlighting |
| **Animation** | **Framer Motion** | Layout animation, page transitions |
| **Charts** | **Recharts** | Composable, mature React ecosystem |
| **Icons** | **Lucide React** | Unified, lightweight |
| **Testing** | **Vitest + Playwright + RTL** | Unit / E2E / Component three-layer |
| **i18n** | **Not needed** | Chinese only. No multilingual support planned. Remove next-intl dependency |

---

## 2. Monorepo Structure

```text
diyu-frontend/
|
+-- apps/
|   +-- web/                      # User-facing app (Step 8)
|   |   +-- app/                  # Next.js App Router
|   |   |   +-- (auth)/           # Auth route group
|   |   |   +-- (main)/           # Main app route group
|   |   |   |   +-- chat/         # Conversation (Scenario 1)
|   |   |   |   +-- content/      # Content production (Scenario 2)
|   |   |   |   +-- merchandising/# Display coordination (Scenario 3)
|   |   |   |   +-- training/     # Regional training content management
|   |   |   |   +-- search/       # Global search
|   |   |   |   +-- memory/       # My memories (view/delete request/PIPL tracking)
|   |   |   |   +-- history/      # Conversation history + folder management + upload to HQ
|   |   |   |   |   +-- folders/
|   |   |   |   |   +-- upload/
|   |   |   |   +-- knowledge-edit/ # Knowledge editing workspace
|   |   |   |   |   +-- templates/
|   |   |   |   |   +-- drafts/
|   |   |   |   |   +-- submitted/
|   |   |   |   +-- store-dashboard/ # Regional agent store dashboard (regional_agent)
|   |   |   |   +-- settings/     # Personal settings
|   |   |   +-- (bookmarks)/      # Artifact bookmarks (V1.1)
|   |   |   +-- api/              # BFF Route Handlers (SaaS mode)
|   |   |   +-- layout.tsx
|   |   +-- components/           # App-specific components
|   |   +-- hooks/                # App-specific hooks
|   |   +-- stores/               # Zustand stores
|   |   +-- lib/                  # Utility functions
|   |   +-- next.config.ts        # Contains DEPLOY_MODE conditional (FE-001)
|   |   +-- __tests__/            # E2E (Playwright)
|   |
|   +-- admin/                    # Admin app (Step 9)
|   |   +-- app/                  # Next.js App Router
|   |   |   +-- (auth)/
|   |   |   +-- (dashboard)/              # Brand HQ Admin pages (brand_hq owner/admin)
|   |   |   |   +-- organizations/        # Org management + approval queue
|   |   |   |   +-- members/              # Member management (brand-wide)
|   |   |   |   +-- knowledge/            # Brand knowledge management
|   |   |   |   |   +-- import-review/    # Subordinate submission download/import status
|   |   |   |   |   +-- local-life/       # Local life knowledge base
|   |   |   |   |   +-- store-nodes/      # National store graph nodes
|   |   |   |   +-- content-review/       # Content review (default off, conditional display)
|   |   |   |   +-- experiments/          # A/B experiments
|   |   |   |   +-- billing/              # Subscription + points + usage reports
|   |   |   |   +-- settings/             # RULE/BRIDGE + BrandTone/Personas/Whitelist
|   |   |   |   +-- audit/                # Audit logs
|   |   |   +-- (platform-ops)/       # Platform ops pages (platform tier only)
|   |   |   |   +-- tenant-overview/
|   |   |   |   +-- tenant-detail/[org_id]/
|   |   |   |   +-- model-registry/
|   |   |   |   +-- model-pricing/
|   |   |   |   +-- subscription-plans/
|   |   |   |   +-- billing-global/
|   |   |   |   +-- global-config/
|   |   |   |   +-- security-config/
|   |   |   |   +-- system-ops/
|   |   |   |   +-- global-knowledge/
|   |   |   |   +-- layout.tsx            # PlatformGuard
|   |   |   +-- layout.tsx
|   |   +-- components/
|   |   +-- hooks/
|
+-- packages/
|   +-- ui/                       # Shared design system
|   |   +-- src/
|   |   |   +-- primitives/       # Base components (shadcn/ui: Button, Input, Card...)
|   |   |   +-- composites/       # Composite components (DataTable, OrgTree...)
|   |   |   +-- chat/             # AI Chat component wrappers (based on assistant-ui)
|   |   |   +-- artifacts/        # Artifact rendering components
|   |   |   +-- commerce/         # Fashion domain components (ProductCard, OutfitGrid, StyleBoard...)
|   |   |   +-- memory/           # Memory visualization (ConfidenceBadge, ProvenanceTag, MemoryCard)
|   |   |   +-- status/           # System status (DegradationBanner, ExperimentIndicator)
|   |   |   +-- data/             # Data display (Chart, MetricCard)
|   |   |   +-- themes/           # Theme tokens + dark/light
|   |   +-- package.json
|   |
|   +-- api-client/               # API client & types
|   |   +-- src/
|   |   |   +-- rest.ts           # Typed REST client
|   |   |   +-- websocket.ts      # WS connection manager
|   |   |   +-- sse.ts            # SSE client
|   |   |   +-- ai-runtime.ts     # AI SDK Custom Runtime adapter (FE-009)
|   |   |   +-- auth.ts           # Auth Strategy Factory (FE-010)
|   |   |   +-- types/            # Types generated from OpenAPI Schema
|   |   |   |   +-- org-context.ts
|   |   |   |   +-- chat.ts
|   |   |   |   +-- knowledge.ts
|   |   |   |   +-- skill-output.ts
|   |   |   |   +-- memory.ts     # MemoryItem + injection_receipt types
|   |   |   |   +-- degradation.ts # degraded_reason enum
|   |   |   +-- hooks/            # useChat, useOrg etc. TanStack Query wrappers
|   |   +-- package.json
|   |
|   +-- shared/                   # Shared utilities
|   |   +-- src/
|   |   |   +-- constants.ts
|   |   |   +-- org-tiers.ts      # Org tier constants (aligned with 06 Section 1.1)
|   |   |   +-- settings-constraints.ts  # LAW/RULE/BRIDGE 25 item enum (aligned with 06 Section 1.6)
|   |   |   +-- validators.ts     # Zod schemas
|   |   |   +-- permissions.ts    # RBAC permission utilities
|   |   |   +-- formatters.ts
|   |   |   +-- feature-flags.ts  # Feature Flag reading + condition evaluation
|   |   +-- package.json
|   |
|   +-- config/                   # Shared config
|       +-- eslint/
|       +-- typescript/
|       +-- tailwind/
|
+-- turbo.json
+-- pnpm-workspace.yaml
+-- package.json
```

---

## 3. Core Layered Architecture

```
+-------------------------------------------------------------------+
|                     Frontend Architecture Layers                    |
|                                                                     |
|  +-- View Layer ---------------------------------------------------+
|  |  apps/web/app/    Route pages + layouts                          |
|  |  apps/admin/app/  Route pages + layouts                          |
|  +-----------------------------------------------------------------+
|                            |
|  +-- Component Layer ----------------------------------------------+
|  |                                                                  |
|  |  packages/ui/primitives/   Base atomic components (shadcn/ui)    |
|  |  packages/ui/composites/   Business composite components         |
|  |  packages/ui/chat/         AI Chat components (assistant-ui wrap) |
|  |  packages/ui/artifacts/    Artifact rendering (Component Registry)|
|  |  packages/ui/commerce/     Fashion domain (ProductCard, OutfitGrid)|
|  |  packages/ui/memory/       Memory visualization (ConfidenceBadge) |
|  |  packages/ui/status/       System status (DegradationBanner)     |
|  |  packages/ui/data/         Data display (Chart, MetricCard)      |
|  +-----------------------------------------------------------------+
|                            |
|  +-- State Layer ----------------------------------------------+
|  |                                                              |
|  |  Server State: TanStack Query (API data cache/invalidation)  |
|  |  Client State: Zustand (UI state: sidebar/theme/notify/Org)  |
|  |  Chat State:   AI SDK useChat via Custom Runtime (FE-009)    |
|  |  Form State:   React Hook Form + Zod (form validation)       |
|  +--------------------------------------------------------------+
|                            |
|  +-- Transport Layer (see FE-02) --------------------------------+
|  |  packages/api-client/rest.ts       REST /api/v1/*              |
|  |  packages/api-client/websocket.ts  WebSocket /ws/conversations/{conversation_id} |
|  |  packages/api-client/sse.ts        SSE /events/*               |
|  |  packages/api-client/ai-runtime.ts AI SDK <-> DIYU WS adapter  |
|  |  packages/api-client/auth.ts       Auth Strategy Factory        |
|  +----------------------------------------------------------------+
|                            |
|                     [ Gateway API ]
```

---

## 4. State Management Strategy

```
+-- Server State (TanStack Query)
|     +-- Organization list/detail
|     +-- Member list
|     +-- Knowledge base entries
|     +-- Content review queue
|     +-- Billing usage data
|     +-- Experiment config
|     +-- My memories list + deletion status
|     Strategy: staleTime configured per data type, mutation triggers invalidation
|
+-- Chat State (AI SDK useChat via DiyuChatRuntime)
|     +-- Current conversation message list
|     +-- Streaming state (ready/submitted/streaming/error)
|     +-- Tool call progress
|     +-- Artifact data
|     Strategy: in-memory management, clean/restore on session switch
|
+-- Client State (Zustand)
|     +-- Current org context (org_id, role, permissions)
|     +-- UI preferences (sidebar, theme, layout)
|     +-- Notification queue
|     +-- Feature Flags
|     +-- Degradation state (degraded_reasons set)
|     +-- Current round injection_receipt (memory transparency panel data)
|     Strategy: persist to localStorage (non-sensitive data)
|
+-- Form State (React Hook Form)
      +-- Form data (only during form lifecycle)
      +-- Validation state
      Strategy: local state, released after submission
```

---

## 5. Package Boundary Contracts

### 5.1 packages/ui

- **Exports**: Primitives, Composites, Chat, Artifacts, Commerce, Memory, Status, Data components
- **Dependencies**: shadcn/ui (Radix), Tailwind CSS, Framer Motion, Recharts, Lucide React
- **Does NOT depend on**: Ant Design (kept pure), packages/api-client, packages/shared
- **Tier/config constants handling**: tier labels and permission/config constants are passed in via props from app layer; `packages/ui` does not import `packages/shared`
- **Consumers**: apps/web, apps/admin

### 5.2 packages/api-client

- **Exports**: REST client, WS manager, SSE client, DiyuChatRuntime, AuthStrategy, type definitions, TanStack Query hooks
- **Dependencies**: packages/shared (for types/validators)
- **Does NOT depend on**: packages/ui, any app-level code
- **Consumers**: apps/web, apps/admin

### 5.3 packages/shared

- **Exports**: org-tiers constants, settings-constraints enum, Zod validators, RBAC permission utilities, feature-flags evaluator, formatters
- **Dependencies**: Zod (only)
- **Does NOT depend on**: packages/ui, packages/api-client
- **Consumers**: packages/api-client, apps/web, apps/admin

### 5.4 packages/config

- **Exports**: ESLint config, TypeScript config, Tailwind config
- **Dependencies**: None (config files only)
- **Consumers**: All apps and packages

---

## 6. Data Flow Topology

```
Browser (apps/web or apps/admin)
   |
   +-- HTTP Request
   |       |
   |       +-- SaaS mode: Cookie auto-attached
   |       |       |
   |       |       v
   |       |   Next.js BFF (app/api/)
   |       |       |  Responsibilities: Cookie->Bearer conversion, response format adaptation,
   |       |       |                    sensitive field filtering
   |       |       |  Does NOT repeat Gateway logic (no auth/rate-limiting/routing)
   |       |       v
   |       |   Backend Gateway (/api/v1/*, /api/v1/admin/*)
   |       |
   |       +-- Private mode: In-memory Bearer Token directly attached
   |               |
   |               v
   |           Backend Gateway (/api/v1/*, /api/v1/admin/*)
   |
   +-- WebSocket (Conversation channel) -- see FE-02
   |       Browser -> wss://api.diyu/ws/conversations/{conversation_id}
   |
   +-- SSE (Notification channel) -- see FE-02
   |       SaaS mode: Browser -> BFF /api/events/* -> Backend (Cookie auto-attached, BFF converts)
   |       Private mode: Browser -> https://api.diyu/events/?token=<jwt> (direct connection)
```

---

## 7. Implementation Phases

### Phase 0: Foundation Skeleton + Admin Skeleton

```
1.  Initialize Turborepo + pnpm monorepo
2.  Create apps/web (Next.js 15 App Router)
3.  Create packages/ui (shadcn/ui + theme referencing Claude.ai design + dark/light mode)
4.  Create packages/api-client (REST + WebSocket client + Auth Strategy Factory + DiyuChatRuntime skeleton)
5.  Create packages/shared (Zod schemas, permission utils, feature-flags, org-tiers, settings-constraints)
6.  Set up CI pipeline (lint + type-check + test + bundle-size-check + a11y-check)
7.  Verify DEPLOY_MODE=private pure static build + nginx container deployment
8.  Verify Auth Strategy Factory both modes operational (Private: reuse login token for WS)
9.  Create apps/admin skeleton (Next.js 15 + Ant Design + style isolation + route group structure)
10. Admin: TierGate implementation (platform full access; brand_hq owner/admin only; others 302 to Web)
11. Admin: Config management basics (LAW/RULE/BRIDGE visualization + review_flow default none)
12. Admin: effective-settings read-only panel (frontend shell + mock data, backend API pending B1)
13. Admin: Member management (brand-wide invite/remove/role change)
14. Admin: Billing & recharge (subscription 299/month + points purchase + usage report)
15. Admin: Knowledge base basic management (CRUD + import-review + local-life + store-nodes)
```

### Phase 1: Core Conversation

```
13. Implement DiyuChatRuntime (AI SDK Custom Runtime adapting DIYU WS protocol)
14. Integrate assistant-ui, implement Chat basic flow
15. WebSocket connection manager (auth/heartbeat/reconnect/resume + Append-Only constraint)
16. Conversation input multimodal support (image upload/paste/DnD + user_message with ContentBlock[] uplink)
17. Conversation message list + streaming render + typing indicator
18. Message copy/code copy + regenerate + thumbs up/down
19. Streaming auto-scroll + scroll-to-bottom button + input auto-resize
20. Conversation page model selector + points balance/quota display
21. Base Component Registry extension (image_generation / knowledge_template / store_dashboard)
22. Dual-pane layout (Chat + Artifact toggle) + DegradationBanner
23. Error experience basics: ToastProvider + route-level ErrorBoundary + WS disconnect banner
```

### Phase 2: Three Scenarios + Memory + Admin Completion

```
24. Search experience (global search bar + intent-driven)
25. Content production view (ContentEditor + Preview)
26. Display coordination view (MerchandisingGrid + DisplayGuide)
27. Conversation history folder management (history/folders + upload)
28. Knowledge editing workspace (knowledge-edit/templates/drafts/submitted)
29. Store local knowledge folder (IndexedDB + server sync)
30. Regional agent store dashboard + store add/remove request flow
31. HQ knowledge expansion (import-review/local-life/store-nodes)
32. Billing model rebuild UI (subscription + points + recharge flow)
33. Browser notification + page visibility management + network offline recovery
34. Org switching + OrgContext management + PermissionGate
35. Memory management page + memory injection transparency panel
36. Context-Aware Suggestion Chips + Task Progress Panel
37. Admin: org/members/review/experiments/audit pages completion
38. Admin: platform ops expansion (tenant-detail/model-pricing/subscription-plans/billing-global)
39. Admin: notification center + onboarding wizard
40. User-facing: multi-session management
41. Regional training content management (training generation/submission/review flow)
42. Store inventory association UI (available/out-of-stock/alternative display)
```

### Phase 3: Brand Customization + Polish

```
43. Share function (link/QR code) + conversation/Artifact export PDF
44. Fullscreen API + long conversation virtual scrolling
45. Client telemetry (Web Vitals/errors/critical path instrumentation)
46. Performance optimization (code splitting, lazy loading, Private build size optimization)
47. E2E test suite (critical paths 100% coverage)
48. Storybook component documentation
49. Experiment variant indicator (debug mode)
50. Brand theme customization (Phase 2 reserved; GET/PUT /api/v1/admin/branding via 05a Section 2.10, L-8)
51. Artifact cross-session reference ("@" selector)
52. Accessibility audit + fixes
```

### Phase 4: Long-term Evolution

```
53. Print style completion
54. Mobile adaptation (responsive + touch gestures + voice input)
55. i18n multilingual enable (currently decided: Chinese only, see FE-00 Q4; re-evaluate if business need arises)
56. Offline PWA / Service Worker (currently decided: not planned, see FE-00 Q2; re-evaluate if business need arises)
57. Advanced analytics panel (cross-org comparison/trend prediction)
```

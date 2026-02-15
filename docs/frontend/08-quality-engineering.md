# FE-08 Quality Engineering

> **contract_version**: 1.0.0
> **min_compatible_version**: 1.0.0
> **breaking_change_policy**: Expand-Contract
> **owner**: Frontend QA Lead
> **source_sections**: frontend_design.md Sections 12, 15

---

## 1. Performance Budget (Owned Contract)

This document is the **sole owner** of performance budget thresholds.

```
Core Web Vitals targets:
  LCP (Largest Contentful Paint):  < 2.5s
  FID (First Input Delay):        < 100ms
  CLS (Cumulative Layout Shift):  < 0.1

Bundle Size (gzipped):
  apps/web first paint:  < 200KB
  packages/ui:           < 50KB (tree-shakeable)

Streaming performance:
  First AI chunk arrival to render: < 50ms
  WS reconnection: < 5s (P95)
```

---

## 2. Security Design

| Threat | Defense |
|--------|---------|
| XSS | DOMPurify sanitizes all AI-generated content; CSP policy; HTML inline forbidden (aligned with 01 Section 4.3) |
| Token leakage | SaaS: HttpOnly Cookie (JS unreadable); Private: in-memory Token + strict CSP |
| CSRF | SaaS: SameSite Cookie + CSRF Token (state-changing operations); Private: N/A (no Cookie) |
| Data leakage | Frontend does not cache sensitive data; clear all state on org switch |
| Privilege escalation | Frontend only provides UI hints, real validation at Gateway |
| Prompt Injection | Frontend input basic filtering + backend Sanitization (01 layer) |
| WS hijacking | WSS + Token auth + heartbeat detection |
| Memory data privacy | Memory panel only shows current user's own memories; Admin does not display Memory Core raw data |

---

## 3. Accessibility (a11y)

```
Target: WCAG 2.1 AA

Radix provides base accessibility primitives (focus management, aria attributes)

Additional requirements:
  - ESLint: eslint-plugin-jsx-a11y enforced check
  - Testing: axe-core integrated into CI (Playwright + @axe-core/playwright)
  - Chat bubbles: aria-live="polite" (AI streaming reply real-time announcement)
  - Color contrast: dark/light mode both meet 4.5:1 ratio
  - Keyboard navigation: all features operable via keyboard
```

---

## 4. Error Boundaries

```
Strategy: Independent ErrorBoundary per functional area

  Global ErrorBoundary
    +-- Chat ErrorBoundary        (AI failure does not affect navigation)
    |     +-- MessageList
    |     +-- StreamingIndicator
    |     +-- TaskProgressPanel
    +-- Artifact ErrorBoundary    (render failure degrades to JSON)
    |     +-- SkillRenderer
    |     +-- MemoryContextPanel
    +-- Memory ErrorBoundary      (memory panel independent)
    +-- Admin ErrorBoundary       (admin functions independent)

Error reporting:
  ErrorBoundary catches -> local degraded UI + report to monitoring (Sentry/self-hosted)
  Do not show technical details to users, only "Something went wrong, please retry"
```

---

## 5. Testing Strategy

```
Layer              | Tool                    | Coverage Target
Unit tests         | Vitest                  | Utility functions, api-client: > 80%
Component tests    | Vitest + Testing Library | Core components: > 70%
E2E tests          | Playwright              | Critical user paths: 100%
Accessibility tests| axe-core + Playwright   | All pages
Contract tests     | Based on OpenAPI spec   | api-client types synced with backend
```

### Critical E2E Paths

```
1.  Login -> select org -> start conversation -> receive streaming reply
2.  Conversation triggers Skill -> right pane shows structured content
3.  Conversation uploads image -> model recognizes and replies
4.  Create history folder -> drag to categorize -> switch folder view verify
5.  Knowledge edit -> fill template -> submit -> HQ views submission list
6.  Quota exhausted -> purchase points -> balance updated
7.  Regional agent -> store dashboard -> request new store -> HQ approval
8.  TierGate: store account accesses Admin -> 302 to Web App
9.  View AI memory -> delete one memory -> confirm deletion
10. Admin: switch org -> modify config -> child org inheritance verification
```

---

## 6. API Contract Generation

```
Pipeline:
  Backend publishes OpenAPI spec (YAML)
    -> CI: openapi-typescript generates packages/api-client/types/
    -> CI: Type validation ensures frontend-backend consistency
    -> Breaking changes auto-alert (schema diff)

  WebSocket message types:
    Manually maintained TypeScript types (packages/api-client/types/chat.ts)
    Each version tag corresponds to a ws-types snapshot
```

---

## 7. UI/UX Design Spec

### 7.1 Visual Tone

```
Aesthetic positioning: "Premium Minimalist" -- aligned with fashion industry aesthetics
Design reference: Claude.ai homepage (claude.ai) -- full replication of visual language for DIYU branding
  - Color palette, typography, spacing, and component patterns from Claude.ai
  - Adapted to DIYU brand identity (fashion industry context)

Color system:
  Default dark mode
  Supports light mode toggle
  Glassmorphism (backdrop-blur) panel effects

Language: Chinese only (no i18n / no next-intl)

Responsive: PC-first (mobile reserved)
  - Current main deliverable: desktop dual-pane workspace + Admin table-intensive operations
  - Mobile strategy: maintain route and component interface compatibility, Phase 4 enable full adaptation
  - Touch gestures/voice input: only abstract layer pre-embedded
```

### 7.2 Fashion Domain Components

```
packages/ui/commerce/:

  <ProductCard>       SKU info + image + price + compatibility tags
  <OutfitGrid>        Outfit combination (top + bottom + shoes + accessories), swappable items
  <StyleBoard>        Style inspiration panel (images + keyword tags)
  <SizeGuide>         Embedded size chart
  <ColorPalette>      Color palette selector
```

### 7.3 Keyboard Shortcuts

```
Cmd+K          Global search
Cmd+N          New conversation
Cmd+Shift+M    View AI memory panel
Cmd+Shift+B    View Artifact bookmarks
Cmd+Shift+H    Conversation history folders
Cmd+Shift+K    Knowledge editing workspace
Enter          Send message
Shift+Enter    Line break
Escape         Close right pane Artifact / close modal
```

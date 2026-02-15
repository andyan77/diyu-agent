# FE-04 Dialog Engine

> **contract_version**: 1.0.0
> **min_compatible_version**: 1.0.0
> **breaking_change_policy**: Expand-Contract
> **owner**: Frontend AI Experience Lead
> **source_sections**: frontend_design.md Sections 8.1 ~ 8.7, 8.10, 8.11, 8.12
> **depends_on**: FE-01 (package structure), FE-02 (WS protocol, SSE events), FE-03 (AuthStrategy)

---

## Scope Boundary

FE-04 owns **dialog orchestration and experience logic** only:
- DiyuChatRuntime interface and AI SDK adaptation (Owned Contract)
- Component Registry interface and rendering (Owned Contract)
- Chat State management (Owned Contract)
- Streaming rendering and Markdown processing
- Dual-pane workspace layout (Chat + Artifacts)
- Degradation UI strategy
- Context-Aware Suggestion Chips
- Task Progress Panel

FE-04 does **NOT** own:
- WS/SSE protocol definitions, connection state machine, close codes (owned by FE-02)
- Auth flow, OrgContext, TierGate (owned by FE-03)
- Page routes and non-chat feature modules (owned by FE-05)

---

## 1. AI SDK & DIYU WebSocket Bridge (ADR FE-009) -- Owned Contract

```
Design Background:
AI SDK's useChat by default assumes frontend controls LLM calls
(frontend -> Next.js API Route -> streamText -> LLM).
DIYU's LLM calls are controlled by backend Brain; frontend only receives WebSocket streaming results.
This is a fundamental protocol difference requiring an explicit adaptation layer.

Bridge Solution: assistant-ui Custom Runtime

                    assistant-ui component layer
                         |
                    useChat hook (AI SDK)
                         |
                    DiyuChatRuntime (custom adapter)
                         |
          +--- Protocol Conversion ---+--- Message Mapping ---+
          |                                                    |
    DIYU WS Protocol                                    AI SDK Message Format
    {                                                   {
      type: "ai_response_chunk",                          role: "assistant",
      delta: "...",                                       content: "...",
      event_id: "..."                                     id: "..."
    }                                                   }
    {                                                   {
      type: "tool_output",                                role: "tool",
      skill: "merchandising",                             toolName: "merchandising_search",
      data: {...}                                         result: {...}
    }                                                   }
          |                                                    |
    WebSocket /ws/conversations/{conversation_id}      assistant-ui rendering

DiyuChatRuntime Responsibilities:
1. Connection management: delegates to websocket.ts (auth/heartbeat/reconnect/resume -- FE-02)
2. Message inbound: DIYU WS message -> AI SDK Message format
3. Message outbound: User input -> DIYU WS send format
4. Streaming state: WS streaming -> AI SDK StreamState (ready/submitted/streaming/error)
5. Tool Output: DIYU tool_output -> AI SDK ToolResult -> Component Registry
6. Metadata passthrough: injection_receipt / degraded_reason -> Zustand (for UI consumption)

Fallback (if Custom Runtime complexity too high):
Backend Gateway adds /api/v1/chat HTTP endpoint, internally forwards to Brain WS,
returns as SSE stream. Frontend useChat directly connects, zero adaptation.
But adds backend work and one hop latency.
Decision: Prioritize Custom Runtime (frontend adaptation); if blocked, degrade to backend API Route.
```

---

## 2. Rendering

```
AI replies use react-markdown + rehype-highlight
Supported: text, code blocks, lists, tables, bold/italic
Unsupported: inline HTML (security concern, aligned with 01 Section 4.3 Sanitization)
```

---

## 3. Architecture Flow

```
User input -> DiyuChatRuntime -> WebSocket /ws/conversations/{conversation_id} (FE-02)
                                  |
                                  v
                       Brain streaming response
                                  |
                       +----------+-----------+
                       |                      |
                  Text chunks              tool_output chunks
                       |                      |
                  Render as Markdown       Component Registry
                  (assistant-ui built-in)  (Generative UI)
                                              |
                                  +--------- Metadata ---------+
                                  |                            |
                            injection_receipt            degraded_reason
                                  |                            |
                            Memory transparency          Degradation status
                            panel (Artifact right)       Banner (global top)
```

---

## 4. Component Registry -- Owned Contract

```
Skill returns structured tool_output, frontend renders dynamically via registry:

Component Registry Design:

registry = {
  // Coordination recommendations
  "merchandising_search":  MerchandisingGrid,
  "merchandising_display": DisplayGuideCard,
  "store_dashboard":       StoreDashboardCard,

  // Content production
  "content_draft":         ContentEditor,
  "content_preview":       ContentPreview,
  "knowledge_template":    KnowledgeTemplateForm,

  // Search & data
  "search_results":        SearchResultList,
  "data_chart":            DataVisualization,

  // Products
  "product_card":          ProductCard,
  "image_generation":      GeneratedImageCard,

  // Training & approval
  "training_material":     TrainingViewer,
  "approval_request":      ApprovalForm,

  // Memory transparency (DIYU-specific)
  "memory_context":        MemoryContextPanel,
}

Degradation strategy:
  Unknown type -> JsonViewer (raw JSON rendering)
  Render error -> ErrorBoundary + plain text fallback
  New Skill -> frontend needs no code change, displays JSON until component registered
```

Example Payload:
```json
{
  "type": "tool_output",
  "tool": "merchandising_search",
  "data": {
    "items": [{ "sku": "123", "name": "Summer dress", "image": "..." }],
    "layout": "grid"
  }
}
```

Frontend handling:
```tsx
// SkillRenderer.tsx
const REGISTRY: Record<string, ComponentType<any>> = {
  merchandising_search: MerchandisingGrid,
  outfit_recommendation: OutfitGrid,
  content_preview: ContentPreview,
  web_search: SearchResultCard,
};

export function SkillRenderer({ payload }: { payload: ToolOutput }) {
  const Component = REGISTRY[payload.tool] ?? JsonViewer;
  return <Component data={payload.data} />;
}
```

---

## 5. Dual-Pane Workspace (Chat + Artifacts)

```
Layout strategy:

+--------------------+------------------------+
|                    |                         |
|   Chat Panel       |   Artifact Panel        |
|   (left, fixed)    |   (right, dynamic)      |
|                    |                         |
|   - Message stream |   - Long copy preview/  |
|   - Search summary |     edit                |
|   - Short Q&A      |   - Coordination viz    |
|   - Agent status   |   - Data chart display  |
|                    |   - Product detail/     |
|                    |     compare             |
|                    |   - Memory injection    |
|                    |     transparency panel  |
+--------------------+------------------------+

Trigger rules:
  - tool_output.layout === "artifact"       -> right pane expands
  - tool_output.type === "memory_context"   -> right pane shows memory panel
  - Plain text length > threshold           -> right pane expands
  - User manual toggle                      -> right pane expands/collapses

Mobile adaptation:
  - This document's main implementation is PC
  - Artifact Drawer / gesture interaction deferred to Phase 4
```

---

## 6. Artifact Persistence & Cross-Session Reference

```
Inspiration: Manus uses filesystem as "infinite context" external memory -- long text written
to files rather than stuffed into prompt, read when needed. DIYU applies this concept to
Artifacts: Skill-produced intermediate results are not only displayed in current bubble,
but can be persisted cross-session, retrospectively referenced.

Persistence mechanism (no new Gateway Port):
  - Backend: tool_output already archived as conversation_events (06 Section 9)
  - Frontend: via GET /api/v1/conversations/{conversation_id}/events?type=tool_output query historical Artifacts
  - Local index: IndexedDB caches recent N Artifact metadata (title/type/conversation_id/timestamp)
    -> accelerates cross-session search, cache invalidation falls back to Gateway

Bookmarks & naming:
  - User can "bookmark" any Artifact (right pane action button)
  - Bookmark = frontend local persistence (IndexedDB) + optional backend marking (if Gateway provides bookmark API)
  - Bookmark list entry: sidebar "My Bookmarks" (Cmd+Shift+B)
  - User can customize Artifact title (default: Skill type + timestamp)

Cross-session reference (V2):
  - Typing "@" in conversation triggers Artifact reference selector
  - Search scope: bookmarked Artifacts + last 30 days tool_output
  - Selected: injected as conversation context reference (similar to "reference previous coordination plan")
  - Backend handling: referenced Artifact content appended as context to current message

Degradation:
  - GET /api/v1/conversations/{conversation_id}/events unavailable -> only show current session Artifacts
  - IndexedDB unavailable -> degrade to current session only (memory mode)
  - Bookmark feature depends on IndexedDB; hide bookmark button when unavailable
```

---

## 7. DIYU-Specific UI Concerns

### 7.1 Memory Injection Transparency Panel

```
Position: Artifact right pane (user-toggleable display)

Display content:
  This round's injected memory list, each containing:
  +-- ConfidenceBadge: confidence color scale (green >=0.8 / yellow 0.5-0.8 / gray <0.5)
  +-- ProvenanceTag:   source label (confirmed_by_user / analysis / observation)
  +-- Memory content summary
  +-- valid_since timestamp
  +-- utilized marker (whether actually referenced this round)

Data source:
  Brain streaming response metadata field (injection_receipt 5-tuple):
    candidate_score, decision_reason, policy_version, guardrail_hit, context_position
  Passed through DiyuChatRuntime to Zustand -> memory panel component consumes

Value:
  - Users can understand "why AI answered this way"
  - Debug tool: verify memory retrieval quality during dev/test
  - Can be controlled via Feature Flag whether visible to end users
```

### 7.2 Degradation State Display

```
Position: Global top Banner (packages/ui/status/DegradationBanner)

Trigger condition:
  Backend response headers or WS metadata contain degraded_reason field

  Backend degraded_reason enum (aligned with 05a-API-Contract.md Section 6.4):
  "knowledge_stores_unavailable"  -- Knowledge Stores entirely unavailable
                                     (01-Brain line 558)
  "pgvector_unavailable"          -- pgvector extension error, FTS-only fallback
                                     (01-Brain line 811)
  "query_rewrite_failed"          -- Query rewrite failed, using original query
                                     (01-Brain line 868)
  "knowledge_timeout"             -- Knowledge Stores query timeout
                                     (01-Brain line 1093)
  "budget_allocator_fallback"     -- Token budget allocator error, static baseline fallback
                                     (01-Brain line 1055)
  "llm_fallback"                  -- LLM primary model unavailable, using fallback model

Display logic:
  degraded_reason                    | User prompt                        | UI behavior
  "knowledge_stores_unavailable"     | "Knowledge base temporarily        | Hide knowledge
                                     |  unavailable, replying based on    | recommendation area
                                     |  memory only"                      |
  "knowledge_timeout"                | "Knowledge base response slow,     | Hide knowledge
                                     |  replying based on memory only"    | recommendation area
  "pgvector_unavailable"             | (not shown, user unaware)          | No visible change
  "query_rewrite_failed"             | (not shown, user unaware)          | No visible change
  "budget_allocator_fallback"        | (not shown, user unaware)          | No visible change
  "llm_fallback"                     | "Currently using backup model"     | Show model identifier
  Memory Core down (hard dep, extreme)| Global error page                 | Block all operations

Implementation:
  - Zustand stores current degraded_reasons set (type: Set<DegradedReason>)
  - DegradationBanner component subscribes, conditional rendering
  - REST responses extracted uniformly via api-client interceptor
  - WS responses passed through via DiyuChatRuntime
  - Unknown degraded_reason values: log warning, do not display to user (forward-compatible)
```

### 7.3 PIPL/GDPR Memory Management

```
Position: apps/web/(main)/memory/ page
Entry: sidebar "AI's memories of you" (Cmd+Shift+M)

Functions:
  1. My memory list: view all memory entries related to self
     - Filter by type/time/confidence/epistemic_type
     - Each shows provenance + confidence + valid_since + epistemic_type
     - Epistemic type indicator (aligned with 01-Brain Section 3.1.0.2):
         fact: "Confirmed fact" badge (solid, high trust)
         opinion: "User opinion" badge (outline)
         preference: "Preference" badge (default, backward compatible)
         outdated: "Outdated" badge (dimmed, strikethrough)
     - Confidence visualization:
         >= 0.8: solid dot (high certainty)
         0.5-0.8: half-solid dot (medium)
         < 0.5: hollow dot (low certainty)
     - Source labels:
         confirmed_by_user: "You confirmed"
         observation: "AI observed"
         analysis: "AI inferred"
     - Visual separation (aligned with privacy hard boundary):
         Personal memory: blue label "Personal"
         Brand knowledge: green label "Brand" (only appears in conversation, not in memory panel)
         The two are never mixed in display

  2. Delete request: user selects memory -> submit delete request
     - Single delete / clear all
     - Single: REST DELETE /api/v1/me/memories/{memory_id} (Response 202 + deletion_receipt)
     - Batch:  REST DELETE /api/v1/me/memories (body: { memory_ids: UUID[] })
               (Response 202 + deletion_receipt)
     - Both paths defined in 05a-API-Contract.md Section 1.2 (RESOLVED M-12)
     - Backend creates tombstone, enters deletion pipeline

  3. Deletion status tracking (aligned with 06-Infrastructure tombstone 8-state machine):
     requested -> verified -> tombstoned -> queued -> processing -> completed
                                                                -> failed -> retry_pending -> processing (loop)
                                                                          -> escalated (retries exhausted)
     Frontend label mapping:
       requested / verified       -> "Submitted" (pending icon)
       tombstoned / queued        -> "Queued" (clock icon)
       processing / retry_pending -> "Deleting..." (spinner)
       completed                  -> remove from list
       failed / escalated         -> "Deletion issue, contact support" (warning icon)
     - List shows each entry's deletion progress
     - Removed from list after completion
     - Progress API: GET /api/v1/me/memories/deletion/{receipt_id}

  4. Compliance prompt: "Your delete request will be completed within X business days"
     (aligned with legal_profile SLA)

     > Data source: SLA values from org_settings (backend-configurable) with
     > frontend hardcoded defaults as fallback. If org_settings does not specify
     > deletion SLA, use default 30 business days.
```

### 7.4 Confidence-Aware Rendering

```
When AI reply references memory, frontend displays differently based on confidence:

  confidence >= 0.8:
    Normal tone, no special marking
    Example: "You mentioned liking sporty style before"

  confidence 0.5-0.8:
    Light hint icon + tentative tone
    Example: (i) "If I recall correctly, you seem to prefer minimalist style"

  confidence < 0.5:
    Not proactively displayed, only viewable in memory panel
```

### 7.5 Experiment Variant Indicator

```
Position: User-facing bottom status bar (visible in debug mode) / Admin experiment management page

Implementation:
  - OrgContext contains current org's experiment assignments
  - packages/shared/feature-flags.ts reads and evaluates
  - Debug mode (developer/internal user): bottom shows "Variant: B (exp-042)" label
  - Production mode: not shown, but written to console.debug
  - Admin side: experiment management page shows each org's assignments + metric comparisons
```

### 7.6 Context-Aware Suggestion Chips

```
Position: Below input box

Design philosophy:
  Inspired by Manus using token logits masking to dynamically enable/disable tool calls
  at the decoding layer, reducing irrelevant tool token consumption. DIYU maps this concept
  to frontend: suggestion chips are not a static list, but dynamically generated by backend
  based on current conversation context, showing only operations relevant to current scenario.

Data source (backend-driven):
  WS downlink message extension field: suggested_actions: SuggestedAction[]
  Each contains: { id, label, intent, priority, expires_at? }
  Backend generates based on:
    - Current conversation intent (fashion coordination / inventory query / content creation / general QA)
    - Recent Skill execution results (coordination complete -> suggest follow-up actions)
    - User historical preferences (Memory Core personal memories)
    - Current Skill availability (unavailable Skills don't generate corresponding suggestions)

  Backend contract dependency:
    P3 reserved (ref M-14): suggested_actions 已在 05a-API-Contract.md Section 4.2
    作为可选扩展字段预留。Phase 1/2 允许后端不返回此字段。
    前端降级策略已就绪 (静态建议 + 本地生成)。

Scenario examples:
  Fashion coordination:
    [Change style] [View coordination detail] [Search inventory] [Save plan]

  Inventory query:
    [Filter by size] [View detail] [Similar recommendations] [Add to comparison]

  Content creation:
    [Adjust tone] [Generate more versions] [Translate to English] [Copy text]

  General/First-time user (degradation):
    [Help me recommend outfits] [Brand introduction] [Create content]

Degradation strategy:
  suggested_actions empty/missing/field not present:
    -> Fall back to static general suggestions (first-time user list)
  Returning user + no suggested_actions:
    -> Generate local suggestions based on recent session titles [Continue last coordination] [See new items]
  Aligned with FE-00 Section 4 backward compatibility: frontend does not error due to backend not returning this field
```

### 7.7 Task Progress Panel

```
Scenario: User issues compound intent -> Brain decomposes into multi-step Skill calls ->
          Frontend shows real-time execution progress

Example:
  User: "Help me coordinate a business casual outfit and search inventory"
  Progress panel:
    [done]    Understand intent: business casual coordination + inventory search
    [done]    Coordination recommendation: 3 plans generated
    [running] Inventory query: searching...
    [pending] Summarize results

Inspiration:
  Manus's todo.md attention manipulation pattern -- Agent "reads aloud" task list at the
  start of each step, forcing task focus into context via attention mechanism, preventing
  task drift in long conversations. DIYU frontend converts this concept into a user-visible
  progress panel, serving as both UI transparency and a frontend anchor for backend
  Context Engineering.

Data source:
  Consumes existing WebSocket downlink messages:
    - tool_output.status (protocol): "running" | "success" | "partial" | "error" | "rate_limited"
    - SkillResult.status (domain): "success" | "error" | "rate_limited"
      frontend lifecycle mapping:
        running -> running
        success -> completed
        partial -> completed (带“部分完成”标签)
        error -> failed
        rate_limited -> failed (show "Rate limited, retry later" + retry-after hint if present)
    - task_complete: marks overall task completion
  No new Gateway endpoint needed (aligned with Step 8 constraint: no new Ports)

UI component: <TaskProgressPanel />
  Position: collapsible area within chat bubble (click to expand detailed steps)
  Status icons: spinner(running) / checkmark(done) / x(failed) / circle(pending)
  Collapse logic: single-step tasks don't show panel; >= 2 steps auto-expand

Degradation:
  Backend doesn't return progress events -> don't show panel (silent degradation)
  Partial step failure -> failed step turns red + "Retry" button (only for retryable Skills)

Phase distinction (important):
  V1.1 -- Skill execution progress: synchronous multi-step Skill call real-time progress (this section)
  Phase 2 -- Task Orchestration: async long-task orchestration (aligned with 01-Brain Section 2.6 reserved interface)
  Frontend reserves TaskOrchestrationPanel component slot, implemented in Phase 2
```

### 7.7.1 degraded_reason Frontend Consumption

```
Data source:
  - HTTP 503 responses: Error.details.degraded_reason (05a Section 6.4)
  - WS metadata: degraded_reason field in error/status messages
  - Authoritative enum: 05a-API-Contract.md Section 6.4 (v1, 7 values)

Frontend display mapping (packages/api-client/types/degradation.ts):

  degraded_reason value              -> UI treatment
  ─────────────────────────────────────────────────────
  knowledge_stores_unavailable       -> DegradationBanner: "Knowledge search temporarily unavailable"
  knowledge_timeout                  -> DegradationBanner: "Knowledge retrieval timed out, using cached data"
  pgvector_unavailable               -> Silent (internal, no user-visible impact beyond slower search)
  query_rewrite_failed               -> Silent (fallback to original query, no user notification)
  budget_allocator_fallback          -> DegradationBanner: "Using simplified response mode"
  llm_fallback                       -> DegradationBanner: "Using backup model" (show model name if available)
  media_security_blocked             -> Inline warning: "Media content temporarily unavailable"

  Unknown value (future additions)   -> Log to console.warn + no UI blocking (forward-compatible)

Component: <DegradationBanner /> (packages/ui/status/)
  Display logic:
    - Show at top of chat area when degraded_reason is present in most recent response
    - Auto-dismiss after 30s or when next non-degraded response arrives
    - "Silent" reasons: no banner, only logged for debugging
    - Multiple simultaneous degradations: show highest-priority banner only
  Priority: media_security_blocked > llm_fallback > budget_allocator_fallback > knowledge_*

tool_output.status "partial" mapping (05a Section 4.2):
  partial -> TaskProgressPanel: show checkmark with "Partial result" label (amber color)
  UI: display available output + "Some data may be incomplete" hint
  Rationale: partial means Skill partially succeeded (e.g., 3/5 tools completed), user should see available results
```

### 7.8 Multimodal Contract Adoption (C-4 + H-14)

```
Authoritative schema source:
  05a-API-Contract.md Section 1.1 / 4.2 + 08-附录 G.2.1 ContentBlock Schema v1.1

Frontend type definition (packages/api-client/types/content-block.ts):
  type ContentBlockType = 'text' | 'image' | 'audio' | 'video' | 'document'

  interface ContentBlock {
    type: ContentBlockType
    text_fallback: string
    media_id?: string
    media_type?: 'image' | 'audio' | 'video' | 'document'
    checksum_sha256?: string
    duration_seconds?: number
    page_count?: number
    width?: number
    height?: number
  }

WS payload adoption:
  - user_message.content: ContentBlock[]
  - ai_response_chunk.content_version: number
  - text-only mode: send one text block using type='text' + text_fallback

security_status-aware rendering (H-14):
  status machine: pending | scanning | safe | rejected | quarantined | expired
  media URL fetch handling:
    403 + code=media_processing  -> show "Media is being verified" + keep text_fallback
    403 + code=media_quarantined -> show "Media flagged for review" + keep text_fallback
    404 (rejected/expired)       -> render text_fallback only
    200 safe URL                 -> render media player/viewer
  upload/complete handling:
    response.security_status != safe -> show processing badge, subscribe media_event updates
  hard rule:
    media unavailable never blocks message rendering; text_fallback always displayed
```

---

## 8. Search Experience

```
+-- Global search bar (Cmd+K / top fixed)
|     |
|     +-- Quick filter: All | Conversations | Knowledge | Products | Content
|     |
|     +-- Intent-driven: natural language -> Chat stream (via WebSocket)
|     |
|     +-- Direct search: keywords -> REST /api/v1/search (if available)
|
+-- Search result rendering:
      +-- In Chat stream: use Component Registry to render
      +-- In search mode: independent search results page (Grid/List toggleable)
```

---

## 9. Billing Awareness in Chat

```
Billing rules (per tenant):
  - Base subscription: 299 CNY/month
  - Included quota: 100 CNY equivalent Token (1:1 Qwen official pricing mapping)
  - Overage purchase: minimum 100 CNY
  - Points value: 100 CNY purchase -> 33 CNY equivalent Qwen Token
  - Commercial pricing note: overage points ~3:1 commercial markup,
    platform revenue model design, not a billing conversion bug
  - Points accumulation: purchased points roll over if unused in month, parallel to subscription quota

UI components:
  - <UsageQuotaBar />: "This month quota 67/100 CNY"
  - <ToolBudgetBar />: "Tool budget 85% remaining"
  - <PointsBalance />: "Points balance XX CNY"
  - <RechargeEntry />: visible to owner/admin, minimum 100 CNY purchase

Data source:
  - GET /api/v1/me/usage (tokens_used + budget_remaining_pct + points_balance)
  - REST headers: X-Budget-Remaining + X-Tool-Budget-Remaining
  - SSE: budget_warning (80%/95%/100%) -- cross-ref: FE-02 Section 2

Interaction:
  - 80%: "Monthly quota running low"
  - 95%: "Monthly quota approaching limit"
  - 100%: "Monthly quota exhausted, please purchase points to continue"
  - Tool budget <20%: show "Tool budget running low" warning (separate from token warning)

HTTP 402 handling:
  - Show billing-specific modal, copy includes:
    1) This month's subscription quota exhausted
    2) Points balance insufficient
    3) Purchase entry (minimum 100 CNY)
  - Not treated as generic error toast
```

---

## 10. Browser Native Capabilities & Basic Interaction Supplement

```
A-1  Multimodal input: image upload/paste/DnD + preview delete + capability grayed out
A-2  Image generation card: image_generation component + download/bookmark
A-3  Copy capability: message/code block Clipboard API one-click copy + Toast
A-4  Paste strategy: rich text degrades to plain text, images go to upload, code preserves indentation
A-5  Notification capability: SSE system_notification -> Notification API (background tab only)
A-6  Page visibility: visibilitychange reduces heartbeat frequency + foreground state check
A-7  Network detection: navigator.onLine + auto-reconnect + message resend
A-8  Fullscreen capability: Artifact Fullscreen API + ESC exit
A-9  Share capability: copy link/QR code; Web Share API only reserved interface
A-10 Export capability: conversation/Artifact export PDF/text + @media print
A-11 Voice I/O: currently only abstract interface reserved, Phase 4 implementation
A-12 Storage monitoring: navigator.storage.estimate() + 80% alert + LRU cleanup
A-13 Input enhancement: auto-resize, character count hint, Enter/Shift+Enter rules
A-14 Message actions: copy/regenerate/thumbs up/thumbs down (only last AI message can regenerate)
A-15 Scroll experience: streaming follow, manual scroll-up pauses, scroll-to-bottom button
A-16 Loading feedback: route skeletons, component-level loading, typing indicator
```

---

## 11. Supplementary Interaction Specs (D-class Details)

```
D-2 Session management UX:
  - Token about to expire: modal "Session about to expire, renew?"
  - Multi-device kick: on conflict login event, prompt and redirect to login page
  - Unsaved content leaving: beforeunload intercept + double confirmation

D-3 Multi-tab coordination:
  - Use BroadcastChannel to sync login/logout state
  - Primary tab maintains WS, secondary tabs reuse message broadcast
  - When primary tab closes, secondary tab auto-competes for new primary

D-5 Form draft recovery:
  - knowledge-edit/content forms auto-save draft every 30s (IndexedDB)
  - On re-entry after unexpected close, prompt recovery
  - Dirty data detection: route leave double confirmation

D-6 Deep links & URL state:
  - Conversation deep link: /chat/{conversation_id}
  - Admin list page filter/sort/pagination state persisted to query string
  - Page state restored after refresh, supports copying link for collaborative debugging
```

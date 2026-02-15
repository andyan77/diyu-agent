# FE-02 Transport Layer

> **contract_version**: 1.0.0
> **min_compatible_version**: 1.0.0
> **breaking_change_policy**: Expand-Contract
> **owner**: Frontend Platform Lead
> **source_sections**: frontend_design.md Sections 5.3, 7, 8.8
> **depends_on**: FE-01 (package structure), FE-03 (AuthStrategy interface), FE-07 (DEPLOY_MODE)

---

## Scope Boundary

FE-02 owns **protocol and connection management** only:
- Auth/REST/WS/SSE protocol definitions
- Connection lifecycle, state machines, heartbeat, reconnection
- Rate-limiting handling
- Message type definitions (uplink/downlink)

FE-02 does **NOT** own:
- Dialog orchestration or streaming render logic (owned by FE-04)
- Runtime adaptation or Generative UI (owned by FE-04)
- Billing awareness in chat (owned by FE-04)

---

## 1. WebSocket -- Conversation Channel (Owned Contract)

This document is the **sole owner** of WS message types, connection state machine, and close codes.

```
Endpoint: wss://api.diyu/ws/conversations/{conversation_id}
Responsibility: Bidirectional conversation (user sends message + AI streaming reply)

Connection Lifecycle:                               [aligned with 05a-API-Contract.md Section 4]
  1. Obtain WS token:
     - SaaS mode: BFF /api/auth/ws-token (Cookie -> short-lived WS token)
     - Private mode: reuse access_token
  2. Frontend: new WebSocket(wss://api.diyu/ws/conversations/{conversation_id})
     NOTE: URL 不携带 token; 认证通过首条 JSON 消息完成 (05a Section 4.1)
  3. Auth handshake (首条消息认证, 05a-API-Contract.md Section 4.1):
     -> Client sends:  { type: "auth", token: "<jwt_or_ws_token>" }
     -> Server success: { type: "auth_result", success: true, session_id: "..." }
     -> Server failure: { type: "auth_result", success: false, error: "..." } + close(4001)
  4. Heartbeat: bidirectional ping/pong (interval 30s, 05a Section 4.3)
     Server sends ping every 30s; client must respond pong
     Disconnect: consecutive 2 missed pongs (~60s) -> server cleans session
     Frontend: detect 2 missed server pings -> enter RECONNECTING state
  5. Disconnect: exponential backoff reconnect (1s -> 2s -> 4s -> 8s -> ... -> 30s cap)
     Max reconnect attempts: 10. After 10 failures, stop reconnecting and
     prompt user to manually refresh (aligned with 05-Gateway Section 7.2 / 05a Section 4.4).
  6. Reconnect: carry last_event_id to resume stream (session persists within 5 minutes)
     On reconnect success, restore session context (server correlates via session_id).
```

### 1.1 Message Types [aligned with 05a-API-Contract.md Section 4.2]

```
Downlink (server -> client):
  auth_result          -- 认证结果 { success, session_id?, error? }
  ai_response_chunk    -- AI reply text chunk { message_id, delta, content_version, finish_reason?, suggested_actions? }
  tool_output          -- Skill structured output { message_id, skill_name, status, output, text_summary }
  task_complete        -- Long task completion { task_id, result }
  error                -- Error message { error: ErrorResponse }
  ping                 -- Server heartbeat (client must respond pong)

Uplink (client -> server):
  auth                 -- 首条认证消息 { token }
  user_message         -- User message { content: ContentBlock[], reply_to?, request_id }
  pong                 -- Heartbeat response

Forbidden uplink types (Append-Only constraint, ADR FE-011):
  edit_message         -- FORBIDDEN
  delete_message       -- FORBIDDEN
  reorder_messages     -- FORBIDDEN

Naming LAW (05a Section 4.2, 05-Gateway:302-305):
  禁止使用废弃命名: assistant_chunk / assistant_complete (v1/v2 废弃)
```

### 1.2 Append-Only Client Constraint

```
- SDK does not send message edit/delete type requests
- Conversation history is append-only mode, frontend does not modify already-sent message content
- Aligned with 01-Brain Section 5: beyond-threshold messages compressed by backend to summary_blocks,
  frontend does not intervene
- Design rationale: protect backend KV cache stable prefix, maximize inference cache hit rate
  (Inspired by Manus Context Engineering "stable prefix + append-only" strategy)
- packages/api-client/websocket.ts type constraint (aligned with 05a-API-Contract.md Section 4.2):
    Uplink message types only allow: auth | user_message | pong
    Forbidden: edit_message | delete_message | reorder_messages
```

### 1.3 Connection State Machine

```
CONNECTING -> AUTHENTICATED -> READY <-> STREAMING
                                |
                            RECONNECTING -> READY
                                |          (attempts <= 10)
                                |
                            RECONNECTING -> FAILED
                                           (attempts > 10, prompt user to refresh)
                                |
                              CLOSED
```

### 1.4 Close Code Handling

```
WebSocket Connection Manager (packages/api-client/websocket.ts):

  Close code handling:
    4001 (auth failed)       -> clear credentials, redirect to login page
    4002 (session expired)   -> silently refresh token, auto-reconnect
    4003 (server maintenance)-> show maintenance page, prohibit reconnect
    1000 (normal close)      -> normal close, do not reconnect
```

---

## 2. SSE -- Notification Channel (Owned Contract)

This document is the **sole owner** of SSE event type definitions.
Event types and payload schemas aligned with 05a-API-Contract.md Section 5.2.
System events (08-Appendix G.3) map 1:1 to SSE transport via Section 5.3.

```
Endpoint:
  SaaS mode:   /api/events/* (BFF route; Cookie auto-attached, BFF converts to auth header)
  Private mode: https://api.diyu/events/?token=<access_token> (direct connection)

Authentication:
  SaaS: SSE routes through BFF (consistent with REST, 05a Section 5.1).
    BFF reads HttpOnly Cookie -> injects Authorization header -> upstream SSE.
  Private: direct connection with in-memory token.
  No AuthStrategy interface change required.

Responsibility: Unidirectional push (task completion, system alerts, async events)

Event types:                                    [aligned with 05a-API-Contract.md Section 5.2]
  task_status_update   -- Async task progress { task_id, status, progress_pct?, result? }
  system_notification  -- System-level notification { notification_id, level, title, body, action_url? }
  budget_warning       -- Quota alert { org_id, threshold_pct: 80|95|100, budget_remaining_pct, period_end }
  knowledge_update     -- Knowledge base change { knowledge_id, action, scope }
  media_event          -- Media lifecycle { media_id, subtype, payload } (7 subtypes, 05a Section 5.2)
  experiment_update    -- [Phase 2 reserved] A/B experiment status { experiment_id, status, traffic_allocation? }

Advantages (vs WebSocket):
  - SSE protocol has built-in auto-reconnect
  - HTTP native, penetrates proxies/firewalls
  - Unidirectional push scenario doesn't need WebSocket's bidirectional overhead
```

### 2.1 Media Upload Frontend State Machine

```
Media upload flow (aligned with 05a Section 1.4 + 05-Gateway Section 8):

Frontend state machine (packages/api-client/media-upload.ts):

  IDLE -> INITIATING -> UPLOADING -> COMPLETING -> SCANNING -> SAFE | REJECTED

  IDLE:
    User selects file(s) -> validate client-side (MIME, size) -> transition to INITIATING

  INITIATING:
    POST /api/v1/media/upload/init -> receive { media_id, upload_url, security_status: "pending" }
    Success -> transition to UPLOADING
    Failure (413/415/422) -> show error, return to IDLE

  UPLOADING:
    Direct PUT to presigned upload_url (S3) with x-amz-checksum-sha256
    Progress: XMLHttpRequest/fetch with upload progress tracking
    Success -> transition to COMPLETING
    Failure -> retry up to 3 times with exponential backoff, then show error

  COMPLETING:
    POST /api/v1/media/upload/complete { media_id }
    Response scenarios:
      200 + security_status: "scanning" -> transition to SCANNING (async deep scan in progress)
      4xx (checksum/magic-bytes/AV fail) -> transition to REJECTED (sync check failed)

  SCANNING (async waiting):
    Strategy: subscribe to SSE media_event (preferred) with polling fallback
      SSE events consumed:
        media.scan_completed { result: "safe" }   -> transition to SAFE
        media.rejected { reason }                  -> transition to REJECTED
        media.upload_expired                       -> transition to REJECTED (timeout)
      Polling fallback (if SSE disconnected):
        GET /api/v1/media/{media_id}/url every 5s (up to 60s)
        If returns URL -> infer SAFE
        If returns 404/410 -> infer REJECTED
    UI: show spinner + "Security scanning..." on the media placeholder

  SAFE:
    Media ready for use in ContentBlock
    UI: replace spinner with actual media preview

  REJECTED:
    UI: show rejection reason + remove from input
    Quota: automatically reclaimed by backend (no frontend action needed)

Timeout: if SCANNING exceeds 60s without SSE/poll resolution, show "Scan taking longer than expected"
         and allow user to continue composing message (media attached as pending)
```

---

## 3. REST -- CRUD Channel

```
Base: /api/v1/* (user-facing) and /api/v1/admin/* (admin)
Client: packages/api-client/rest.ts (typed REST client)
```

### 3.1 Client Timeout Configuration (Aligned with 05-Gateway Section 6)

```
packages/api-client/rest.ts default timeout configuration:

  Conversation REST endpoints (/api/v1/conversations/*):
    timeout: 60_000 ms (60s)
    Rationale: includes LLM generation time, which can be lengthy for complex tasks

  Admin/management endpoints (/api/v1/admin/*):
    timeout: 30_000 ms (30s)
    Rationale: CRUD operations should complete within reasonable time

  WebSocket idle timeout (aligned with 05a-API-Contract.md Section 4.3):
    Server sends PING every 30s; client PONG must respond within server's timeout window
    Frontend websocket.ts: count-based detection (2 consecutive missed server PINGs
    -> treat as connection lost -> enter RECONNECTING state, ~60s aligned with backend)
    Backend: consecutive 2 missed pongs -> clean session -> close connection

Source: 05a-API-Contract.md Section 4.3, 05-Gateway层.md lines 254-257
```

### 3.2 Rate-Limit and Budget Header Handling (Owned Contract)

```
Backend response headers (05a-API-Contract.md Section 7.2):
  X-RateLimit-Limit: 60
  X-RateLimit-Remaining: 3
  X-RateLimit-Reset: 1707465600
  X-Budget-Remaining: 72                -- Token budget remaining % (0-100)
  X-Tool-Budget-Remaining: 85           -- Tool budget remaining % (0-100, v3.6 ADR-047)

Frontend strategy:
  Rate limiting:
    Remaining < 5: show "Request rate approaching limit" below input box
    429 Too Many Requests:
      -> Show "Please try again later" + countdown based on Reset
      -> Exponential backoff retry (1s -> 2s -> 4s, max 3 times)
      -> Beyond retry count: prompt user to try again later

  Budget awareness:
    X-Budget-Remaining < 20: show token budget warning indicator
    X-Tool-Budget-Remaining < 20: show tool budget warning indicator
    402 Payment Required: billing-specific modal (not generic error toast)

  Media security status handling (H-14, aligned with 05a Section 1.4):
    GET /api/v1/media/{media_id}/url:
      403 + code=media_processing  -> show processing state, keep text_fallback
      403 + code=media_quarantined -> show quarantine warning, keep text_fallback
      404 (rejected/expired)       -> render text_fallback only

  packages/api-client/rest.ts built-in interceptor:
    - Auto-parse X-RateLimit-* headers
    - Auto-parse X-Budget-Remaining + X-Tool-Budget-Remaining headers
    - Queue requests to avoid triggering rate limit
```

### 3.3 Error Retry Strategy (aligned with 05a Section 6.3)

```
packages/api-client/rest.ts retry logic (05a-API-Contract.md Section 6.3):

  429 Rate Limited:
    -> Obey Retry-After header
    -> Exponential backoff: 1s -> 2s -> 4s (max 30s), max 3 retries

  5xx Server Error:
    Idempotent methods (GET/PUT/DELETE):
      -> Exponential backoff retry (1s -> 2s -> 4s, max 3 times)
      -> Exclude 501 (Not Implemented) and 505 (HTTP Version Not Supported)
    Non-idempotent methods (POST):
      -> Retry ONLY if request includes Idempotency-Key header
      -> Same backoff strategy as above
      -> Without Idempotency-Key: do NOT retry (risk of duplicate side effects)

  402 Payment Required:
    -> Do NOT retry (budget exhaustion requires human action)
```

---

## 4. Data Flow Topology Summary

```
Browser (apps/web or apps/admin)
   |
   +-- HTTP Request (REST)
   |       |
   |       +-- SaaS mode: Cookie auto-attached -> BFF -> Gateway
   |       +-- Private mode: Bearer Token directly -> Gateway
   |
   +-- WebSocket (Conversation channel)
   |       Browser -> wss://api.diyu/ws/conversations/{conversation_id}
   |       SaaS: BFF issues short-lived one-time WS token
   |       Private: reuse access_token or Gateway /api/v1/auth/ws-token
   |       Bidirectional: user messages up / AI streaming replies down
   |
   +-- SSE (Notification channel)
           SaaS: Browser -> BFF /api/events/* -> Backend (Cookie auth, BFF converts)
           Private: Browser -> https://api.diyu/events/?token=<access_token> (direct)
           Unidirectional: task completion, system alerts, async events
           Auto-reconnect (SSE protocol built-in)
```

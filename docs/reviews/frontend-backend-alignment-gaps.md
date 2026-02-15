# DIYU Agent -- Frontend-Backend Alignment Gap Report (v4)

> **audit_date**: 2026-02-11
> **revision**: v4.6.1 (v4.6 + 05a Section 4.2 tool_output.status enum aligned to 03-Skill SkillResult Schema v1; C-1/H-2 problem description paragraphs annotated [HISTORICAL])
> **backend_version**: v3.6
> **frontend_version**: FE-00 ~ FE-08 (contract_version 1.0.0)
> **auditor**: Architecture Review
> **reviewer**: Independent Third-Party (11 rounds)
> **status**: 55 DISPOSITIONED (every gap has explicit disposition: CLOSED/RESOLVED/DOCUMENTED/PHASE-RESERVED/DEFERRED/EXTERNAL/NO-ACTION)
> **disposition_policy**: 已处置(Dispositioned) = 每个 Gap 必须有明确裁决，不以“是否已开发完成”作为唯一闭环标准
> **coverage_dimensions**: Contract conflicts (C/H/M/L) + Backend API requirements (B-series) + Verified alignments (Appendix D) + Multimodal landing verification (Appendix F)
> **api_contract_doc**: 05a-API-Contract.md (v1.0, companion to 05-Gateway v3.6)

---

## Revision History

### v1 -> v2 Correction Log

| v1 Item | Error | Correction |
|---------|-------|-----------|
| C-1 | Claimed backend org_tier has 4 values, omitting `platform` | Backend 05-Gateway line 97 has 5 values: `platform/brand/region/store/counter`. Root cause upgraded to "Backend SSOT Conflict" (S-1) |
| C-2 | Claimed "12 permission codes" | Backend 06-Infrastructure lines 110-120 lists exactly 11 codes. Corrected to 11 |
| C-3 | Claimed `fallback_chain` in `model_access`, `legal_profile` in OrgContext | Backend 05-Gateway `model_access` has `allowed_models/default_model/budget_monthly_tokens` only; `legal_profile` not in OrgContext Schema v1. Corrected |
| H-7 | Listed SkillResult sub-fields (compliance_status etc.) as backend-defined | 03-Skill line 51 only declares `-> SkillResult` return type without field expansion. Downgraded to M-class |
| M-2 | Claimed frontend lacks `utilized` | FE-04 line 266 explicitly has `utilized marker`. Corrected |
| M-3 | Listed ProposalStatus/SyncStatus as defined enums | Not found as formal enums in backend docs. Corrected evidence level |

### v2 -> v3 Correction Log

| v2 Item | Issue | Correction |
|---------|-------|-----------|
| C-1 (permissions) | Severity over-rated; frontend already has replacement strategy (FE-00 B7); Gateway enforces real permissions | Downgraded from Critical to **High** (renumbered to H-1a) |
| M-1 (degraded_reason) | v2 listed backend enum values as definitive; actually these are informal string literals scattered in scenario descriptions, not a formal enum definition | Added clarification note: values are de-facto strings, not formal enum. FE-04 fix still correct but adds note about informal source |
| M-6 (KnowledgeBundle) | KnowledgeBundle is backend internal structure (Brain->Skill), frontend consumes via Gateway tool_output | Downgraded from Medium to **Low** (renumbered to L-6) |
| M-10 (experiment dimensions) | Frontend uses human-readable display names, not code enums; Phase 2 aligns naturally | Downgraded from Medium to **Low** (renumbered to L-7) |
| L-3 (SLI count) | Cited "5 SLI (ADR-036)"; ADR-038 amends ADR-036, expanding to 7 SLI | Corrected to 7 SLI (ADR-038) |
| -- | Missing 9 alignment gaps (X-1~X-9) identified by review round 2 | Added as new items with verified evidence |

### v3.1 -> v4.0 Correction Log

| v3.1 Item | Issue | Correction |
|-----------|-------|-----------|
| H-8 | Only listed user-facing REST endpoints; Admin API endpoints (FE-06) not included | Expanded H-8 to cover both user and admin API endpoints |
| M-4 | Only covered Knowledge Write/Promotion Pipeline; missed history upload and training submission | Expanded M-4 to cover all 3 submission pipelines |
| -- | B-series (FE-00 Section 10) backend requirements not tracked in Gap Report | Added H-12 (B1 effective-settings, Phase 0) + M-17~M-20 (B2/B4/B6/B8, Phase 2) + M-21 (experiments API) |
| -- | 5xx retry strategy defined in backend, not covered by frontend | Added M-15 |
| -- | WS heartbeat timeout detection mechanism inconsistent | Added M-16 |
| -- | No record of verified alignments | Added Appendix D (verified alignment items) |
| -- | No full dependency tracking matrix | Added Appendix E (frontend-backend dependency traceability matrix) |

### v4.0 -> v4.1 Correction Log

| v4.0 Item | Issue | Correction |
|-----------|-------|-----------|
| Appendix E | FE-06 dependencies only covered Section 4 (brand Admin); Section 5 Platform-Ops (7 modules) had zero coverage | Added Platform-Ops dependencies (#22~#29) to FE-06 table; added M-22 for Platform-Ops Admin API |
| -- | SSE authentication chain inconsistency across FE-01/FE-02/FE-03 not captured | Added C-3 (SSE auth chain not closed-loop) |
| H-8 Impact | Did not mention contract testing prerequisite dependency | Added note about FE-08 contract test dependency on OpenAPI |
| B5 | Tracked as "Note" only; frontend has explicit dependency (FE-01:370) | Promoted to L-8 formal Gap |
| -- | FE-06 Section 4.17 inventory association dependency not tracked | Added L-9 (conditional external dependency) |
| Coverage Summary | Claimed "100%" which was inaccurate given Platform-Ops omission | Revised to actual coverage numbers |

### v4.1 -> v4.2 Correction Log

| v4.1 Item | Issue | Correction |
|-----------|-------|-----------|
| Header | `backend_version: v3.5.1` while backend architecture docs are at v3.6 (multimodal fully landed). Audit baseline lagged by one minor version, creating blind spot on entire multimodal contract surface | Upgraded to `backend_version: v3.6`. Added full v3.6 multimodal alignment audit |
| -- | ContentBlock Schema v1.1 (ADR-043) defined in backend v3.6 but not audited against frontend multimodal design | Added **C-4** (ContentBlock Schema structural mismatch) |
| -- | Three-step upload protocol (ADR-045) endpoints defined in 05-Gateway:330-416 but not compared to frontend's assumed upload paths | Added **H-13** (upload endpoint path mismatch) |
| -- | security_status 6-state machine (ADR-051) with three-layer interception defined in backend but zero frontend reference | Added **H-14** (security_status unhandled) |
| -- | budget_tool_amount (ADR-047) and X-Tool-Budget-Remaining header not covered | Added **M-23** (tool billing gap) |
| -- | media_config RULE config items (ADR-044) not in frontend OrgSettings | Added **M-24** (media_config missing) |
| -- | content_version WS message-level field (ADR-050) not in frontend WS types | Added **M-25** (content_version unhandled) |
| -- | media_event 7 subtypes not mapped to frontend SSE | Added **M-26** (media_event gap) |
| -- | media_refs in KnowledgeBundle (v3.6 Expand) not consumed by frontend | Added **L-10** (media_refs not consumed) |
| H-2 | Only covered X-Budget-Remaining | Expanded to include X-Tool-Budget-Remaining (v3.6) |
| H-8 | Media API endpoints (8 total: 4 personal + 4 enterprise) not in endpoint catalog | Expanded with media API endpoints |
| H-9 | media_event (7 subtypes) not in SSE coverage | Expanded with media_event types |
| C-2 | WS Schema gap did not mention ContentBlock or content_version | Expanded to include multimodal payload fields |
| -- | `后端多模态完善补全.md` v3.4 Final Merge (14 items) landing verification not recorded | Added **Appendix F** with full verification evidence |
| Appendix E | Missing v3.6 multimodal dependencies across FE-02/03/04/05/06 | Added ~15 new dependency rows |
| Coverage Summary | v4.1 total 47 gaps at v3.5.1 baseline | v4.2 total **55** gaps at v3.6 baseline |

### v4.2 -> v4.3 Correction Log

| v4.2 Item | Issue | Correction |
|-----------|-------|-----------|
| C-3 | SSE authentication chain not closed-loop: FE-01/FE-02/FE-03 three-way inconsistency on SSE auth in SaaS mode. HttpOnly Cookie JS-inaccessible but SSE endpoint required JWT query parameter | **RESOLVED**: Selected Option A (SSE routes through BFF). Updated FE-01 Section 6 (topology), FE-02 Section 2 (endpoint), FE-03 Section 2.1 (SSE auth flow). No AuthStrategy interface change needed |
| H-11 | Resolution options listed but no selected option or backend team backlog notation | Added **Backend Team Backlog** note: Option A selected (DP endpoint). Backend must provide `GET /api/v1/organizations?scope=regional` before Phase 1 |
| M-14 | Classified as generic Medium gap; actual nature is frontend feature request, not backend omission | Added **Classification Note**: M-14 is D-class (frontend feature request), not A-class (backend design omission) |
| L-2 | FE-04 Section 7.3 SLA data source unspecified | Added data source annotation to FE-04: org_settings with hardcoded 30-day default fallback |
| L-4 | content_policy enum UI impact not documented in frontend | Added UI impact mapping to FE-06 Section 4.3: relaxed/standard/strict behavior |
| L-5 | Privacy hard boundary (FE-00 constraint #3) missing ADR-018 traceability reference | Added `(ref: ADR-018)` to FE-00 Section 8 constraint #3 |
| Gap Summary | 7 RESOLVED | **8 RESOLVED** (+C-3 resolved in v4.3) |

### v4.5 -> v4.6 Adjudication Landing

| v4.5 Item | Issue | Correction |
|-----------|-------|-----------|
| Global status semantics | "closed vs reserved vs open" mixed usage caused interpretation ambiguity | Adopted **Dispositioned** policy: each gap must have explicit adjudication outcome |
| M-18 | Session lifecycle only partially defined (missing rename/delete) | 05a Section 1.1 added PATCH title update + DELETE permanent delete; M-18 closed |
| M-21 | FE required assignments/event reporting while backend only had admin experiments API | Adjudicated backend-only runtime ownership; FE-06 removed assignments/event dependency |
| C-4/H-14/M-23/M-24/H-7 | Backend-side closed but FE docs had incomplete adoption traces | FE-04/FE-03/FE-02 documentation updated with explicit frontend handling logic |
| Appendix E | Status column stale (many OPEN rows conflicted with正文) | Appendix E statuses synchronized to `DISPOSITIONED` rule (no residual OPEN rows) |
| H-7 / 05a Section 4.2 | tool_output.status 枚举仅 3 值 (running/success/error)，缺少 rate_limited/partial，与 03-Skill:62 SkillResult Schema v1 不对齐 | 05a Section 4.2 tool_output.status 补齐为 5 值: running/success/partial/error/rate_limited，含语义说明 |
| C-1 / H-2 问题描述 | 正文 Analysis/Frontend 段落保留 v1 旧表述 (如 "URL query parameter"、"Only parses X-RateLimit-*")，虽 Status 已 CLOSED 但误导首次阅读者 | 在问题描述段落添加 `[HISTORICAL]` 标注，明确为初始发现快照而非当前状态 |

---

## Severity Definitions

| Level | Definition | Action Required |
|-------|-----------|-----------------|
| **Structural** | Backend documents internally inconsistent, blocking all downstream alignment | Must resolve at backend level before frontend can align |
| **Critical** | Data contract mismatch that will cause runtime failure at integration time | Must fix before Phase 0 development |
| **High** | Enum/field/protocol mismatch causing incorrect behavior or logic errors | Must fix before corresponding Phase |
| **Medium** | Missing specification with reasonable defaults available | Should fix, can use temporary workaround |
| **Low** | Documentation inconsistency or optimization opportunity | Fix when convenient |

---

## Gap Summary

| Severity | Count | Phase 0 Resolved |
|----------|-------|------------------|
| Structural | 1 | 1 (DOCUMENTED, backend-owned) |
| Critical | 4 (+C-4 new in v4.2) | 1 (C-3 resolved in v4.3) |
| High | 15 (+H-13, H-14 new in v4.2) | 4 (H-1, H-1a, H-3 + C-2 v2) |
| Medium | 25 (+M-23~M-26 new in v4.2) | 2 (M-1, M-10) |
| Low | 10 (+L-10 new in v4.2) | 0 |
| **Total** | **55** | **8** (7 substantive + 1 documented) |

> **v4.2 Coverage Note**: v4.1 tracked 47 items at backend v3.5.1 baseline. v4.2 upgrades baseline to v3.6, adding 8 new gaps for multimodal contract surface alignment (C-4, H-13~14, M-23~26, L-10), expanding 4 existing gaps (H-2, H-8, H-9, C-2) with v3.6 additions, and adding Appendix F (multimodal landing verification). v3.6 multimodal architecture (14 items from `后端多模态完善补全.md` v3.4 Final Merge) has been verified as fully landed in backend architecture docs. See Appendix F for verification evidence.

---

## Structural Gaps (Backend SSOT Conflict)

### S-1. org_tier Enum Inconsistent Across Backend Documents

**Backend 05-Gateway (line 97) OrgContext Schema v1**:
```
org_tier: "platform" | "brand" | "region" | "store" | "counter"
```

**Backend 06-Infrastructure (lines 30-36) Organization tier definition**:
```
tier: platform | brand_hq | brand_dept | regional_agent | franchise_store
```

**Frontend (FE-03 Section 3)**:
```
org_tier: 'platform' | 'brand_hq' | 'brand_dept' | 'regional_agent' | 'franchise_store'
```

**Analysis**: The two backend documents define the same concept with incompatible enums:
- 05-Gateway uses abbreviated generic names (5 values: `platform/brand/region/store/counter`)
- 06-Infrastructure uses business-specific names (5 values: `platform/brand_hq/brand_dept/regional_agent/franchise_store`)
- Frontend adopts 06-Infrastructure's naming

This is NOT a frontend-backend alignment problem -- it is a **backend internal SSOT conflict**. The frontend cannot align until backend resolves which enum is authoritative.

**Impact**: Frontend's TierGate, PermissionGate, and feature exposure matrices use 06-Infrastructure naming. If Gateway sends 05-Gateway naming at runtime, every permission check will fail.

**Resolution**: Backend team must designate one authoritative org_tier enum.

**Status**: **DOCUMENTED** -- FE-03 Section 3.1 now contains explicit WARNING block. Frontend adopts 06-Infrastructure naming with mapping strategy documented. v3.6 ADR-049 has unified org_tier to 06-Infrastructure's 5-level business naming (05-Gateway lines 97-99 updated).

**Evidence**: `05-Gateway层.md` lines 97-99 (v3.6 ADR-049), `06-基础设施层.md` lines 30-36

---

## Critical Gaps

### C-1. WS Authentication Method Conflict [NEW in v3]

**Backend (05-Gateway line 272)**:
```
连接建立 -> 认证（首条消息携带 token）
```

**Frontend (FE-02 line 37) [HISTORICAL -- v1 snapshot; FE-02 已改为首条 JSON 认证]**:
```
Frontend: new WebSocket(url + ?token=<ws_token>)   // v1 旧设计, 已废弃
```

**Analysis [HISTORICAL -- v1 initial finding, below describes the original conflict; see Status for current state]**: Backend specifies authentication via **first message** (in-band). Frontend implements authentication via **URL query parameter** (out-of-band). These two approaches are fundamentally incompatible -- the WebSocket handshake will succeed, but authentication will never complete because:
- Backend waits for first message containing token
- Frontend already sent token in URL and expects to be authenticated immediately

**Impact**: **Phase 0 blocker**. No WS connection can authenticate without resolving this conflict.

**Resolution**: Backend and frontend must agree on one method:
- Option A: Backend accepts URL query param (common in web apps, but token visible in server logs)
- Option B (selected): Frontend sends token as first message after connection (more secure, requires protocol change in FE-02)
- Option C: Backend accepts both (most flexible, recommended)

**Status**: **CLOSED** -- 05a-API-Contract.md Section 4.1 + FE-02 Section 1 已统一为首条 JSON 认证（不通过 URL query 传 token）。

**Evidence**: `05-Gateway层.md` line 272, `02-transport-layer.md` line 37

**Affected FE Docs**: FE-02 Section 1, FE-03 Section 2.1/2.2

---

### C-2. WS Message Types Backend Has No Formal Definition [NEW in v3, downgraded to High in v4.4]

**Backend (05-Gateway lines 276-280)**:
```
消息类型（语义级，不锁定字段名）:
+-- 用户消息: 用户输入文本/指令
+-- AI 响应: 流式文本块 / 完成标记
+-- 系统事件: Skill 执行状态、错误通知
+-- 心跳: 双向 ping/pong（间隔 30s）
```

**Frontend (FE-02 Section 1.1)**: Defines 8 concrete message types with specific type strings:
```
Downlink: ai_response_chunk, tool_output, task_complete, error
Uplink: user_message, multimodal_message, ping, session_resume
```

**Analysis**: Backend explicitly states "语义级，不锁定字段名" (semantic level, field names not locked). Frontend has already committed to specific type strings and payload formats. There is no backend schema to validate against -- frontend's message types are entirely self-defined.

**Impact**: **Phase 0 blocker**. When backend implements WS message handling, their field names/types may differ from frontend's assumed format, causing parse failures.

**Resolution**: This is fundamentally a **backend API contract gap**. Backend Gateway team must publish a formal WS message schema (type strings + payload structure) before frontend can validate alignment.

**Interim action**: Frontend should mark FE-02 Section 1.1 message types as "frontend-proposed, pending backend confirmation".

**v4.2 expansion**: Backend v3.6 adds multimodal payload fields to WS messages (ADR-043/050). When backend publishes formal WS schema (resolving C-2), it MUST include:
- `blocks?: ContentBlock[]` field in both `user_message` (uplink) and `ai_response_chunk` (downlink)
- `content_version?: number` field for multimodal capability negotiation
- See C-4 for ContentBlock Schema v1.1 structural definition
- See M-25 for content_version semantics

**Severity**: Downgraded from Critical to **High** in v4.4. Rationale: Backend 05-Gateway v3.6 lines 294-305 now locks field names (`ai_response_chunk`, `tool_output`, `task_complete`) as LAW naming constraints, reducing the risk of field name divergence. The remaining gap is formal payload schema (field types, required/optional), not fundamental incompatibility.

**Status**: **CLOSED** -- Backend-side resolved via 05a-API-Contract.md Section 4.2 (WS Message Schema). All message types defined with type strings, payload fields, and required/optional annotations. Frontend FE-02 Section 1.1 message types confirmed aligned.

**Evidence**: `05-Gateway层.md` lines 276-280/289-299, `02-transport-layer.md` lines 47-63

**Affected FE Docs**: FE-02 Section 1.1, FE-04 Section 1

---

### C-3. SSE Authentication Chain Not Closed-Loop [NEW in v4.1]

**FE-02 (line 137)**: SSE endpoint specified as direct connection with JWT query parameter:
```
Endpoint: https://api.diyu/events/?token=<jwt>
```

**FE-03 (lines 65-66)**: SaaS mode (CookieAuthStrategy):
```
getHeaders()          -> empty (Cookie auto-attached by browser, BFF converts)
getWsToken()          -> POST /api/auth/ws-token (BFF endpoint)
```
No `getSseToken()` or equivalent method defined.

**FE-01 (line 293)**: Network topology diagram:
```
Browser -> https://api.diyu/events/?token=<jwt>
```

**Analysis**: Three-way inconsistency in the SSE authentication chain:

1. **SaaS mode has no explicit SSE token acquisition**: CookieAuthStrategy defines `getHeaders()` (empty) and `getWsToken()` but NOT an SSE token method. How does the frontend obtain the JWT for SSE URL query parameter?

2. **Direct connection vs BFF proxy**: SaaS mode architecture routes REST through BFF (which converts HttpOnly Cookie to Authorization header). But FE-01 and FE-02 show SSE as **browser direct connection** to `api.diyu`. If SSE bypasses BFF, the HttpOnly Cookie cannot provide authentication (SSE EventSource API does not support custom headers). If SSE goes through BFF, the URL should be a BFF route, not `api.diyu`.

3. **Private mode works, SaaS mode does not**: Private mode (BearerAuthStrategy) has explicit token in memory, so `?token=<jwt>` works. But SaaS mode stores auth in HttpOnly Cookie (inaccessible to JS), so frontend cannot construct the token URL.

**Impact**: **Phase 0 blocker for SaaS deployment**. SSE notifications will fail to authenticate in SaaS mode.

**Resolution options**:
- Option A (selected): SaaS mode routes SSE through BFF (`/api/events/*` BFF route), BFF injects auth. FE-01/FE-02 URLs change.
- Option B: AuthStrategy interface adds `getSseToken()` method, SaaS mode calls BFF to get a dedicated SSE token.
- Option C: Backend SSE endpoint accepts HttpOnly Cookie authentication (no query param needed in SaaS mode).

**Status**: **RESOLVED in v4.3** -- Option A selected and implemented. SSE in SaaS mode routes through BFF (consistent with REST routing). Changes applied:
- FE-01 Section 6: Network topology updated -- SSE shows BFF route for SaaS, direct for Private
- FE-02 Section 2: SSE endpoint updated to dual-mode (BFF route / direct connection)
- FE-03 Section 2.1: SSE auth flow added to SaaS Auth Flow section
- No AuthStrategy interface change needed (BFF handles auth transparently)

**Evidence**: `02-transport-layer.md` line 137, `03-auth-permission.md` lines 65-68, `01-monorepo-infrastructure.md` line 293

**Affected FE Docs**: FE-01 Section 6, FE-02 Section 2, FE-03 Section 2.1

---

### C-4. ContentBlock Schema Structural Mismatch (Frontend vs Backend v3.6) [NEW in v4.2]

**Backend (05-Gateway:292/296/430, 01-Brain:918-926, 06-Infrastructure:891-935)**:
ContentBlock Schema v1.1 (ADR-043):
```
{
  type: "text" | "image" | "audio" | "video" | "document",
  media_id?: UUID,              // External unified ID (LAW)
  text_fallback: string,        // REQUIRED for all media blocks
  media_type?: "image" | "audio" | "video" | "document",
  checksum_sha256?: string,     // Integrity verification (v3.6)
  // Optional metadata per type:
  duration_seconds?: number,    // audio/video
  page_count?: number,          // document
  width?: number,               // image
  height?: number               // image
}
```

**Frontend (FE-04 Section 7, inferred from multimodal design)**:
Frontend self-defines a different ContentBlock structure:
```
{
  type: "text" | "image" | "file",
  source?: { type: "base64" | "url" | "reference", media_type?, data?, url? },
  name?: string,
  mime_type?: string,
  size?: number,
  file_id?: string
}
```

**Analysis**: Five structural incompatibilities:
1. **Type values differ**: Backend has 5 media types (`image/audio/video/document`); frontend has 2 (`image/file`)
2. **Media reference mechanism**: Backend uses `media_id` (UUID, references personal/enterprise_media_objects); frontend uses `source.url` or `file_id`
3. **Mandatory field missing**: Backend requires `text_fallback` on every media block; frontend has no equivalent
4. **Integrity field absent**: Backend includes `checksum_sha256`; frontend has no checksum
5. **Nesting structure differs**: Backend is flat (`media_id` at top level); frontend nests media reference inside `source` object

**Impact**: **Phase 1 blocker (multimodal feature)**. WS messages carrying multimodal content will fail to deserialize. Frontend `multimodal_message` uplink will not match backend's expected `blocks: [ContentBlock]` format. Backend `ai_response_chunk` with `blocks` field will not render correctly in frontend.

**Resolution**: Frontend must adopt backend's ContentBlock Schema v1.1. Specific changes:
- `packages/api-client/types/content-block.ts`: Define type matching backend schema exactly
- `packages/api-client/websocket.ts`: WS uplink `user_message` includes `blocks: [ContentBlock]` and `content_version: 1`
- Frontend Component Registry: Map `type` values to renderers (`audio` -> AudioPlayer, `video` -> VideoPlayer, `document` -> DocumentViewer)
- `text_fallback`: Always provide; used as degradation display when media unavailable

**Status**: **CLOSED** -- Backend Schema authority + Frontend adoption 均已落盘：05a-API-Contract.md Section 1.1/4.2 与 FE-04 Section 7.8 统一使用 ContentBlock Schema v1.1。

**Evidence**: `05-Gateway层.md` lines 292-296/430, `01-对话Agent层-Brain.md` lines 918-926, `06-基础设施层.md` lines 891-935

**Affected FE Docs**: FE-02 Section 1.1, FE-04 Sections 4/7, FE-05 Section 2

---

## High Gaps

### H-1. WS Reconnect Max Attempts Mismatch

**Backend (05-Gateway line 301)**: Maximum 10 reconnect attempts, then prompt user to refresh.

**Frontend (FE-02 Section 1)**: Previously no max specified.

**Status**: **RESOLVED** -- FE-02 Section 1 updated with max 10 attempts + FAILED terminal state.

**Evidence**: `05-Gateway层.md` line 301

---

### H-1a. Permission Code Naming Mismatch [downgraded from C-1 in v2]

**Backend (06-Infrastructure lines 110-120)**: 11 permission codes using singular form (`member.manage`).

**Frontend**: Previously used suggested plural form (`members.manage`). Frontend explicitly pre-planned replacement strategy (FE-00 Backlog B7).

**Impact**: Downgraded from Critical because: (1) frontend already has replacement strategy, (2) permission enforcement is at Gateway, frontend only does UI visibility.

**Status**: **RESOLVED** -- FE-03 Section 1.1 now contains all 11 exact backend permission codes.

**Evidence**: `06-基础设施层.md` lines 108-120, `03-auth-permission.md` Section 1.1

---

### H-2. Missing Budget Header Handling [expanded in v4.2]

**Backend (05-Gateway line 234, lines 444-445)**: Returns budget headers:
```
X-Budget-Remaining          -- Token budget percentage remaining
X-Tool-Budget-Remaining     -- Tool budget percentage remaining (v3.6 NEW, ADR-047)
```

**Frontend (FE-02 Section 3.2) [HISTORICAL -- v1 initial finding; see Status for current state]**: Only parses `X-RateLimit-*` headers. Neither `X-Budget-Remaining` nor `X-Tool-Budget-Remaining` is parsed.

**Resolution**: Add both `X-Budget-Remaining` and `X-Tool-Budget-Remaining` parsing to rest.ts interceptor. Display dual-dimension budget indicators. See also M-23 for the broader budget_tool_amount gap.

**Status**: **CLOSED** -- 05a-API-Contract.md Section 7.2 定义 + FE-02 Section 3.2 已解析 X-Budget-Remaining / X-Tool-Budget-Remaining。

**Evidence**: `05-Gateway层.md` line 234, lines 444-445

**Affected FE Docs**: FE-02 Section 3.2, FE-04 Section 9

---

### H-3. Client Timeout Values Not Specified

**Backend (05-Gateway lines 256-257)**: Chat 60s, Admin 30s.

**Status**: **RESOLVED** -- FE-02 Section 3.1 now specifies timeout configuration.

**Evidence**: `05-Gateway层.md` lines 256-257

---

### H-4. Missing epistemic_type Enum in Memory Panel

**Backend (01-Brain Section 2.3, 06-Infrastructure lines 666-669)**: `epistemic_type: "fact" | "opinion" | "preference" | "outdated"`.

**Frontend (FE-04 Section 7.1, 7.3)**: Memory panel shows confidence + provenance but NOT epistemic_type.

**Note**: epistemic_type is v3.5.2 addition; frontend docs based on v1.0.0 contract. Version gap is expected but must be addressed before Phase 2.

**Resolution**: Add epistemic_type as filter and visual indicator.

**Disposition**: **DISPOSITIONED** -- Backend/Frontend 都已明确定义，前端吸收完成。

**Status**: **CLOSED** -- FE-04 Section 7.3 已包含 epistemic_type 过滤与展示。

**Affected FE Docs**: FE-04 Sections 7.1, 7.3

---

### H-5. Knowledge Visibility Inheritance UI Not Specified

**Backend (02-Knowledge Section 3.1)**: Defines `inheritable` and `override_allowed` flags.

**Frontend (FE-06 Section 4.10)**: Only visibility labels, no inheritance UI. Tagged [Phase 2].

**Resolution**: Add inheritance visualization before Phase 2.

**Disposition**: **DISPOSITIONED** -- Backend/Frontend 都已明确定义，前端吸收完成。

**Status**: **CLOSED** -- FE-06 Section 4.10 已包含 inheritable/override_allowed UI 与数据源。

**Affected FE Docs**: FE-06 Section 4.10

---

### H-6. Deletion Pipeline State Machine Incomplete

**Backend (06-Infrastructure lines 633-636)**: 8 states.

**Frontend (FE-04 Section 7.3)**: 3 states.

**Resolution**: Map all 8 backend states to frontend labels.

**Disposition**: **DISPOSITIONED** -- Backend/Frontend 都已明确定义，前端吸收完成。

**Status**: **CLOSED** -- FE-04 Section 7.3 已落盘 8-state 映射与前端标签策略。

**Evidence**: `06-基础设施层.md` lines 633-636, `04-dialog-engine.md` Section 7.3

---

### H-7. Tool Execution Status Missing "rate_limited"

**Backend (04-Tool line 86)**: `status: success | error | rate_limited`

**Frontend (FE-04 Section 7.7)**: `"started" | "running" | "completed" | "failed"` (lifecycle states, not result states).

**Resolution**: Define mapping between backend result states and frontend lifecycle states. Add `rate_limited` handling.

**Status**: **CLOSED** -- 03-Skill SkillResult Schema v1 + FE-04 Section 7.7 映射规则已包含 rate_limited。

**Affected FE Docs**: FE-04 Section 7.7

---

### H-8. REST API Endpoint Contract Gap [NEW in v3, expanded in v4, v4.2]

**Backend (05-Gateway lines 66-74, 330-416)**: Defines route partitions (`/api/v1/*` user, `/api/v1/admin/*` admin) but only specifies **1 concrete user endpoint**: `DELETE /api/v1/me/memories`. v3.6 adds 8 media endpoints (4 personal + 4 enterprise) with full request/response schemas, but these are the exception -- most endpoints remain unspecified.

**Frontend**: Consumes 10+ user-facing REST endpoints AND 8+ admin REST endpoints across FE-03 through FE-06, all without backend formal contract:

User-facing endpoints (`/api/v1/*`):
- `GET /api/v1/me/memories` (FE-05 Section 3.2)
- `DELETE /api/v1/me/memories/{id}` (FE-04 Section 7.3) -- see also M-12
- `GET /api/v1/sessions/{id}/events` (FE-04 Section 6)
- `GET /api/v1/billing/usage` (FE-04 Section 9)
- `GET /api/v1/billing/points-balance` (FE-04 Section 9)
- `GET /api/v1/search` (FE-04 Section 8)
- `POST /api/auth/login` (FE-03 Section 2.1)
- `POST /api/auth/ws-token` (FE-03 Section 2.1)
- Various session CRUD APIs (FE-05 Section 3.3)

Media endpoints (`/api/v1/media/*`) [added in v4.2 -- NOTE: these ARE defined in backend v3.6]:
- `POST /api/v1/media/upload/init` (05-Gateway:330) -- presigned URL generation
- `POST /api/v1/media/upload/complete` (05-Gateway:360) -- upload confirmation + security scan
- `GET /api/v1/media/{media_id}/url` (05-Gateway:390) -- presigned download URL
- `DELETE /api/v1/media/{media_id}` (05-Gateway:410) -- trigger deletion pipeline

Admin endpoints (`/api/v1/admin/*`) [added in v4]:
- `GET/POST/PUT/DELETE /api/v1/admin/organizations` (FE-06 Section 4.1)
- `GET/POST/DELETE /api/v1/admin/members` (FE-06 Section 4.2)
- `PUT /api/v1/admin/settings` (FE-06 Section 4.3)
- `GET/POST/PUT /api/v1/admin/knowledge` (FE-06 Section 4.4)
- `GET/POST/DELETE /api/v1/admin/experiments` (FE-06 Section 4.5)
- `GET /api/v1/admin/billing` (FE-06 Section 4.6)
- `GET /api/v1/admin/audit` (FE-06 Section 4.7)
- `GET /api/v1/admin/effective-settings` (FE-06 Section 4.11) -- also tracked as H-12

Enterprise media endpoints (`/api/v1/admin/knowledge/media/*`) [added in v4.2]:
- `POST /api/v1/admin/knowledge/media/upload/init` (FE-06 Section 4.4)
- `POST /api/v1/admin/knowledge/media/upload/complete` (FE-06 Section 4.4)
- `GET /api/v1/admin/knowledge/media/{media_id}/url` (FE-06 Section 4.4)
- `DELETE /api/v1/admin/knowledge/media/{media_id}` (FE-06 Section 4.4)

**Analysis**: This is a **backend API contract documentation gap**. Backend Gateway doc focuses on middleware/routing architecture rather than endpoint catalog. Frontend has specified these endpoints based on feature requirements without backend formal contract. v4 expansion: Admin Console (FE-06) consumes even more unspecified admin endpoints than the user app. Admin Console Phase 0 scope includes organizations, members, knowledge, billing, and settings -- all without backend API contracts. v4.2 note: Backend v3.6 media endpoints (personal 4 + enterprise 4) ARE fully specified with request/response schemas in 05-Gateway:330-416 -- these are the ONLY consumer-facing endpoints with complete contract in the entire backend Gateway documentation. See H-13 for path mismatch between these specified endpoints and frontend assumptions.

**Impact**: All REST integrations (user AND admin) are unvalidated. Path, parameters, request/response schemas undefined by backend. Additionally, FE-08 Section 5 defines "Contract tests: Based on OpenAPI spec" (line 95) -- this testing layer cannot be implemented until H-8 is resolved, making the frontend's quality engineering strategy partially blocked.

**Resolution**: Backend Gateway team should publish a REST API catalog (or OpenAPI spec) covering both `/api/v1/*` and `/api/v1/admin/*` partitions. Until then, all frontend endpoints are self-proposed.

**Status**: **CLOSED** -- Resolved via 05a-API-Contract.md Sections 1-3. Complete REST API catalog covering User API (Section 1), Admin API (Section 2), and Platform-Ops API (Section 3).

**Evidence**: `05-Gateway层.md` lines 60-74, FE-03~FE-06 multiple sections

**Affected FE Docs**: FE-02, FE-03, FE-04, FE-05, FE-06

---

### H-9. SSE Event Types Backend Has No Definition [NEW in v3]

**Backend (05-Gateway lines 80-82)**:
```
/events/*       -> SSE 分区
  认证: 查询参数或 Header 携带 token
  消费者: Frontend UI / Admin Console
```

No event type definitions, no payload schemas, no event names.

**Frontend (FE-02 Section 2)**: Defines 4 SSE event types:
```
task_status_update, system_notification, budget_warning, knowledge_update
```

**Analysis**: Same systemic issue as C-2 (WS) -- backend defines transport existence but not message contract. Related to M-7 (event mapping to 08-Appendix G.3) but more fundamental: the Gateway layer itself has no SSE event schema.

**Resolution**: Backend Gateway should define SSE event types. Until then, frontend event types are self-proposed.

**Status**: **CLOSED** -- Resolved via 05a-API-Contract.md Section 5 (SSE Event Schema). All event types defined with payload schemas.

**v4.2 expansion**: Backend v3.6 adds `media_event` with 7 subtypes (06-Infrastructure:558-577): `upload_initiated | upload_completed | upload_expired | scan_completed | rejected | deletion_requested | deletion_completed`. These are defined in the event model but NOT mapped to SSE transport, widening the SSE event gap from the original 4 frontend-proposed types to now 4 + 7 = 11 types needing backend SSE schema. See M-26 for detailed media_event gap.

**Evidence**: `05-Gateway层.md` lines 80-82, `06-基础设施层.md` lines 558-577, `02-transport-layer.md` lines 111-115

**Affected FE Docs**: FE-02 Section 2

---

### H-10. DEPLOY_MODE Backend Has No Formal Definition [NEW in v3]

**Backend (07-Deployment lines 11-15)**: Describes three deployment modes conceptually in a table (SaaS, Private, Hybrid) but does NOT define a formal enum or contract.

**Frontend (FE-07 lines 16-21)**: Defines formal enum:
```
DEPLOY_MODE = 'saas' | 'private' | 'hybrid'
```
FE-07 declares itself as **"sole owner"** of this contract.

**Analysis**: Frontend proactively owns this definition, which is correct given backend's lack of formal definition. The risk is if backend implements deployment mode detection with different naming.

**Resolution**: Backend should either (a) formally adopt frontend's `DEPLOY_MODE` enum, or (b) publish their own enum for frontend to align to.

**Status**: **CLOSED** -- Resolved via 07-部署与安全.md Section 1.1 (DEPLOY_MODE formal definition) and 05a-API-Contract.md Section 7.3. Formally defines "saas" | "private" | "hybrid" with semantics.

**Evidence**: `07-部署与安全.md` lines 11-15, `07-deployment.md` lines 13-21

**Affected FE Docs**: FE-07 (owns), FE-00, FE-01, FE-02, FE-03 (consume)

---

### H-11. regional_agent Web Route Uses Admin API Without Admin Permission [NEW in v3.1]

**Frontend (FE-05 line 170)**:
```
store-dashboard/ Data source: REST /api/v1/admin/organizations (filtered by regional scope)
```

**Backend (05-Gateway lines 61-62)**:
```
/api/v1/admin/* -> 管理 API 分区 [CP - Control Plane]
  中间件: JWT 认证 -> OrgContext 组装 -> RBAC 权限校验(需 *.manage 类权限码)
```

**Frontend (FE-03 line 237)**: `regional_agent` has no Admin Console entry. FE-03 Section 1.1 shows `regional_agent` typical roles do not have `org.manage` permission.

**Analysis**: The store-dashboard route in Web App (accessible to `regional_agent`) calls `/api/v1/admin/organizations`, which is in the admin API partition requiring `*.manage` permissions. But `regional_agent` users do not have `org.manage` or any `*.manage` permission. This creates a guaranteed 403 Forbidden at runtime.

**Impact**: store-dashboard feature will be completely non-functional for its intended users (`regional_agent`). This is a permission chain contradiction within the frontend's own documents (FE-05 calls admin API, FE-03 says no admin access).

**Resolution options**:
- Option A (preferred): Backend provides a user-facing endpoint `/api/v1/organizations` (under Data Plane, not Control Plane) with scope filtering for regional_agent. Frontend changes data source in FE-05.
- Option B: Backend adds a read-only exception to `/api/v1/admin/organizations` for `regional_agent` with scope filtering (breaks the clean CP/DP separation).
- Option C: Frontend changes store-dashboard to use a different data source pattern (e.g., dedicated `/api/v1/stores` endpoint).

> **Backend Team Backlog [v4.3]**: This gap has dual ownership -- frontend internal contradiction (FE-05 calls admin API, FE-03 denies admin access to regional_agent) plus backend endpoint gap (no Data Plane org query endpoint exists). Resolution selected: **Option A**. Backend team must provide `GET /api/v1/organizations?scope=regional` or equivalent DP endpoint before store-dashboard feature development (Phase 1). Frontend will update FE-05:170 data source upon backend endpoint confirmation. FE-05:171-178 WARNING block already documents this dependency.

**Status**: **CLOSED** -- Resolved via 05a-API-Contract.md Section 1.6 (GET /api/v1/organizations Data Plane endpoint). Option A selected and implemented.

**Evidence**: `05-page-routes.md` line 170, `05-Gateway层.md` lines 61-62, `03-auth-permission.md` line 237

**Affected FE Docs**: FE-05 Section 3.5, FE-03 Section 4.3

---

### H-12. effective-settings API Required for Phase 0 Admin Console [NEW in v4]

**Frontend (FE-06 Section 4.11, FE-00 B1)**:
```
effective-settings read-only panel: shows current org's final effective config
(after merging inheritance chain). Requires backend GET /api/v1/admin/effective-settings API.
```

**Backend**: No such endpoint defined. 06-Infrastructure defines config inheritance semantics (LAW/RULE/BRIDGE) but no API to retrieve the merged result.

**Analysis**: This was a **Phase 0 blocker** for Admin Console. FE-00 Section 10 explicitly lists this as B1 (Phase 0 priority). 已通过 05a Section 2.3 闭环。

**Impact**: Admin Console Phase 0 scope includes config management (FE-06:190-194). The "source annotation" feature (showing "Inherited from [parent org]" vs "This level setting") is entirely dependent on this API.

**Resolution**: Backend must implement `GET /api/v1/admin/effective-settings` that returns the merged config after inheritance chain resolution, annotated with per-item source (LAW/RULE/BRIDGE level).

**Status**: **CLOSED** -- Resolved via 05a-API-Contract.md Section 2.3. Complete response schema defined with value/source/source_org_id/source_org_name/constraint/is_locked/admin_ui per settings key. [裁决]

**Evidence**: `06-admin-console.md` line 194, `00-architecture-overview.md` line 258 (B1)

**Affected FE Docs**: FE-06 Section 4.11

---

### H-13. Three-Step Upload Protocol Endpoint Path Mismatch [NEW in v4.2]

**Backend (05-Gateway lines 330-416)**: Defines complete three-step media upload protocol (ADR-045):
```
Step 1: POST /api/v1/media/upload/init
  Request: { media_type, size, mime_type, checksum_sha256 }
  Response: { media_id, presigned_url, upload_token }

Step 2: Client direct upload to presigned_url (S3/OSS)

Step 3: POST /api/v1/media/upload/complete
  Request: { media_id, confirmation_token }
  Response: { media_id, security_status, scan_result }

Additional endpoints:
  GET    /api/v1/media/{media_id}/url -> presigned download URL (5min TTL)
  DELETE /api/v1/media/{media_id}     -> trigger deletion pipeline

Enterprise domain (Admin):
  POST   /api/v1/admin/knowledge/media/upload/init
  POST   /api/v1/admin/knowledge/media/upload/complete
  GET    /api/v1/admin/knowledge/media/{media_id}/url
  DELETE /api/v1/admin/knowledge/media/{media_id}
```

**Frontend (FE-04 multimodal design, inferred)**: Assumes different endpoint paths:
```
Step 1: POST /api/v1/upload/presigned-url
Step 3: POST /api/v1/upload/confirm
```

**Analysis**: Endpoint paths are completely different:
- Backend uses `/media/upload/init` and `/media/upload/complete` (media-centric naming)
- Frontend assumes `/upload/presigned-url` and `/upload/confirm` (generic naming)
- Backend separates personal domain (`/api/v1/media/*`) from enterprise domain (`/api/v1/admin/knowledge/media/*`); frontend does not distinguish

**Impact**: **Phase 1 blocker (multimodal feature)**. Frontend HTTP requests to assumed paths will return 404. The entire upload flow depends on correct endpoint paths.

**Resolution**: Frontend adopts backend's exact endpoint paths. Update `packages/api-client/media.ts` (or equivalent) to use:
- Personal: `/api/v1/media/upload/init`, `/complete`, `/{media_id}/url`, `/{media_id}` (DELETE)
- Enterprise: `/api/v1/admin/knowledge/media/upload/init`, `/complete`, `/{media_id}/url`, `/{media_id}` (DELETE)

**Status**: **CLOSED** -- Resolved via 05a-API-Contract.md Section 1.4 (personal media) and Section 2.4 (enterprise media). Paths exactly aligned with 05-Gateway:356-359.

**Evidence**: `05-Gateway层.md` lines 330-416

**Affected FE Docs**: FE-02 Section 3 (REST client), FE-04 Section 7 (multimodal), FE-05 Section 2 (file upload), FE-06 Section 4.4 (knowledge media)

---

### H-14. security_status 6-State Machine Frontend Has No Handling [NEW in v4.2]

**Backend (05-Gateway:421-427, 06-Infrastructure:902-903, 08-Appendix ADR-051)**:
Defines 6-state security status machine with three-layer interception:
```
States: pending | scanning | safe | rejected | quarantined | expired

Three-layer interception (LAW, cannot bypass):
  Layer 1 (Gateway): GET /media/{id}/url
    safe -> presigned download URL (5min TTL)
    pending | scanning -> 403 "media_processing"
    rejected -> 404 (treat as non-existent)
    quarantined -> 403 "media_quarantined"
    expired -> 404

  Layer 2 (Brain): Writing conversation_events
    Non-safe media_id -> reject entire message

  Layer 3 (LLMCallPort): Building LLM payload
    Non-safe media_id -> replace with text_fallback
    Record: degraded_reason="media_security_blocked"
```

**Frontend**: Zero references to `security_status` across all frontend documents (FE-00 through FE-08). No handling for:
- 403 `media_processing` response (media still being scanned)
- 403 `media_quarantined` response (NSFW/PII detected)
- 404 for rejected/expired media
- Upload completion callback where `security_status` may not be `safe`
- Transition display (pending -> scanning -> safe progression)

**Impact**: **Phase 1 blocker (multimodal feature)**. Users will see raw HTTP error codes instead of meaningful status indicators when media is being processed, rejected, or quarantined. Uploaded media in `pending`/`scanning` state will appear broken until safe. No degradation to `text_fallback` on frontend side.

**Resolution**: Frontend must implement security_status-aware media rendering:
1. Upload flow: After `/upload/complete`, check `security_status` in response. If not `safe`, show processing indicator.
2. Media display: When fetching `/media/{id}/url`, handle 403/404 responses with user-friendly messages:
   - `media_processing`: "Media is being verified, please wait..."
   - `media_quarantined`: "Media flagged for review" + text_fallback display
   - 404 (rejected/expired): Show text_fallback only
3. Real-time update: Subscribe to `media_event` SSE (see M-26) for status transitions
4. Degradation: Always render `text_fallback` when media cannot be displayed

**Status**: **CLOSED** -- 05a-API-Contract.md Section 1.4/5.2 定义 + FE-02 Section 3.2、FE-04 Section 7.8 已补齐前端处理逻辑。

**Evidence**: `05-Gateway层.md` lines 421-427, `06-基础设施层.md` lines 902-903, `08-附录.md` ADR-051

**Affected FE Docs**: FE-04 Section 7 (multimodal rendering), FE-02 Section 3 (REST error handling), FE-05 Section 2 (upload UX)

---

## Medium Gaps

### M-1. degraded_reason Enum Name Mismatch

**Backend (01-Brain)**: Uses these string values inline (NOT a formal enum definition):
- `"knowledge_stores_unavailable"` (line 558)
- `"pgvector_unavailable"` (line 811)
- `"query_rewrite_failed"` (line 868)
- `"knowledge_timeout"` (line 1093)
- `"budget_allocator_fallback"` (line 1055)

Database schema (06-Infrastructure line 713): `degraded_reason: TEXT` (free-form, nullable).

**Frontend (FE-04 Section 7.2)**: Previously used `"knowledge_unavailable"`, missing 3 backend values.

**Note on formality**: Backend does NOT define `degraded_reason` as a formal enum. Values appear as de-facto string literals in scenario descriptions throughout 01-Brain. Frontend alignment is based on these de-facto values. If backend formalizes the enum later, a re-alignment pass will be needed.

**Status**: **RESOLVED** -- FE-04 Section 7.2 rewritten with all 6 de-facto values (5 backend + 1 frontend-originated `llm_fallback`), source line references, and forward-compatible unknown value handling. Inline note added about informal source.

**Affected FE Docs**: FE-04 Section 7.2

---

### M-2. injection_receipt decision_reason Enum and Extension Fields

**Backend (01-Brain, 06-Infrastructure lines 722-733)**: injection_receipt v3.1 includes 5-tuple + extension fields.

**Frontend (FE-04 Section 7.1)**: Shows 5-tuple names and `utilized marker` but NOT `decision_reason` enum values, `utilization_signal`, or `user_feedback_signal`.

**Resolution**: Add missing fields to FE-04 Section 7.1.

**Status**: **CLOSED** -- Resolved via 01-Brain.md injection_receipt @api-exposed/@api-internal field annotations.

**Affected FE Docs**: FE-04 Section 7.1

---

### M-3. SkillResult Internal Structure Undefined (Backend Gap)

**Backend (03-Skill line 51)**: `execute(...) -> SkillResult` -- no field expansion.

**Status**: Backend specification gap. Frontend cannot align to undefined contract.

**Status**: **CLOSED** -- Resolved via 03-Skill層.md SkillResult Schema v1 definition with rate_limited semantics.

**Affected FE Docs**: FE-04 Section 4 (pending backend spec)

---

### M-4. Cross-Org Submission Pipeline API Contracts Missing [expanded in v4]

**Backend (02-Knowledge Section 7)**: 5-stage knowledge promotion pipeline. No formal ProposalStatus/SyncStatus enums. No API endpoints for submission/review workflow.

**Frontend**: Three submission pipelines all require cross-org-tier workflow APIs (subordinate submits -> superior reviews):

1. **Knowledge submission** (FE-05:154, FE-06:36):
   - `knowledge-edit/submitted/` status tracking: pending / approved / rejected
   - Admin `import-review/` queue on brand_hq side
   - API needed: submission CRUD + status query + review actions

2. **Conversation history upload** (FE-05:144-146) [added in v4]:
   - `history/upload/` packages selected conversations for brand_hq knowledge pipeline
   - Status tracking: submitted / under review / approved / rejected
   - API needed: multipart upload + approval status tracking

3. **Training content submission** (FE-06:222-226) [added in v4]:
   - Regional generates training materials -> submit -> HQ review and publish
   - API needed: template CRUD + submission + review status + export

**Analysis**: All three pipelines share a common pattern: subordinate org submits content to superior org for review. Backend defines the knowledge promotion pipeline internally (02-Knowledge) but provides no consumer-facing API for any of these workflows.

**Resolution**: Backend should define a unified submission/review API pattern covering all three content types (knowledge, history, training). Or at minimum, define per-type endpoints.

**Status**: **CLOSED (Phase 2 reserved)** -- Reserved declaration via 05a-API-Contract.md Section 2.7 (Content Review Pipeline).

**Affected FE Docs**: FE-05 Section 3.3 (history upload), FE-05 Section 3.4 (knowledge-edit), FE-06 Section 4.4, FE-06 Section 4.16 (training)

---

### M-5. Entity Type Registry Not Referenced in Frontend

**Backend (02-Knowledge Section 4)**: 23 entity types.

**Frontend (FE-04 Section 4)**: Component Registry routes by `tool` name, not entity type.

**Status**: **CLOSED** -- Resolved via 05-Gateway層.md entity_type_registry reference to 02-Knowledge層.

**Affected FE Docs**: FE-04 Section 4

---

### M-7. Event Contract Types Not Mapped to SSE

**Backend (08-Appendix G.3)**: 9 event types.

**Frontend (FE-02 Section 2)**: 4 SSE event types.

**Note**: This is a mapping gap (event names). The more fundamental issue of backend not defining SSE event schema is captured in H-9.

**Status**: **CLOSED** -- Resolved via 08-附録.md G.3 SSE Transport Mapping and 05a-API-Contract.md Section 5.3.

**Affected FE Docs**: FE-02 Section 2

---

### M-8. Settings Keys Incomplete

**Backend (06-Infrastructure)**: `temperature_override`, `feature_flags.experiment_participation` not in frontend.

**Status**: **CLOSED** -- Resolved via 06-基础設施層.md Settings frontend exposure index and 05a-API-Contract.md Section 2.3.

**Affected FE Docs**: FE-03 Section 5

---

### M-9. Organization Status Enum Mismatch

**Backend**: `active | suspended | archived`. **Frontend**: `normal/suspended/overdue`.

**Status**: **CLOSED** -- Resolved via 06-基礎設施層.md org status frontend consumption note and 05a-API-Contract.md Section 2.1.

**Affected FE Docs**: FE-06 Section 5.1

---

### M-10. WS Heartbeat Direction Mismatch [NEW in v3]

**Backend (05-Gateway line 280)**: `心跳: 双向 ping/pong（间隔 30s）` (bidirectional).

**Frontend (FE-02 line 46)**: Now reads `Heartbeat: bidirectional ping/pong (interval 30s)`.

**Status**: **RESOLVED** -- FE-02 Section 1 step 4 updated to bidirectional ping/pong, aligned with backend spec. NOTE block added documenting the change.

**Evidence**: `05-Gateway层.md` line 280, `02-transport-layer.md` line 46 (updated)

---

### M-11. Contract Test Layers Not Defined in Frontend

**Backend (ADR-034, G.4)**: 4-layer contract testing. **Frontend (FE-08)**: Single line.

**Status**: **CLOSED** -- Resolved via 08-附録.md G.4 frontend contract testing participation layer.

**Affected FE Docs**: FE-08 Section 5

---

### M-12. Memory Delete API Path Parameter Mismatch [NEW in v3]

**Backend (05-Gateway line 72)**: `DELETE /api/v1/me/memories` (no path parameter).

**Frontend (FE-04 line 346)**: `DELETE /api/v1/me/memories/{id}` (with `{id}` path parameter).

**Analysis**: Backend appears to support batch deletion (all memories, returns `deletion_receipt` with `item_count`). Frontend expects single-item deletion by ID. This may indicate:
- Backend supports both (batch and single) but only documents batch
- Or there is a genuine API path mismatch

**Resolution**: Clarify with backend: does the endpoint accept `/{id}` for single deletion? If not, frontend must adapt to batch-only API.

**Status**: **CLOSED** -- Resolved via 05a-API-Contract.md Section 1.2. Both DELETE paths (batch and single) defined.

**Evidence**: `05-Gateway层.md` line 72, `04-dialog-engine.md` Section 7.3

**Affected FE Docs**: FE-04 Section 7.3

---

### M-13. Billing Business Model Backend Incomplete [NEW in v3]

**Backend (06-Infrastructure lines 282-288)**: Defines `TokenBillingService` with 3 methods:
- `record_usage(...)` -- token usage tracking
- `check_budget(...)` -- budget check
- `enforce_budget(...)` -- budget enforcement

Database schema includes `llm_usage_records` and `usage_budgets`.

**Frontend (FE-04 Section 9)**: Designs complete billing UX:
- Subscription model (299 CNY/month)
- Included quota (100 CNY token)
- Overage purchase (minimum 100 CNY)
- Points system (3:1 commercial markup)
- Recharge flow

**Analysis**: Backend has token billing infrastructure but no subscription/payment/recharge contract. Frontend's billing UX is self-designed based on business requirements, not backend API.

**Resolution**: Backend should define billing API endpoints (subscription, payment, recharge). Until then, frontend billing UX is business-requirement-driven, pending API integration.

**Status**: **PHASE 2 RESERVED** -- Reserved declaration via 05a-API-Contract.md Section 2.8 (Billing).

**Evidence**: `06-基础设施层.md` lines 282-288, `04-dialog-engine.md` Section 9

**Affected FE Docs**: FE-04 Section 9, FE-06 Section 4.6

---

### M-14. suggested_actions WS Extension Field Not in Backend [NEW in v3]

**Backend (05-Gateway Section 7.1)**: No `suggested_actions` field defined in WS protocol.

**Frontend (FE-04 lines 390-412)**: Designs Context-Aware Suggestion Chips dependent on `suggested_actions: SuggestedAction[]` WS downlink field. Frontend **self-documents this gap** at line 408-410:
> "Current 05-Gateway 7.1 does not define this field, needs backend iteration"

**Analysis**: Frontend correctly identified and documented this as a forward-looking requirement. No immediate action needed beyond tracking.

**Resolution**: Backend iteration required. Frontend already has degradation strategy (fall back to static suggestions).

> **Classification Note [v4.3]**: M-14 is a "frontend feature request" (D-class), not a "backend design omission" (A-class). Frontend proactively designed this feature and explicitly documented the backend dependency. No immediate action required; tracked for future backend iteration.

**Disposition**: **DEFERRED (P3)** -- suggested_actions WS extension field deferred to Phase 3.

**Status**: **DEFERRED (P3)** -- Frontend feature request (D-class). Frontend has degradation strategy. Deferred to Phase 3 backend iteration.

**Evidence**: `04-dialog-engine.md` lines 400-410

**Affected FE Docs**: FE-04 Section 7.6 (already self-documented)

---

### M-15. 5xx Retry Strategy Not Covered by Frontend [NEW in v4]

**Backend (05-Gateway lines 250-254)**:
```
5xx 响应:
+-- 可重试，指数退避
+-- 幂等请求（GET/PUT/DELETE）最多 3 次
+-- 非幂等请求（POST）仅在有 Idempotency-Key 时重试
```

**Frontend (FE-02 Section 3.2)**: Only defines 429 retry strategy (exponential backoff, max 3 times). No 5xx retry logic.

**Analysis**: Backend explicitly defines different retry behaviors for idempotent vs non-idempotent requests on 5xx errors, including Idempotency-Key support. Frontend REST client only handles rate limiting (429), not server errors (5xx). This means:
- GET requests that fail with 500 will not be retried (backend expects clients to retry)
- POST requests with Idempotency-Key will not be retried (missed retry opportunity)
- Non-idempotent POST without Idempotency-Key correctly should not be retried (aligned by omission)

**Resolution**: FE-02 Section 3.2 should add 5xx retry logic to `packages/api-client/rest.ts`:
- Idempotent methods (GET/PUT/DELETE): retry up to 3 times with exponential backoff
- Non-idempotent methods (POST): retry only if `Idempotency-Key` header is present
- Exclude 501/505 (not transient)

**Status**: **CLOSED** -- Resolved via 05a-API-Contract.md Section 6.3 retry strategy (aligned with 05-Gateway:268-271).

**Evidence**: `05-Gateway层.md` lines 250-254, `02-transport-layer.md` Section 3.2

**Affected FE Docs**: FE-02 Section 3.2

---

### M-16. WS Heartbeat Timeout Detection Mechanism Inconsistent [NEW in v4]

**Backend (05-Gateway line 295)**:
```
断线检测:
+-- 心跳超时（连续 2 次未收到 pong）
```

**Frontend (FE-02 Section 3.1 lines 176-177)**:
```
client-side idle detection (no PING received for 90s -> treat as connection lost)
```

**Analysis**: Two different timeout detection mechanisms:
- Backend: count-based (2 consecutive missed pongs). With 30s ping interval, disconnection detected at ~60s.
- Frontend: time-based (90s without receiving PING). Disconnection detected at 90s.

This creates a **30-second window** where backend has already declared the connection dead and started cleanup (session state release, resource reclaim) while frontend still believes the connection is alive. During this window, frontend may queue messages that will never be delivered.

**Resolution**: Align detection mechanisms. Recommended: frontend adopts count-based detection matching backend (miss 2 consecutive pings -> treat as disconnected), or explicitly agree on timing: frontend should detect disconnection within 60s (not 90s) to stay ahead of or equal to backend's cleanup window.

**Status**: **CLOSED** -- Resolved via 05a-API-Contract.md Section 4.3 heartbeat parameters. [裁決: 30s interval, 2 missed pongs, ~60s disconnect]

**Evidence**: `05-Gateway层.md` line 295, `02-transport-layer.md` lines 176-177

**Affected FE Docs**: FE-02 Section 3.1

---

### M-17. model_registry CRUD API Undefined (B2) [NEW in v4]

**Frontend (FE-06 Section 5.3, FE-00 B2)**: Global model registry page requires model_registry CRUD API.

**Backend**: 05-Gateway mentions LLM Gateway but defines no model_registry management endpoints.

**Phase**: Phase 2. **Owner**: Backend (LLM Gateway).

**Status**: **PHASE 2 RESERVED** -- Reserved declaration via 05a-API-Contract.md Section 2.5 (Model Registry).

**Affected FE Docs**: FE-06 Section 5.3

---

### M-18. Session List + Lifecycle API Undefined (B4) [NEW in v4]

**Frontend (FE-06 Section 4.14, FE-00 B4)**: Multi-session management requires session list, create, switch, and archive APIs.

**Backend**: 05-Gateway defines WebSocket per-session connection semantics but no session CRUD endpoints.

**Phase**: Phase 2. **Owner**: Backend (Gateway / Session).

**Status**: **CLOSED** -- 05a-API-Contract.md Section 1.1 now defines full lifecycle:
  GET /api/v1/conversations (list, status + cursor),
  POST /api/v1/conversations (create),
  PATCH /api/v1/conversations/{id} (archive/restore + title rename),
  DELETE /api/v1/conversations/{id} (permanent delete).
  Session switch remains frontend behavior (WS reconnect to target conversation_id).

**Affected FE Docs**: FE-06 Section 4.14, FE-05 Section 3.3

---

### M-19. Onboarding Wizard Status API Undefined (B6) [NEW in v4]

**Frontend (FE-06 Section 4.12, FE-00 B6)**: Onboarding wizard requires persisting step completion status (prevents progress loss on mid-exit).

**Backend**: No endpoint defined for onboarding state persistence.

**Phase**: Phase 2. **Owner**: Backend (Infrastructure).

**Status**: **PHASE 2 RESERVED** -- Reserved declaration via 05a-API-Contract.md Section 2.9 (Onboarding).

**Affected FE Docs**: FE-06 Section 4.12

---

### M-20. Knowledge Visibility Filter API Parameter Undefined (B8) [NEW in v4]

**Frontend (FE-06 Section 4.10, FE-00 B8)**: Knowledge visibility partitioning requires filter parameter on knowledge API (visibility: global | brand | region | store).

**Backend (02-Knowledge)**: Knowledge retrieval API does not define visibility filter parameter.

**Phase**: Phase 2. **Owner**: Backend (Knowledge).

**Status**: **CLOSED** -- Resolved via 05a-API-Contract.md Section 2.4 (`GET /api/v1/admin/knowledge/visibility`). Visibility filter parameter defined.

**Affected FE Docs**: FE-06 Section 4.10

---

### M-21. Experiment Engine Frontend API Scope Clarified [NEW in v4]

**Frontend (FE-06 Section 6)**: 经裁决，前端不消费 assignments API，不上报 experiment_assignment_id。

**Backend (06-Infrastructure Section 5)**: Defines Experiment Engine internal mechanism (5-dimension experiments, traffic splitting, auto-stopping) but no consumer-facing API endpoint. The variant is injected internally by Gateway into OrgContext (line 384).

**Analysis (Adjudicated)**: 实验分流（Prompt 调参、模型切换）归后端内部能力。前端仅提供 Admin 管理入口（/api/v1/admin/experiments，Phase 2 reserved），运行时不直接拉取 assignments、不上报 experiment events。

**Phase**: Phase 2. **Owner**: Backend (Infrastructure / Gateway).

**Status**: **CLOSED** -- 需求边界已裁决并落盘到 FE-06 Section 6：前端无需 assignments/event reporting；后端保持 admin/experiments 管理 API（05a Section 2.6, Phase 2 reserved）。

**Evidence**: `06-admin-console.md` lines 290-304, `06-基础设施层.md` Section 5

**Affected FE Docs**: FE-06 Section 6

---

### M-22. Platform-Ops Module Admin API Contracts Missing [NEW in v4.1]

**Frontend (FE-06 Section 5.1~5.7)**: Platform-Ops route group (platform tier only) defines 7 modules, each with explicit backend field and operation dependencies:

| Module | FE-06 Section | Key Backend Dependencies |
|--------|--------------|------------------------|
| tenant-detail | 5.1 | Tenant status CRUD, quota management, exemption CRUD |
| model-pricing | 5.2 | Provider pricing sync API, price reconciliation |
| subscription-plans | 5.3 | Plan CRUD, version publishing, effective time control |
| billing-global | 5.4 | Platform revenue reporting, overdue policy config |
| security-config | 5.5 | Global forbidden_words CRUD, login policy versioned publishing |
| system-ops | 5.6 | Gateway/Brain/Memory/Knowledge health API, maintenance mode toggle, announcement publish |
| global-knowledge | 5.7 | Platform template CRUD, version control |

**Backend**: None of these Platform-Ops APIs are defined in backend documentation. 05-Gateway only defines the `/api/v1/admin/*` route partition; specific platform-ops endpoints are unspecified.

**Analysis**: This is the same systemic issue as H-8 (backend defines routing but not endpoints), manifested specifically for the platform-ops tier. Unlike brand Admin Console (which shares endpoint patterns with brand_hq operations), Platform-Ops operations are unique to the `platform` tier and require dedicated API design (tenant management, model registry pricing, system health monitoring).

**Phase**: Phase 2 (Platform-Ops is post-brand-admin). **Owner**: Backend (Gateway / Infrastructure).

**Status**: **PARTIALLY CLOSED** -- 05a-API-Contract.md Section 3 defines complete Schema for:
  tenants CRUD (GET/POST/PATCH with full request/response fields),
  audit-logs (GET with query params + paginated response),
  global-settings (GET/PUT with settings key response).
Remaining Phase 2 reserved (no Schema): model-pricing, subscription-plans, billing-global,
  security-config, system-ops, global-knowledge.

**Evidence**: `06-admin-console.md` lines 241-283

**Affected FE Docs**: FE-06 Section 5

---

### M-23. budget_tool_amount and X-Tool-Budget-Remaining Not Covered [NEW in v4.2]

**Backend (06-Infrastructure:155-157, 05-Gateway:444-445)**: v3.6 introduces independent tool billing (ADR-047):
```
org_settings.budget_tool_amount: Float    // Tool budget (independent of token budget)
model_access.budget_tool_amount: Float    // Same value propagated
Response header: X-Tool-Budget-Remaining  // Tool budget percentage remaining

Pre-check (Gateway): check budget_tool_amount; if exhausted -> 402 Payment Required
Post-settle: tool execution cost deducted from tool budget (tool_usage_records table)
```

**Frontend (FE-03 Section 3.2, FE-02 Section 3.2, FE-04 Section 9)**:
- OrgSettings: includes `budget_tool_amount`
- ModelAccess: includes `budget_tool_amount`
- REST interceptor: parses both `X-Budget-Remaining` and `X-Tool-Budget-Remaining`
- Billing UI: token/tool dual budget indicators

**Analysis**: Backend has dual-dimension budget control (token + tool), but frontend only tracks token dimension. When tool budget is exhausted, users will see a 402 error with no prior warning (no approaching-limit indicator for tool budget).

**Resolution**:
- FE-03: Add `budget_tool_amount` to OrgSettings and ModelAccess interfaces
- FE-02: Add `X-Tool-Budget-Remaining` parsing to rest.ts interceptor
- FE-04: Add tool budget display alongside token budget in billing section
- FE-05: Add tool budget remaining indicator in chat UI (parallel to token budget)

**Status**: **CLOSED** -- Backend contract + frontend absorption both completed (05a Section 7.2/5.2, FE-03/FE-02/FE-04 updates).

**Evidence**: `06-基础设施层.md` lines 155-157, `05-Gateway层.md` lines 444-445

**Affected FE Docs**: FE-02 Section 3.2, FE-03 Section 3.2, FE-04 Section 9, FE-05 Section 3

---

### M-24. media_config RULE Config Items Not in Frontend OrgSettings [NEW in v4.2]

**Backend (06-Infrastructure, ADR-044)**: v3.6 adds media governance config under RULE constraint:
```
org_settings.media_config: {
  allowed_media_types: ["image", "audio", "video", "document"],
  file_size_limit: Integer,          // bytes, per-file limit
  media_quota: Integer,              // bytes, total org quota
  nsfw_sensitivity: Float,           // detection threshold
  quarantine_expire_days: Integer    // auto-delete after quarantine
}
// Governed by Loop E (governance loop)
// is_locked: BRIDGE can lock for child orgs
```

**Frontend (FE-03 Section 3.2/5)**:
- OrgSettings includes `media_config` structure
- settings-constraints includes media_config sub-keys

**Analysis**: Admin Console config management page (FE-06 Section 4.3) cannot display or edit media governance settings. Brand admins have no way to:
- Restrict allowed media types for their organization
- Set file size limits
- Configure NSFW detection sensitivity
- View/manage media quota

**Resolution**: Add `media_config` to `packages/shared/settings-constraints.ts` as RULE items. Add media config section to Admin Console settings page (FE-06 Section 4.3).

**Status**: **CLOSED** -- Backend definition + frontend absorption both completed (06 settings index + FE-03 updates).

**Evidence**: `06-基础设施层.md` media_config definition, `03-auth-permission.md` Section 5

**Affected FE Docs**: FE-03 Section 5, FE-06 Section 4.3

---

### M-25. content_version WS Message-Level Version Field Not Handled [NEW in v4.2]

**Backend (05-Gateway:289-299, ADR-050)**: v3.6 defines three-layer version number separation:
```
WS message payload fields (Layer 2 - message level):
  user_message:        { text, blocks?, content_version?, session_id }
  ai_response_chunk:   { text, blocks?, content_version?, ... }

  content_version = absent -> pure text mode (v0 compatibility)
  content_version = 1     -> ContentBlock Schema v1.1 (blocks field populated)

Constraint (LAW): content JSONB must NOT contain version numbers
  (three-layer separation: DB row-level / WS message-level / event-level)
```

**Frontend (FE-02 Section 1.1)**: WS message type definitions:
```
Uplink: user_message, multimodal_message, ping, session_resume
Downlink: ai_response_chunk, tool_output, task_complete, error
```
No `content_version` field in any message type. No `blocks` field in message payloads.

**Analysis**: Without `content_version`, frontend cannot negotiate multimodal capability with backend. Backend uses this field to determine whether to send `blocks` in response. Frontend uplink without `content_version` will be treated as pure-text client, and backend response will omit `blocks` even if multimodal content is available.

**Resolution**:
- FE-02 Section 1.1: Add `content_version?: number` and `blocks?: ContentBlock[]` to user_message and ai_response_chunk type definitions
- Frontend multimodal-capable clients should send `content_version: 1` in uplink messages
- Frontend parser should handle presence/absence of `blocks` field gracefully

**Status**: **CLOSED** -- Resolved via 05a-API-Contract.md Section 4.2 (content_version in ai_response_chunk, ADR-050 semantics).

**Evidence**: `05-Gateway层.md` lines 289-299, ADR-050 in `08-附录.md`

**Affected FE Docs**: FE-02 Section 1.1, FE-04 Section 1

---

### M-26. media_event 7 Subtypes Not Mapped to Frontend SSE [NEW in v4.2]

**Backend (06-Infrastructure:558/562-577, 08-Appendix)**: v3.6 defines media_event with 7 subtypes:
```
media_event subtypes:
  upload_initiated       -- Step 1 complete, presigned URL issued
  upload_completed       -- Step 3 passed all checks, security_status=safe
  upload_expired         -- Timeout recovery: pending > 1 hour
  scan_completed         -- Async deep scan finished (NSFW/PII/copyright)
  rejected               -- Security scan failed, media deleted
  deletion_requested     -- User or admin initiated deletion
  deletion_completed     -- Deletion pipeline finished all steps

Common fields:
  { media_id, media_domain: "personal" | "enterprise", media_type, action_detail, ... }
```

**Frontend (FE-02 Section 2)**: SSE event types:
```
task_status_update, system_notification, budget_warning, knowledge_update
```
No `media_event` or any media-related SSE event.

**Analysis**: Frontend cannot receive real-time media processing status updates. Upload progress will appear frozen between Step 3 (`/upload/complete`) response and actual safe confirmation. Async scan results (NSFW detection completing after initial safe status) will not be reflected in UI.

**Resolution**:
- FE-02 Section 2: Add `media_event` to SSE event type list
- Frontend media upload component: Subscribe to `media_event` for status transitions
- Admin Console: Display media audit events in monitoring dashboard

**Phase**: Phase 2 (media upload in Phase 1 can use polling fallback; SSE subscription is Phase 2 enhancement)

**Status**: **CLOSED** -- Resolved via 05a-API-Contract.md Section 5.2 (media_event with 7 subtypes).

**Evidence**: `06-基础设施层.md` lines 558-577, `08-附录.md` media_event definition

**Affected FE Docs**: FE-02 Section 2, FE-04 Section 7, FE-06 Section 5.6

---

## Low Gaps

### L-1. budget_monthly_tokens Legacy Handling

Frontend handles with backward compatibility (read-only + legacy marking). No action needed.

**Status**: **NO-ACTION** -- Frontend already handles legacy field with backward compatibility.

---

### L-2. SLA Configuration Source Not Specified

FE-04 Section 7.3 shows deletion SLA but doesn't specify data source. Should read from org-level configuration.

**Status**: **NO-ACTION** -- Informational. SLA source will be org_settings when implemented.

---

### L-3. Memory Quality SLI Not Surfaced

Backend defines **7** SLI metrics (ADR-038, amending ADR-036's original 5). The 7 SLIs are: `staleness_rate, conflict_rate, injection_quality, retrieval_latency_p95, context_overflow_rate, deletion_timeout_rate, receipt_completeness_rate` (01-Brain lines 335-389). No frontend display.

**Note**: v2 incorrectly cited "5 SLI (ADR-036)". ADR-038 expands to 7.

**Evidence**: `08-附录.md` line 89 (ADR-038), `01-对话Agent层-Brain.md` lines 333-389

**Status**: **NO-ACTION** -- SLI metrics are backend-internal monitoring. Frontend surfacing is optional enhancement.

**Affected FE Docs**: FE-06 Section 5.6

---

### L-4. Content Policy Enum Workflow Impact Not Documented

Backend `content_policy: relaxed | standard | strict` affects review workflow. Frontend mentions as config item but no UI impact spec.

**Status**: **NO-ACTION** -- Informational. UI impact spec will be defined when content review UI is built (Phase 2).

---

### L-5. Privacy Hard Boundary ADR-018 Reference Missing

Frontend constraint #3 should reference ADR-018 for traceability.

**Status**: **NO-ACTION** -- Traceability note. ADR-018 reference is documentation improvement, not functional gap.

---

### L-6. KnowledgeBundle Schema Not Needed in Frontend [downgraded from M-6 in v2]

KnowledgeBundle is a backend internal structure (Brain -> Skill transfer). Frontend consumes Skill output via Gateway's `tool_output`, not raw KnowledgeBundle. Frontend does not need this type.

**Rationale for downgrade**: Frontend is an external consumer; internal backend data transfer contracts should not leak to frontend API surface.

**Status**: **NO-ACTION** -- Backend internal structure, not applicable to frontend API surface.

---

### L-7. Experiment Dimension Names Use Display Labels [downgraded from M-10 in v2]

Backend: `brain_routing, skill_execution, knowledge_retrieval, prompt_version, model_selection`

Frontend (FE-06): `Skill / Brain / Knowledge / Prompt / Model` -- these are human-readable display labels, not code enums. Phase 2 implementation will naturally align when building the experiment management UI.

**Status**: **NO-ACTION** -- Display labels vs code enums; will naturally align in Phase 2 experiment UI.

---

### L-8. org_settings.branding Extension Backend Dependency (B5) [NEW in v4.1]

**Frontend (FE-01 line 370, FE-00 B5)**: Phase 3 roadmap item "Brand theme customization (needs backend org_settings.branding extension)".

**Backend**: `org_settings` in 06-Infrastructure defines LAW/RULE/BRIDGE config types but no `branding` field.

**Analysis**: Phase 3 dependency. Frontend has explicit requirement; backend has no corresponding field definition. Low severity because Phase 3 is distant and the requirement is simple (add RULE config items: theme color/logo/font).

**Phase**: Phase 3. **Owner**: Backend (Infrastructure).

**Status**: **CLOSED** -- Resolved via 06-基础设施层.md branding Phase 2 reserved declaration and 05a-API-Contract.md Section 2.10 (Branding reserved endpoints).

**Evidence**: `01-monorepo-infrastructure.md` line 370, `00-architecture-overview.md` line 262 (B5)

---

### L-9. Inventory Association System External Dependency [NEW in v4.1]

**Frontend (FE-06 Section 4.17)**: Inventory association capability for store-level chat and coordination. Explicitly conditional: "enabled when inventory system exists".

**Backend**: No inventory system defined in backend architecture documents. This is an **external system integration**, not a core backend API dependency.

**Analysis**: FE-06:237 already defines complete degradation strategy ("no inventory integration -> hide inventory labels, retain general coordination recommendations"). This is a well-handled conditional dependency. Low severity because it's optional and fully degradable.

**Phase**: Phase 2+. **Owner**: External integration.

**Disposition**: **EXTERNAL DEPENDENCY** -- Not a backend documentation gap. External system integration, fully degradable.

**Status**: **EXTERNAL DEPENDENCY** -- Not a backend gap. Inventory is external system; frontend has complete degradation strategy.

**Evidence**: `06-admin-console.md` lines 233-237

---

### L-10. media_refs in KnowledgeBundle Not Consumed by Frontend [NEW in v4.2]

**Backend (02-Knowledge:212-225)**: v3.6 adds `media_contents` to KnowledgeBundle (Expand-compatible):
```
KnowledgeBundle {
  entities: Map<string, Entity[]>,
  relationships: Relationship[],
  semantic_contents: Content[],
  media_contents?: MediaRef[],       // v3.6 NEW (Expand)
  ...
}

MediaRef {
  media_id: UUID,                    // External unified ID (LAW)
  text_fallback: string,             // Pure text fallback
  associated_entity_id: string,      // graph_node_id
  content_type: string               // "product_image" | "brand_guideline" etc.
}
```

**Frontend (FE-04 Section 4)**: Component Registry routes by `tool` name to render Skill output. Knowledge-related components (`KnowledgeTemplateForm`) consume `semantic_contents` but do not reference `media_contents` or `MediaRef`.

**Analysis**: When knowledge retrieval returns multimedia assets (product images, brand guidelines), frontend will ignore them. Degradation is graceful: `text_fallback` is always available and the knowledge text content renders normally. Media enrichment is lost but core functionality preserved.

**Phase**: Phase 2 (knowledge multimedia is enhancement, not critical path)

**Resolution**: When implementing knowledge multimedia display:
- Component Registry: Add media renderer for `MediaRef` items
- Knowledge display components: Render `media_contents` alongside `semantic_contents`
- Use `text_fallback` as alt text / loading placeholder

**Evidence**: `02-Knowledge层.md` lines 212-225

**Status**: **NO-ACTION** -- Phase 2 enhancement. Graceful degradation via text_fallback. No functional loss.

**Affected FE Docs**: FE-04 Section 4, FE-06 Section 4.4

---

## Resolution Priority Matrix

### Prerequisite: Backend API Contract Publication -- ALL RESOLVED (v4.4)

| Gap | Action | Owner | Status (v4.4) |
|-----|--------|-------|---------------|
| **S-1** | org_tier unified via ADR-049 | **Backend Architecture** | **DOCUMENTED** |
| **C-1** | WS auth via first JSON message | **Backend + Frontend** | **CLOSED** (backend-side) |
| **C-2** | WS message schema published | **Backend Gateway** | **CLOSED** (05a Section 4) |
| **C-3** | SSE auth via BFF | **Frontend** | **RESOLVED v4.3** |
| **H-8** | REST API catalog published | **Backend Gateway** | **CLOSED** (05a Sections 1-3) |
| **H-9** | SSE event schema defined | **Backend Gateway** | **CLOSED** (05a Section 5) |
| **H-10** | DEPLOY_MODE formalized | **Backend + Frontend** | **CLOSED** (07 Section 1.1) |
| **H-12** | effective-settings API defined | **Backend** | **CLOSED** (05a Section 2.3) |

> **Systemic root cause RESOLVED**: Backend Gateway documentation gap (the common root cause of C-1, C-2, H-8, H-9, H-12) has been resolved via 05a-API-Contract.md. All consumer-facing API contracts (REST endpoints, WS message schema, SSE event types) are now formally defined.

### Phase 0 -- ALL RESOLVED

| Gap | Action | Owner | Status |
|-----|--------|-------|--------|
| **H-1a** | Adopt backend's 11 permission codes exactly | Frontend | RESOLVED (FE-03 Section 1.1) |
| **C-2 (v2)** | Extend OrgContext type with all Schema v1 fields | Frontend | RESOLVED (FE-03 Section 3.2) |
| **H-1** | Add max 10 reconnect attempts to FE-02 | Frontend | RESOLVED (FE-02 Section 1) |
| **H-3** | Add timeout values (60s chat, 30s admin) to FE-02 | Frontend | RESOLVED (FE-02 Section 3.1) |
| **M-1** | Align degraded_reason enum names | Frontend | RESOLVED (FE-04 Section 7.2) |

### Phase 0 Addendum -- ALL CLOSED (v4.4 API Contract landing)

| Gap | Action | Owner | Status |
|-----|--------|-------|--------|
| **C-1** | WS auth via first JSON message | Backend + Frontend | **CLOSED** (backend-side, 05a Section 4.1) |
| **C-2** | WS message schema published | Backend | **CLOSED** (05a Section 4.2) |
| **C-3** | SSE auth chain (SaaS: BFF proxy) | Frontend | **RESOLVED v4.3** (SSE via BFF) |
| **H-8** | REST API catalog published | Backend | **CLOSED** (05a Sections 1-3) |
| **H-9** | SSE event schema defined | Backend | **CLOSED** (05a Section 5) |
| **H-11** | Data Plane org endpoint | Backend + Frontend | **CLOSED** (05a Section 1.6) |
| **H-12** | effective-settings API defined | Backend | **CLOSED** (05a Section 2.3) |

### Before Phase 1 Development -- ALL CLOSED (v4.4 backend-side)

| Gap | Action | Owner | Status (v4.4) |
|-----|--------|-------|---------------|
| **C-4** | ContentBlock Schema v1.1 defined | Backend | **CLOSED** (05a Section 1.1, 08-附录 G.2.1) |
| **H-2** | Budget headers defined | Backend | **CLOSED** (05a Section 7.2) |
| **H-7** | SkillResult rate_limited defined | Backend | **CLOSED** (03-Skill SkillResult Schema v1) |
| **H-10** | DEPLOY_MODE formalized | Backend | **CLOSED** (07 Section 1.1) |
| **H-13** | Media upload paths defined | Backend | **CLOSED** (05a Section 1.4) |
| **H-14** | security_status 6-state defined | Backend | **CLOSED** (05a Section 1.4) |
| **M-2** | injection_receipt @api annotated | Backend | **CLOSED** (01-Brain annotations) |
| **M-3** | SkillResult schema formalized | Backend | **CLOSED** (03-Skill Schema v1) |
| **M-7** | Event-to-SSE mapping defined | Backend | **CLOSED** (08-附录 G.3, 05a Section 5.3) |
| **M-12** | Memory delete API clarified | Backend | **CLOSED** (05a Section 1.2) |
| **M-15** | Retry strategy defined | Backend | **CLOSED** (05a Section 6.3) |
| **M-16** | Heartbeat params defined | Backend | **CLOSED** (05a Section 4.3) |
| **M-25** | content_version defined | Backend | **CLOSED** (05a Section 4.2) |

> Note: 采用 Dispositioned 口径后，上述条目均有明确裁决；是否开发完成由 Phase 里程碑单独跟踪。

### Before Phase 2 Development

| Gap | Action | Owner | Status (v4.4) |
|-----|--------|-------|---------------|
| **H-4** | Add epistemic_type to memory panel | Frontend | **CLOSED** (adopted in FE-04 Section 7.3) |
| **H-5** | Add knowledge visibility inheritance UI | Frontend | **CLOSED** (adopted in FE-06 Section 4.10) |
| **H-6** | Expand deletion state machine to 8 states | Frontend | **CLOSED** (adopted in FE-04 Section 7.3) |
| **M-4** | Submission pipeline APIs | Backend | **CLOSED** (Phase 2 reserved, 05a Section 2.7) |
| **M-5** | entity_type_registry reference | Backend | **CLOSED** (05-Gateway reference) |
| **M-8** | Settings keys exposed | Backend | **CLOSED** (06 Settings index) |
| **M-9** | org status frontend note | Backend | **CLOSED** (06 status note) |
| **M-11** | Contract test frontend layer | Backend | **CLOSED** (08-附录 G.4) |
| **M-13** | Billing API | Backend | **PHASE 2 RESERVED** (05a Section 2.8) |
| **M-14** | suggested_actions WS field | Backend | **DEFERRED (P3)** |
| **M-17** | model_registry CRUD API | Backend | **PHASE 2 RESERVED** (05a Section 2.5) |
| **M-18** | Session lifecycle API (list/create/archive/rename/delete) | Backend | **CLOSED** (05a Section 1.1 full lifecycle) |
| **M-19** | Onboarding wizard API | Backend | **PHASE 2 RESERVED** (05a Section 2.9) |
| **M-20** | Knowledge visibility filter API | Backend | **CLOSED** (05a Section 2.4) |
| **M-21** | Experiment engine frontend assignments/event API | Backend | **CLOSED** (adjudicated backend-only runtime; FE-06 Section 6 updated) |
| **M-22** | Platform-Ops APIs | Backend | **PARTIALLY CLOSED** (05a Section 3: tenants/audit-logs/global-settings have full Schema; 4 modules remain Phase 2) |
| **M-23** | budget_tool_amount headers | Backend | **CLOSED** (05a Section 7.2) |
| **M-24** | media_config settings exposed | Backend | **CLOSED** (06 Settings index) |
| **M-26** | media_event SSE defined | Backend | **CLOSED** (05a Section 5.2) |
| **L-10** | media_refs in KnowledgeBundle | Frontend | **NO-ACTION** (graceful degradation) |

### When Convenient

| Gap | Action | Owner | Status (v4.4) |
|-----|--------|-------|---------------|
| **L-1** ~ **L-7** | Documentation alignment | Frontend | **NO-ACTION** (7 items) |
| **L-8** | branding field reserved | Backend | **CLOSED** (06 + 05a Section 2.10) |
| **L-9** | Inventory system integration | External | **EXTERNAL DEPENDENCY** |
| **L-10** | media_refs consumption | Frontend | **NO-ACTION** |

---

## Appendix A: Backend Document to Frontend Document Mapping

| Backend Doc | Primary FE Consumer | Secondary FE Consumers |
|------------|--------------------|-----------------------|
| 00-Overview | FE-00 | FE-08 |
| 01-Brain | FE-04 | FE-05 (memory page) |
| 02-Knowledge | FE-06 (knowledge mgmt) | FE-05 (knowledge-edit), FE-04 (Component Registry) |
| 03-Skill | FE-04 (Component Registry) | FE-06 (skill whitelist) |
| 04-Tool | FE-04 (Task Progress) | FE-06 (tool whitelist) |
| 05-Gateway | FE-02, FE-03 | FE-04, FE-05, FE-06 |
| 05a-API-Contract | FE-02, FE-03, FE-05 | FE-04, FE-06 |
| 06-Infrastructure | FE-03, FE-06 | FE-00, FE-05 |
| 07-Deployment | FE-07 | FE-00 |
| 08-Appendix | FE-00 (ADR registry) | All (contracts, enums, glossary) |

---

## Appendix B: Evidence Verification Summary (v1 -> v2 -> v3)

| Claim | Source | Verification | Action |
|-------|--------|-------------|--------|
| Backend org_tier = 4 values | v1 subagent | **Wrong**. 05-Gateway:97 has 5 values | Fixed v2 S-1 |
| Backend has 12 permission codes | v1 subagent | **Wrong**. 06-Infra:110-120 has 11 | Fixed v2 C-1 |
| OrgContext has `fallback_chain` | v1 subagent | **Wrong**. Not in model_access | Fixed v2 C-2 |
| OrgContext has `legal_profile` | v1 subagent | **Wrong**. Not in Schema v1 | Fixed v2 C-2 |
| SkillResult has compliance_status | v1 subagent | **Wrong**. 03-Skill:51 no expansion | Fixed v2 M-3 |
| Frontend lacks `utilized` | v1 oversight | **Wrong**. FE-04:266 has it | Fixed v2 M-2 |
| ProposalStatus is formal enum | v1 subagent | **Wrong**. Not in backend | Fixed v2 M-4 |
| degraded_reason is formal enum | v2 implicit | **Imprecise**. Informal string literals | Clarified v3 M-1 |
| ADR-036 defines 5 SLI | v2 | **Outdated**. ADR-038 expands to 7 | Fixed v3 L-3 |
| C-1 permissions is Critical | v2 | **Over-rated**. Frontend has strategy | Downgraded v3 H-1a |
| KnowledgeBundle needs frontend type | v2 M-6 | **Over-scoped**. Internal structure | Downgraded v3 L-6 |
| Experiment dimensions is Medium | v2 M-10 | **Over-rated**. Display labels only | Downgraded v3 L-7 |

---

## Appendix C: Systemic Root Cause Analysis [NEW in v3]

The single most impactful finding from review round 2 is **not any individual gap**, but a systemic pattern:

**Backend Gateway (05-Gateway) defines infrastructure but not API contracts.**

Specifically, 05-Gateway thoroughly covers:
- Middleware chain architecture
- Authentication/authorization flow
- OrgContext assembly pipeline
- Rate limiting and budget enforcement mechanics
- WebSocket lifecycle semantics

But does NOT define:
- REST endpoint catalog (paths, parameters, request/response schemas)
- WS message schema (type strings, payload structures)
- SSE event types (names, payloads)
- WS authentication handshake details (URL param vs first-message)

This means all frontend API consumption (FE-02 through FE-06) is based on **self-proposed endpoints** inferred from feature requirements, not validated against backend contracts.

**Recommendation**: Before Phase 0 integration begins, backend should publish:
1. OpenAPI spec for REST endpoints (at minimum: auth, session CRUD, memory, billing, search, admin CRUD)
2. AsyncAPI or equivalent for WS message schema
3. SSE event type catalog
4. WS authentication handshake specification

---

## Appendix D: Verified Alignment Items [NEW in v4]

The following contract points have been verified as **consistent** between frontend and backend documents. No gap exists; recorded here for completeness and coverage proof.

| # | Contract Point | Frontend Source | Backend Source | Status |
|---|---------------|----------------|----------------|--------|
| VA-1 | WS Close Codes (4001/4002/4003/1000) | FE-02 Section 1.4 | 05-Gateway:282-286 | Aligned |
| VA-2 | 402 Payment Required trigger and handling | FE-04 Section 9 | 05-Gateway:229 | Aligned |
| VA-3 | Rate-limit response headers (X-RateLimit-*) | FE-02 Section 3.2 | 05-Gateway:233-234 | Aligned |
| VA-4 | WS heartbeat interval (30s) | FE-02 Section 1 step 4 | 05-Gateway:280 | Aligned |
| VA-5 | WS reconnect backoff strategy | FE-02 Section 1 step 5 | 05-Gateway:301 | Aligned |
| VA-6 | RBAC 11 permission codes | FE-03 Section 1.1 | 06-Infrastructure:108-120 | Aligned (RESOLVED H-1a) |
| VA-7 | OrgContext Schema v1 (10 fields) | FE-03 Section 3.2 | 05-Gateway:92-117 | Aligned (RESOLVED C-2 v2) |
| VA-8 | SSE auth chain (SaaS: BFF proxy, Private: direct) | FE-01 Section 6, FE-02 Section 2, FE-03 Section 2.1 | N/A (frontend internal consistency) | Aligned (RESOLVED C-3 v4.3) |

---

## Appendix E: Frontend-Backend Dependency Traceability Matrix [NEW in v4]

This matrix maps every identified frontend-to-backend dependency to a Gap ID, ensuring no dependency is untracked. Dependencies are organized by frontend document.
Status 列采用 v4.6 Dispositioned 规则：`DISPOSITIONED` 表示该依赖已在对应 Gap ID 获得明确裁决（不等价于功能已开发完成）。

### FE-02 (Transport Layer) Dependencies

| # | Dependency | Gap ID | Phase | Status |
|---|-----------|--------|-------|--------|
| 1 | WS auth method (URL param vs first message) | C-1 | P0 | DISPOSITIONED |
| 2 | WS message type strings + payload schema | C-2 | P0 | DISPOSITIONED |
| 3 | WS close codes (4001/4002/4003/1000) | VA-1 | -- | Aligned |
| 4 | WS heartbeat interval (30s) | VA-4 | -- | Aligned |
| 5 | WS heartbeat timeout detection (count vs time) | M-16 | P1 | DISPOSITIONED |
| 6 | WS reconnect strategy (backoff + max 10) | VA-5 + H-1 | -- | RESOLVED |
| 7 | SSE event types + payload schema | H-9 | P0 | DISPOSITIONED |
| 8 | REST rate-limit headers (X-RateLimit-*) | VA-3 | -- | Aligned |
| 9 | REST 429 retry strategy | -- | -- | Defined in FE-02 |
| 10 | REST 5xx retry strategy (idempotent distinction) | M-15 | P1 | DISPOSITIONED |
| 11 | REST timeout values (60s/30s) | H-3 | P0 | RESOLVED |
| 12 | REST X-Budget-Remaining header | H-2 | P1 | DISPOSITIONED |
| 13 | SSE authentication method (token query vs Cookie) | C-3 | P0 | RESOLVED v4.3 |
| 14 | ContentBlock Schema v1.1 in WS messages [v4.2] | C-4 | P1 | DISPOSITIONED |
| 15 | content_version field in WS messages [v4.2] | M-25 | P1 | DISPOSITIONED |
| 16 | Three-step upload protocol endpoints [v4.2] | H-13 | P1 | DISPOSITIONED |
| 17 | security_status 6-state error handling [v4.2] | H-14 | P1 | DISPOSITIONED |
| 18 | X-Tool-Budget-Remaining header [v4.2] | M-23 | P2 | DISPOSITIONED |
| 19 | media_event SSE subscription [v4.2] | M-26 | P2 | DISPOSITIONED |

### FE-03 (Auth & Permission) Dependencies

| # | Dependency | Gap ID | Phase | Status |
|---|-----------|--------|-------|--------|
| 1 | 11 RBAC permission codes | VA-6 (H-1a) | P0 | RESOLVED |
| 2 | OrgContext Schema v1 (10 fields) | VA-7 (C-2 v2) | P0 | RESOLVED |
| 3 | org_tier enum naming (SSOT conflict) | S-1 | P0 | DOCUMENTED |
| 4 | Private mode WS token endpoint (optional) | Note | -- | Documented in FE-03:135 |
| 5 | DEPLOY_MODE enum | H-10 | P1 | DISPOSITIONED |
| 6 | SSE token acquisition (no getSseToken in AuthStrategy) | C-3 | P0 | RESOLVED v4.3 (BFF proxy) |
| 7 | media_config in OrgSettings [v4.2] | M-24 | P2 | DISPOSITIONED |
| 8 | budget_tool_amount in OrgSettings/ModelAccess [v4.2] | M-23 | P2 | DISPOSITIONED |

### FE-04 (Dialog Engine) Dependencies

| # | Dependency | Gap ID | Phase | Status |
|---|-----------|--------|-------|--------|
| 1 | degraded_reason values | M-1 | P0 | RESOLVED |
| 2 | injection_receipt fields | M-2 | P1 | DISPOSITIONED |
| 3 | SkillResult schema | M-3 | P1 | DISPOSITIONED |
| 4 | Entity type -> Component Registry | M-5 | P2 | DISPOSITIONED |
| 5 | epistemic_type in memory panel | H-4 | P2 | DISPOSITIONED |
| 6 | Deletion state machine (8 states) | H-6 | P2 | DISPOSITIONED |
| 7 | Tool execution status rate_limited | H-7 | P1 | DISPOSITIONED |
| 8 | Memory delete API path (/{id} vs batch) | M-12 | P1 | DISPOSITIONED |
| 9 | suggested_actions WS field | M-14 | P2 | DISPOSITIONED |
| 10 | 402 Payment Required handling | VA-2 | -- | Aligned |
| 11 | Runtime fallback /api/v1/chat | Note | -- | Internal fallback (FE-04:73) |
| 12 | ContentBlock Schema v1.1 adoption [v4.2] | C-4 | P1 | DISPOSITIONED |
| 13 | security_status media rendering [v4.2] | H-14 | P1 | DISPOSITIONED |
| 14 | media_refs in KnowledgeBundle [v4.2] | L-10 | P2 | DISPOSITIONED |
| 15 | Tool budget display (budget_tool_amount) [v4.2] | M-23 | P2 | DISPOSITIONED |

### FE-05 (Page Routes) Dependencies

| # | Dependency | Gap ID | Phase | Status |
|---|-----------|--------|-------|--------|
| 1 | Memory API (GET/DELETE) | H-8 + M-12 | P0/P1 | DISPOSITIONED |
| 2 | Session CRUD APIs | H-8 + M-18 | P0/P2 | DISPOSITIONED |
| 3 | History upload API (multipart + review) | M-4 | P2 | DISPOSITIONED |
| 4 | Knowledge submission API | M-4 | P2 | DISPOSITIONED |
| 5 | Store dashboard org API | H-11 | P0 | DISPOSITIONED |
| 6 | Search API | H-8 | P0 | DISPOSITIONED |
| 7 | Three-step upload UI flow (personal media) [v4.2] | H-13 | P1 | DISPOSITIONED |
| 8 | security_status upload feedback [v4.2] | H-14 | P1 | DISPOSITIONED |

### FE-06 (Admin Console) Dependencies

| # | Dependency | Gap ID | Phase | Status |
|---|-----------|--------|-------|--------|
| 1 | Admin organizations CRUD | H-8 | P0 | DISPOSITIONED |
| 2 | Admin members CRUD | H-8 | P0 | DISPOSITIONED |
| 3 | Admin settings PUT | H-8 | P0 | DISPOSITIONED |
| 4 | Admin knowledge CRUD | H-8 | P0 | DISPOSITIONED |
| 5 | Admin experiments CRUD | H-8 | P0 | DISPOSITIONED |
| 6 | Admin billing GET | H-8 | P0 | DISPOSITIONED |
| 7 | Admin audit GET | H-8 | P0 | DISPOSITIONED |
| 8 | effective-settings API (B1) | H-12 | P0 | DISPOSITIONED |
| 9 | Model registry CRUD (B2) | M-17 | P2 | DISPOSITIONED |
| 10 | Session lifecycle (list/create/archive/rename/delete) (B4) | M-18 | P2 | DISPOSITIONED |
| 11 | Onboarding wizard status (B6) | M-19 | P2 | DISPOSITIONED |
| 12 | Knowledge visibility filter (B8) | M-20 | P2 | DISPOSITIONED |
| 13 | Experiment assignments API | M-21 | -- | DISPOSITIONED (out-of-scope by adjudication) |
| 14 | Experiment event reporting | M-21 | -- | DISPOSITIONED (out-of-scope by adjudication) |
| 15 | Training submission pipeline | M-4 | P2 | DISPOSITIONED |
| 16 | SSE notifications | H-9 | P0 | DISPOSITIONED |
| 17 | Organization status enum | M-9 | P2 | DISPOSITIONED |
| 18 | Settings keys completeness | M-8 | P2 | DISPOSITIONED |
| 19 | Billing API endpoints | M-13 | P2 | DISPOSITIONED |
| 20 | Knowledge promotion pipeline | M-4 | P2 | DISPOSITIONED |
| 21 | Contract test layers | M-11 | P2 | DISPOSITIONED |
| 22 | Tenant status CRUD + quota management (Section 5.1) | M-22 | P2 | DISPOSITIONED |
| 23 | Model pricing sync API (Section 5.2) | M-22 | P2 | DISPOSITIONED |
| 24 | Subscription plan CRUD + version publishing (Section 5.3) | M-22 | P2 | DISPOSITIONED |
| 25 | Platform billing reporting + overdue policy (Section 5.4) | M-22 | P2 | DISPOSITIONED |
| 26 | Security config versioned publishing (Section 5.5) | M-22 | P2 | DISPOSITIONED |
| 27 | System health monitoring + maintenance toggle (Section 5.6) | M-22 | P2 | DISPOSITIONED |
| 28 | Global knowledge template CRUD (Section 5.7) | M-22 | P2 | DISPOSITIONED |
| 29 | Inventory association system (Section 4.17, conditional) | L-9 | P2+ | DISPOSITIONED (degradable) |
| 30 | Enterprise media upload API (Section 4.4) [v4.2] | H-13 | P1 | DISPOSITIONED |
| 31 | media_config RULE settings (Section 4.3) [v4.2] | M-24 | P2 | DISPOSITIONED |
| 32 | media_refs in knowledge display (Section 4.4) [v4.2] | L-10 | P2 | DISPOSITIONED |
| 33 | Tool budget display in billing (Section 4.6) [v4.2] | M-23 | P2 | DISPOSITIONED |

### FE-07 (Deployment) Dependencies

| # | Dependency | Gap ID | Phase | Status |
|---|-----------|--------|-------|--------|
| 1 | DEPLOY_MODE enum | H-10 | P1 | DISPOSITIONED |

### FE-00 (Architecture) B-Series Backend Requirements

| B# | Requirement | Gap ID | Phase | Status |
|----|-----------|--------|-------|--------|
| B1 | effective-settings API | H-12 | P0 | DISPOSITIONED |
| B2 | model_registry CRUD | M-17 | P2 | DISPOSITIONED |
| B3 | SSE event type extensions | H-9 | P0 | DISPOSITIONED |
| B4 | Session lifecycle API | M-18 | P2 | DISPOSITIONED |
| B5 | org_settings.branding extension | L-8 | P3 | DISPOSITIONED |
| B6 | Onboarding wizard status API | M-19 | P2 | DISPOSITIONED |
| B7 | RBAC permission code naming | H-1a | P0 | RESOLVED |
| B8 | Knowledge visibility filter | M-20 | P2 | DISPOSITIONED |

### Coverage Summary

| Dimension | Count | Tracked By | Coverage |
|-----------|-------|-----------|----------|
| Gap items (S/C/H/M/L) | 55 | S-1, C-1~C-4, H-1~H-14, M-1~M-26, L-1~L-10 | 100% |
| B-series backend requirements (FE-00 Section 10) | 8 | B1=H-12, B2=M-17, B3=H-9, B4=M-18, B5=L-8, B6=M-19, B7=H-1a, B8=M-20 | 100% |
| Verified alignment items | 8 | VA-1~VA-8 (Appendix D) | 100% |
| v3.6 multimodal landing verification | 14 | Appendix F | 100% |
| **Total unique dependencies** | -- | Appendix E matrices | **100%** |

> Note: B-series items are cross-referenced to existing Gap IDs (not double-counted). v4.6 adopts the Dispositioned policy: every Gap has an explicit adjudication and Appendix E status is synchronized to that adjudication (no residual OPEN rows).

---

## Appendix F: v3.6 Multimodal Landing Verification [NEW in v4.2]

**Source document**: `docs/reviews/后端多模态完善补全.md` v3.4 Final Merge (7 review rounds)
**Verification date**: 2026-02-11
**Verification method**: Grep + manual line-level verification across all 9 backend architecture docs
**Result**: **ALL 14 ITEMS FULLY LANDED**

| # | Item | ADR | Target Doc | Evidence Location | Status |
|---|------|-----|-----------|-------------------|--------|
| 1 | ContentBlock Schema v1.1 | ADR-043 | 05-Gateway, 01-Brain, 08-Appendix | 05-Gateway:292/296/430, 01-Brain:918-926, 08-Appendix:97 | LANDED |
| 2 | personal_media_objects DDL | ADR-044 | 06-Infrastructure | 06-Infrastructure:891-908 | LANDED |
| 3 | enterprise_media_objects DDL | ADR-044 | 06-Infrastructure | 06-Infrastructure:911-935 | LANDED |
| 4 | tool_usage_records DDL | ADR-047 | 06-Infrastructure | 06-Infrastructure:942-957 | LANDED |
| 5 | ObjectStoragePort interface | ADR-045 | 06-Infrastructure, 08-Appendix | 06-Infrastructure (Port definitions), 08-Appendix | LANDED |
| 6 | content_schema_version field | ADR-050 | 06-Infrastructure, 01-Brain, 05-Gateway | 06-Infrastructure (DDL), 05-Gateway:289-299 | LANDED |
| 7 | ADR-043 through ADR-052 (10 ADRs) | -- | 08-Appendix | 08-Appendix:97-106 | LANDED |
| 8 | security_status 6-state machine | ADR-051 | 06-Infrastructure, 05-Gateway, 08-Appendix | 05-Gateway:421-427, 06-Infrastructure:902-903 | LANDED |
| 9 | Three-step upload protocol | ADR-045 | 05-Gateway | 05-Gateway:330-416 | LANDED |
| 10 | budget_tool_amount field | ADR-047 | 06-Infrastructure, 05-Gateway | 06-Infrastructure:155-157, 05-Gateway:444-445 | LANDED |
| 11 | media_event model (7 subtypes) | -- | 06-Infrastructure, 08-Appendix | 06-Infrastructure:558/562-577 | LANDED |
| 12 | content_version in WS messages | ADR-050 | 05-Gateway | 05-Gateway:289-299 | LANDED |
| 13 | media_refs in Qdrant (KnowledgeBundle) | -- | 02-Knowledge | 02-Knowledge:212-225 | LANDED |
| 14 | Multimodal capabilities in Skill | -- | 03-Skill | 03-Skill:60-69 | LANDED |

**Cross-layer consistency check**: All 14 items maintain proper layered isolation:
- Port interfaces (ObjectStoragePort, LLMCallPort) define abstract contracts only
- DDL additions (personal/enterprise_media_objects, tool_usage_records) are in 06-Infrastructure only
- Protocol specifications (three-step upload, WS content_version) are in 05-Gateway only
- Business logic (security_status interception, media_event) spans appropriate layers with clear ownership

**Conclusion**: `后端多模态完善补全.md` v3.4 Final Merge has been 100% incorporated into the backend architecture document set. No residual unmerged items. The v3.6 backend architecture is multimodal-complete. The remaining work is aligning the **frontend** architecture docs and the **gap report** to reference these v3.6 contracts (addressed by C-4, H-13, H-14, M-23~26, L-10 in this v4.2 update).

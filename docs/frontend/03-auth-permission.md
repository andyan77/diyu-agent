# FE-03 Auth & Permission

> **contract_version**: 1.0.0
> **min_compatible_version**: 1.0.0
> **breaking_change_policy**: Expand-Contract
> **owner**: Frontend Security Lead
> **source_sections**: frontend_design.md Sections 6.1, 6.2
> **depends_on**: FE-01 (package structure), FE-07 (DEPLOY_MODE)

---

## Scope Boundary

FE-03 owns:
- AuthStrategy interface and implementations (Owned Contract)
- OrgContext type definition (Owned Contract)
- TierGate access rules (Owned Contract)
- RBAC permission utilities
- Settings constraints enum (LAW/RULE/BRIDGE)

---

## 1. Org Hierarchy & RBAC

Backend definitions:
- Org tree: `platform > brand_hq > brand_dept/regional_agent > franchise_store`
- RBAC: `owner / admin / editor / reviewer / viewer`
- Config inheritance: `LAW / RULE / BRIDGE(is_locked)`

### 1.1 RBAC Permission Codes (Aligned with 06-Infrastructure Section 1.3)

Backend defines exactly **11** permission codes. Frontend MUST use these exact keys in PermissionGate checks:

| Permission Key | Description | Typical Roles |
|---------------|-------------|---------------|
| `org.manage` | Org CRUD, hierarchy adjustment | owner, admin |
| `member.manage` | Invite/remove/role changes | owner, admin |
| `content.create` | Initiate content generation tasks | owner, admin, editor |
| `content.review` | Approve content publication | owner, admin, reviewer |
| `content.read` | Read content and conversation history | owner, admin, editor, reviewer, viewer |
| `knowledge.manage` | Knowledge Stores write/delete | owner, admin |
| `settings.manage` | OrganizationSettings modification (RULE level) | owner, admin |
| `data.export` | Data export/report download | owner, admin |
| `model.manage` | Model register/enable/disable/fallback chain config | owner, admin |
| `experiment.manage` | Experiment create/start/stop/traffic config | owner, admin |
| `billing.read` | Token usage and cost report viewing | owner, admin |

> **Source of truth**: `06-基础设施层.md` lines 108-120. Frontend `packages/shared/permissions.ts` MUST mirror this table exactly.

---

## 2. Auth Strategy Factory (ADR FE-010) -- Owned Contract

> **Decision**: BFF + output:'export' compatibility conflict resolved via Auth Strategy Factory pattern. SaaS mode uses HttpOnly Cookie + BFF (highest security); Private mode degrades to in-memory Bearer Token (security via private network isolation).

```
Auth Strategy Factory (packages/api-client/auth.ts):

  interface AuthStrategy {
    getHeaders(): Record<string, string>   // Get auth headers
    handleUnauthorized(): Promise<boolean>  // Handle 401 refresh
    getWsToken(): Promise<string>           // Get WebSocket token
  }

  SaaS Mode (CookieAuthStrategy):
    getHeaders()          -> empty (Cookie auto-attached by browser, BFF converts)
    handleUnauthorized()  -> empty (BFF intercepts and handles)
    getWsToken()          -> POST /api/auth/ws-token (BFF endpoint)

  Private Mode (BearerAuthStrategy):
    getHeaders()          -> { Authorization: `Bearer ${memoryToken}` }
    handleUnauthorized()  -> use refresh_token to get new access_token, store in memory
    getWsToken()          -> directly reuse current access_token (short validity)
                             or Gateway provides equivalent endpoint GET /api/v1/auth/ws-token

  Factory:
    const strategy = DEPLOY_MODE === 'saas'
      ? new CookieAuthStrategy()
      : new BearerAuthStrategy()   // private + hybrid both use Bearer (FE-07: hybrid same as private)

  Upper-layer code:
    const headers = strategy.getHeaders()  // unaware
    fetch('/api/v1/...', { headers })      // unified call
```

### 2.1 SaaS Auth Flow (BFF)

```
Login:
  User submits credentials -> BFF /api/auth/login -> backend auth
    -> Backend returns JWT
    -> BFF writes HttpOnly Secure SameSite=Strict Cookie
    -> Frontend cannot read token via JS (XSS protection)

Request chain:
  Browser auto-attaches Cookie -> BFF reads Cookie
    -> Extracts JWT -> Adds Authorization: Bearer <jwt>
    -> Forwards to backend Gateway

Token refresh:
  Cookie contains refresh_token -> BFF intercepts 401 response
    -> Automatically uses refresh_token to get new access_token
    -> Updates Cookie -> Retries original request
    -> User unaware

WebSocket auth:
  BFF provides short-lived one-time WS token (/api/auth/ws-token)
    -> Frontend uses this token to establish WS connection
    -> Avoids exposing long-lived JWT in URL

SSE auth (RESOLVED C-3):
  SSE routes through BFF: /api/events/* (BFF route)
    -> Browser auto-attaches Cookie -> BFF reads Cookie
    -> BFF extracts JWT -> Adds Authorization header -> Upstream SSE to backend
    -> No getSseToken() needed; SSE uses same Cookie->BFF path as REST
    -> Consistent with REST auth chain (no special SSE token acquisition)
```

### 2.2 Private Auth Flow (Bearer)

```
Login:
  User submits credentials -> directly call Gateway /api/v1/auth/login
    -> Gateway returns { access_token, refresh_token }
    -> access_token stored in memory (lost on page close)
    -> refresh_token stored in memory (not persisted)

Request chain:
  BearerAuthStrategy.getHeaders() -> { Authorization: Bearer <token> }
    -> Direct request to backend Gateway

Token refresh:
  api-client interceptor detects 401 -> handleUnauthorized()
    -> Use refresh_token to get new access_token
    -> Update in-memory token -> Retry original request
    -> User unaware

WebSocket auth:
  Method 1 (default): Reuse access_token for WS auth
    -> Acceptable within private network, security via network isolation
    -> Gateway already supports Bearer auth WS, no changes needed
  Method 2 (optional, more secure): Gateway exposes /api/v1/auth/ws-token endpoint
    -> Requires backend cooperation, but minimal change (one short-lived JWT signing endpoint)
```

### 2.3 Security Differences (ADR FE-010)

| Dimension | SaaS (BFF) | Private (Bearer) |
|-----------|-----------|-----------------|
| XSS Protection | HttpOnly Cookie (JS unreadable) | In-memory Token (XSS can steal) |
| Mitigation | -- | Private network isolation + strict CSP |
| Token leakage window | Cookie expiry time | In-memory Token (lost on page close) |
| CSRF | SameSite=Strict Cookie + CSRF Token | N/A (no Cookie) |
| Acceptability | Public internet deployment standard | Acceptable for private intranet |

---

## 3. OrgContext Management -- Owned Contract

### 3.1 org_tier Naming (RESOLVED S-1)

Backend org_tier SSOT unified by ADR-049: 05-Gateway lines 97-99 updated to use
06-Infrastructure's 5-tier business names. Authoritative enum:
  `platform | brand_hq | brand_dept | regional_agent | franchise_store`
Frontend `packages/api-client/types/org-context.ts` uses this enum directly. No mapping layer needed.

### 3.2 OrgContext Type Definition

Aligned with backend 05-Gateway Section 4.2 OrgContext Schema v1 (`05-Gateway层.md` lines 92-117):

```
OrgContext type (packages/api-client/types/org-context.ts):
  {
    // --- Fields from backend OrgContext Schema v1 ---
    user_id: string                    // Current request user (required)
    org_id: string                     // Current organization ID (required)
    org_tier: OrgTier                  // 5-tier enum, see Section 3.1 (required)
    org_path: string                   // LTREE path e.g. 'diyu.brand_a.region_east' (required)
    org_chain: string[]                // Root-to-current org ID chain (required, at least self)
    brand_id?: string                  // null = platform-level user (optional)
    role: 'owner' | 'admin' | 'editor' | 'reviewer' | 'viewer'  // (required)
    permissions: PermissionCode[]      // See Section 1.1 for exact codes (required)
    org_settings: OrgSettings          // Merged config after inheritance (required)
    model_access: ModelAccess          // Model availability config (required)
    experiment_context?: {
      assignments: Record<string, string>  // dimension -> variant
      updated_at?: string
    }                               // Optional experiment routing context

    // --- Frontend-added fields (not in backend Schema v1, fetch separately or derive) ---
    org_name?: string                  // Display name; derive from org lookup API
    parent_org_id?: string             // Derivable from org_path
  }

  type OrgTier = 'platform' | 'brand_hq' | 'brand_dept' | 'regional_agent' | 'franchise_store'
  // ADR-049 unified: backend uses these exact names. No mapping needed.

  type PermissionCode =
    | 'org.manage' | 'member.manage' | 'content.create' | 'content.review'
    | 'content.read' | 'knowledge.manage' | 'settings.manage' | 'data.export'
    | 'model.manage' | 'experiment.manage' | 'billing.read'

  interface OrgSettings {
    content_policy: 'relaxed' | 'standard' | 'strict'
    review_flow: {
      auto_compliance_check: boolean
      require_regional_review: boolean
      require_hq_review: boolean
    }
    budget_monthly_tokens: number       // 0 = no budget limit (platform level)
    budget_tool_amount: number          // v3.6: tool budget, independent from token budget
    media_config: {
      allowed_media_types: ('image' | 'audio' | 'video' | 'document')[]
      file_size_limit: number
      media_quota: number
      nsfw_sensitivity: number
      quarantine_expire_days: number
    }
    is_locked: Record<string, boolean>  // Per RULE config item
    // ... other RULE/BRIDGE items (see Section 5)
  }

  interface ModelAccess {
    allowed_models: string[]            // Empty = no models available (should degrade with error)
    default_model: string               // Must not be empty
    budget_monthly_tokens: number       // Same value as org_settings.budget_monthly_tokens
    budget_tool_amount: number          // Same value as org_settings.budget_tool_amount
  }
```

> **Note**: v1 of this document incorrectly listed `fallback_chain` under ModelAccess and `legal_profile` as an OrgContext field. Current alignment:
> `model_access` uses `allowed_models/default_model/budget_monthly_tokens/budget_tool_amount` (v3.6 dual-budget expansion),
> and `legal_profile` is NOT in OrgContext Schema v1.

Frontend handling:
- Org Switcher: switching org refreshes OrgContext, rebuilds WS, cleans local temp state
- Permission guards layered: `TierGate` controls entry (org_tier-based), `PermissionGate` controls buttons/actions (permissions[]-based)
- Frontend permissions only for UI visibility; real permission validation always at Gateway
- Config inheritance visualization: LAW read-only, RULE editable, BRIDGE locks child orgs
- Model selector: reads `model_access.allowed_models` and `model_access.default_model`

---

## 4. TierGate Access Rules -- Owned Contract

### 4.1 Admin Console TierGate

```ts
if (org_tier === 'platform') allowAdmin();
else if (org_tier === 'brand_hq' && role in ['owner', 'admin']) allowAdmin();
else redirectToWebApp(); // 302 to apps/web
```

Key constraints:
- Platform-wide member management only accessible to `platform` + `brand_hq(owner/admin)`
- `brand_dept/regional_agent/franchise_store` have no Admin Console entry
- `brand_hq(editor/viewer)` have no Admin Console entry, only Web App

### 4.2 Admin Console Feature Exposure Matrix

| Feature Module | platform | brand_hq (owner/admin) | Other roles/tiers |
|---------------|----------|------------------------|-------------------|
| Operations Dashboard | Global | Brand-level | None |
| Org Tree Management | Global | Brand subtree | None |
| Member Management | Global | Brand-wide | None |
| Brand Knowledge | Platform templates | Brand CRUD + import | None |
| Content Review Rules | Rule templates | Toggle + config (default off) | None |
| Settings (RULE/BRIDGE) | Global | Brand-level | None |
| Usage/Billing | Global billing | Brand billing (subscription + points) | None |
| Audit Logs | Global | Brand-level | None |
| Experiment Management | Global | Brand-level | None |
| platform-ops/* | All | None | None |

### 4.3 Web App Feature Exposure Matrix

| Feature | brand_hq staff | brand_dept | regional_agent | franchise_store |
|---------|---------------|------------|----------------|-----------------|
| AI Chat + Model Selection | Y | Y | Y | Y |
| Content Creation | Y | Y | Y(regional) | Y(store) |
| History Folders + Upload to HQ | Y | Y | Y | Y |
| Knowledge Editing Workspace | Y | Contribute | Template edit + submit | Local folder + template + submit |
| Store Dashboard/Store Change Request | - | - | Y | - |
| Local Knowledge Folder | - | - | - | Y |
| Usage & Points Balance View | Y | Y | Y | Y |
| Recharge Entry | owner/admin | - | - | - |
| Memory Management | Y | Y | Y | Y |

---

## 5. Settings Constraints Enum

`packages/shared/settings-constraints.ts` based on business rules:
- Retained: `content_policy / review_flow / content_restrictions / allowed_models / default_model / fallback_chain / skill_whitelist / tool_whitelist / is_locked`
- Added (v3.6): `media_config.allowed_media_types / media_config.file_size_limit / media_config.media_quota / media_config.nsfw_sensitivity / media_config.quarantine_expire_days`
- Added (v3.6): `budget_tool_amount` (dual-budget model: token + tool)
- New business items: `brand_tone / personas / knowledge_visibility_acl`
- Editable budget items align with backend RULE constraints: `budget_monthly_tokens / budget_hard_limit / budget_tool_amount`
- Compatibility strategy: unknown historical budget fields use read-only fallback with `legacy` marking

# FE-06 Admin Console

> **contract_version**: 1.0.0
> **min_compatible_version**: 1.0.0
> **breaking_change_policy**: Expand-Contract
> **owner**: Frontend Admin Lead
> **source_sections**: frontend_design.md Sections 9.1 ~ 9.5 (full coverage)
> **depends_on**: FE-01 (package structure), FE-02 (SSE events), FE-03 (TierGate, OrgContext)

---

## Scope Boundary

FE-06 covers all Section 9.x content including:
- 9.1 Core pages and route structure
- 9.2 UI library hybrid strategy (ADR FE-008)
- 9.3 Technical characteristics
- 9.4.1 ~ 9.4.17 Admin module detailed design
- 9.5.1 ~ 9.5.7 Platform-Ops detailed design

---

## 1. Core Pages

```
Admin Console entry rules (cross-ref: FE-03 TierGate):
  - platform: Full Admin
  - brand_hq(owner/admin): Brand-level Admin
  - Other tiers and roles: 302 to apps/web

(dashboard)/ route group -- brand_hq(owner/admin) visible:
+-- Dashboard         # Brand overview
+-- Organizations     # Org tree management + store add/remove approval
+-- Members           # Brand-wide member management (sole business layer entry)
+-- Knowledge         # Brand knowledge base
|   +-- import-review/ # Subordinate submission download/import status
|   +-- local-life/    # Local life knowledge base
|   +-- store-nodes/   # National store graph nodes
+-- Content Review    # Content review workflow (default off, show when enabled)
+-- Experiments       # A/B experiment management
+-- Billing           # Subscription/points/usage reports
+-- Settings          # RULE + BRIDGE + BrandTone + Personas + Skill/Tool whitelist
+-- Audit             # Brand audit logs

(platform-ops)/ route group -- platform only:
+-- tenant-overview/      # Tenant overview
+-- tenant-detail/[org_id]/ # Tenant detail + quota + exemptions
+-- model-registry/       # Global model registry
+-- model-pricing/        # Qwen official pricing mapping
+-- subscription-plans/   # Plan definition + point packages
+-- billing-global/       # Platform-wide billing
+-- global-config/        # Global default config
+-- security-config/      # Security & compliance
+-- system-ops/           # Ops monitoring
+-- global-knowledge/     # Platform-level knowledge templates

Route guards:
  apps/admin entry TierGate:
    if (org_tier === 'platform') allow
    else if (org_tier === 'brand_hq' && role in ['owner', 'admin']) allow
    else redirect to apps/web
  Admin full scope (delivered across Phase 0-4):
    Phase 0: skeleton + TierGate + effective-settings panel (FA0-1~FA0-3)
    Phase 2: user management + org management + audit log (FA2-1~FA2-3)
    Phase 3: knowledge workspace + content review + config management (FA3-1~FA3-3)
    Phase 4: monitoring + quota + backup (FA4-1~FA4-3)
    Note: Billing/recharge delivered via Web (FW4-5), not Admin.
```

---

## 2. UI Library Hybrid Strategy (ADR FE-008)

apps/admin uses shadcn/ui base + Ant Design enterprise components:

| Component Need | Source | Rationale |
|---------------|--------|-----------|
| Button, Input, Card, Dialog | shadcn/ui | Unified with packages/ui |
| 5-level org tree (ltree) + drag | Ant Design Tree | Out-of-box, self-build cost ~2 person-weeks |
| Complex data table (server pagination/sort/filter) | TanStack Table + shadcn/ui | Higher flexibility |
| Cascader (org/region/store) | Ant Design Cascader | Out-of-box, self-build cost ~1 person-week |
| Approval workflow status | Ant Design Steps + Timeline | Semantically complete |
| Complex forms (conditional show/hide/nested/array) | React Hook Form + shadcn/ui | More control |
| Date range/time picker | Ant Design DatePicker | Complete i18n |
| Statistics cards/data overview | Ant Design Statistic | Out-of-box |

Style isolation:
  - Ant Design components isolated via CSS prefix (ConfigProvider prefixCls="diyu-admin")
  - Tailwind and antd styles do not conflict (Tailwind preflight skips antd components)
  - packages/ui shadcn/ui components work normally in Admin

Dependency control:
  - Ant Design declared only in apps/admin/package.json
  - packages/ui does NOT depend on Ant Design (kept pure)
  - Tree-shakeable: babel-plugin-import or native Tree Shaking

---

## 3. Technical Characteristics

```
+-- RSC (React Server Components): Data-intensive tables/reports (SaaS mode)
+-- Private degradation: output:'export' degrades RSC to CSR (FE-001)
+-- DataTable: TanStack Table + server pagination/sort/filter
+-- Org tree visualization: Ant Design Tree (5-level, LTREE path)
+-- Real-time: SSE /events/* receives config change notifications (cross-ref: FE-02)
+-- Permissions: Every page/action bound to *.manage permission code
```

---

## 4. Admin Module Detailed Design

### 4.1 Org Tree Navigation (organizations/)

- Tree display: brand_hq > brand_dept/regional_agent > franchise_store
- brand_hq can directly add/adjust regional agents and stores
- regional_agent store changes can only submit requests, approved by brand_hq then executed
- Constraint: store add/remove requests are NOT member management/personnel changes; regional team personnel changes are handled uniformly by brand_hq in the members module

### 4.2 Member Management (members/)

- Only platform and brand_hq(owner/admin) visible
- brand_hq handles brand-wide member invite/remove/role changes
- Store accounts follow 1 primary + 1 backup, managed uniformly by brand_hq

### 4.3 Config Management (settings/)

- Config item list, each annotated with constraint type:
    LAW:    gray lock icon, read-only, "System enforced"
    RULE:   editable input field
    BRIDGE: editable + "Child orgs cannot override" label
- Inheritance source: "Inherited from [brand name]" hint
- Brand rule priorities:
    content_policy / review_flow / content_restrictions
    allowed_models / fallback_chain / skill_whitelist / tool_whitelist
    brand_tone / personas / knowledge_visibility_acl
- Save validation: is_locked items prevent child org modification
- review_flow uses object model (aligned with 06-Infrastructure Section 1.5):
    auto_compliance_check / require_regional_review / require_hq_review (three toggles)
  Default: all false (content review default off)
- content_policy UI impact mapping (RESOLVED L-4):
    relaxed:  content publishes directly, no review entry shown
    standard: AI auto-review (only escalate to human on anomaly)
    strict:   all content requires manual review before publication

### 4.4 Knowledge Management (knowledge/)

- Brand knowledge base: product info/brand specs/SOP CRUD
- import-review: subordinate submission view/download (for ops manual format conversion)/manual import/status records
- local-life: local life content production knowledge base
- store-nodes: national store graph node entity management

### 4.5 Experiment Management (experiments/)

- Brand-level A/B experiments (Prompt version/model selection/strategy)
- Experiment list: name, status, group ratios, key metrics

### 4.6 Billing & Usage (billing/)

- Base subscription: 299 CNY/month
- Included quota: 100 CNY equivalent Token (1:1 Qwen official pricing mapping)
- Overage points: minimum 100 CNY purchase; 100 CNY = 33 CNY equivalent Token
- Commercial pricing note: overage points ~3:1 markup as platform profit model; subscription quota still 1:1
- Views: monthly quota consumption, points balance, subordinate org usage summary, recharge records
- Alerts: 80%/95%/100% staged prompts

### 4.7 Audit Logs (audit/)

- Full-chain operation records (time, operator, action, target)
- Filters: time range, operation type, operator, sensitive operations
- Export (CSV)

### 4.8 Model Config -- Brand Level (settings/ embedded) [Phase 0]

- brand_hq configures allowed_models range (constrained by platform intersection)
- End users freely switch models in Web conversation page, middle tiers do not second-gate
- Model display: name + capability tags + reference pricing

### 4.9 Model Registry -- Global (platform-ops/model-registry/) [Phase 2]

- Platform only visible
- CRUD: ModelDefinition (model_id, provider, capabilities, tier, pricing, status)
- Default provider strategy: Qwen main model pool as default (text + multimodal)
- Pricing strategy: auto-fetch/sync Qwen official pricing and map to model-pricing
- Platform maintains fallback chain defaults; brand tier only selects within allowed_models

### 4.10 Knowledge Visibility Partitioning (knowledge/) [Phase 2]

- visibility labels: global | brand | region | store
- Inheritance flags (aligned with 02-Knowledge Section 3.1, RESOLVED H-5):
    inheritable: Boolean -- whether knowledge can be inherited by child orgs
    override_allowed: Boolean -- whether child orgs can override parent knowledge
    UI rendering: inheritable toggle + override_allowed toggle per knowledge entry
    Data source: GET /api/v1/admin/knowledge/visibility (05a Section 2.4)
      response includes inheritable + override_allowed per item
- Node ACL matrix: which orgs can view/retrieve
- Store content production default retrieval: store memory + HQ knowledge + store graph + local life knowledge

### 4.11 Config Management Enhancement (settings/) [Phase 0]

- effective-settings read-only panel: shows current org's final effective config (after merging inheritance chain)
- Source annotation: each config item annotated "This level setting" / "Inherited from [parent org name]" / "System default (LAW)"
- Backend API: GET /api/v1/admin/effective-settings (05a-API-Contract.md Section 2.3, RESOLVED H-12)
  Response per key: { value, source: "self"|"inherited"|"default", source_org_id?,
    source_org_name?, constraint: "LAW"|"RULE"|"BRIDGE", is_locked, admin_ui: "readonly"|"control"|"hidden" }
  Settings key list: 06-Infrastructure Section 1.5 (~25 keys, 7 groups)
- Frontend directly renders response; admin_ui field drives display mode

### 4.12 Onboarding Wizard (onboarding/) [Phase 2]

- New brand first-login guide: basic info -> model selection -> knowledge import -> complete
- Step state persisted (prevents progress loss on mid-exit)
- Skippable; after skip, Dashboard shows pending completion hints

### 4.13 Notification Center (notifications/) [Phase 2]

- Consumes SSE /events/* push (cross-ref: FE-02 Section 2)
- Notification types: config change / review request / quota alert / system announcement
- Read/unread status, mark all as read
- Bell icon + unread count badge

### 4.14 Multi-Session Management -- User-facing (apps/web) [Phase 2]

- Sidebar session list: session title + last message time + unread indicator
- Create/switch/rename/archive/delete sessions
- On switch: clean current Chat State, restore target session context
- Aligned with 05 Section 7.1 WebSocket per-session connection semantics

### 4.15 Persona Management (settings/personas) [Phase 2]

- Multi-persona templates: brand official / VLOG / training / event etc.
- UI: list CRUD + default persona marker + Prompt snippet editor + applicable scenario tags
- Publishing strategy: draft/active version dual-state; active version enters Web model assist prompt

### 4.16 Training Content Management (training) [Phase 2]

- Entry: regional_agent Web App + brand_hq Admin review page
- Flow: region generates training materials -> submit -> HQ review and publish
- UI: template selection, chapter editing, status flow, export and archive

### 4.17 Inventory Association Capability (store inventory) [Phase 2]

- Store side can view inventory-associated recommendations in chat and coordination pages (enabled when inventory system exists)
- UI: "In stock/Out of stock/Alternative" labels + one-click replace coordination item
- Degradation: no inventory integration -> hide inventory labels, retain general coordination recommendations

---

## 5. Platform-Ops Module Detailed Design

### 5.1 tenant-detail/[org_id]

- Fields: tenant status (normal/suspended/overdue), quota, exemption type and validity
- Operations: suspend/resume/delete tenant (dangerous operations require double confirmation)
- UI: detail card + operation drawer + risk confirmation modal

### 5.2 model-pricing

- Fields: provider/model_id/capabilities/official unit price/effective time
- Operations: official price sync (manual trigger + failure retry) + difference reconciliation
- UI: price comparison table + sync status badge

### 5.3 subscription-plans

- Fields: base plan (299/month with 100 CNY quota), point packages (minimum 100 CNY purchase), conversion rules
- Operations: plan enable/disable, version publishing, effective time control
- UI: plan cards + rule form + publishing records

### 5.4 billing-global

- Fields: platform revenue, receivables, overdue, tenant consumption distribution
- Operations: overdue policy config (N days then degrade/suspend)
- UI: overview charts + drill-through to tenant billing details

### 5.5 security-config

- Fields: global forbidden_words (LAW), login security policies, data retention period
- Operations: policy versioned publishing + rollback
- UI: partitioned form + change audit sidebar

### 5.6 system-ops

- Fields: Gateway/Brain/Memory/Knowledge health status, alerts, maintenance windows
- Operations: maintenance mode toggle, global announcement publishing
- UI: status big screen + timeline + announcement editor

### 5.7 global-knowledge

- Fields: platform universal templates, industry templates, RAG default parameters
- Operations: template CRUD, version effective control
- UI: template list + version comparison + publish button

---

## 6. Experiment Engine Integration

```
Backend Experiment Engine (06 Section 4) provides 5-dimension experiment capability:
  Skill / Brain / Knowledge / Prompt / Model

Ownership decision (M-21 adjudication):
  Experiment routing/prompt tuning/model switching remains backend-internal.
  Frontend does not consume assignments API and does not report experiment events.

Frontend integration scope:
  1. Admin management UI only:
     - Uses /api/v1/admin/experiments for create/list/update (Phase 2 reserved)
  2. Runtime rendering:
     - No direct experiment-dependent branching in FE
     - Backend returns already-selected behavior/output for the current request
  3. Feature Flags:
     - Keep generic feature-flag mechanism
     - Do not bind to experiment_assignment_id
```

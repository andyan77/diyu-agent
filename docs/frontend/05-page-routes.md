# FE-05 Page Routes & Feature Modules

> **contract_version**: 1.0.0
> **min_compatible_version**: 1.0.0
> **breaking_change_policy**: Expand-Contract
> **owner**: Frontend Product Lead
> **source_sections**: frontend_design.md Sections 5.1 (apps/web route tree), 8.5.3, 8.5.5, 8.6, 8.7
> **depends_on**: FE-01 (package structure), FE-02 (SSE events -- non-chat subdomain), FE-03 (OrgContext, TierGate), FE-04 (DiyuChatRuntime, Component Registry -- chat subdomain only)

---

## Scope Boundary

FE-05 describes all **apps/web page routes and feature modules**. It is split into two subdomains:

### Chat Subdomain (depends on FE-04)
Routes that require DiyuChatRuntime, Component Registry, or Chat State:
- `chat/` -- AI conversation
- `content/` -- Content production (embedded chat)
- `merchandising/` -- Display coordination (embedded chat)
- `search/` -- Global search (intent-driven via chat)

### Non-Chat Subdomain (depends on FE-01, FE-02, FE-03 only)
Routes that use REST/SSE but NOT the dialog engine:
- `(auth)/` -- Login/register
- `memory/` -- Memory management
- `history/` -- Conversation history folders
- `knowledge-edit/` -- Knowledge editing workspace
- `store-dashboard/` -- Regional agent store dashboard
- `settings/` -- Personal settings
- `(bookmarks)/` -- Artifact bookmarks
- `training/` -- Training content (regional)

---

## 1. apps/web Route Tree

```
apps/web/app/
  +-- (auth)/              # Login/register route group
  |
  +-- (main)/              # Main application route group
  |   +-- chat/            # [Chat Subdomain] AI conversation (Scenario 1)
  |   +-- content/         # [Chat Subdomain] Content production (Scenario 2)
  |   +-- merchandising/   # [Chat Subdomain] Display coordination (Scenario 3)
  |   +-- search/          # [Chat Subdomain] Global search
  |   +-- training/        # [Non-Chat] Regional training content management
  |   +-- memory/          # [Non-Chat] My memories (view/delete/PIPL tracking)
  |   +-- history/         # [Non-Chat] Conversation history + folders + upload to HQ
  |   |   +-- folders/
  |   |   +-- upload/
  |   +-- knowledge-edit/  # [Non-Chat] Knowledge editing workspace
  |   |   +-- templates/
  |   |   +-- drafts/
  |   |   +-- submitted/
  |   +-- store-dashboard/ # [Non-Chat] Regional agent store dashboard
  |   +-- settings/        # [Non-Chat] Personal settings
  |
  +-- (bookmarks)/         # [Non-Chat] Artifact bookmarks (V1.1)
  +-- api/                 # BFF Route Handlers (SaaS mode only)
  +-- layout.tsx           # Root layout
```

---

## 2. Chat Subdomain Routes

### 2.1 chat/ -- AI Conversation (Scenario 1)

Primary route. Uses DiyuChatRuntime (FE-04) for full dialog experience:
- Streaming AI replies + typing indicator
- Component Registry rendering for tool_output
- Dual-pane workspace (Chat + Artifact)
- Memory injection transparency panel
- Context-Aware Suggestion Chips
- Task Progress Panel
- Model selector + billing awareness

### 2.2 content/ -- Content Production (Scenario 2)

Content creation workspace with embedded chat:
- Left pane: chat-driven content generation
- Right pane: ContentEditor + ContentPreview Artifacts
- Brand tone presets (from settings/brand_tone)
- Draft management (auto-save to IndexedDB)

### 2.3 merchandising/ -- Display Coordination (Scenario 3)

Fashion coordination workspace with embedded chat:
- Left pane: chat-driven outfit recommendations
- Right pane: MerchandisingGrid + DisplayGuideCard + OutfitGrid Artifacts
- Inventory association (when available -- FE-06 Section 4.17)
- Store dashboard link (for regional_agent)

### 2.4 search/ -- Global Search

```
+-- Global search bar (Cmd+K / top fixed)
|     |
|     +-- Quick filter: All | Conversations | Knowledge | Products | Content
|     |
|     +-- Intent-driven: natural language -> Chat stream (via WebSocket, Chat Subdomain)
|     |
|     +-- Direct search: keywords -> REST /api/v1/search (if available)
|
+-- Search result rendering:
      +-- In Chat stream: use Component Registry (FE-04) to render
      +-- In search mode: independent search results page (Grid/List toggleable)
```

---

## 3. Non-Chat Subdomain Routes

### 3.1 (auth)/ -- Login & Register

- Login form with credential submission
- Auth flow delegated to AuthStrategy (FE-03)
- SaaS: BFF /api/auth/login flow
- Private: direct Gateway /api/v1/auth/login flow
- Post-login: load OrgContext, redirect to (main)/chat/

### 3.2 memory/ -- Memory Management

See FE-04 Section 7.3 for full PIPL/GDPR memory management spec.

Page features:
- My memory list with type/time/confidence filters
- Confidence visualization (solid/half-solid/hollow dots)
- Provenance labels (confirmed_by_user / observation / analysis)
- Visual separation: personal memory (blue) vs brand knowledge (green, conversation-only)
- Delete request submission + tombstone tracking
- Compliance SLA display

Data source: REST GET /api/v1/me/memories, DELETE /api/v1/me/memories/{memory_id},
             GET /api/v1/me/memories/deletion/{receipt_id}

### 3.3 history/ -- Conversation History

- Sidebar session list: session title + last message time + unread indicator
- Session operations: create / switch / rename / archive / delete
- Folder management (history/folders/):
  - Create/rename/delete folders
  - Drag conversations into folders
  - Folder-based filtering
- Upload to HQ (history/upload/):
  - Select conversations -> package and upload to brand_hq knowledge submission pipeline
  - Status tracking: submitted / under review / approved / rejected

Data source: REST session APIs
  - GET /api/v1/conversations (list)
  - POST /api/v1/conversations (create)
  - PATCH /api/v1/conversations/{conversation_id} (archive/restore/rename via title)
  - DELETE /api/v1/conversations/{conversation_id} (permanent delete)
  - upload via multipart form

### 3.4 knowledge-edit/ -- Knowledge Editing Workspace

- templates/: Browse and select knowledge templates
- drafts/: In-progress knowledge entries (auto-saved every 30s to IndexedDB)
- submitted/: Entries submitted for review (status: pending / approved / rejected)

Workflow:
1. Select template -> fill form -> auto-save draft
2. Submit -> enters brand_hq import-review queue (FE-06 Section 4.4)
3. Track submission status

Route leave protection: dirty data detection + double confirmation

### 3.5 store-dashboard/ -- Regional Agent Store Dashboard

- Only visible to regional_agent tier (PermissionGate)
- Store list with key metrics
- Store add/remove request initiation (requests, not direct operations)
- Request status tracking: pending -> brand_hq approved/rejected -> executed

Data source: REST GET /api/v1/organizations (Data Plane, 05a-API-Contract.md Section 1.6)
  Non-admin path; regional_agent uses this endpoint to list accessible organizations.
  No org.manage permission required; Gateway returns orgs scoped to caller's org_path.

### 3.6 settings/ -- Personal Settings

- User-editable preferences (theme, language placeholder, shortcuts)
- Model preference (if brand allows user selection)
- Notification preferences
- No admin-level config here (those are in FE-06 Admin settings/)

### 3.7 (bookmarks)/ -- Artifact Bookmarks (V1.1)

- Entry: sidebar "My Bookmarks" (Cmd+Shift+B)
- Bookmarked Artifacts from IndexedDB local storage
- Custom titles, search, filter by type
- Click to navigate to source conversation
- Degradation: IndexedDB unavailable -> hide bookmarks entry

### 3.8 training/ -- Regional Training Content

- Entry: regional_agent in Web App
- Browse and manage training materials
- Generate training materials via chat (Chat Subdomain link)
- Submit to brand_hq for review
- Status tracking: draft -> submitted -> under review -> published / rejected

---

## 4. Feature Exposure by Org Tier

Cross-ref: FE-03 Section 4.3 Web App Feature Exposure Matrix.

| Route | brand_hq staff | brand_dept | regional_agent | franchise_store |
|-------|---------------|------------|----------------|-----------------|
| chat/ | Y | Y | Y | Y |
| content/ | Y | Y | Y(regional) | Y(store) |
| merchandising/ | Y | Y | Y | Y |
| search/ | Y | Y | Y | Y |
| memory/ | Y | Y | Y | Y |
| history/ | Y | Y | Y | Y |
| knowledge-edit/ | Y | Contribute | Template edit + submit | Local folder + template + submit |
| store-dashboard/ | - | - | Y | - |
| settings/ | Y | Y | Y | Y |
| (bookmarks)/ | Y | Y | Y | Y |
| training/ | - | - | Y | - |
| Recharge (billing widget) | owner/admin | - | - | - |

---

## 5. Billing Awareness UI in Web App

Billing components appear in apps/web as widgets, not standalone pages:

- `<UsageQuotaBar />`: visible in sidebar or top bar, "Monthly quota 67/100 CNY"
- `<PointsBalance />`: visible alongside quota, "Points balance XX CNY"
- `<RechargeEntry />`: visible only to owner/admin, minimum 100 CNY
- SSE budget_warning events (cross-ref: FE-02) trigger toast notifications
- HTTP 402 triggers billing-specific modal (not generic error toast)

Full billing management is in Admin Console (FE-06 Section 4.6).

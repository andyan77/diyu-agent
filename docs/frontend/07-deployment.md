# FE-07 Deployment & CI/CD

> **contract_version**: 1.0.0
> **min_compatible_version**: 1.0.0
> **breaking_change_policy**: Expand-Contract
> **owner**: Frontend DevOps Lead
> **source_sections**: frontend_design.md Section 14

---

## 1. DEPLOY_MODE Enum (Owned Contract)

This document is the **sole owner** of the DEPLOY_MODE contract. Other documents reference but do not redefine.

```
DEPLOY_MODE = 'saas' | 'private' | 'hybrid'
```

- `saas`: Full Next.js with RSC, deployed to Vercel/Cloudflare/internal cluster
- `private`: output:'export' pure static, nginx:alpine container, zero Node.js dependency
- `hybrid`: Same as private (client-side deployment, server-side SaaS Gateway)

---

## 2. Deployment Mode Differentiation (ADR FE-001)

```
+-----------+-----------------------------+------------------------------+
| Mode      | apps/web (User-facing)      | apps/admin (Admin)           |
+-----------+-----------------------------+------------------------------+
| SaaS      | Vercel/Cloudflare deploy    | Vercel/internal cluster      |
|           | Full Next.js (RSC available) | Full Next.js (RSC available) |
|           | CDN edge caching            | Internal network, not public |
+-----------+-----------------------------+------------------------------+
| Private   | output:'export' -> static   | output:'export' -> static    |
|           | nginx:alpine container (6MB)| nginx:alpine container (6MB) |
|           | Zero Node.js dependency     | RSC degrades to CSR          |
|           | /api/* reverse proxy to     | /api/* reverse proxy to      |
|           | backend container           | backend container            |
+-----------+-----------------------------+------------------------------+
| Hybrid    | Same as Private             | Same as Private              |
+-----------+-----------------------------+------------------------------+
```

---

## 3. Build Switch

```
DEPLOY_MODE=saas    -> Standard Next.js build (retains RSC/SSR)
DEPLOY_MODE=private -> next.config.ts sets output:'export' (pure static)

// next.config.ts
const config = {
  output: process.env.DEPLOY_MODE === 'private' ? 'export' : undefined,
  // ...
}
```

---

## 4. Docker Image Strategy

```
SaaS:    node:22-slim base image, runs Next.js server
Private: nginx:alpine base image, only mounts out/ static directory + nginx.conf (reverse proxy)
```

---

## 5. Impact Assessment

```
Private mode RSC unavailable -> Admin data tables degrade to CSR
Impact: Slightly slower first paint (JS bundle includes table rendering logic)
Mitigation: Code splitting + route-level lazy loading, actual perceptible difference manageable
           (Admin targets internal users)

Private mode BFF unavailable -> Auth degrades to BearerAuthStrategy
Impact: XSS protection degrades from HttpOnly Cookie to in-memory Token
Mitigation: Private network isolation + strict CSP policy (see FE-03 ADR FE-010)
```

---

## 6. SSR Strategy Table

| Page Type | Rendering Strategy | Rationale |
|-----------|-------------------|-----------|
| Login/Register | SSR | SEO + first paint speed |
| Chat main interface | CSR | Real-time interaction, no SEO need |
| AI Memory panel | CSR | Personal data, no SEO need |
| Artifact bookmarks | CSR | Personal data, IndexedDB driven |
| Conversation history folders | CSR | IndexedDB driven, strong interaction |
| Knowledge editing workspace | CSR | Form-intensive interaction, no SEO need |
| Regional store dashboard | SSR + Hydration | Aggregate display, high first-paint readability |
| Recharge/points purchase | CSR | Payment flow and security interaction priority |
| Platform tenant management | SSR + Hydration | Large data volume, fast first paint |
| Platform ops monitoring | CSR | Real-time refresh/long connection driven |
| Public knowledge pages (if any) | SSG/ISR | Stable content, cacheable |

> All SSR pages auto-degrade to CSR in Private mode (output:'export' constraint).

---

## 7. Deployment Topology

```
apps/web   -> Docker image -> CDN edge (SaaS) / nginx container (Private)
                                |
apps/admin -> Docker image -> Internal network (SaaS) / nginx container (Private)
                                |
                          Gateway API <------- Backend Services
```

---

## 8. CI/CD Pipeline

```
PR -> Lint + TypeCheck + Unit Test (Turbo incremental) + Bundle Size Check + a11y Check
Merge to main -> Build (both DEPLOY_MODE) + E2E Test -> Deploy to Staging
Release Tag -> Production Deploy (SaaS + Private dual artifacts)
```

---

## 9. Performance Budget (Cross-ref: FE-08)

CI enforces the performance budget defined in FE-08 Section 1. Build fails if bundle size exceeds thresholds.

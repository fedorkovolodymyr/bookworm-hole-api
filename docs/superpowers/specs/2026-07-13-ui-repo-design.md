# Bookworm Hole UI — New Repo Design

## Purpose

New standalone frontend repo (`bookworm-hole-ui`) for `bookworm-hole-api`, deployed on Vercel. Progressive delivery in large, logical blocks, each covering one API domain end-to-end (list/detail/create/edit flows for that domain's routers). Final block produces an endpoint audit: which API endpoints the UI actually needs, which existing endpoints are unused/excess, which are missing.

## Stack

| Concern | Choice | Why |
|---|---|---|
| Framework | Next.js (App Router) | SSR/SEO for public catalog pages, file-based routing, native Vercel deploy, middleware for route protection |
| Styling | Tailwind CSS | Utility-first, fast iteration, easy design tokens |
| Component kit | shadcn/ui (Radix primitives) | Components are copied into the repo, not an npm dependency — swapping/customizing later means editing owned code, not fighting a library API |
| Data/cache | TanStack Query + axios | Server-state caching, revalidation, request dedup over REST |
| Auth | Next.js middleware + httpOnly cookie via BFF route | Token never touches `localStorage`/JS — avoids XSS token theft; middleware gates protected routes server-side |
| Component workshop | Storybook | Every base/domain component ships a story from day one — isolated visual review, no need to run the full app |
| Testing | Vitest + React Testing Library (unit/component), Playwright (e2e happy paths) | Fast component tests; a thin e2e layer over critical flows (login, browse, review) |
| Lint/format | ESLint + Prettier + typescript strict | Mirrors backend's "lint + format must pass" gate |
| Package manager | pnpm | Fast installs, disk-efficient, Vercel supports natively |

## Repo Structure

```text
bookworm-hole-ui/
  app/                    # Next.js App Router routes
    (auth)/               # login, register
    (app)/                # authenticated shell: books, collections, reviews, reading, friends, chat, admin
  components/
    ui/                   # shadcn/ui primitives (Button, Input, Card, Dialog, ...)
    <domain>/             # domain-specific composed components (BookCard, ReviewForm, ...)
  lib/
    api/                  # axios client, per-domain API modules (books.ts, collections.ts, ...), generated or hand-written types matching API schemas
    auth/                 # session helpers, middleware
  hooks/                  # TanStack Query hooks per domain (useBooks, useCollections, ...)
  styles/                 # tailwind.config, globals.css, design tokens
  stories/ or co-located *.stories.tsx
  tests/                  # Vitest setup; Playwright in e2e/
  .github/workflows/      # ci.yml: lint, type-check, test, build
```

## Design System (Block 0 deliverable)

- Design tokens: color palette (primary/neutral/semantic — success/error/warning), typography scale (font family, sizes, weights), spacing scale, radii, shadows — defined in `tailwind.config` theme, backed by CSS variables for light/dark mode.
- Base components via shadcn/ui CLI: Button, Input, Textarea, Select, Checkbox, Card, Dialog/Modal, Dropdown, Avatar, Badge, Toast, Tabs, Skeleton, Pagination.
- Each component gets a Storybook story covering its variants/states (default, disabled, loading, error).
- App shell: header/nav, auth-aware layout, responsive breakpoints.

## Delivery Blocks

Each block = its own spec → plan → implementation cycle (per `writing-plans`/`executing-plans`), building on the previous block's shell and API client.

| # | Block | API routers covered | UI surface |
|---|---|---|---|
| 0 | Foundation | — | Repo scaffold, CI (lint/format/test/build), design tokens, base component kit, Storybook, app shell/layout |
| 1 | Auth & Session | `auth`, `users` (me) | Login, register, logout, session refresh, profile view/edit, delete-account flow |
| 2 | Catalog | `books`, `releases`, `contributors`, `external` | Book search/browse, book detail (releases, contributors), external-source lookup UI |
| 3 | Collections & Reviews | `collections`, `reviews`, `statuses`, `status_views`, `share` | User collections CRUD, add/remove book to collection, review CRUD, status feed, share links |
| 4 | Reading | `reading_sessions`, `reading_stats` | Start/stop reading session, session history, stats dashboard (charts) |
| 5 | Social | `friends` | Friend list, requests, search users |
| 6 | AI & Chat | `ai`, `chat` | AI recommendations UI, chat interface |
| 7 | Admin | `admin_users`, `admin_audit_logs`, `admin_contributions` | Admin-only dashboard: user management, audit log viewer, contribution moderation queue |
| 8 | API Audit | all of the above | Cross-reference every endpoint actually called by the UI against the full API surface; report endpoints to add, change (shape/params), or remove as dead |

Each block after Block 0 follows the same internal shape:

1. `lib/api/<domain>.ts` — typed client functions matching request/response schemas
1. `hooks/use<Domain>.ts` — TanStack Query hooks (queries + mutations, cache invalidation)
1. `components/<domain>/` — presentational components (Storybook-covered)
1. `app/(app)/<domain>/...` — pages wiring hooks + components
1. Vitest/RTL tests per component + hook; Playwright happy-path per block once the flow is navigable end-to-end
1. Update Block 8's running endpoint-usage log with every endpoint consumed this block

## Data Flow & Error Handling

- Axios instance with baseURL from env, `withCredentials: true` for cookie-based auth.
- Response interceptor: on 401, attempt one silent refresh via BFF route, retry original request once, else redirect to login.
- Domain API errors (404/409/422/etc. from the backend's `AppError` shapes) surface through TanStack Query's `error` state; components render inline error states, not global crash boundaries, except for truly unexpected errors (React error boundary at route-segment level).
- Loading states via Query's `isPending`/`isFetching` + Skeleton components from the base kit.

## Testing Strategy

- Vitest + RTL: every base component (Storybook-covered) gets a render/interaction test; every domain hook gets a test against a mocked API (msw) covering success + error branches.
- Playwright: one happy-path e2e per block once wired (e.g. Block 1 → login redirects to catalog; Block 3 → create collection, add book, leave review).
- CI (`.github/workflows/ci.yml`): lint → type-check → unit/component tests → build → (Playwright on a schedule/PR-label, not every push, to keep CI fast).

## API Audit Deliverable (Block 8)

Produces a table: `endpoint | method | used by (block/page) | status (keep/change/unused)` plus a short list of endpoints the UI needed but the API doesn't yet expose (candidates to add). This becomes the input for a follow-up API-side cleanup pass in `bookworm-hole-api`.

## Out of Scope (this spec)

- Mobile app (native) — not covered.
- i18n — single-locale for now, structure allows adding later (not implemented in Block 0-8).
- Actual Vercel project creation/env config — assumed done manually once repo exists; not part of implementation plan.

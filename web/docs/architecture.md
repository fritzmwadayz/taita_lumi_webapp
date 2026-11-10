# Lumi — Frontend Architecture

> **Audience:** developers new to the Lumi codebase.
> **Purpose:** explain how the Nuxt 4 frontend fits together — the request
> flow, the auth system, the session model, and where the code for each
> concern lives. Read this once before touching `app/` or `server/`.

---

## 1. What Lumi is

Lumi is a project developed to support the digitization of the **Taita language**.
It is designed to be community centric and has Taita-to-Swahili and Taita-to-English translations. 
Users can browse, search, suggest new words and edits, vote on suggestions, and (for reviewers/admins) curate the
dictionary directly.

It has three parts:

| Part | Stack | Hosts |
|---|---|---|
| **Frontend** | Nuxt 4 + Vue 3 + Tailwind CSS v3 | Netlify |
| **Backend API** | FastAPI (Python) | Render |
| **Database** | PostgreSQL | Neon |

This document covers the **frontend** only — but the frontend is tightly
coupled to the backend through a Nitro proxy, so we'll trace requests all the
way through.

---

## 2. The three-tier request flow

Every API call from the browser goes through **two server-side hops** before
hitting the database. This is the single most important thing to understand:

```
Browser                Nuxt/Nitro (Netlify)          FastAPI (Render)        Neon DB
  │                         │                              │                    │
  │  GET /api/words         │                              │                    │
  │ ───────────────────────>│                              │                    │
  │                         │  reads session cookie        │                    │
  │                         │  extracts JWT                 │                    │
  │                         │  GET /api/words               │                    │
  │                         │  Authorization: Bearer …      │                    │
  │                         │  X-Session-Cookie: <anon-uuid>│                    │
  │                         │ ────────────────────────────> │                    │
  │                         │                              │  SQL query         │
  │                         │                              │ ─────────────────> │
  │                         │                              │  rows              │
  │                         │                              │ <───────────────── │
  │                         │  JSON                         │                    │
  │                         │ <──────────────────────────── │                    │
  │  JSON                   │                              │                    │
  │ <───────────────────────│                              │                    │
```

**Why the proxy exists** (instead of the browser calling FastAPI directly):

1. **No CORS** — the browser talks same-origin to Nitro. Nitro talks
   server-to-server to FastAPI. No preflight, no origin headers.
2. **Token isolation** — the JWTs live in an httpOnly cookie that the browser
   can't read. Nitro reads them server-side and attaches the
   `Authorization` header to the outbound FastAPI request.
3. **Transparent refresh** — if FastAPI returns 401 (expired access token),
   Nitro silently refreshes and retries. The browser never sees the 401.
4. **Anon tracking** — even unauthenticated requests carry an `X-Session-Cookie`
   (a UUID) so FastAPI can rate-limit and audit anonymous activity.

---

## 3. The Nitro server layer

Nuxt's server engine (Nitro) handles two kinds of `/api/*` routes:

### 3a. Specific auth handlers (`server/api/auth/*.ts`)

These run **instead of** the catch-all. They manage the session cookie —
something the catch-all can't do because it doesn't know about auth state:

| File | Route | What it does |
|---|---|---|
| `login.post.ts` | `POST /api/auth/login` | Forwards creds to FastAPI, gets JWTs, fetches profile, sets session |
| `register.post.ts` | `POST /api/auth/register` | Same flow for new accounts |
| `logout.post.ts` | `POST /api/auth/logout` | Clears the session |
| `oauth/google.get.ts` | `GET /api/auth/oauth/google` | Initiates Google OAuth flow |
| `_auth/session.get.ts` | `GET /api/_auth/session` | Returns the public session (**strips JWTs**) |

The `_auth/` prefix is a nuxt-auth-utils convention — the framework looks there
for the session endpoint. Our handler overrides the default to ensure tokens
are never sent to the client.

### 3b. The catch-all proxy (`server/api/[...].ts`)

Everything else — `/api/words/*`, `/api/search`, `/api/suggestions/*`,
`/api/admin/*`, `/api/auth/me/*`, `/api/auth/password-reset/*` — hits the
catch-all, which reads the method, query, and body, then hands them to
`server/utils/proxy.ts`.

### 3c. The proxy helper (`server/utils/proxy.ts`)

This is the heart of the server layer. For each request it:

1. **Reads the session** via `getUserSession(event)` — returns `{ user, tokens }`
   or `{}` if not logged in.
2. **Reads/generates the anon cookie** (`lumi_anon`) — a UUID that persists
   across visits for rate-limiting and audit even when unauthenticated.
3. **Builds headers** — `Authorization: Bearer <access_token>` (if logged in),
   `X-Session-Cookie: <anon-uuid>` (always), `Content-Type: application/json`.
4. **Forwards** to `${apiBase}${path}` via `$fetch`.
5. **Handles errors**:
   - **401** → tries `POST /api/auth/refresh` once with the refresh token,
     updates the session, retries the original request. If refresh fails,
     clears the session and throws 401.
   - **403 with "blocked"** → clears the session (blocked user shouldn't stay
     "logged in" client-side) and re-throws with `data: { blocked: true }`.
   - **Other errors** → re-throws with the backend's `detail` message.

```
proxyToApi(event, path, options)
  │
  ├── getUserSession(event) ──> { user, tokens } | {}
  ├── getCookie('lumi_anon')  ──> uuid (or generate + set)
  ├── build headers
  ├── $fetch(`${apiBase}${path}`, { method, headers, query, body })
  │
  └── catch:
        ├── 401 + refreshToken + not already retried
        │     ├── POST /api/auth/refresh ──> new tokens
        │     ├── setUserSession(updated tokens)
        │     └── proxyToApi(event, path, { ...options, _retried: true })
        │
        ├── 403 + "blocked" in detail
        │     ├── clearUserSession(event)
        │     └── throw 403 { data: { blocked: true } }
        │
        └── else: re-throw with backend detail
```

The `_retried` flag prevents infinite refresh loops: if the retried request
also 401s, we don't refresh again.

---

## 4. Session model

### 4a. What's in the session

nuxt-auth-utils stores the session in an **httpOnly, encrypted cookie**
(`NUXT_SESSION`). The cookie is set with:

```
httpOnly: true          ← browser JS can't read it (XSS-safe)
sameSite: 'lax'         ← protects against CSRF for most cases
secure: !import.meta.dev ← HTTPS-only in production
maxAge: 2 years         ← the cookie itself is long-lived; the JWTs inside expire
```

The session payload (defined in `app/types/index.ts` as `SessionData`):

```ts
interface SessionData {
  user?: User                    // id, email, display_name, role, created_at, …
  tokens?: {
    access_token: string         // short-lived JWT (~15 min)
    refresh_token: string        // long-lived JWT (~7 days)
  }
}
```

### 4b. What the client sees vs. what the server sees

This distinction is critical:

| | Client (browser) | Server (Nitro) |
|---|---|---|
| Reads session via | `useUserSession()` | `getUserSession(event)` |
| Sees `user` | ✓ | ✓ |
| Sees `tokens` | **✗** (stripped by `_auth/session.get.ts`) | ✓ |
| Can attach `Authorization` header | ✗ (no token to attach) | ✓ (in `proxyToApi`) |

The `GET /api/_auth/session` endpoint (called automatically by
`useUserSession()` on page load) returns the session **without** the `tokens`
field:

```ts
// server/api/_auth/session.get.ts
const { tokens: _tokens, ...publicSession } = session
return publicSession
```

This means the JWTs never reach the browser. The only way they're used is
server-side, inside `proxyToApi`, when forwarding requests to FastAPI.

### 4c. Session lifecycle

```
register / login
    │
    ├── POST /api/auth/login (or register)
    │     └── Nitro handler: forwards to FastAPI, gets JWTs + user profile
    │         └── setUserSession(event, { user, tokens })
    │
    ▼
session cookie set (httpOnly, encrypted)
    │
    ├── browser: useUserSession() fetches /api/_auth/session
    │     └── gets { user } (no tokens)
    │
    ├── subsequent /api/* requests
    │     └── catch-all proxy reads full session (incl. tokens) server-side
    │         └── attaches Authorization: Bearer <access_token>
    │
    ├── access token expires (15 min)
    │     └── FastAPI returns 401
    │         └── proxy silently refreshes via /api/auth/refresh
    │             └── updates session, retries request
    │
    ├── logout
    │     └── POST /api/auth/logout → clearUserSession(event)
    │
    └── account deletion
        └── DELETE /api/auth/me → 204 → clearUserSession(event) → redirect /
```

---

## 5. The auth system

### 5a. `useAuth()` composable (`app/composables/useAuth.ts`)

This is the single entry point for auth state in components. It wraps
nuxt-auth-utils' `useUserSession()` and exposes:

```ts
const {
  user,              // ComputedRef<User | null>
  isAuthenticated,   // ComputedRef<boolean>
  isAdmin,           // ComputedRef<boolean> — role === 'admin'
  isReviewer,        // ComputedRef<boolean> — role === 'reviewer' || 'admin'
  displayName,       // ComputedRef<string> — display_name or email prefix
  initial,           // ComputedRef<string> — first letter, for avatars
  loading,           // ComputedRef<boolean> — !session.ready
  login(email, password),
  register(email, password, displayName?),
  loginWithGoogle(),     // navigates to /api/auth/oauth/google
  logout(),
  session,               // the raw useUserSession() instance
} = useAuth()
```

**Critical pattern:** after `login()` or `register()`, the composable calls
`await session.fetch()`. This refreshes the client-side session state after
the server has set the cookie. Without this, the UI wouldn't know the user is
logged in until the next page navigation.

### 5b. Route middleware (`app/middleware/`)

Middleware runs before a page renders. Lumi has four:

| Middleware | File | Behavior |
|---|---|---|
| `auth` | `auth.ts` | Waits for session to load (`session.fetch()` if not ready), redirects to `/login?next=<path>` if no user |
| `guest` | `guest.ts` | Redirects to `/` if already logged in — used on login, forgot-password, reset-password |
| `admin` | `admin.ts` | Checks `role === 'admin'`, redirects otherwise |
| `reviewer` | `reviewer.ts` | Checks `role === 'reviewer' \|\| 'admin'` |

Applied via `definePageMeta({ middleware: 'auth' })` on each page.

### 5c. OAuth (Google sign-in)

The flow uses nuxt-auth-utils' built-in OAuth helpers:

```
browser                      Nitro                         Google
  │                            │                              │
  │ GET /api/auth/oauth/google │                              │
  │ ──────────────────────────>│                              │
  │                            │ redirect to Google consent   │
  │ <── 302 to accounts.google │                              │
  │                            │                              │
  │ user consents              │                              │
  │ ────────────────────────────────────────────────────────────>│
  │                            │                              │
  │ redirect back to /api/auth/oauth/google?code=…             │
  │ ──────────────────────────>│                              │
  │                            │ exchanges code for tokens    │
  │                            │ fetches profile              │
  │                            │ setUserSession(event, …)     │
  │ <── 302 to / (or ?next=…)  │                              │
```

OAuth-only accounts (no password set) are flagged via
`user.oauth_provider === 'google'`. The profile page uses this (combined with
the `connected-accounts` endpoint) to hide the password-change, email-change,
and account-deletion forms for these users — Google manages those credentials.

---

## 6. SSR vs SPA-mode pages

Nuxt has SSR **globally enabled** (`ssr: true` in `nuxt.config.ts`). But
authed pages opt out individually:

```ts
// login.vue, me.vue, forgot-password.vue, reset-password.vue
definePageMeta({
  ssr: false,              // ← SPA mode: render client-side only
  middleware: 'guest',     // (or 'auth' for me.vue)
})
```

**Why?** Authed pages depend on the session cookie to decide what to render.
During SSR, the server doesn't have the user's cookie yet (or it does, but the
content is user-specific and shouldn't be cached). Rendering client-side avoids
a flash of wrong content and simplifies the auth flow.

**Public pages stay SSR** for SEO and fast first paint:
- `/` (home), `/search`, `/words/[id]`, `/guide`, `/support`, `/contact`,
  `/contribute`, `/suggestions/[id]`

These render on the server, get cached at the CDN edge, and hydrate on the
client. The auth state is applied during hydration (the navbar updates to
show the user's avatar if they're logged in).

### Page-route map

| Route | SSR? | Middleware | Purpose |
|---|---|---|---|
| `/` | ✓ | — | Home: hero, word-of-day, recently added |
| `/search` | ✓ | — | Browse + search results |
| `/words/[id]` | ✓ | — | Word detail (inline action cluster, senses, examples) |
| `/contribute` | ✓ | — | Suggest a word + suggestion list |
| `/suggestions/[id]` | ✓ | — | Suggestion detail + voting |
| `/guide` | ✓ | — | Reading guide |
| `/support` | ✓ | — | Support info |
| `/contact` | ✓ | — | Contact form |
| `/login` | ✗ (SPA) | `guest` | Login + signup tabs, Google OAuth |
| `/forgot-password` | ✗ (SPA) | `guest` | Request password reset email |
| `/reset-password` | ✗ (SPA) | `guest` | Set new password via token |
| `/me` | ✗ (SPA) | `auth` | Profile: name/email/connected accounts/stats/password/deletion |
| `/review` | ✗ (SPA) | `reviewer` | Review queue + quick add |
| `/admin` | ✗ (SPA) | `admin` | Admin dashboard |
| `/admin/users` | ✗ (SPA) | `admin` | User management |
| `/admin/words` | ✗ (SPA) | `admin` | Word management |
| `/admin/audit-log` | ✗ (SPA) | `admin` | Audit log |

---

## 7. The profile & account lifecycle

The `/me` page (`app/pages/me.vue`) is the hub for account self-service.
It's organized into four sections:

```
┌─ Profile ──────────────────────────────────────────────────┐
│  Display name (inline edit)                                │
│  Email (changeable — requires current password)            │
│  Role badge + join date                                    │
│  Connected accounts (Google / Password badges)             │
└────────────────────────────────────────────────────────────┘

┌─ My contributions ─────────────────────────────────────────┐
│  Stats card (words added, suggestions, votes)              │
│  Suggestion breakdown (open / accepted / rejected)         │
│  Admin dashboard link (if admin)                           │
│  Review queue link (if reviewer)                           │
└────────────────────────────────────────────────────────────┘

┌─ Security ─────────────────────────────────────────────────┐
│  Change password (inline form — hidden for OAuth-only)     │
└────────────────────────────────────────────────────────────┘

┌─ Danger zone ──────────────────────────────────────────────┐
│  Delete account (requires password — hidden for OAuth)     │
└────────────────────────────────────────────────────────────┘

[ Log out ]
```

### API calls from /me

| Action | Endpoint | Notes |
|---|---|---|
| Load stats | `GET /api/auth/me/stats` | Fetched on mount, in parallel with connected-accounts |
| Load connected accounts | `GET /api/auth/me/connected-accounts` | Returns `{ google: bool, has_password: bool }` |
| Update display name | `PATCH /api/auth/me` | Body: `{ display_name: string }` |
| Change password | `PATCH /api/auth/me/password` | Body: `{ current_password, new_password }` |
| Change email | `PATCH /api/auth/me/email` | Body: `{ new_email, current_password }` — 401 on wrong pw, 409 if taken |
| Delete account | `DELETE /api/auth/me` | Body: `{ password }` — 204 on success, then `session.clear()` + redirect `/` |

### OAuth-only handling

The page computes `isOAuthOnly` from the connected-accounts response
(`google === true && has_password === false`). For these users:

- Email change form is hidden → shows "Your email is managed by Google."
- Password change form is hidden → shows "You're signed in with Google —
  no password to change."
- Account deletion is hidden → shows "Account deletion is not available for
  Google sign-in accounts."

While the connected-accounts request is in flight, the page falls back to
`user.oauth_provider === 'google'` so the forms don't flash for Google users.

---

## 8. The password reset flow

Two pages, one flow:

```
/forgot-password                    /reset-password?token=…
     │                                    │
     │ POST /api/auth/                    │ POST /api/auth/
     │   password-reset/request           │   password-reset/confirm
     │   { email }                        │   { token, new_password }
     ▼                                    ▼
  FastAPI checks email              FastAPI validates token
  → sends email with link           → sets new password
  → always returns 200             → 200 on success
    (enumeration-safe)               → 400 if token invalid/expired
     │                                → 422 if password too short
     ▼                                    │
  "Check your email"                      ▼
  (link expires in 1 hour)          "Password reset!"
                                   → redirect to /login after 3s
```

**Key design decisions:**

1. **Enumeration prevention** — `/forgot-password` always shows the success
   panel, whether or not the email exists. This prevents attackers from
   probing which emails have accounts. Only 429 (rate limited) and 422
   (invalid email format) produce error states.

2. **No auto-login after reset** — on success, the user is redirected to
   `/login` to log in with their new password. This avoids the complexity of
   session establishment through a reset token.

3. **Rate limiting** — the frontend handles 429 by disabling the submit
   button for 60 seconds and showing "Too many requests." The backend
   enforces the actual rate limit.

4. **Token delivery** — the reset token is sent via email. The frontend
   can't test the happy path (it can't read the email); only the error paths
   (invalid token, expired token, short password) are testable from the UI.

---

## 9. Layout & component architecture

### 9a. Root (`app/app.vue`)

Minimal — just the route announcer (for a11y) and the layout/page wrapper:

```vue
<div>
  <NuxtRouteAnnouncer />
  <NuxtLayout>
    <NuxtPage />
  </NuxtLayout>
</div>
```

### 9b. Default layout (`app/layouts/default.vue`)

```
┌─────────────────────────────────────────────────────┐
│  AppNavbar                                           │
├──────────┬──────────────────────────────────────────┤
│          │                                          │
│  Admin   │                                          │
│  Sidebar │            <slot /> (page)               │
│  (if     │                                          │
│  reviewer│                                          │
│  +)      │                                          │
│          │                                          │
├──────────┴──────────────────────────────────────────┤
│  AppFooter                                           │
└─────────────────────────────────────────────────────┘
```

The sidebar shows for **reviewer and admin** roles on **every page** (not just
`/admin/*`). This gives power users persistent navigation context whether
they're browsing words or managing the dictionary. Anonymous and regular users
get the full-width layout.

### 9c. Key components

| Component | Purpose |
|---|---|
| `AppNavbar` | Top nav: logo, search, auth links / user menu |
| `AppFooter` | Footer with links |
| `AppToaster` | Renders the toast queue (mounted once in `app.vue` via `useToast()`) |
| `AdminSidebar` | Persistent sidebar for reviewer+ |
| `SearchBar` | Shared search input (home + search page) |
| `WordCard` | Word list item |
| `PosBadge` | Part-of-speech badge (color + symbol) |
| `StatusBadge` | Suggestion status (open / accepted / rejected) |
| `SuccessOverlay` | Full-screen success moment (used on login/register) |
| `ShareButtons` | Social share (bar variant on word pages) |
| `AudioPlaceholder` | Placeholder for future audio feature |
| `MobileDrawer` | Mobile nav drawer |
| `ExampleForm` / `ExampleEditor` / `SenseForm` | Inline editors for word content |

---

## 10. Design system

### 10a. Color tokens (`tailwind.config.js`)

Six families, each with shades for backgrounds, borders, and text:

| Token | Hex | Role |
|---|---|---|
| `forest` | `#2D5A3D` | Brand, primary buttons, headings |
| `terracotta` | `#C75B39` | Danger, deletion, primary action (alt) |
| `cream` | `#FBF7F0` | Page background, cards |
| `ochre` | `#D4A24C` | Accent, highlights |
| `stone` | `#6B7280` | Secondary text, muted UI |
| `ink` | `#1F2937` | Primary text |

Each has `dark` (hover/pressed), `light` (soft hover), `tint` (light bg),
`wash` (lightest bg) variants. Example: `bg-forest-tint text-forest-dark`.

### 10b. Fonts

- **Body:** Inter (self-hosted via `@nuxt/fonts`)
- **Headings / word display:** Source Serif 4

### 10c. Form primitives (`app/assets/css/main.css`)

Defined in `@layer components` so they're available everywhere:

| Class | What it styles |
|---|---|
| `.field` | Text inputs, selects, textareas |
| `.field-label` | Small uppercase label above fields |
| `.field-error` | Error state (terracotta border + wash bg) |
| `.btn` + `.btn-primary` / `.btn-secondary` / `.btn-ghost` / `.btn-danger` | Button variants |
| `.btn-sm` / `.btn-md` / `.btn-lg` | Button sizes |
| `.focus-ring` | Focus-visible ring (cream + forest) for a11y |
| `.tab-underline` / `.tab-underline-active` | Underline-style tab navigation |
| `.pos-badge` + `.pos-noun` / `.pos-verb` / … | POS badges (color-blind friendly) |
| `.status-badge` + `.status-open` / `.status-accepted` / `.status-rejected` | Suggestion status |
| `.tri-pattern` | Subtle triangle background motif (hero panels) |

### 10d. Toast system (`app/composables/useToast.ts`)

Global, shared toast queue via `useState()`:

```ts
const toast = useToast()
toast.success('Word added')
toast.error('Something went wrong')
toast.info('Suggestion rejected')
toast.success('Accepted', { action: { label: 'Undo', fn: undoFn } })
```

Rendered by `<AppToaster />` (mounted once). Auto-dismisses after 4s (errors:
6s). Max 4 toasts visible; oldest dropped first.

---

## 11. API wrappers (`app/utils/auth.ts`)

All auth/profile API calls are centralized in `app/utils/auth.ts`. These are
auto-imported by Nuxt (no explicit import needed in pages). The wrappers fall
into three groups:

**Session/profile (existing):**
- `updateMe(displayName)` → `PATCH /api/auth/me`
- `fetchMyStats()` → `GET /api/auth/me/stats`
- `changePassword(current, new)` → `PATCH /api/auth/me/password`

**Password reset (new):**
- `requestPasswordReset(email)` → `POST /api/auth/password-reset/request`
- `confirmPasswordReset(token, newPassword)` → `POST /api/auth/password-reset/confirm`

**Account management (new):**
- `changeEmail(newEmail, currentPassword)` → `PATCH /api/auth/me/email`
- `deleteAccount(password)` → `DELETE /api/auth/me`
- `getConnectedAccounts()` → `GET /api/auth/me/connected-accounts`

All use `$fetch('/api/...')` — same-origin, goes through the Nitro proxy.

---

## 12. Runtime configuration

### 12a. The "no secrets in nuxt.config" rule

This is a **critical** architectural constraint. From `nuxt.config.ts`:

> Values assigned in `nuxt.config` are **baked into the Nitro server bundle** at
> build time. Any env var read there ends up in the deployable bundle, and
> Netlify's secrets scanner will block the deploy.

**The pattern:** leave defaults empty (or dev-only localhost fallback), let
Nuxt's runtime override inject real values:

```ts
runtimeConfig: {
  apiBase: 'http://localhost:8000',           // ← dev fallback
  oauth: {
    google: {
      clientId: '',                            // ← empty at build time
      clientSecret: '',                        // ← empty at build time
    },
  },
  public: {
    apiBase: '',                               // ← empty = relative URLs
  },
}
```

At runtime (on Netlify), these are overridden by env vars:

| Env var | Injects into |
|---|---|
| `NUXT_API_BASE` | `runtimeConfig.apiBase` |
| `NUXT_OAUTH_GOOGLE_CLIENT_ID` | `runtimeConfig.oauth.google.clientId` |
| `NUXT_OAUTH_GOOGLE_CLIENT_SECRET` | `runtimeConfig.oauth.google.clientSecret` |
| `NUXT_SESSION_PASSWORD` | `runtimeConfig.session.password` (nuxt-auth-utils) |

The bundle ships with empty strings → the scanner sees nothing → deploy passes.

### 12b. Why `public.apiBase` is empty

```ts
public: { apiBase: '' }
```

Empty string means the browser uses **relative URLs** (`/api/words`), which
hit the same Netlify origin and route to Nitro. If we set it to the FastAPI
URL directly, the browser would try to call FastAPI cross-origin (CORS
nightmare). The proxy exists precisely to avoid this.

---

## 13. Testing

### 13a. End-to-end API test (`api-e2e-test.sh`)

A bash script that walks through the full user lifecycle via curl, using a
cookie jar for session persistence (exactly like a browser):

```
register → login → session → connected accounts → stats
→ update name → change password → change email
→ password reset request (valid/nonexistent/invalid)
→ password reset confirm (bogus token/short password)
→ logout → post-logout 401 checks
→ delete account (wrong pw/correct/login after delete)
```

Run it with:

```bash
npm run dev                    # start Nuxt dev server (:3000)
# FastAPI running on :8000

./api-e2e-test.sh              # plain run
VERBOSE=1 ./api-e2e-test.sh    # show response bodies
SKIP_DESTRUCTION=1 ./api-e2e-test.sh   # skip delete-account tests
```

~30 assertions, color-coded pass/fail, exit code 0/1 for CI.

### 13b. What the script can't test

The password-reset **happy path** (real token → 200) requires reading the
email, which a shell script can't do. Only the error paths are covered. If
the backend ever gets a dev mode that logs tokens to stdout, you could
capture and feed them back in — section 10 of the script has a placeholder.

---

## 14. Directory structure

```
web/
├── app/
│   ├── app.vue                    # Root: NuxtLayout > NuxtPage
│   ├── error.vue                  # Error page
│   ├── assets/
│   │   ├── css/main.css           # Design tokens + primitives
│   │   └── css/motion.css         # Transitions, skeletons, toasts
│   ├── components/                # Shared components
│   │   ├── AppNavbar.vue
│   │   ├── AppFooter.vue
│   │   ├── AppToaster.vue
│   │   ├── SearchBar.vue
│   │   ├── WordCard.vue
│   │   ├── PosBadge.vue
│   │   ├── SuccessOverlay.vue
│   │   └── admin/AdminSidebar.vue
│   ├── composables/
│   │   ├── useAuth.ts             # Auth state + actions
│   │   ├── useToast.ts            # Global toast queue
│   │   └── useRecentSearches.ts   # Recent search persistence
│   ├── layouts/
│   │   ├── default.vue            # Navbar + sidebar + footer
│   │   └── admin.vue              # Admin layout
│   ├── middleware/
│   │   ├── auth.ts                # Redirect to /login if unauthenticated
│   │   ├── guest.ts               # Redirect to / if authenticated
│   │   ├── admin.ts               # Require admin role
│   │   └── reviewer.ts            # Require reviewer+ role
│   ├── pages/                     # File-based routing
│   │   ├── index.vue              # Home
│   │   ├── search.vue             # Browse + search
│   │   ├── words/[id].vue         # Word detail
│   │   ├── login.vue              # Login + signup (SPA, guest)
│   │   ├── forgot-password.vue    # Request reset (SPA, guest)
│   │   ├── reset-password.vue     # Set new password (SPA, guest)
│   │   ├── me.vue                 # Profile (SPA, auth)
│   │   ├── contribute.vue         # Suggest a word
│   │   ├── review/index.vue       # Reviewer queue (SPA, reviewer)
│   │   ├── admin/                 # Admin pages (SPA, admin)
│   │   └── …
│   ├── types/
│   │   └── index.ts               # All TypeScript interfaces
│   └── utils/
│       ├── auth.ts                # Auth API wrappers
│       ├── words.ts               # Word API wrappers
│       ├── suggestions.ts         # Suggestion API wrappers
│       └── admin.ts               # Admin API wrappers
├── server/
│   ├── api/
│   │   ├── [...].ts               # Catch-all proxy → FastAPI
│   │   ├── _auth/session.get.ts   # Public session (strips tokens)
│   │   └── auth/
│   │       ├── login.post.ts      # Login handler
│   │       ├── register.post.ts   # Register handler
│   │       ├── logout.post.ts     # Logout handler
│   │       └── oauth/google.get.ts
│   ├── utils/
│   │   └── proxy.ts               # proxyToApi() — JWT refresh, anon cookie
│   └── middleware/
│       └── anon.ts                # Anon cookie injection
├── docs/
│   └── architecture.md            # ← this file
├── nuxt.config.ts                 # Modules, SSR, runtime config, Nitro
├── tailwind.config.js             # Color tokens, fonts, shadows
└── package.json
```

---

## 15. Key architectural decisions (and why)

### Why a proxy instead of direct browser → FastAPI?

Three reasons, all about security:
1. **JWT isolation** — tokens never reach the browser (httpOnly cookie +
   server-side reading). XSS can't steal what it can't see.
2. **No CORS** — same-origin requests from the browser. No preflight, no
   origin config on FastAPI.
3. **Transparent refresh** — the browser never sees a 401 from an expired
   token. Nitro handles it silently.

### Why SSR for public pages but SPA for authed pages?

Public pages (`/`, `/search`, `/words/[id]`) benefit from SSR: SEO indexing,
fast first paint, CDN caching. Authed pages (`/me`, `/admin`, `/login`)
depend on session state that's user-specific — rendering them server-side
would either require passing the cookie through (complex) or produce a flash
of wrong content. SPA mode is simpler and avoids both.

### Why nuxt-auth-utils instead of rolling our own?

It handles the hard parts: encrypted httpOnly session cookies, OAuth flow
state management, and the `useUserSession()` composable that syncs server and
client state. Rolling our own would mean reimplementing cookie encryption,
CSRF protection, and OAuth state — all error-prone.

### Why are secrets empty in nuxt.config?

Netlify's secrets scanner inspects the deployed bundle. If `nuxt.config.ts`
reads `process.env.DATABASE_URL` at build time, that value gets baked into the
Nitro server bundle as a string literal. The scanner flags it and blocks the
deploy. By leaving defaults empty and using `runtimeConfig` (which Nuxt
overrides at request time from env vars), the bundle ships clean.

### Why does the sidebar show on every page for reviewers?

Power users (reviewers, admins) navigate between reading words and managing
the dictionary constantly. A persistent sidebar gives them context ("you're
in reviewer mode") and quick access to the review queue / admin dashboard
from anywhere. Anonymous and regular users get full-width content — they
don't need the power-user navigation.

### Why does forgot-password always show success?

To prevent **account enumeration**. If the endpoint returned 404 for
non-existent emails, an attacker could probe which emails have accounts by
submitting them and watching the response. By always returning the same
success response, the endpoint reveals nothing about whether the email is
registered. The reset email is only sent if the account exists.

---

## 16. Where to go next

- **Clone the repo** → `npm install` → `npm run dev`
- **Set env vars** → `NUXT_API_BASE`, `NUXT_SESSION_PASSWORD`, and (for
  Google OAuth) `NUXT_OAUTH_GOOGLE_CLIENT_ID` / `NUXT_OAUTH_GOOGLE_CLIENT_SECRET`
- **Start the backend** → FastAPI on `:8000`
- **Run the e2e test** → `./api-e2e-test.sh` to verify the full flow
- **Read the code** → start with `app/composables/useAuth.ts`, then
  `server/utils/proxy.ts`, then any page in `app/pages/`

For the API contract (request/response shapes for every endpoint), see the
backend API documentation — the frontend's `app/types/index.ts` mirrors the
backend's Pydantic schemas.

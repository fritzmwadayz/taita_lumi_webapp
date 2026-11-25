# Changelog

Notable changes to the web frontend, in reverse chronological order. For
commit-level history, see `git log`. This doc is user-readable — it covers
feature additions and breaking changes, not refactor commits.

## [Unreleased]

Nothing staged yet.

## [0.3.0] — 2026-11-25

The "static dictionary" release. The public site is now static-first:
the whole dictionary is exported into static JSON at deploy time, word pages
are pre-rendered to static HTML, and search runs in the browser. Anonymous
traffic serves from the CDN and never touches the Render API or the Neon
database. No `.env` changes required.

### Added

#### Static dictionary snapshot

- `scripts/export-dictionary.mjs` — deploy-time snapshot script. Runs as
  part of `npm run build` (before `nuxt build`): fetches
  `GET /api/export/dictionary` (one request, ~6 DB queries) and writes
  `public/dictionary/` — `words.json` (list index), `words/<slug>.json`
  (full WordDetail per word), `manifest.json` (slugs + total), and
  `sitemap-words.xml` (sitemap fragment). If the API is down mid-deploy it
  keeps the previous snapshot and the build still succeeds.
- `app/composables/useDictionary.ts` — loads the snapshot once per browser
  session (disk-read during SSR/prerender, CDN fetch on the client);
  powers the home page, browse mode, and autocomplete. Falls back to the
  live `/api/search` if the snapshot is missing.
- `app/composables/useStaticWord.ts` — word-detail loader: static
  `<slug>.json` first, live `GET /api/words/{id}` fallback for words added
  after the last export, and a `refresh()` that always goes live (a
  reviewer just edited the word and must see it now).

#### Client-side search (pg_trgm parity)

- `app/utils/dictSearch.ts` — in-browser trigram search that mirrors the
  backend's `GET /api/search` ranking exactly: same trigram extraction
  (2-space prefix / 1-space suffix per word, alphanumerics only), Jaccard
  similarity over deduplicated trigram sets, the 0.3 `%` threshold,
  headword/slug prefix (ILIKE) branches, and `similarity DESC, headword
  ASC` ordering. Autocomplete no longer calls the API per keystroke.

#### Build & config

- `vercel.json` — minimal project config (framework preset + build
  command); Vercel auto-detects the rest.
- `web/docs/static-dictionary.md` — the pipeline, freshness model, and
  deploy checklist.
- `web/docs/CHANGELOG.md` — this file.

### Changed

- Word detail page (`app/pages/words/[id].vue`) — reads the static
  snapshot first (rendered into the prerendered HTML — real content for
  SEO and no-JS visitors), live API only as fallback/post-edit refresh.
- Home page (`app/pages/index.vue`) and search page
  (`app/pages/search.vue`) — read the static index instead of
  `GET /api/words`; browse filters and pagination run client-side;
  `SearchBar.vue` autocomplete uses the in-browser index.
- `nuxt.config.ts` — `routeRules` now prerender `/words/**`, `/`,
  `/search`, `/guide`, `/support`, `/contact`; CDN cache lifetimes for the
  snapshot and word HTML move into `routeRules.headers` (Vercel ignores
  hand-written `vercel.json` headers for Nitro build output); a
  `prerender:routes` **Nuxt hook** adds every slug from
  `public/dictionary/manifest.json`.
- `server/routes/sitemap.xml.ts` — word URLs come from the local
  `sitemap-words.xml` fragment instead of a live API call.
- `package.json` — `build` now runs the export first
  (`export && nuxt build`); new `export` / `build:static` scripts.
- `.env.example` — comments updated from Netlify to Vercel (deploy
  target, OAuth redirect URI, Nitro preset note). No variable changes.

### Fixed

- **Word pages were never actually pre-rendered.** The old
  `server/plugins/prerender-words.ts` had two dead layers:
  1. it fetched `/api/words?size=10000`, which the backend rejects
     (422 — `size` is capped at 100), so it never got slugs; and
  2. it registered its hook as a runtime Nitro plugin, which never
     executes during `nuxt build` anyway. Every word view fell back to
     ISR → a live API call per view. Replaced by the manifest-driven
     `prerender:routes` Nuxt hook in `nuxt.config.ts`.
- Word pages rendered "Word not found" during prerender when the static
  JSON was fetched with a relative URL on the server (`event.$fetch` is
  plain ofetch there and can't resolve relative URLs) — the snapshot is
  now read from disk during SSR/prerender and fetched from the CDN only
  on the client.

### Notes

- The backend side of this release (`GET /api/export/dictionary`) is
  logged in the api changelog as `[0.3.0]`.
- Freshness model: the snapshot is as fresh as the last deploy. After
  reviewers accept/import words, redeploy the frontend to fold them in;
  post-deploy words still work via the live API fallback.

## [0.2.0] — 2026-11-22

The "Nuxt port + Nitro proxy" release. Port of the original Vue 3 SPA to
Nuxt 4 with server-side auth.

- Nuxt 4 + Tailwind + nuxt-auth-utils; public pages SSR, authed pages
  SPA-mode (`definePageMeta({ ssr: false })`)
- Nitro server routes: `/api/*` catch-all proxy to FastAPI with the JWT
  session attached server-side, anon-cookie middleware, login/register/
  logout/OAuth handlers, dynamic sitemap/robots
- Pages: home, search + autocomplete, word detail (senses, examples,
  variations, relationships), contribute, review queue, admin surface
  (users, words, audit log), login/forgot/reset password, guide/support
- `/api/*` requests never expose JWTs to the browser

## [0.1.0] — 2026-11-11

Original Vue 3 SPA (pre-Nuxt). Not in this repo's history — kept for
reference.

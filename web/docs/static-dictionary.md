# Lumi — Static Dictionary Pipeline

> **What changed:** the dictionary's read paths no longer touch the FastAPI
> backend or the Neon database for anonymous traffic. The whole dictionary is
> exported into static JSON at deploy time, word pages are pre-rendered as
> static HTML, and search runs client-side with pg_trgm-equivalent ranking.
> Write paths (login, suggestions, votes, admin, review) are untouched.

---

## 1. How it works

```
deploy time (Vercel build)                    request time (visitor)
─────────────────────────                     ────────────────────────────
npm run build
 └─ scripts/export-dictionary.mjs             Home / Browse / Search:
     GET {API}/api/export/dictionary            /dictionary/words.json (CDN)
     (ONE request, ~6 DB queries)               → in-browser trigram search
     ↓                                          Word pages:
  public/dictionary/                             /words/<slug> → static HTML
    words.json        (list index)               (pre-rendered at build)
    words/<slug>.json (full WordDetail x N)    Autocomplete:
    manifest.json     (slugs + total)           same words.json, client-side
    sitemap-words.xml (sitemap fragment)
     ↓
  nuxt build → prerenders every /words/<slug>  Sitemap: reads the local
  + /, /search, /guide, ...                    fragment — no backend call.
```

Anonymous visitors never hit Render or Neon. The only remaining function
invocations are `/api/_auth/session` (local cookie check, no backend) and
actual write actions.

## 2. Files

| File | Role |
|---|---|
| `web/scripts/export-dictionary.mjs` | Snapshots the dictionary into `public/dictionary/` before `nuxt build` (runs as part of `npm run build`; env `LUMI_API_BASE_URL`). Keeps the existing snapshot if the backend is down mid-deploy. |
| `web/app/utils/dictSearch.ts` | Client-side search with **pg_trgm parity**: trigram sets (2-space prefix, 1-space suffix per word, alnum-only), Jaccard similarity, > 0.3 threshold, headword/slug prefix ILIKE branches, `similarity DESC, headword ASC` ordering. |
| `web/app/composables/useDictionary.ts` | Loads `words.json` once per session (disk-read during SSR/prerender, CDN fetch on client). Exposes search + list lookups. Falls back to live `/api/search` if the snapshot is missing. |
| `web/app/composables/useStaticWord.ts` | Word-detail loader: static `<slug>.json` first (disk on server, CDN on client), live `/api/words/{id}` fallback for post-export words. `refresh()` always goes live (post-edit). |
| `web/nuxt.config.ts` | `prerender:routes` Nuxt hook adds every slug from the manifest (⚠️ must be a Nuxt hook — `server/plugins/*` never run at build time); routeRules prerender `/words/**`, `/`, `/search`; `nitro.preset` = vercel. |
| `web/server/routes/sitemap.xml.ts` | Sitemap from the local `sitemap-words.xml` fragment — no backend call. |
| `web/vercel.json` | CDN caching headers for the snapshot + word pages. |

Backend: `api/app/routes/export.py` (`GET /api/export/dictionary`) returns every
live word as full `WordDetail` + the list index in ~6 queries. Tests: `api/tests/test_export.py` (3 passing; full suite 238).

## 3. Freshness model

- The snapshot is as fresh as the last deploy. Since pushing to `master`
  auto-deploys Vercel, an empty commit (`git commit --allow-empty -m
  "refresh dictionary snapshot" && git push`) re-snapshots everything after
  reviewers accept/import words.
- Words added after the last export still work: the word page falls through
  to the live `/api/words/{id}` fetch (one API call per view, like today).
- Reviewer edits call `refresh()` → live API → immediate feedback.

## 4. Known fix included

The old `server/plugins/prerender-words.ts` fetched
`/api/words?size=10000`, which the backend **rejects (422 — `size` is
capped at 100)**, so word pages were never actually prerendered and every
word view hit Render via ISR. Two dead layers: the plugin also ran at
runtime only (see nuxt.config.ts note). Both are replaced by the
manifest-driven Nuxt hook.

## 5. Deploy checklist (Vercel)

1. Backend: deploy `app/routes/export.py` + `main.py` router registration
   (Render).
2. Frontend env (Vercel): `LUMI_API_BASE_URL=https://<render-app>.onrender.com`,
   `NUXT_SESSION_PASSWORD`, `NUXT_OAUTH_GOOGLE_*` (as before).
3. Redeploy the frontend — `npm run build` snapshots + prerenders.
4. Verify: `curl https://kitaita.vercel.app/dictionary/manifest.json` shows
   the word count; a word page view should be static HTML (`curl -s
   https://kitaita.vercel.app/words/<slug> | grep <headword>`).

If the backend is down during a deploy, the build keeps the previous
snapshot (word pages prerender from the old data; new words use the live
fallback until the next deploy).

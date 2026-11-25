# Lumi — web (Nuxt frontend)

The Nuxt 4 frontend for the Lumi dictionary — the site running at
<https://kitaita.vercel.app>. This is the `web/` subfolder of the Lumi
monorepo; the sibling `api/` folder holds the FastAPI backend, and the repo
root has the deployment instructions.

## What's here

- **Nuxt 4 + Tailwind** — public pages SSR/prerendered, authed pages SPA-mode
- **Nitro server routes** — `/api/*` proxy to the FastAPI backend with the
  JWT session attached (tokens never reach the browser), plus sitemap/robots
- **Static-first dictionary** — the whole dictionary ships as static JSON +
  prerendered word pages; search runs in the browser. See
  [docs/static-dictionary.md](docs/static-dictionary.md) for how it works.

| File | Role |
|---|---|
| `scripts/export-dictionary.mjs` | Deploy-time snapshot: `GET /api/export/dictionary` → `public/dictionary/` (list index, per-word JSON, manifest, sitemap fragment) |
| `app/utils/dictSearch.ts` | Client-side trigram search — pg_trgm parity (same trigrams, Jaccard similarity, 0.3 threshold, prefix matches, same ordering) |
| `app/composables/useDictionary.ts` | Loads the snapshot once per session; powers home, browse, autocomplete |
| `app/composables/useStaticWord.ts` | Word detail: static JSON first, live API fallback for post-deploy words, live refresh after reviewer edits |
| `server/utils/proxy.ts` | The `/api/*` → FastAPI proxy (auth + anon cookie + token refresh) |

## Quickstart

```bash
# needs the backend running on :8000 (see ../api)
cp .env.example .env      # fill NUXT_APP_SECRET at minimum
npm install
LUMI_API_BASE_URL=http://localhost:8000 npm run dev
```

## Scripts

| Command | What it does |
|---|---|
| `npm run dev` | Dev server |
| `npm run build` | Export snapshot (`scripts/export-dictionary.mjs`) **then** `nuxt build` (prerenders every word page) |
| `npm run export` | Snapshot only |
| `npm run build:static` | Snapshot + full static generate |

In production (Vercel), `LUMI_API_BASE_URL` must point at the deployed API —
the build snapshots the live dictionary from it. If the API is down during
a build, the previous snapshot is kept and the build still succeeds.

## Docs

- [docs/static-dictionary.md](docs/static-dictionary.md) — the static
  pipeline, freshness model, and deploy checklist
- [docs/CHANGELOG.md](docs/CHANGELOG.md) — version history
- [docs/architecture.md](docs/architecture.md) — app structure

Env vars are documented inline in [.env.example](.env.example).

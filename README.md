# Lumi — Taita Dictionary

A web interface for the digital Taita dictionary: a public, community-built
dictionary of the Taita language (Dawida, Sagala, Kasighau) with Swahili and
English translations.

**Live:** <https://kitaita.vercel.app>

This repo is a monorepo:

| Folder | What's in it | Docs |
|---|---|---|
| [`api/`](api/) | FastAPI backend — words, senses, translations, examples, variations, relationships; auth (JWT + Google OAuth); suggestions + votes; admin surface | [`api/README.md`](api/README.md) · [`api/docs/`](api/docs/) |
| [`web/`](web/) | Nuxt 4 frontend — the site you see at kitaita.vercel.app | [`web/README.md`](web/README.md) · [`web/docs/`](web/docs/) |

Since the static-dictionary release, the public site is **static-first**: the
whole dictionary is exported into static JSON at deploy time, word pages are
pre-rendered to static HTML, and search runs in the browser with
pg_trgm-equivalent ranking. Anonymous traffic is served from the CDN and
never touches the backend. See
[`web/docs/static-dictionary.md`](web/docs/static-dictionary.md) for the full
pipeline.

## How it's deployed

```
Neon Postgres ── Render (FastAPI, api/) ── Vercel (Nuxt, web/) ── CDN
                                                  │
        deploy-time: `npm run build` snapshots the whole dictionary
        from the API into static JSON + prerendered word pages
```

| Piece | Host | Free tier notes |
|---|---|---|
| Frontend | Vercel | Deploys on every push to `master`. Static HTML + JSON serve from the CDN; only write actions (`/api/*`) invoke serverless functions. |
| Backend | Render | FastAPI service. Handles auth, suggestions, votes, admin, and the `GET /api/export/dictionary` bulk dump the frontend snapshots at deploy. |
| Database | Neon (Postgres 14+, `pg_trgm`) | The only persistent state. |

## Deployment instructions

You only do the full setup below once. After that, **pushing to `master`
triggers Vercel to rebuild the frontend automatically** (Render redeploys
api/ when its code changes too — point both at this repo, or push api/
changes before web/ ones).

### 0. Prerequisites

- Postgres 14+ with the `pg_trgm` extension for local dev (see
  [`api/docs/getting-started.md`](api/docs/getting-started.md))
- Node 20+ (web/) and Python 3.11+ (api/)

### 1. Database — Neon

1. Create a project at <https://neon.tech> and copy the pooled connection
   string (it looks like
   `postgresql+asyncpg://user:pass@host/db?sslmode=require` — swap the
   scheme from `postgresql://`).
2. Enable the extension: in the Neon SQL editor run
   `CREATE EXTENSION IF NOT EXISTS pg_trgm;` (once).

### 2. Backend — Render

1. **New → Web Service**, connected to this repo with **Root Directory =
   `api`**.
2. Build: `pip install -e .` — Start:
   `uvicorn app.main:app --host 0.0.0.0 --port 8000`
   (Render's health check pings `/api/health`).
3. Environment variables (full reference in
   [`api/docs/configuration.md`](api/docs/configuration.md)):

   | Var | Value |
   |---|---|
   | `DATABASE_URL` | the Neon string from step 1 |
   | `JWT_SECRET` | `python -c "import secrets; print(secrets.token_hex(32))"` |
   | `CORS_ORIGINS` | `https://kitaita.vercel.app,http://localhost:3000` |
   | `FRONTEND_URL` | `https://kitaita.vercel.app` |
   | `APP_ENV` | `production` |
   | `GOOGLE_OAUTH_CLIENT_ID` / `GOOGLE_OAUTH_CLIENT_SECRET` | from Google Cloud Console (optional) |
   | `SMTP_*` | for password-reset email (optional — see [`api/docs/email.md`](api/docs/email.md)) |

4. Run migrations once (Render shell or locally against the Neon URL):
   `alembic upgrade head`
5. Bootstrap the first admin: register via the API, then
   `UPDATE users SET role='admin' WHERE email='you@example.com';`

### 3. Frontend — Vercel

1. **New Project → Import** this repo with **Root Directory = `web`**;
   Vercel auto-detects Nuxt (`vercel.json` sets the framework preset).
2. Environment variables (`web/.env.example` is the annotated template):

   | Var | Value |
   |---|---|
   | `LUMI_API_BASE_URL` | `https://your-api.onrender.com` — **used at deploy time** by `scripts/export-dictionary.mjs` to snapshot the dictionary |
   | `NUXT_APP_SECRET` | `openssl rand -hex 32` (seals the session cookie; separate from the JWT secret) |
   | `NUXT_OAUTH_GOOGLE_CLIENT_ID` / `NUXT_OAUTH_GOOGLE_CLIENT_SECRET` | from Google Cloud Console (optional) |

3. Deploy. The build runs `npm run build`, which first snapshots the whole
   dictionary from your Render API (`GET /api/export/dictionary`, one
   request, ~6 DB queries) into `public/dictionary/`, then prerenders every
   word page as static HTML.
4. Smoke test the deployment:

   ```bash
   curl https://kitaita.vercel.app/api/health          # via the proxy → Render
   curl https://kitaita.vercel.app/dictionary/manifest.json   # {"total": N, ...}
   curl -s https://kitaita.vercel.app/words/mlima | grep -i mlima  # static HTML
   ```

### 4. Keeping the dictionary fresh

The static snapshot is as fresh as the last deploy. After reviewers accept
suggestions or import words, **redeploy the frontend** (an empty commit is
enough — Vercel's "Redeploy" button works too). Words that slip in between
deploys still work fine: their pages fall back to the live API until the
next deploy folds them into the snapshot.

### Local development

```bash
# api/ — see api/docs/getting-started.md for the full walkthrough
pip install -e ".[dev]" && ./dev_server.sh --local --init && ./dev_server.sh --local

# web/ — needs the backend running on :8000
npm install && LUMI_API_BASE_URL=http://localhost:8000 npm run dev
```

Docs index: [`api/docs/README.md`](api/docs/README.md) (backend) ·
[`web/README.md`](web/README.md) (frontend, incl. the static dictionary
pipeline).

## License

MIT — see [LICENSE](LICENSE).

---

Built with assistance from GLM (Z.ai).

# Deployment

> **This is a stub.** The user owns the full deployment story — see the
> note at the bottom.

This doc covers what the backend needs from a hosting environment, so
you can plan a deployment. The actual step-by-step for specific hosts
(Render, Fly, Railway, your own VPS) is being written as a separate
deployment guide at the repo root.

## What the backend needs

### Runtime

- **Python 3.11+**
- **FastAPI + Uvicorn** (installed via `pip install -e .`)
- **Postgres 14+** reachable over TCP, with the `pg_trgm` extension
  enabled (the migrations create it; some managed Postgres providers
  need it enabled via a dashboard toggle)

### Process model

A single Uvicorn process can handle moderate traffic. For more, run
multiple Uvicorn workers behind a load balancer (Render does this
automatically when you set the start command).

The in-memory rate limiters (suggestions, password-reset) are
per-process — if you scale to multiple workers, the limits are
per-worker, not global. This is fine for v1 (single Render free tier
instance). For multi-worker, you'd need Redis — not currently
supported.

### Persistent storage

The Postgres database is the only persistent state. The backend has no
local filesystem dependencies (the `EMAIL_LOG_FILE` is a dev-mode thing,
not for prod). So you can run stateless workers and let the load balancer
route anywhere.

## Environment variables

These must be set on the host (Render env vars, Fly secrets, etc.).
See [configuration.md](configuration.md) for the full reference.

### Required

| Var | Why |
|---|---|
| `DATABASE_URL` | Where to find Postgres. Format: `postgresql+asyncpg://user:pass@host:port/db?sslmode=require` |
| `JWT_SECRET` | Any random 32+ char string. **Generate a new one per environment.** |
| `CORS_ORIGINS` | The frontend's origin(s), comma-separated. Must include the deployed frontend URL. |
| `FRONTEND_URL` | Used in password-reset email links. Set to the deployed frontend URL. |
| `APP_ENV` | `production` |

### Required for password reset to actually send email

| Var | Why |
|---|---|
| `SMTP_HOST` | SMTP server hostname (e.g. `smtp.sendgrid.net`) |
| `SMTP_USERNAME` | SMTP auth username (e.g. `apikey` for SendGrid) |
| `SMTP_PASSWORD` | SMTP auth password (or API key) |
| `SMTP_FROM` | Sender address (must be on a verified domain) |
| `SMTP_PORT` | Usually `587` |
| `SMTP_USE_TLS` | Usually `true` |

See [email.md](email.md) for provider-specific setup (Gmail, SendGrid,
Resend, Mailgun).

### Required for Google OAuth to work

| Var | Why |
|---|---|
| `GOOGLE_OAUTH_CLIENT_ID` | From Google Cloud Console |

### Optional

| Var | Default | Notes |
|---|---|---|
| `JWT_ALGORITHM` | `HS256` | Don't change unless you know what you're doing |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `30` | |
| `GOOGLE_OAUTH_CLIENT_SECRET` | `""` | Only needed for the deprecated server-side auth flow |
| `EMAIL_LOG_FILE` | `""` | **Leave empty in prod** — test tokens would leak |

## Pre-deploy checklist

- [ ] Postgres provider chosen (Neon, Supabase, Render Postgres, RDS, etc.)
- [ ] `DATABASE_URL` set with `?sslmode=require` if needed
- [ ] `pg_trgm` extension enabled (run `CREATE EXTENSION IF NOT EXISTS pg_trgm;` once via psql)
- [ ] Migrations applied: `DATABASE_URL=... alembic upgrade head`
- [ ] First admin bootstrapped (register via API, then `UPDATE users SET role='admin' WHERE email='...'`)
- [ ] `JWT_SECRET` generated (not `change-me`)
- [ ] `CORS_ORIGINS` includes the frontend URL
- [ ] `FRONTEND_URL` matches the deployed frontend
- [ ] SMTP provider configured and tested
- [ ] `EMAIL_LOG_FILE` empty (or you'll leak tokens)
- [ ] `APP_ENV=production`

## Post-deploy smoke test

After the deploy is live:

```bash
# 1. Health check
curl https://your-api.example.com/api/health
# {"status":"ok"}

# 2. Readiness check (DB reachable)
curl https://your-api.example.com/api/health/ready
# {"status":"ok","database":"connected"}

# 3. Auth smoke test
ADMIN_EMAIL='admin@your-domain.com' ADMIN_PASSWORD='AdminPass12345!' \
    BASE_URL=https://your-api.example.com \
    ./test_api_endpoints.sh
# → 22 PASS

# 4. Full lifecycle test (use KEEP_USER=1 if you don't want to delete the test user)
KEEP_USER=1 ADMIN_EMAIL='admin@your-domain.com' ADMIN_PASSWORD='AdminPass12345!' \
    BASE_URL=https://your-api.example.com \
    ./test_full_api.sh
# → 79 PASS
```

If any of those fail, check the host's logs.

## Where this doc is thin (intentional)

The user said they'll write a separate deployment-instructions doc at
the repo root. This doc is just the env-var reference for the backend —
the actual step-by-step (Render dashboard clicks, Neon project setup,
DNS records, etc.) is being written separately.

Future plans the user mentioned:
- Maybe a "edit when you launch" desktop application that prompts for
  names, tags, deployment config — would replace the manual env-var
  setup with a wizard. That's a future project, not a current feature.

For now, see:
- [configuration.md](configuration.md) — every env var
- [email.md](email.md) — SMTP provider setup
- [getting-started.md](getting-started.md) — local setup (most of
  which mirrors prod setup)
- The repo root — for the upcoming dedicated deployment guide

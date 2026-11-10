# Configuration

Every env var the backend reads, with default, required-vs-optional, and
what breaks if you get it wrong. The source of truth is
[`app/config.py`](../app/config.py) — this doc is derived from it.

## How config is loaded

The backend uses `pydantic-settings`, which reads in this order (later
wins):

1. The class defaults in `app/config.py`
2. A `.env` file in the working directory (if present)
3. Actual environment variables (highest priority)

So you can:
- Put long-term defaults in a `.env` file (gitignored — don't commit secrets)
- Override per-run with env vars: `JWT_SECRET=secret ./dev_server.sh --local`
- Override per-deploy with the host's env var UI (Render, Neon, etc.)

### The `.env` file

If you put a `.env` file in the `api/` directory:

```bash
# .env (don't commit this — add to .gitignore)
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/lumi_test
JWT_SECRET=your-actual-secret-not-change-me
SMTP_HOST=smtp.gmail.com
SMTP_USERNAME=you@gmail.com
SMTP_PASSWORD=your-app-password
FRONTEND_URL=https://lumi.example.com
```

…pydantic-settings will pick it up automatically. This is the cleanest
way to avoid typing env vars every time you start the backend.

### A sample `.env.example`

Copy this to `.env` and fill in your values:

```bash
# ── Database ───────────────────────────────────────────────
# Local Postgres (dev):
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/lumi_test
# Neon (prod):
# DATABASE_URL=postgresql+asyncpg://user:pass@ep-xxx.us-east-2.aws.neon.tech/lumi?sslmode=require

# ── JWT ────────────────────────────────────────────────────
# CHANGE THIS IN PROD. Any random 32+ char string works.
JWT_SECRET=change-me-to-a-real-secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=30

# ── Google OAuth ────────────────────────────────────────────
# From Google Cloud Console → APIs & Services → Credentials → OAuth 2.0 Client ID
GOOGLE_OAUTH_CLIENT_ID=
GOOGLE_OAUTH_CLIENT_SECRET=

# ── Email (SMTP) ────────────────────────────────────────────
# Leave SMTP_HOST empty for dev mode (emails logged to stdout + EMAIL_LOG_FILE)
SMTP_HOST=
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_FROM=noreply@lumi.taita
SMTP_USE_TLS=true

# ── Email log file (dev-mode capture) ───────────────────────
# If set (and SMTP_HOST is empty), each email is also appended as a JSON line here.
# Lets test scripts capture real password-reset tokens without SMTP.
EMAIL_LOG_FILE=/tmp/lumi-test-emails.log

# ── Frontend URL ────────────────────────────────────────────
# Used to build absolute links in emails (e.g. password reset link)
FRONTEND_URL=http://localhost:3000

# ── CORS ────────────────────────────────────────────────────
# Comma-separated list of allowed origins
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# ── App ────────────────────────────────────────────────────
APP_ENV=development
```

---

## Reference

### Database

#### `DATABASE_URL`

The SQLAlchemy async URL for Postgres. Format:
`postgresql+asyncpg://<user>:<password>@<host>:<port>/<dbname>`

| | |
|---|---|
| Default | `postgresql+asyncpg://localhost/Lumi` |
| Required | Yes — the engine is created at import time; if this is missing or malformed, `from app.main import app` fails |
| What breaks if wrong | The backend won't start. The error is usually `Could not parse SQLAlchemy URL from given URL string` |

For Neon (prod), append `?sslmode=require`:
```
postgresql+asyncpg://user:pass@ep-xxx.us-east-2.aws.neon.tech/lumi?sslmode=require
```

For local dev, the `lumi_test` DB is created by `dev_server.sh --local
--init` (or manually via `psql`).

### JWT

#### `JWT_SECRET`

The HS256 secret used to sign all JWTs (access, refresh, password-reset).

| | |
|---|---|
| Default | `change-me` |
| Required | **Yes in prod** — keep it a secret, any random 32+ char string |
| What breaks if wrong | Anyone who knows the secret can mint tokens for any user. Don't commit a real one. |

Generate one with:
```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
# or
openssl rand -base64 48
```

The test scripts use `change-me` (the default) so they work out of the
box. In prod, override this on the host (Render env var, etc.).

#### `JWT_ALGORITHM`

| | |
|---|---|
| Default | `HS256` |
| Required | No |
| Notes | HS256 = symmetric. The same secret signs and verifies. Fine for v1 (single server). For RS256/ES256 (asymmetric), you'd need a public/private keypair and a different verifier — not currently supported. |

#### `ACCESS_TOKEN_EXPIRE_MINUTES`

| | |
|---|---|
| Default | `30` |
| Required | No |

How long access tokens live. After expiry, the frontend's auto-refresh
interceptor calls `/api/auth/refresh` to get a new pair.

#### `REFRESH_TOKEN_EXPIRE_DAYS`

| | |
|---|---|
| Default | `30` |
| Required | No |

How long refresh tokens live. After this, the user has to log in again.

### Google OAuth

#### `GOOGLE_OAUTH_CLIENT_ID`

| | |
|---|---|
| Default | `""` (empty) |
| Required | Only if you want Google sign-in to work |
| What breaks if wrong | `POST /api/auth/oauth/google` returns 503 `"Google OAuth is not configured on the server."` |

Get this from Google Cloud Console → APIs & Services → Credentials →
Create OAuth 2.0 Client ID. The format is
`<numeric>-<random>.apps.googleusercontent.com`.

This same value is used by the frontend (to initialize Google Identity
Services) — it's safe to expose to the browser. The secret (next) is
not.

#### `GOOGLE_OAUTH_CLIENT_SECRET`

| | |
|---|---|
| Default | `""` (empty) |
| Required | No (we use ID-token verification, not the server-side auth flow, so the secret isn't strictly needed) |
| Notes | If you want to support the deprecated server-side auth flow, set this. Otherwise leave empty. |

### Email (SMTP)

See [email.md](email.md) for the full guide, including Gmail app
passwords and SendGrid setup.

#### `SMTP_HOST`

| | |
|---|---|
| Default | `""` (empty) |
| Required | No — empty = dev mode |
| What breaks if wrong | If you set this to a non-empty value, the backend will try to send real email via `aiosmtplib`. If the host is unreachable, the `send_email()` function logs a warning but doesn't raise — so password-reset still returns 200, but no email gets delivered. |

When empty (or whitespace-only), emails go to stdout AND (if
`EMAIL_LOG_FILE` is set) the log file. This is dev mode.

#### `SMTP_PORT`

| | |
|---|---|
| Default | `587` |
| Required | No |
| Notes | 587 = STARTTLS (most common). 465 = SMTPS (implicit TLS — set `SMTP_USE_TLS=false` for that, since `aiosmtplib` treats `start_tls` separately). 25 = plain (insecure, don't use). |

#### `SMTP_USERNAME` / `SMTP_PASSWORD`

| | |
|---|---|
| Default | `""` (empty) |
| Required | No — if both are empty, no auth is attempted (some internal SMTP relays don't need auth) |

For Gmail, use an App Password (not your regular password). See
[email.md](email.md) for the setup.

#### `SMTP_FROM`

| | |
|---|---|
| Default | `noreply@localhost` |
| Required | No, but **set this in prod** — otherwise your emails come from `noreply@localhost`, which most SMTP providers reject |

The sender address. Should match a verified sender on your SMTP
provider (Gmail: your Gmail address; SendGrid: a sender-verified
domain).

#### `SMTP_USE_TLS`

| | |
|---|---|
| Default | `true` |
| Required | No |
| Notes | When `true`, `aiosmtplib` negotiates STARTTLS after connecting. Set to `false` for SMTPS (port 465, implicit TLS) or for plain (insecure, don't). |

### Email log file

#### `EMAIL_LOG_FILE`

| | |
|---|---|
| Default | `""` (empty) |
| Required | No |
| What breaks if wrong | If the path is unwritable, `send_email()` logs a warning but doesn't raise. Emails still go to stdout. |

When set (and `SMTP_HOST` is empty), each email sent in dev mode is
appended as a JSON line:

```json
{"to":"alice@example.com","subject":"Lumi — Password reset","body":"...","html":"...","ts":1731345218.04}
```

The test scripts read this file to capture real password-reset tokens
without needing SMTP. See [email.md](email.md).

Ignored in SMTP mode — real email delivery is the source of truth, and
writing to a log file in prod would be misleading (and a privacy concern).

### Frontend URL

#### `FRONTEND_URL`

| | |
|---|---|
| Default | `http://localhost:3000` |
| Required | No for dev; yes for prod |
| What breaks if wrong | Password-reset emails contain a link to `<FRONTEND_URL>/reset-password?token=<jwt>`. If this points at the wrong place, users click the link and end up on the wrong frontend. |

No trailing slash — the backend strips one if present.

### CORS

#### `CORS_ORIGINS`

| | |
|---|---|
| Default | `http://localhost:5173` (Vite dev server default) |
| Required | No for dev; yes for prod |
| Notes | Comma-separated list. The frontend's origin must be in this list or browsers will block the requests. |

For the Nuxt frontend (`web/` subfolder), the default is
`http://localhost:3000`. Add it:

```
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

For prod, add your Netlify/Vercel URL.

### App

#### `APP_ENV`

| | |
|---|---|
| Default | `development` |
| Required | No |
| Notes | When set to `development`, `app/db.py` enables SQLAlchemy query logging (`echo=True`). Set to `production` for prod. |

### Test harness only

These are read by `scripts/run_local_api.py` (the in-memory launcher) —
not by the backend itself.

#### `LUMI_HARNESS_FIRST_USER_ROLE`

| | |
|---|---|
| Default | `admin` |
| Required | No |
| Notes | Set to `user` (or `reviewer`) to disable the "first registered user becomes admin" behavior. Useful for testing the `test_full_api.sh` harness-admin auto-promote flow against the in-memory launcher. |

### Test scripts only

These are read by the test scripts (`test_api_endpoints.sh`,
`test_full_api.sh`, `dev_server.sh`) — not by the backend.

| Var | Default | Used by |
|---|---|---|
| `BASE_URL` | `http://localhost:8000` | Both test scripts — API base URL |
| `JWT_SECRET` | `change-me` | Both test scripts — fallback for minting a reset token if `EMAIL_LOG_FILE` is unavailable |
| `EMAIL_LOG_FILE` | `/tmp/lumi-test-emails.log` | Both test scripts — where to read real reset tokens from |
| `EMAIL_DOMAIN` | `example.com` | Both test scripts — domain for test emails |
| `KEEP_USER` | `0` | `test_full_api.sh` — set to `1` to skip account deletion (debugging) |
| `SKIP_RESET` | `0` | `test_full_api.sh` — set to `1` to skip the password-reset/confirm step |
| `ADMIN_EMAIL` + `ADMIN_PASSWORD` | — | `test_full_api.sh` — existing admin credentials (alternative to harness auto-admin) |
| `ADMIN_BOOTSTRAP` | `0` | `test_full_api.sh` — set to `1` to skip promote/demote entirely |
| `LUMI_TEST_DB` | `lumi_test` | `test_full_api.sh` — DB name for the harness-admin auto-promote via psql |
| `LOCAL_DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/lumi_test` | `dev_server.sh` — override for `--local` mode |

---

## What's NOT configurable

A few things are hardcoded (not env vars) by design:

| What | Where | Why |
|---|---|---|
| Password-reset token expiry (1 hour) | `app/security.py` (`PASSWORD_RESET_TOKEN_EXPIRE_SECONDS = 3600`) | Should rarely change; making it an env var invites misconfiguration |
| Suggestion auto-promote threshold (7 days, 3 net votes, 2 non-anon upvotes) | `app/promote.py` | Same |
| Anon rate limits (5 suggestions/hour/session, 10/hour/IP, 15/hour/registered user, 3/hour/email for password reset) | `app/anon.py` | Same |
| Anonymized email placeholder pattern | `app/routes/auth.py` (`deleted+<uuid>@anon.lumi`) | Should match what the frontend expects |
| Default role for new users | `app/routes/auth.py` (`'user'`) | Should never change without a migration |

If you need to change any of these, edit the source. They're not env
vars because the contract says they shouldn't be tuned per-deploy.

## See also

- [email.md](email.md) — the SMTP providers (Gmail, SendGrid, etc.) with concrete setup
- [deployment.md](deployment.md) — what to set on Render/Netlify
- [authentication.md](authentication.md) — how `JWT_SECRET` is used
- [`app/config.py`](../app/config.py) — the actual source of truth

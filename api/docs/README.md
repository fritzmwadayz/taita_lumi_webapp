# Lumi API documentation

Welcome. This folder is the long-form documentation for the backend
(`api/`) subfolder of the Lumi project. The Nuxt frontend lives in the
sibling `web/` folder; deployment instructions for both live at the repo
root and in a future dedicated deployment guide.

## Start here

If you're new to the codebase, read these in order:

1. **[Getting started](getting-started.md)** — install Postgres, install
   Python deps, run migrations, start the server, hit `/api/health`. Covers
   the Fedora-specific gotchas (postgresql-setup, peer auth, pg_hba.conf).
2. **[Architecture](architecture.md)** — 10-minute overview of how the
   pieces fit together: routes → deps → models → db, the audit log, the
   suggestion lifecycle, the in-memory test launcher.
3. **[Authentication](authentication.md)** — the JWT model, role hierarchy
   (`user < reviewer < admin`), how to bootstrap the first admin, the
   password-reset flow, account deletion.
4. **[Testing](testing.md)** — the three test modes: 235 Python unit tests,
   the 22-step auth smoke test, the 79-step full lifecycle test. Plus
   `dev_server.sh`, the launcher that ties them together.

## Reference

When you're looking something up rather than reading top-to-bottom:

- **[API reference](api-reference.md)** — every endpoint with method, path,
  auth requirement, request/response examples, and status codes. Examples
  use real Taita dictionary words (`mlima` = mountain, `kuja` = to come, etc.).
- **[Configuration](configuration.md)** — every env var with default,
  required-vs-optional, and what breaks if you get it wrong. Includes a
  sample `.env` block.
- **[Email](email.md)** — dev-mode email capture (no SMTP needed) and real
  SMTP setup for Gmail / SendGrid / Resend / Mailgun.
- **[Deployment](deployment.md)** — short. The user (you) owns the full
  deployment story; this is just a stub pointing at what env vars each host
  needs.
- **[CHANGELOG](CHANGELOG.md)** — what changed in each version.

## Suggested reading order by role

**New contributor** — start at getting-started, then architecture, then
testing. Skip straight to running `./test_full_api.sh` once your local
Postgres is up.

**Frontend dev consuming the API** — start at the API reference. Skim
authentication for the JWT + roles model. The configuration doc tells you
what env vars the frontend Nitro proxy needs to know about (basically:
none — the frontend just talks to `/api/*` through the proxy).

**Ops / deploy** — configuration and email are the deep ones. Deployment
is intentionally thin; the user is writing a separate deployment guide.

## What's NOT in these docs

- **Frontend code** — that's in `web/`, with its own docs.
- **Database schema migrations** — those are in `alembic/versions/`, each
  with an inline docstring explaining what it adds. Read them in order.
- **Deployment to specific hosts** — that's the user's separate doc.
- **The lexicon.db import** — the CLI in `app/cli/import_data.py` has its
  own `--help` output. Not a typical contributor path.

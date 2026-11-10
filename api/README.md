# Lumi API

FastAPI backend for the **Lumi** dictionary — a public, community-built
dictionary of the Taita language.

This is the `api/` subfolder of the larger Lumi monorepo. The sibling
`web/` subfolder contains the Nuxt frontend; deployment instructions for both
live at the repo root and (eventually) in a dedicated deployment guide.

## What's here

- **FastAPI** app with async SQLAlchemy 2 + asyncpg + Postgres 14+
- **JWT auth** (access + refresh) with role hierarchy: `user < reviewer < admin`
- **Google OAuth** sign-in (ID token exchange)
- **Password reset** via email + **email sending** (`aiosmtplib`, with a dev-mode log-file sink for testing without SMTP)
- **Words, senses, translations, examples, variations, relationships** —
  the word graph that makes up the dictionary
- **Suggestions + votes** — community-driven corrections with auto-promotion
  after a voting threshold
- **Admin surface** — user role/block management, word hide/merge, audit log

## Quickstart

```bash
# 1. Set up local Postgres (Fedora: see docs/getting-started.md for the full walkthrough)
sudo systemctl enable --now postgresql
sudo -u postgres psql -c "ALTER USER postgres WITH PASSWORD 'postgres';"

# 2. Install backend deps (in a venv)
pip install -e ".[dev]"

# 3. Create the test DB + run migrations
./dev_server.sh --local --init

# 4. Start the backend
./dev_server.sh --local
# → Uvicorn running on http://0.0.0.0:8000

# 5. In another terminal, run the full end-to-end test suite
./test_full_api.sh
# → 79 PASS, 0 FAIL
```

If any of those steps fail, **read [`docs/getting-started.md`](docs/getting-started.md)**
— it covers the Fedora-specific gotchas (postgresql-setup --initdb, peer vs
password auth, pg_hba.conf) and the admin-bootstrap workflow.

## Documentation

All long-form docs live in [`docs/`](docs/). The index is at
[`docs/README.md`](docs/README.md) — start there.

| File | What's in it |
|---|---|
| [docs/getting-started.md](docs/getting-started.md) | Local setup walkthrough (Postgres, deps, migrations, first run) |
| [docs/api-reference.md](docs/api-reference.md) | Every endpoint with examples and role requirements |
| [docs/authentication.md](docs/authentication.md) | JWT model, roles, password reset, OAuth, account lifecycle |
| [docs/architecture.md](docs/architecture.md) | Routes → deps → models → db; audit log; suggestion lifecycle |
| [docs/testing.md](docs/testing.md) | The 3 test modes (unit / smoke / full lifecycle) + the dev_server launcher |
| [docs/configuration.md](docs/configuration.md) | Every env var with defaults and what breaks if you get it wrong |
| [docs/email.md](docs/email.md) | Dev-mode email capture + real SMTP setup (Gmail, SendGrid, etc.) |
| [docs/deployment.md](docs/deployment.md) | Production deployment (stub — full deploy docs live elsewhere) |
| [docs/CHANGELOG.md](docs/CHANGELOG.md) | Version history |

## Stack

- Python 3.11+
- FastAPI 0.115+, Uvicorn
- SQLAlchemy 2.0 (async) + asyncpg + Alembic for migrations
- Pydantic v2 + pydantic-settings
- python-jose (HS256 JWT) + passlib with bcrypt
- aiosmtplib for email
- google-auth for OAuth ID token verification
- pytest + pytest-asyncio + httpx for tests

## License

MIT — see the repo root for the full text.

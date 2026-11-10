# Getting started

This walks through setting up the backend on a fresh Fedora install (the
OS we've actually tested). For Ubuntu/macOS, the commands are similar — see
the platform-specific notes inline. If you hit a snag, jump to
[Troubleshooting](#troubleshooting) at the bottom.

> **Time budget:** about 20 minutes if Postgres is already installed; 35
> minutes from scratch. Most of that is Postgres setup — the Python side
> is one `pip install`.

## 1. Prerequisites

### Python 3.11+

```bash
python3 --version
# Python 3.12.16  ✓
```

If you're on 3.10 or older, install 3.11+ (Fedora: `sudo dnf install python3.12`;
Ubuntu: `sudo apt install python3.11`; macOS: `brew install python@3.12`).

### PostgreSQL 14+

The backend uses Postgres 14+ features (gen_random_uuid, JSONB, pg_trgm).
Most distros ship 14+ by default; if you're on something ancient, upgrade.

Check if it's installed:

```bash
psql --version
# psql (PostgreSQL) 18.6  ✓
```

If not installed, install the server + client:

```bash
# Fedora
sudo dnf install postgresql postgresql-server

# Ubuntu / Debian
sudo apt install postgresql postgresql-contrib

# macOS (Homebrew)
brew install postgresql@16
```

### Other tools

- `curl` — for the test scripts (always present)
- `python3` — used by the test scripts for JSON parsing (always present)
- `git`, `make` — standard dev tools

## 2. Set up Postgres (the Fedora gotchas)

This is the step that bit us. On Fedora, `dnf install postgresql-server`
**does not** initialize the data directory or start the service. You have
to do both manually.

### 2a. Initialize the database cluster

```bash
# Check if /var/lib/pgsql/data exists and is initialized
sudo ls /var/lib/pgsql/data/PG_VERSION 2>/dev/null \
  && echo "already initialized" \
  || echo "needs initdb"
```

If it needs initdb:

```bash
sudo postgresql-setup --initdb
```

If `postgresql-setup` complains that `/var/lib/pgsql/data exists`, the
directory is there but empty or corrupt. Back it up and re-init:

```bash
sudo mv /var/lib/pgsql/data /var/lib/pgsql/data.bak.$(date +%s)
sudo postgresql-setup --initdb
```

### 2b. Start the service

```bash
sudo systemctl enable --now postgresql
sudo systemctl status postgresql
# Active: active (running) ✓
```

If the service still fails, check the journal:

```bash
sudo journalctl -xeu postgresql --no-pager | tail -40
```

Look for `FATAL: data directory ... does not exist` (re-run initdb) or
`FATAL: lock file "postmaster.pid" already exists` (a stale lock — remove
the file: `sudo rm /var/lib/pgsql/data/postmaster.pid`).

### 2c. Set a password for the `postgres` role

Fedora's default `pg_hba.conf` uses peer auth for local connections, but
the backend connects over TCP (which requires a password). Set one:

```bash
sudo -u postgres psql -c "ALTER USER postgres WITH PASSWORD 'postgres';"
```

### 2d. Allow TCP password auth (if needed)

If step 2c didn't take (you still get `authentication failed` over TCP),
edit `pg_hba.conf`:

```bash
# Find the file
sudo -u postgres psql -tAc 'SHOW hba_file'
# /var/lib/pgsql/data/pg_hba.conf

# Change the host lines from peer/ident to scram-sha-256
sudo sed -i 's/^\(host\s\+all\s\+all\s\+127.0.0.1\/32\s\+\)ident\|peer/\1scram-sha-256/' /var/lib/pgsql/data/pg_hba.conf
sudo sed -i 's/^\(host\s\+all\s\+all\s\+::1\/128\s\+\)ident\|peer/\1scram-sha-256/' /var/lib/pgsql/data/pg_hba.conf
sudo systemctl restart postgresql
```

### 2e. Verify

```bash
sudo -u postgres psql -c '\l'
# Should list: postgres, template0, template1
```

And test the password-based connection the backend will use:

```bash
PGPASSWORD=postgres psql -h localhost -U postgres -c 'SELECT 1'
#  ?column?
# ----------
#         1
```

If that works, you're done with Postgres setup. The actual `lumi_test`
database is created by `dev_server.sh --local --init` in step 4 below.

## 3. Install the backend dependencies

```bash
cd /path/to/Lumi/website/api

# Create a venv (recommended)
python3 -m venv .venv
source .venv/bin/activate

# Install the backend in editable mode + dev extras
pip install -e ".[dev]"

# Verify
python -c "import fastapi, sqlalchemy, jose, passlib, aiosmtplib; print('all imports OK')"
# all imports OK  ✓
```

The `[dev]` extra pulls in `pytest`, `pytest-asyncio`, `httpx`, `ruff`.

## 4. Create the test database + run migrations

```bash
./dev_server.sh --local --init
```

What this does:
1. Connects to the maintenance `postgres` DB via `psql`
2. `CREATE DATABASE lumi_test` if it doesn't exist
3. Runs `alembic upgrade head` to apply all 6 migrations

If you see `→ Done. Re-run without --init to start the server.`, you're
set. If you see the preflight error message (Postgres not running, no
password, etc.), go back to step 2.

### Manual alternative

If `dev_server.sh --local --init` doesn't work for some reason, do it by
hand:

```bash
sudo -u postgres psql -c "CREATE DATABASE lumi_test;"
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/lumi_test \
    alembic upgrade head
```

## 5. Start the backend

```bash
./dev_server.sh --local
```

This launches uvicorn with:
- `SMTP_HOST=""` — emails logged to stdout, not sent
- `EMAIL_LOG_FILE=/tmp/lumi-test-emails.log` — also captured as JSON lines (so test scripts can read reset tokens)
- `JWT_SECRET=test-secret-for-dev-only` — matches the test scripts' default
- `FRONTEND_URL=http://localhost:3000` — for reset links

You should see:

```
→ Mode: local Postgres
  DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/lumi_test
  Email log:    /tmp/lumi-test-emails.log
  JWT secret:   tes*** (test script must match this)
  ...

INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

Leave that terminal open. In another terminal, hit the health endpoint:

```bash
curl http://localhost:8000/api/health
# {"status":"ok"}  ✓
```

And visit the interactive API docs (FastAPI auto-generates these):

```
http://localhost:8000/docs
```

## 6. Run the test suite

With the backend still running in terminal 1, in terminal 2:

```bash
cd /path/to/Lumi/website/api

# The full lifecycle test — 79 steps, all 30+ endpoints
./test_full_api.sh
```

The first time you run this, it will:
1. Register a "harness-admin" user (which is just a regular `user` against
   real Postgres, not auto-promoted like in the in-memory launcher)
2. Detect that the harness-admin can't access `/api/admin/stats` (403)
3. Try `sudo -u postgres psql -d lumi_test -c "UPDATE users SET role='admin' ..."` — type your Fedora password
4. Re-login to get a fresh admin-scoped token
5. Run through all 8 lifecycle stages (anon → user → reviewer → admin → demote → delete)

You should see:

```
Total: 79 passed, 0 failed
```

See [testing.md](testing.md) for the full breakdown of test modes.

## 7. Bootstrap the first admin (manual alternative)

If you'd rather not let the test script auto-promote via sudo, do it
manually once:

```bash
# Register a normal user via the API (so they have a proper password hash)
curl -X POST -H 'Content-Type: application/json' \
  -d '{"email":"admin@example.com","password":"AdminPass12345!","display_name":"Admin"}' \
  http://localhost:8000/api/auth/register

# Promote them via psql
sudo -u postgres psql -d lumi_test \
  -c "UPDATE users SET role='admin' WHERE email='admin@example.com';"

# Verify
sudo -u postgres psql -d lumi_test \
  -c "SELECT email, role, (password_hash IS NOT NULL) AS has_password FROM users WHERE email='admin@example.com';"
#       email       | role  | has_password
# -------------------+-------+--------------
#  admin@example.com | admin | t

# Then run the test with those credentials
ADMIN_EMAIL='admin@example.com' ADMIN_PASSWORD='AdminPass12345!' ./test_full_api.sh
```

See [authentication.md](authentication.md) for the full role model and why
the first admin must be bootstrapped via the DB (not via an API call —
which admin would call it?).

## 8. What to read next

- [architecture.md](architecture.md) — how the routes/deps/models/db pieces fit together
- [api-reference.md](api-reference.md) — every endpoint
- [authentication.md](authentication.md) — JWT, roles, password reset, OAuth
- [testing.md](testing.md) — the 3 test modes in detail

## Troubleshooting

### `psql: error: connection to server at "localhost" (...) failed: Connection refused`

Postgres service isn't running. See [step 2b](#2b-start-the-service).

### `FATAL: password authentication failed for user "mwadime"`

You're trying to connect as your Linux user, but Postgres doesn't have a
role for them. Either:
- Connect as the `postgres` OS user: `sudo -u postgres psql ...`
- Create a role matching your username: `sudo -u postgres createuser --superuser $USER`

### `FATAL: password authentication failed for user "postgres"`

The `postgres` role has no password set (Fedora default). See
[step 2c](#2c-set-a-password-for-the-postgres-role).

### `psql: error: FATAL: database "lumi_test" does not exist`

You skipped the init step. Run `./dev_server.sh --local --init`.

### `alembic upgrade head` fails with `Could not parse SQLAlchemy URL`

The `DATABASE_URL` env var isn't set. `dev_server.sh` sets it for you, but
if you're running alembic manually, prefix it:

```bash
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/lumi_test \
    alembic upgrade head
```

### The test script returns `HTTP 000000`

That's curl's "could not connect" code — the backend isn't running. Start
it in another terminal: `./dev_server.sh --local`.

### The test script says `harness-admin is NOT an admin (got 403 on /api/admin/stats)`

The harness-admin auto-promote step failed (sudo not available, or DB
name wrong). Either let the script auto-promote via sudo, or follow the
manual admin-bootstrap steps in [section 7 above](#7-bootstrap-the-first-admin-manual-alternative).

### `pip install -e .` succeeds but `import sqlalchemy` fails

You're in the wrong venv, or you don't have one. Re-run:

```bash
source .venv/bin/activate
pip install -e ".[dev]"
python -c "import sqlalchemy; print('ok')"
```

### `ModuleNotFoundError: No module named 'app'`

You're not in the `api/` directory. The `app` package is at `api/app/`.
`cd` there, or set `PYTHONPATH=/path/to/api`.

### `alembic` command not found

The `alembic` script is installed in your venv's `bin/`. If you're using
a venv, activate it first. If not, install with `pip install alembic`.

### `Test script can't read reset token from email log file`

The backend isn't writing to `EMAIL_LOG_FILE`. Make sure you started it
with `dev_server.sh --local` (which sets `EMAIL_LOG_FILE`), not bare
`uvicorn app.main:app` (which doesn't). Or set it manually:

```bash
EMAIL_LOG_FILE=/tmp/lumi-test-emails.log ./dev_server.sh --local
```

### Still stuck

Read the test scripts' header comments (`test_full_api.sh`, `dev_server.sh`) —
they're long and explain every option. Then check [testing.md](testing.md).

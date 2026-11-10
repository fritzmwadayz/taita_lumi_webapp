# Testing

Three modes, in order of weight:

| Mode | What it tests | When to use | Time |
|---|---|---|---|
| **Python unit tests** | Every endpoint's logic with mocked DB | After every code change | ~13s |
| **`test_api_endpoints.sh`** | The auth + profile surface end-to-end | Smoke-testing a fresh deploy | ~5s |
| **`test_full_api.sh`** | Every endpoint, full lifecycle | Pre-release / after big changes | ~10s |

Plus the launcher: **`dev_server.sh`** ties them all together by starting
the backend in dev mode with email capture, so the test scripts can read
real password-reset tokens from a file instead of needing SMTP.

## 1. Python unit tests

235 tests in `tests/`, all using `AsyncMock` for the DB session. They run
without Postgres installed — the only env var needed is `DATABASE_URL` (any
syntactically valid URL works, since the engine is created at import time
but never actually connects).

### Running

```bash
# Activate your venv first
source .venv/bin/activate

# Run the full suite
DATABASE_URL=postgresql+asyncpg://x:x@localhost/x pytest -q

# Run a single file
DATABASE_URL=postgresql+asyncpg://x:x@localhost/x pytest tests/test_password_reset.py -v

# With coverage
pip install pytest-cov
DATABASE_URL=postgresql+asyncpg://x:x@localhost/x pytest --cov=app --cov-report=term-missing
```

### What's covered

| File | Tests | Surface |
|---|---|---|
| `test_auth.py` | register, login, refresh, me, OAuth (mocked Google token) | Auth |
| `test_password_reset.py` | request (with rate limit, OAuth-only, blocked user), confirm (valid, expired, email-mismatch, blocked) | Password reset |
| `test_profile_endpoints.py` | email change (success, wrong pw, OAuth-only, duplicate, idempotent), account delete (success, wrong pw, OAuth-only, unique placeholder per user), connected accounts | Profile mgmt |
| `test_email.py` | dev mode (log file capture, stdout), SMTP mode (aiosmtplib invocation), failure swallowing, whitespace-only SMTP_HOST | Email |
| `test_audit_log.py` | `_map_action()` pure function, `_build_audit_entry()`, the audit-log endpoint filter (both bare and dotted action forms) | Audit log |
| `test_phase_b_audit_writes.py` | Audit rows written by PATCH /admin/users, POST /admin/suggestions/{id}/decide, POST /admin/words/{id}/hide, POST /admin/words/merge | Audit writes |
| `test_words*.py`, `test_suggestions.py`, `test_votes.py`, `test_admin.py`, etc. | Each surface's endpoints + edge cases | All other endpoints |
| `test_phase_*.py` | Phase-specific tests from earlier development milestones | Historical |

### Patterns

The tests follow a consistent pattern (see `test_auth.py` for the
canonical example):

```python
class MockResult:
    """Mock SQLAlchemy Result that returns a single scalar or None."""
    def __init__(self, value=None):
        self._value = value
    def scalar_one_or_none(self):
        return self._value

@pytest.fixture
async def mock_db():
    """Mock AsyncSession. Tests configure return values per-test."""
    session = AsyncMock()
    session.execute = AsyncMock(return_value=MockResult(None))
    return session

@pytest.fixture
async def client_with_mock_db(mock_db):
    """HTTP client with the DB dependency overridden."""
    async def override_get_db():
        yield mock_db
    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
```

Each test then configures `mock_db.execute` to return the right value
for that scenario (a real user, None, a blocked user, etc.), and asserts
on the HTTP response. Real bcrypt + real JWT — we want those code paths
to actually run.

### Why mock the DB instead of using a real one?

- **Speed**: 235 tests in 13s vs. ~5 minutes against real Postgres (each
  test would need a transaction rollback)
- **Isolation**: tests don't depend on the DB state
- **No fixtures**: no test-database creation, no migrations to run
- **CI-friendly**: works on any machine with Python, no Postgres install

The tradeoff: the mocks don't catch DB-level issues (constraint
violations, cascade deletes, trigram search behavior). For those, use
`test_full_api.sh` against a real Postgres.

## 2. `test_api_endpoints.sh` — auth + profile smoke test

22 steps covering the auth + profile + password-reset surface. Use this
when you want a quick "is the deploy up?" smoke test.

### Running

```bash
# Terminal 1: backend running
./dev_server.sh --local

# Terminal 2: the smoke test
./test_api_endpoints.sh
```

### What it covers

```
 1. GET  /                                  health
 2. POST /api/auth/register                  signup
 3. POST /api/auth/login
 4. GET  /api/auth/me
 5. PATCH /api/auth/me                       display name
 6. PATCH /api/auth/me/password
 7. GET  /api/auth/me/connected-accounts
 8. PATCH /api/auth/me/email                 email change
 9. POST /api/auth/password-reset/request
10. POST /api/auth/password-reset/confirm   real token from EMAIL_LOG_FILE
11. DELETE /api/auth/me                     soft-delete
12. POST /api/auth/login                    should now fail
```

Each step prints `PASS` or `FAIL` with the HTTP status. Stops on first
failure unless you set `fail_fast=0` at the top of the script.

### Key feature: real reset tokens via `EMAIL_LOG_FILE`

Step 10 reads the password-reset token from `/tmp/lumi-test-emails.log`
(the file `dev_server.sh` writes to in dev mode). This tests the full
request→email→confirm flow end-to-end, with the actual JWT the backend
issued — not a fake one minted client-side.

If the log file isn't being written (e.g. you're testing against a
remote deploy without `EMAIL_LOG_FILE` set), the script falls back to
minting a token with `JWT_SECRET` (which must match the backend's).

See [email.md](email.md) for the dev-mode capture flow.

## 3. `test_full_api.sh` — full lifecycle test

79 steps covering **every endpoint**, walking through the full account
lifecycle with role changes:

```
STAGE A — Anonymous browsing          (no auth)
STAGE B — Sign up + user-mode actions (role='user')
STAGE B.5 — Suggestion + vote (user-mode)
STAGE C — Promote to reviewer          (role='reviewer') + reviewer-only actions
STAGE D — Promote to admin             (role='admin')   + admin-only actions
STAGE E — Demote back to user          (verify role reduction works)
STAGE F — Password reset + email change (the recovery flow)
STAGE G — Delete account               (soft-delete / anonymize)
STAGE H — Verify the account is gone
```

### Running

```bash
# Terminal 1: backend running
./dev_server.sh --local

# Terminal 2: the full test
./test_full_api.sh
```

### Admin bootstrap modes

The test needs an admin to exercise promote/demote. Three strategies:

| Mode | How to enable | What happens |
|---|---|---|
| **Harness auto-admin** (default) | Just run `./test_full_api.sh` with no env vars | Registers a "harness-admin" user, detects they're not an admin (against real Postgres), tries `sudo -u postgres psql -d lumi_test -c "UPDATE users SET role='admin' ..."` — type your sudo password. Re-logs in to get a fresh admin-scoped token. |
| **Existing admin** | Set `ADMIN_EMAIL=...` and `ADMIN_PASSWORD=...` | Logs in as the existing admin and uses their token. Use this when you've already bootstrapped an admin manually. |
| **Skip promote/demote** | Set `ADMIN_BOOTSTRAP=1` | Skips stages C, D, E entirely. Only tests that a regular user CAN'T call those endpoints (403). Use in CI without sudo. |

### The harness-admin auto-promote flow

When you run `./test_full_api.sh` against real Postgres with no admin
env vars, here's what happens in stage B.0b:

```
── B.0b Login as harness-admin ──
  PASS: POST /api/auth/login (admin) (HTTP 200)
  FAIL: harness-admin is NOT an admin (got 403 on /api/admin/stats)
    body: {"detail":"Admin only"}

  Note: harness auto-admin only works against the in-memory launcher.
  Against a real Postgres, the first registered user is role='user'.
  Trying to auto-promote via psql...

[sudo] password for mwadime:
  PASS: auto-promoted harness-admin via psql (db: lumi_test)
  PASS: harness-admin is now an admin (verified after re-login)
```

If auto-promote fails (no sudo, wrong DB name), the script prints clear
instructions and continues in bootstrap mode (skipping only the
admin-only paths; everything else still runs):

```
  Auto-promote failed. sudo/psql not available non-interactively,
  or the DB name is wrong (default: lumi_test — override with LUMI_TEST_DB).

  To fix this manually, run this in another terminal:
    sudo -u postgres psql -d lumi_test -c "UPDATE users SET role='admin' WHERE email='admin+...@example.com';"

  Then re-run with: ADMIN_EMAIL='admin+...@example.com' ADMIN_PASSWORD='AdminPass12345!' ./test_full_api.sh

  Continuing in ADMIN_BOOTSTRAP mode (skipping promote/demote/admin-only endpoints).
```

### Env vars

| Var | Default | Purpose |
|---|---|---|
| `BASE_URL` | `http://localhost:8000` | API base URL |
| `JWT_SECRET` | `change-me` | Fallback for minting a reset token if `EMAIL_LOG_FILE` is unavailable |
| `EMAIL_LOG_FILE` | `/tmp/lumi-test-emails.log` | Where the backend writes dev-mode emails; the script reads reset tokens from here |
| `KEEP_USER` | `0` | Set to `1` to skip the account-deletion step (debugging) |
| `SKIP_RESET` | `0` | Set to `1` to skip the password-reset/confirm step |
| `EMAIL_DOMAIN` | `example.com` | Domain for the test user's email |
| `ADMIN_EMAIL` + `ADMIN_PASSWORD` | — | Existing admin credentials (alternative to harness auto-admin) |
| `ADMIN_BOOTSTRAP` | `0` | Set to `1` to skip promote/demote entirely |
| `LUMI_TEST_DB` | `lumi_test` | DB name for the harness-admin auto-promote via psql |

### Common failure modes

| Symptom | Cause | Fix |
|---|---|---|
| `HTTP 000000` on every request | Backend not running | Start it: `./dev_server.sh --local` |
| `harness-admin is NOT an admin (got 403)` | Real Postgres: first user is not auto-admin | Let the auto-promote via sudo run (type your password), or pre-bootstrap an admin and pass `ADMIN_EMAIL`/`ADMIN_PASSWORD` |
| `POST /api/admin/suggestions/{id}/decide → 403 "Admin only"` | Cascade from above — the admin token isn't actually admin | Same fix as above |
| `GET /api/words/{id} → 307` | The previous `POST /api/words` failed (403), so the word doesn't exist; the GET redirects to slug-search | Same fix as above |
| `POST /api/auth/password-reset/confirm → 400 Invalid or expired reset token` | The email log file wasn't being written, so the script minted a token with the wrong `JWT_SECRET` | Start the backend with `dev_server.sh --local` (which sets `EMAIL_LOG_FILE`), or set `JWT_SECRET` to match |

## 4. `dev_server.sh` — the launcher

Ties the test scripts together with the backend. Sets up dev-mode env
vars (SMTP_HOST empty, EMAIL_LOG_FILE, JWT_SECRET, FRONTEND_URL) so the
test scripts work without any configuration.

### Modes

| Flag | What it does | What it needs |
|---|---|---|
| `--local` (default) | Connects to local Postgres | `LOCAL_DATABASE_URL` env or default `postgresql+asyncpg://postgres:postgres@localhost:5432/lumi_test` |
| `--local --init` | One-time setup: creates `lumi_test` DB + runs `alembic upgrade head` | Same + `psql` on PATH |
| `--prod` | Connects to your Neon prod DB. **Prompts `Type 'yes' to continue`.** | `DATABASE_URL` in `.env` or env var |
| `--in-memory` | No Postgres — uses `scripts/run_local_api.py`. Quick smoke tests. | The launcher script (in the deliverable zip under `scripts/`) |

### What it sets

In all modes:
- `SMTP_HOST=""` — emails logged, not sent
- `EMAIL_LOG_FILE=/tmp/lumi-test-emails.log` — captured for test scripts
- `JWT_SECRET=test-secret-for-dev-only` — matches test scripts' default
- `FRONTEND_URL=http://localhost:3000` — for reset links

### Usage

```bash
# One-time: create local test DB + run migrations
./dev_server.sh --local --init

# Start the backend (stays running)
./dev_server.sh --local

# In another terminal: run either test
./test_api_endpoints.sh
./test_full_api.sh

# Or: against the in-memory launcher (no Postgres needed)
./dev_server.sh --in-memory
./test_full_api.sh

# Or: against production (with confirmation prompt)
./dev_server.sh --prod
KEEP_USER=1 ./test_full_api.sh   # don't delete the test account
```

### `--init` preflight checks

`./dev_server.sh --local --init` does a 3-second preflight reachability
check before trying to create the database. If it can't connect, instead
of dumping the raw `psql` error, it prints:

```
ERROR: could not connect to PostgreSQL at: postgresql://postgres:postgres@localhost:5432/postgres

Common causes on a fresh install (Fedora/RHEL):

  1. The server service isn't running.
     Check with:    systemctl status postgresql
     Start with:    sudo systemctl enable --now postgresql

  2. The 'postgres' role has no password set (Fedora default).
     Set one with:  sudo -u postgres psql -c "ALTER USER postgres WITH PASSWORD 'postgres';"

  3. Postgres is on a non-default host/port/user.
     Override with: LOCAL_DATABASE_URL='postgresql+asyncpg://USER:PASS@HOST:PORT/lumi_test' \
                        ./dev_server.sh --local --init
```

See [getting-started.md](getting-started.md) for the full Postgres setup
walkthrough.

## 5. The in-memory launcher

`scripts/run_local_api.py` overrides `get_db` with an in-memory dict-backed
session, so the entire API runs without Postgres. Used by `dev_server.sh
--in-memory` and for the test scripts' own development.

### How it works

- Every SQLAlchemy model is backed by a Python dict (keyed by primary key
  UUID) or list (for `EditLog`, `WordVariation`, `WordRelationship`)
- `execute(stmt)` parses the WHERE clauses (equality, IN, ILIKE, !=, and
  the trigram `%` operator) and filters the in-memory store
- `add(obj)` inserts into the store, sets a UUID + timestamps + sensible
  defaults for NOT NULL fields (so e.g. `Word.status='live'`,
  `User.is_blocked=False`)
- The `selectinload(Word.translations)` pattern is handled by
  pre-populating `word.translations` on each row before returning

### Special test-harness behaviors

- **First registered user is auto-promoted to admin** — override with
  `LUMI_HARNESS_FIRST_USER_ROLE=user`. Lets `test_full_api.sh` exercise
  promote/demote without external DB manipulation against the in-memory
  launcher.
- **CompoundSelect (UNION) queries** are handled by inspecting the inner
  selects' whereclauses (used by `/api/admin/stats`).

See [architecture.md](architecture.md#the-in-memory-test-launcher) for
more.

### Limitations

- No real persistence (state cleared on restart)
- No real constraint enforcement (CHECK, UNIQUE — the dict just lets you
  add duplicates)
- No real trigram search (the `%` operator is treated as "match all"
  — for fuzzy search testing, use real Postgres with pg_trgm)
- No real `server_default` (NOT NULL fields get sensible defaults via
  `_ensure_pk` instead)

For real testing of the database layer, use `--local` (real Postgres).

## When to use which

| Scenario | Use |
|---|---|
| Quick "did I break anything?" after a code change | Python unit tests (`pytest -q`) |
| Smoke-test a fresh deploy | `test_api_endpoints.sh` |
| Pre-release / after big changes | `test_full_api.sh` (against `--local`) |
| No Postgres available (CI without DB service) | `dev_server.sh --in-memory` + `test_full_api.sh` |
| Testing a specific endpoint interactively | FastAPI's `/docs` Swagger UI |
| Testing the DB layer (constraints, trigram, migrations) | Real Postgres via `--local` |

## See also

- [getting-started.md](getting-started.md) — getting Postgres up
- [architecture.md](architecture.md) — how the in-memory launcher works internally
- [email.md](email.md) — the `EMAIL_LOG_FILE` flow
- The header comments in `dev_server.sh`, `test_api_endpoints.sh`, `test_full_api.sh` — exhaustive usage docs

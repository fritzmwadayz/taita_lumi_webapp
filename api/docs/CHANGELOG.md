# Changelog

Notable changes to the backend, in reverse chronological order. For
commit-level history, see `git log`. This doc is user-readable — it
covers feature additions and breaking changes, not refactor commits.

## [Unreleased]

Nothing staged yet.

## [0.2.0] — 2026-11-10

The "auth additions" release. Adds password reset, profile management,
and email sending infrastructure. No DB migrations needed.

### Added

#### Password reset workflow

- `POST /api/auth/password-reset/request` — always returns 200 (anti-enumeration).
  Mints a 1-hour JWT reset token, sends the email, writes an audit row.
  Rate-limited to 3 requests per email per hour.
- `POST /api/auth/password-reset/confirm` — verifies the reset token
  (signature, expiry, type, email match) and sets a new password.
  Returns 400 for invalid/expired tokens, 403 for blocked users, 422
  for short passwords.

See [docs/authentication.md](authentication.md#password-reset) for the
full flow.

#### Profile management

- `PATCH /api/auth/me/email` — change email (requires current password
  verification). Returns 400 for OAuth-only accounts, 401 for wrong
  password, 409 for duplicate email.
- `DELETE /api/auth/me` — soft-delete / anonymize the account. Replaces
  the email with a unique placeholder (`deleted+<uuid>@anon.lumi`),
  nulls out the password and OAuth fields, sets `is_blocked=true`.
  Keeps the user's community contributions (suggestions, words) visible.
- `GET /api/auth/me/connected-accounts` — returns `{google, has_password}`
  so the frontend can show "Connected with Google" badges and hide/show
  the password change form appropriately.

See [docs/authentication.md](authentication.md#account-lifecycle).

#### Email sending infrastructure

- `app/email.py` — async `send_email(to, subject, body, html=None)`
  with two modes:
  - **Dev mode** (`SMTP_HOST` empty): logs to stdout AND appends to
    `EMAIL_LOG_FILE` as JSON lines (lets test scripts capture real
    password-reset tokens without SMTP)
  - **SMTP mode** (`SMTP_HOST` set): sends via `aiosmtplib` with
    STARTTLS. Failures are swallowed (logged as warnings, never
    raised) so the calling flow always succeeds.
- New env vars: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`,
  `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_USE_TLS`, `EMAIL_LOG_FILE`,
  `FRONTEND_URL`.
- New dependency: `aiosmtplib>=3.0.0`.

See [docs/email.md](email.md).

#### New audit log actions

Added to the public dotted action namespace:

- `user.password_reset_request` — password-reset email requested
- `user.password_reset` — password successfully reset via token
- `user.email_change` — email address changed
- `user.delete` — account deleted (anonymized)

The `GET /api/admin/audit-log?action=...` filter now ORs the dotted
form with the bare-verb form, so filtering by `user.password_reset`
finds rows stored as `user.password_reset` (already-dotted) — the
previous behavior only matched bare verbs and silently dropped these.

#### In-memory test launcher

- `scripts/run_local_api.py` — overrides `get_db` with an in-memory
  dict-backed session. Backs every model (User, Word, Suggestion,
  Vote, EditLog, etc.) with Python dicts/lists. Lets the full test
  suite run without Postgres.
- First registered user is auto-promoted to admin via the
  `LUMI_HARNESS_FIRST_USER_ROLE` env var (default `admin`). Override
  with `user` to disable.

See [docs/architecture.md](architecture.md#the-in-memory-test-launcher).

#### Test scripts

- `test_api_endpoints.sh` — 22-step auth+profile smoke test. Reads
  real reset tokens from `EMAIL_LOG_FILE`.
- `test_full_api.sh` — 79-step full lifecycle test covering every
  endpoint, walking through anon → user → reviewer → admin → demote
  → delete. Includes the harness-admin auto-promote via `sudo -u
  postgres psql` flow for real Postgres (or `LUMI_HARNESS_FIRST_USER_ROLE`
  for the in-memory launcher).
- `dev_server.sh` — launcher with `--local`, `--prod`, `--in-memory`,
  `--init` modes. Sets up dev-mode env vars (`SMTP_HOST=""`,
  `EMAIL_LOG_FILE`, `JWT_SECRET`, `FRONTEND_URL`) so the test scripts
  work without any configuration. Includes a 3-second preflight
  reachability check for `--local --init` with clear error messages
  for common Postgres setup issues.

See [docs/testing.md](testing.md).

#### Tests

235 Python unit tests (was 183). New test files:

- `tests/test_password_reset.py` — 19 tests covering the request
  endpoint (rate limit, OAuth-only, blocked user, email enumeration
  prevention) and the confirm endpoint (valid, expired, email-mismatch,
  blocked, short password, missing fields). Includes a full
  request→email→confirm flow.
- `tests/test_profile_endpoints.py` — 16 tests for `PATCH /me/email`
  (success, lowercasing, wrong password, OAuth-only, duplicate,
  same-email idempotency, invalid format), `DELETE /me` (success,
  wrong password, OAuth-only, unique placeholder per user), and
  `GET /me/connected-accounts` (password-only, oauth, oauth-only,
  requires auth, real-JWT end-to-end).
- `tests/test_email.py` — 15 tests (was 9): dev-mode log file
  capture, multiple-email accumulation, SMTP mode (aiosmtplib
  invocation, no-auth-when-credentials-blank, no-TLS-when-disabled),
  failure swallowing, whitespace-only `SMTP_HOST` treated as unset.
- `tests/test_audit_log.py` — 2 new tests for the dotted-action
  filter behavior (already-dotted rows + legacy bare-verb rows both
  findable).

### Changed

- `app/routes/auth.py` module docstring updated to list all 14
  endpoints (was 6).
- `app/routes/admin.py` audit-log filter now ORs dotted and bare-verb
  action forms.
- `app/config.py` gained SMTP + frontend URL + email log file settings.
- `app/security.py` gained `create_password_reset_token()` and
  `PASSWORD_RESET_TOKEN_EXPIRE_SECONDS`.

### Notes on interpretation

Two interpretations called out in the contract:

1. **`EditLog.entity_id` is `NOT NULL`** in the schema, but the contract
   suggested `entity_id=null` for unknown emails in the password-reset
   request. Resolution: only write the audit row when a real user is
   found. For unknown emails, no row is written (the 200 response is
   unchanged). Documented in the route docstring.

2. **`User.email` is `NOT NULL UNIQUE`**, but the contract suggested
   `user.email = null` for account deletion. Resolution: replace with
   a unique placeholder (`deleted+<uuid>@anon.lumi`) — the real email
   is discarded, the user is effectively anonymized. Documented in the
   route docstring.

## [0.1.0] — 2026-11-07

Initial baseline. All endpoints that existed before the auth additions.

### Endpoints

- `GET /` — root metadata
- `GET /api/health` — liveness
- `GET /api/health/ready` — readiness
- `GET /api/words` — paginated list with filters
- `POST /api/words` — create word (reviewer+)
- `GET /api/words/{slug_or_id}` — full word detail
- `PATCH /api/words/{word_id}` — edit word (reviewer+)
- `POST /api/words/{word_id}/examples` — append example (reviewer+)
- `POST /api/words/{word_id}/senses` — add sense (reviewer+)
- `PATCH /api/senses/{sense_id}` — edit sense (reviewer+)
- `GET /api/search` — fuzzy search (pg_trgm)
- `POST /api/auth/register` — email + password signup
- `POST /api/auth/login` — email + password login
- `POST /api/auth/refresh` — rotate tokens
- `GET /api/auth/me` — current user profile
- `PATCH /api/auth/me` — update display name
- `PATCH /api/auth/me/password` — change password
- `GET /api/auth/me/stats` — contribution stats
- `POST /api/auth/logout` — client-side logout
- `POST /api/auth/oauth/google` — Google ID token exchange
- `GET /api/suggestions` — list suggestions
- `POST /api/suggestions` — create suggestion (anon or contributor)
- `GET /api/suggestions/{suggestion_id}` — get suggestion
- `POST /api/suggestions/{suggestion_id}/decide` — reviewer accept/reject
- `POST /api/suggestions/{suggestion_id}/vote` — cast/change vote
- `DELETE /api/suggestions/{suggestion_id}/vote` — remove vote
- `GET /api/admin/stats` — dashboard summary
- `GET /api/admin/users` — list users
- `PATCH /api/admin/users/{user_id}` — change role / block
- `POST /api/admin/suggestions/{suggestion_id}/decide` — admin decide
- `PATCH /api/admin/words/{word_id}` — admin edit word
- `POST /api/admin/words/{word_id}/hide` — soft-delete word
- `POST /api/admin/words/merge` — merge two words
- `GET /api/admin/audit-log` — query audit trail

### Stack

- FastAPI 0.115+, Uvicorn
- SQLAlchemy 2.0 (async) + asyncpg + Postgres 14+ + Alembic
- Pydantic v2 + pydantic-settings
- python-jose (HS256 JWT) + passlib + bcrypt
- google-auth for OAuth ID token verification

### Migrations (Alembic)

Six migrations applied to date:
- `0001_initial` — all 10 tables + extensions (pg_trgm)
- `0002_rename_contributor_to_reviewer` — role name change
- `0003_word_slugs` — add `slug` column to words
- `0004_split_variations_relationships` — split the legacy
  `word_relations` table into `word_variations` (definitional) and
  `word_relationships` (typed)
- `0005_senses` — add the `senses` table; backfill existing translations
  and examples to a default sense per word
- `0006_rename_glosses_to_translations` — rename the `glosses` table to
  `translations` (more intuitive for non-lexicographers)

### Tests

183 Python unit tests covering every endpoint with mocked DB
(AsyncMock). No integration tests against real Postgres in this
release — the in-memory launcher and end-to-end test scripts come in
0.2.0.

# Authentication

The backend uses **JWT-based auth** with a 3-tier role hierarchy. This
doc covers the token lifecycle, the role model, the password-reset flow,
Google OAuth, and how to bootstrap the first admin (which has to be done
via the DB — there's no API endpoint for it, by design).

## The JWT model

Two token types, both signed with the same `JWT_SECRET` using `HS256`
(per [configuration.md](configuration.md)):

| Token type | Purpose | Lifetime | Where sent |
|---|---|---|---|
| **Access** | Sent on every authenticated request via `Authorization: Bearer <token>` | 30 minutes | Always |
| **Refresh** | Exchange for a new access token via `POST /api/auth/refresh` | 30 days | Only when the access token expires |

Both tokens are **stateless** — there's no server-side blacklist. After
logout, the client just discards them; they keep working until they
expire. (A blacklist could be added later if needed, but it's not worth
the complexity for v1.)

### Token payload

**Access token:**
```json
{
  "sub": "<user_id>",
  "email": "mwadime@example.com",
  "role": "user",
  "type": "access",
  "exp": 1731345218,
  "iat": 1731343418
}
```

**Refresh token:**
```json
{
  "sub": "<user_id>",
  "type": "refresh",
  "exp": 1733935418,
  "iat": 1731343418
}
```

Notice the refresh token carries minimal info — just the user ID. The
access token carries the role too, because the role check on every
request reads from the token (no DB hit needed).

### Refresh rotation

Every call to `POST /api/auth/refresh` issues a **new pair** — both a
new access token AND a new refresh token. The old refresh token is
invalidated implicitly because:

- The next time the old refresh token is used, the user lookup succeeds
  (the row is the same), so it would technically still work
- BUT: if the user has been blocked, deleted, or had their email changed,
  the lookup fails and refresh fails

So refresh rotation is a soft form of invalidation — the old token works
until something material changes about the user. This is intentional and
simplifies the stateless model.

## The role hierarchy

```
user       <       reviewer       <       admin
```

- **user** — registered contributor. Can submit suggestions, vote on
  others' suggestions, manage their own profile (display name, password,
  email, account deletion).
- **reviewer** — can additionally create words directly (skipping the
  suggestion queue), edit word fields, add examples/senses, decide
  suggestions.
- **admin** — can additionally manage users (promote/demote/block),
  hide/merge words, view the audit log, view dashboard stats.

### What each role CAN'T do

| Action | user | reviewer | admin |
|---|---|---|---|
| POST /api/words (create word directly) | ❌ | ✓ | ✓ |
| PATCH /api/words/{id} | ❌ | ✓ | ✓ |
| POST /api/words/{id}/examples | ❌ | ✓ | ✓ |
| POST /api/words/{id}/senses | ❌ | ✓ | ✓ |
| PATCH /api/senses/{id} | ❌ | ✓ | ✓ |
| POST /api/suggestions/{id}/decide (reviewer) | ❌ | ✓ | ✓ |
| GET /api/admin/stats | ❌ | ❌ | ✓ |
| GET /api/admin/users | ❌ | ❌ | ✓ |
| PATCH /api/admin/users/{id} (promote/demote/block) | ❌ | ❌ | ✓ |
| POST /api/admin/words/merge | ❌ | ❌ | ✓ |
| POST /api/admin/words/{id}/hide | ❌ | ❌ | ✓ |
| GET /api/admin/audit-log | ❌ | ❌ | ✓ |

### The role-in-token gotcha

The role is encoded in the JWT **at issue time**. If you promote a user
from `user` to `reviewer` via `PATCH /api/admin/users/{id}`, their
existing access token still says `role: "user"` and will keep saying
that until it expires (30 minutes) or they re-login.

This is by design — it means the auth check is a single token decode, no
DB hit. But it has a UX implication:

> After promoting/demoting a user, tell them to log out and log back in
> (or just wait up to 30 minutes for their access token to expire).

The `test_full_api.sh` script handles this automatically — after each
promote/demote, it does a fresh login to get a token with the new role.

## Bootstrapping the first admin

There's no API endpoint to create the first admin — by design, because
which admin would call it? You bootstrap via the DB.

### The clean way (recommended)

Register a normal user via the API (which sets the bcrypt password hash
correctly), then promote them via `psql`:

```bash
# 1. Register a normal user via the API
curl -X POST -H 'Content-Type: application/json' \
  -d '{"email":"admin@example.com","password":"AdminPass12345!","display_name":"Admin"}' \
  http://localhost:8000/api/auth/register

# 2. Promote them via psql
sudo -u postgres psql -d lumi_test \
  -c "UPDATE users SET role='admin' WHERE email='admin@example.com';"

# 3. Verify
sudo -u postgres psql -d lumi_test -c \
  "SELECT email, role, (password_hash IS NOT NULL) AS has_password FROM users WHERE email='admin@example.com';"
```

### The dirty way (don't do this)

You could INSERT directly into the users table, but you'd need to
generate a bcrypt hash yourself. Don't bother — the API registration
endpoint does it correctly with the same `passlib` config the auth flow
uses.

```sql
-- ❌ Bad: this row has no password_hash, so login will fail
INSERT INTO users (email, role) VALUES ('admin@example.com', 'admin');
```

### The auto-promote way (test script only)

The `test_full_api.sh` script does the bootstrap for you when run
against real Postgres: it registers a "harness-admin" user, detects
they're not an admin, and runs `sudo -u postgres psql -d lumi_test -c
"UPDATE users SET role='admin' ..."` to promote them. See
[testing.md](testing.md).

The in-memory test launcher (`scripts/run_local_api.py`) takes a
different shortcut: the **first** registered user is auto-promoted to
admin via the `LUMI_HARNESS_FIRST_USER_ROLE` env var (default `admin`).
That's a test-harness convenience — real Postgres doesn't do this.

## Password reset

The password-reset flow is a 2-step process: request a reset link by
email, then confirm with the token from that email.

### Step 1: request

```bash
curl -X POST -H 'Content-Type: application/json' \
  -d '{"email":"mwadime@example.com"}' \
  http://localhost:8000/api/auth/password-reset/request
```

The endpoint always returns 200, even if the email doesn't exist —
otherwise an attacker could enumerate accounts by observing which emails
return 200 vs. 404.

If the email **does** exist:
1. A 1-hour JWT is minted with `type='reset'`, `sub=<user_id>`, `email=<user_email>`
2. An email is sent to the user with a link: `<FRONTEND_URL>/reset-password?token=<jwt>`
3. An audit-log row is written: `action='user.password_reset_request'`

If the email doesn't exist (or the user is blocked, or OAuth-only): no
email, no audit row, still 200.

### Step 2: confirm

```bash
curl -X POST -H 'Content-Type: application/json' \
  -d '{"token":"<jwt from email>","new_password":"BrandNew12345!"}' \
  http://localhost:8000/api/auth/password-reset/confirm
```

The endpoint:
1. Decodes the JWT, verifies signature + expiry + `type == 'reset'`
2. Looks up the user by `sub`
3. Checks the email in the token still matches the user's current email
   (invalidates the token if the user changed their email after the
   reset was requested — a safety net)
4. Hashes the new password, updates `user.password_hash`
5. Writes audit-log row: `action='user.password_reset'`

### How to test the reset flow without SMTP

In dev mode (`SMTP_HOST=""`), the email is logged to stdout AND, if
`EMAIL_LOG_FILE` is set, appended as a JSON line:

```json
{"to":"mwadime@example.com","subject":"Lumi — Password reset","body":"...token=...","ts":1731345218}
```

The test scripts read the latest "Password reset" line from that file and
extract the token. See [email.md](email.md) for the full setup.

### Token invalidation

Reset tokens are stateless JWTs, so they can't be truly invalidated
server-side after use. The 1-hour expiry is the primary safety net.
The email-mismatch check is the secondary safety net: if the user
changes their email after requesting a reset, the token becomes invalid
(because the email in the token no longer matches the user's current
email). The error message is the same as for an expired token — the
endpoint doesn't reveal the specific reason.

### Rate limiting

Max 3 reset requests per email per hour. The limiter is in-memory (same
as the suggestion limiter) and keyed by the lowercased email. The 4th
request within an hour returns 429 with a `Retry-After: 3600` header.

## Google OAuth

The backend supports Google sign-in via ID token exchange.

### How it works

1. The frontend obtains a Google ID token via Google Identity Services
   (the `gsi` library shows the "Sign in with Google" button)
2. The frontend POSTs the ID token to `/api/auth/oauth/google`
3. The backend verifies the ID token with Google
   (`id_token.verify_oauth2_token` from `google-auth`):
   - Signature is valid
   - Audience matches `GOOGLE_OAUTH_CLIENT_ID`
   - Token hasn't expired
4. The backend looks up the user by `oauth_provider='google'` + `oauth_subject=<sub>`
5. If not found, tries by email (and links the Google account to the
   existing email-based account)
6. If still not found, creates a new user
7. Returns a JWT pair (same as register/login)

### Configuration

Set these env vars (see [configuration.md](configuration.md)):

```bash
GOOGLE_OAUTH_CLIENT_ID=<your-client-id>.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=<your-client-secret>  # only needed if backend does the exchange
```

The frontend also needs `GOOGLE_OAUTH_CLIENT_ID` (it uses it to initialize
the GIS library). It's safe to expose the client ID to the browser — the
client secret is what's sensitive, and we don't actually need it for
ID-token verification (the backend just verifies the token Google gave
the browser).

### OAuth-only users

Users who sign in via Google but never set a password are "OAuth-only":
their `password_hash` is NULL. They:
- Can log in via Google
- Cannot use `PATCH /api/auth/me/password` (returns 400 `"This account
  uses Google sign-in and has no password set."`)
- Cannot use `PATCH /api/auth/me/email` (returns 400 `"This account
  uses Google sign-in."`)
- Cannot use `DELETE /api/auth/me` (returns 400 `"This account uses
  Google sign-in and has no password."`)

The frontend can detect this case via `GET /api/auth/me/connected-accounts`:

```json
{ "google": true, "has_password": false }
```

…and hide the password change form accordingly.

### Email verification

The backend requires `email_verified=true` in the Google ID token. If
the user's Google email isn't verified, the endpoint returns 400 with
the message `"Google email is not verified. Verify your email with
Google first."`. This prevents account takeover via unverified Google
emails.

## Account lifecycle

### Registration

`POST /api/auth/register` with email + password. The user is created
with `role='user'` and a bcrypt-hashed password. Returns a JWT pair
immediately (no email verification in v1).

### Profile changes

- `display_name` → `PATCH /api/auth/me` (no password required)
- `password` → `PATCH /api/auth/me/password` (requires current password)
- `email` → `PATCH /api/auth/me/email` (requires current password, must
  be unique — 409 if taken)

All three write audit-log rows where applicable:
- Password change: not audited (too noisy)
- Email change: `action='user.email_change'` with `before={email: old}` and `after={email: new}`

### Soft delete

`DELETE /api/auth/me` requires the current password. The account is
**anonymized**, not removed:

| Field | Before | After |
|---|---|---|
| `email` | `mwadime@example.com` | `deleted+<uuid>@anon.lumi` |
| `display_name` | `Mwadime` | `deleted user` |
| `password_hash` | `<bcrypt hash>` | `null` |
| `oauth_provider` | `google` (or null) | `null` |
| `oauth_subject` | `<sub>` (or null) | `null` |
| `is_blocked` | `false` | `true` |

The user's existing suggestions and words **remain visible** — the
`author_display` field on suggestions will now show `"deleted user"`.

The `email` field becomes a unique placeholder rather than NULL because
the DB schema has `email NOT NULL UNIQUE` (and the contract specifies no
migrations for this feature). The placeholder is deterministic per
user_id, so it can't collide and can't be confused with a real email.

After deletion:
- The user's existing JWTs keep working until expiry (stateless)
- The next `/api/auth/me` or `/api/auth/refresh` call returns 403
  (`is_blocked=true`)
- The original email can no longer be used to log in (it no longer
  matches any row)
- The original email becomes available for re-registration (since the
  deleted user now has the placeholder email)

### Hard delete

There's no hard-delete endpoint in v1. If you need to truly remove a
user's row from the DB (e.g. for GDPR compliance), do it via `psql`:

```sql
-- Anonymize first (so suggestions/words don't dangle)
UPDATE users SET display_name='deleted user', password_hash=NULL,
                 oauth_provider=NULL, oauth_subject=NULL, is_blocked=true,
                 email='deleted+' || id::text || '@anon.lumi'
WHERE email='mwadime@example.com';

-- Then optionally delete the row entirely
DELETE FROM users WHERE email='deleted+%@anon.lumi' AND email='mwadime@example.com';
```

But think twice — keeping the anonymized row preserves the audit trail
and the integrity of `created_by_user_id` foreign keys on suggestions and
words.

## See also

- [api-reference.md](api-reference.md) — every auth/profile endpoint with examples
- [configuration.md](configuration.md) — `JWT_SECRET`, `GOOGLE_OAUTH_*`, `FRONTEND_URL`
- [email.md](email.md) — the email-sending infrastructure behind password reset
- [architecture.md](architecture.md) — how `get_current_user` works internally

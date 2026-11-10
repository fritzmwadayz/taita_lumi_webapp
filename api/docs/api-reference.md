# API reference

Every endpoint in the Lumi backend, grouped by surface area. Examples
use mock words mostly Swahili.

## Conventions

- All paths are prefixed with `/api` except the root `/`.
- All request bodies are JSON (`Content-Type: application/json`).
- All responses are JSON.
- Authenticated requests use `Authorization: Bearer <access_token>`.
- Auth requirements are noted per endpoint as one of: **none**, **user**,
  **reviewer**, **admin**. See [authentication.md](authentication.md) for the
  role model.
- Timestamps are ISO-8601 UTC (e.g. `2026-11-10T14:32:18.123456+00:00`).
- UUIDs are returned as strings in JSON.

## Authentication header

For any endpoint marked **user**, **reviewer**, or **admin**:

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

Get the token by registering or logging in. See
[authentication.md](authentication.md) for the JWT lifecycle.

---

## Health

### `GET /`

API metadata. No auth.

**Response (200):**
```json
{
  "name": "Lumi API",
  "version": "0.1.0",
  "docs": "/docs"
}
```

### `GET /api/health`

Liveness check — does not touch the DB. Use this for load balancer health
checks. **none** auth.

**Response (200):**
```json
{ "status": "ok" }
```

### `GET /api/health/ready`

Readiness check — verifies the DB is reachable. **none** auth.

**Response (200):**
```json
{ "status": "ok", "database": "connected" }
```

**Response (200, degraded):**
```json
{ "status": "degraded", "database": "<error message>" }
```

The endpoint always returns 200 — the `status` field tells you whether the
DB is up. Useful for Kubernetes readiness probes that should not restart
the pod on DB outages.

---

## Words

### `GET /api/words`

Paginated list of live words. **none** auth.

**Query params:**

| Param | Type | Default | Notes |
|---|---|---|---|
| `q` | string | — | Fuzzy search by headword (pg_trgm similarity) |
| `pos` | string | — | Filter by part of speech (e.g. `noun`) |
| `dialect` | string | — | Filter by dialect (e.g. `Dawida`) |
| `page` | int | 1 | 1-indexed |
| `size` | int | 20 | Max 100 |

**Example:**
```bash
curl 'http://localhost:8000/api/words?q=mlima&size=5'
```

**Response (200):**
```json
{
  "items": [
    {
      "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
      "slug": "mlima",
      "headword": "mlima",
      "part_of_speech": "noun",
      "noun_class": null,
      "dialect": "Dawida",
      "swahili_translation": "mlima",
      "english_translation": "mountain",
      "has_relations": true
    }
  ],
  "total": 1,
  "page": 1,
  "size": 5,
  "has_next": false
}
```

### `POST /api/words`

Create a live word directly. **reviewer+** auth.

Words created this way get `status='live'`, `source='user'`, and a
provenance `Suggestion` row marked `accepted`. An audit-log row
(`action='create'`) is written.

**Request body:**
```json
{
  "headword": "mlima",
  "part_of_speech": "noun",
  "noun_class": null,
  "dialect": "Dawida",
  "literal_translation": null,
  "morphology_notes": null,
  "swahili_translation": "mlima",
  "english_translation": "mountain",
  "examples": [
    {
      "taita_text": "Mlima u Mwachi unenea kwi vinya.",
      "swahili_text": "Mlima wa Mwachi unenea kwa nguvu.",
      "english_text": "Mount Mwachi stands tall.",
      "source_ref": "field notes, 2024"
    }
  ]
}
```

Only `headword` is required. The first translation pair creates a default
sense (order_index=1); examples are scoped to it.

**Response (201):** Full `WordDetail` shape — see `GET /api/words/{slug_or_id}`.

**Status codes:**
- `201` — created
- `403` — not a reviewer/admin
- `409` — word with the same normalized headword already exists
- `422` — empty headword / validation

### `GET /api/words/{slug_or_id}`

Full word detail. **none** auth. Accepts either the slug (`mlima`) or the
UUID.

**Example:**
```bash
curl http://localhost:8000/api/words/mlima
```

**Response (200):**
```json
{
  "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "slug": "mlima",
  "headword": "mlima",
  "normalized_form": "mlima",
  "part_of_speech": "noun",
  "noun_class": null,
  "dialect": "Dawida",
  "literal_translation": null,
  "morphology_notes": null,
  "senses": [
    {
      "id": "sense-uuid",
      "order_index": 1,
      "part_of_speech": null,
      "definition": null,
      "notes": null,
      "translations": [
        { "id": "t1", "language": "sw", "text": "mlima" },
        { "id": "t2", "language": "en", "text": "mountain" }
      ],
      "examples": [
        {
          "id": "ex1",
          "taita_text": "Mlima u Mwachi unenea kwi vinya.",
          "swahili_text": "Mlima wa Mwachi unenea kwa nguvu.",
          "english_text": "Mount Mwachi stands tall.",
          "source_ref": "field notes, 2024"
        }
      ]
    }
  ],
  "variations": [],
  "relationships": [],
  "relations": [],
  "created_at": "2026-11-10T14:32:18+00:00",
  "created_by_user_id": "user-uuid",
  "reviewed_at": null,
  "reviewed_by_user_id": null
}
```

### `PATCH /api/words/{word_id}`

Edit a word's fields. **reviewer+** auth. Only provided fields are updated.

**Request body** (all optional):
```json
{
  "headword": "mlima",
  "part_of_speech": "noun",
  "noun_class": null,
  "dialect": "Dawida",
  "literal_translation": null,
  "morphology_notes": "Class 3/4 — see Mwagha 2018.",
  "swahili_translation": "mlima",
  "english_translation": "mountain, hill",
  "examples": null
}
```

If `examples` is provided, it **REPLACES** the word's example set: existing
examples not in the list are deleted, examples with a matching `id` are
updated, examples without an `id` are created.

**Response (200):** Updated `WordDetail`.

**Status codes:**
- `200` — updated
- `403` — not a reviewer/admin
- `404` — word not found

### `POST /api/words/{word_id}/examples`

Append a single example to a word. **reviewer+** auth. Skips the
suggestion-vote flow — useful for reviewers who want to add an example
without going through the queue.

**Request body:**
```json
{
  "taita_text": "Ku dilwa ng'alu ni mlu wa mlima.",
  "swahili_text": "Kuenda ng'alu ni juu ya mlima.",
  "english_text": "To go to Ng'alu is to climb the mountain.",
  "source_ref": "field recording, 2024-03-15",
  "sense_id": null
}
```

If `sense_id` is omitted, the word's default sense (order_index=1) is used;
if no senses exist, a default sense is created.

**Response (201):** Updated `WordDetail`.

### `POST /api/words/{word_id}/senses`

Add a new sense to a word. **reviewer+** auth. The new sense gets the next
available `order_index` (e.g. if the word has senses 1 and 2, the new one
becomes 3).

**Request body** (all optional):
```json
{
  "part_of_speech": "noun",
  "definition": "a pile or heap of objects",
  "notes": "Second sense of 'mlima', per Ndingo 2011."
}
```

**Response (201):** Updated `WordDetail`.

### `PATCH /api/senses/{sense_id}`

Edit a sense's fields. **reviewer+** auth. Only provided fields are updated.

**Request body** (all optional):
```json
{
  "order_index": 2,
  "part_of_speech": "noun",
  "definition": "a pile or heap (e.g. of stones, harvested crops)",
  "notes": "Re-ordered — this sense is now sense 2, not 1."
}
```

**Response (200):** Updated `WordDetail` (for the word this sense belongs to).

### `GET /api/search`

Fuzzy search using pg_trgm. **none** auth.

**Query params:**

| Param | Type | Default | Notes |
|---|---|---|---|
| `q` | string | required | Search query (min 2 chars) |
| `page` | int | 1 | 1-indexed |
| `size` | int | 20 | Max 100 |

**Example:**
```bash
curl 'http://localhost:8000/api/search?q=kuja&size=5'
```

**Response (200):**
```json
{
  "items": [
    {
      "id": "word-uuid",
      "slug": "kuja",
      "headword": "kuja",
      "swahili_translation": "kuja",
      "english_translation": "to come",
      "similarity": 1.0
    }
  ],
  "total": 1,
  "page": 1,
  "size": 5
}
```

---

## Auth

### `POST /api/auth/register`

Register a new user with email + password. **none** auth.

Returns a JWT pair immediately (no email verification step in v1). New
users default to `role='user'`.

**Request body:**
```json
{
  "email": "mwadime@example.com",
  "password": "SecurePass12345!",
  "display_name": "Mwadime"
}
```

**Response (201):**
```json
{
  "access_token": "eyJhbGciOi...",
  "refresh_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

**Status codes:**
- `201` — registered
- `409` — email already exists
- `422` — invalid email, short password (< 8 chars)

### `POST /api/auth/login`

Login with email + password. **none** auth.

The same error is returned for "no such email" and "wrong password" to
prevent email enumeration.

**Request body:**
```json
{
  "email": "mwadime@example.com",
  "password": "SecurePass12345!"
}
```

**Response (200):** Same as register — JWT pair.

**Status codes:**
- `200` — logged in
- `401` — incorrect email or password
- `403` — account blocked

### `POST /api/auth/refresh`

Exchange a refresh token for a new access + refresh token (rotation).
**none** auth (the refresh token in the body is the credential).

**Request body:**
```json
{ "refresh_token": "eyJhbGciOi..." }
```

**Response (200):** New JWT pair.

**Status codes:**
- `200` — refreshed
- `401` — invalid/expired refresh token, or user no longer available

### `POST /api/auth/logout`

Logout. **user** auth (but the token is discarded client-side; the
endpoint is essentially a no-op since JWTs are stateless).

Returns 204 No Content. Future versions may add a server-side blacklist
if needed.

### `POST /api/auth/oauth/google`

Login or register with a Google ID token. **none** auth.

The frontend obtains the Google ID token via Google Identity Services
and posts it here. The backend verifies it with Google, then either:
1. Finds an existing user with `oauth_provider='google'` + `oauth_subject=sub`, or
2. Finds an existing user with the same email (and links the Google account), or
3. Creates a new user.

**Request body:**
```json
{ "id_token": "google-id-token-string" }
```

**Response (200):** JWT pair.

**Status codes:**
- `200` — logged in / registered
- `400` — Google email is not verified
- `401` — invalid Google token
- `403` — account blocked
- `503` — Google OAuth not configured on the server (`GOOGLE_OAUTH_CLIENT_ID` empty)

---

## Profile management

### `GET /api/auth/me`

Get the current user's profile. **user** auth.

**Response (200):**
```json
{
  "id": "user-uuid",
  "email": "mwadime@example.com",
  "display_name": "Mwadime",
  "role": "user",
  "created_at": "2026-11-10T14:32:18+00:00",
  "last_seen_at": "2026-11-10T15:00:00+00:00",
  "oauth_provider": null
}
```

Also updates `last_seen_at` (best-effort).

### `PATCH /api/auth/me`

Update the current user's display name. **user** auth. Only
`display_name` is editable here in v1.

**Request body:**
```json
{ "display_name": "Mwadime Mwagha" }
```

**Response (200):** Updated `UserResponse` (same shape as `GET /me`).

### `PATCH /api/auth/me/password`

Change the current user's password. **user** auth. Requires the current
password. OAuth-only users (no `password_hash`) cannot use this endpoint.

**Request body:**
```json
{
  "current_password": "SecurePass12345!",
  "new_password": "EvenMoreSecure12345!"
}
```

**Response (200):**
```json
{ "status": "ok", "message": "Password changed." }
```

**Status codes:**
- `200` — changed
- `400` — OAuth-only account (`"This account uses Google sign-in and has no password set."`)
- `401` — current password incorrect
- `422` — new password < 8 chars

### `PATCH /api/auth/me/email`

Change the current user's email address. **user** auth. Separate from
`PATCH /me` (display name only) to require password verification.

**Request body:**
```json
{
  "new_email": "mwadime.new@example.com",
  "current_password": "SecurePass12345!"
}
```

**Behavior:**
1. Verify current password (401 if wrong)
2. If OAuth-only: 400 `"This account uses Google sign-in."`
3. Lowercase the new email
4. Check for duplicates (409 if another user has this email)
5. Update `user.email`
6. Write audit-log row: `action='user.email_change'`

**Response (200):** Updated `UserResponse` (with the new email).

**Status codes:**
- `200` — email changed
- `400` — OAuth-only account
- `401` — current password incorrect
- `409` — email already taken
- `422` — invalid email format

### `GET /api/auth/me/stats`

Contribution stats for the current user. **user** auth.

**Response (200):**
```json
{
  "words_added": 12,
  "suggestions_submitted": 47,
  "suggestions_accepted": 18,
  "suggestions_open": 21,
  "suggestions_rejected": 8,
  "votes_cast": 132
}
```

### `GET /api/auth/me/connected-accounts`

Show which OAuth providers are linked + whether the user has a password.
**user** auth.

The frontend uses this to show "Connected with Google" badges and to
hide/show the password change form appropriately.

**Response (200):**
```json
{
  "google": false,
  "has_password": true
}
```

### `DELETE /api/auth/me`

Soft-delete / anonymize the current user's account. **user** auth.
Requires the current password. Anonymizes personal data but keeps
contributions visible.

**Request body:**
```json
{ "password": "SecurePass12345!" }
```

**Behavior:**
1. Verify password (401 if wrong)
2. If OAuth-only: 400 `"This account uses Google sign-in and has no password."`
3. Anonymize:
   - `email` → `deleted+<uuid>@anon.lumi` (DB column is `NOT NULL UNIQUE`, so a unique placeholder replaces NULL)
   - `display_name` → `"deleted user"`
   - `password_hash` → `null`
   - `oauth_provider`, `oauth_subject` → `null`
   - `is_blocked` → `true` (prevents any future auth via the same row)
4. Keep all `Suggestion` and `Word` rows (community content remains visible — `author_display` will now show "deleted user")
5. Write audit-log row: `action='user.delete'`
6. Return 204

**Response:** `204 No Content`

**Status codes:**
- `204` — account deleted (anonymized)
- `400` — OAuth-only account
- `401` — password incorrect

**Note:** the user's existing JWTs continue to work until expiry (stateless).
The next `/refresh` or `/me` call will fail because `is_blocked=true`.

---

## Password reset

### `POST /api/auth/password-reset/request`

Request a password reset link. **none** auth. **Always returns 200** —
even if the email doesn't exist — to prevent email enumeration.

**Request body:**
```json
{ "email": "mwadime@example.com" }
```

**Behavior:**
1. Rate limit: max 3 requests per email per hour (429 if exceeded)
2. Look up the user (case-insensitive — emails are lowercased on storage)
3. If found AND not blocked AND has a `password_hash` (not OAuth-only):
   - Generate a 1-hour reset JWT (`type='reset'`, `sub=user_id`, `email=user.email`)
   - Send a reset email to the user containing the frontend reset link
   - Write audit-log row: `action='user.password_reset_request'`
4. If not found, blocked, or OAuth-only: do nothing (still return 200)

**Response (200):**
```json
{
  "status": "ok",
  "message": "If an account exists for that email, a reset link has been sent."
}
```

**Status codes:**
- `200` — always (even if email not found)
- `429` — rate limit exceeded (`Retry-After: 3600` header)
- `422` — invalid email format

The reset link points at `<FRONTEND_URL>/reset-password?token=<jwt>`. In
dev mode (SMTP_HOST empty), the email is logged to stdout and (if
`EMAIL_LOG_FILE` is set) appended as a JSON line — see
[email.md](email.md) for how test scripts capture the token.

### `POST /api/auth/password-reset/confirm`

Verify a reset token and set a new password. **none** auth (the token in
the body is the credential).

**Request body:**
```json
{
  "token": "eyJhbGciOi...",
  "new_password": "BrandNew12345!"
}
```

**Behavior:**
1. Decode the JWT, verify signature + expiry + `type == 'reset'`
2. Look up the user by `sub` (user_id)
3. Verify the user still exists, is not blocked, and the email in the
   token matches the user's current email (invalidates the token if the
   email was changed after the reset was requested)
4. Hash the new password with bcrypt, update `user.password_hash`
5. Write audit-log row: `action='user.password_reset'`

**Response (200):**
```json
{
  "status": "ok",
  "message": "Your password has been reset. Please log in."
}
```

**Status codes:**
- `200` — password reset
- `400` — invalid/expired token, OR email mismatch (same generic message — don't reveal the reason)
- `403` — user is blocked
- `422` — password too short (< 8 chars)

---

## Suggestions

A suggestion is a proposal to add or correct a word, translation,
example, relation, or variation. Suggestions go through the
[community vote flow](architecture.md#suggestion-lifecycle) and can be
auto-promoted after a threshold.

### `GET /api/suggestions`

List suggestions with optional filters. **none** auth (public read). If
the caller is authenticated, `user_vote` is populated per item.

**Query params:**

| Param | Type | Default | Notes |
|---|---|---|---|
| `status` | string | `open` | `open` / `accepted` / `rejected` / `withdrawn` |
| `target_type` | string | — | Filter by target type |
| `page` | int | 1 | 1-indexed |
| `size` | int | 20 | Max 100 |

**Response (200):**
```json
{
  "items": [
    {
      "id": "sugg-uuid",
      "target_type": "new_word",
      "target_id": null,
      "field_path": null,
      "proposed_value": { "headword": "kuja", "swahili_translation": "kuja" },
      "rationale": "Common verb, missing from the dictionary.",
      "status": "open",
      "created_at": "2026-11-10T14:32:18+00:00",
      "created_by_user_id": "user-uuid",
      "author_display": "@Mwadime",
      "upvotes": 2,
      "downvotes": 0,
      "user_vote": null
    }
  ],
  "total": 1,
  "page": 1,
  "size": 20,
  "has_next": false
}
```

### `POST /api/suggestions`

Create a new suggestion. **none** auth — anonymous visitors can suggest
via the `X-Session-Cookie` header (a random UUID the frontend stores in
localStorage). Authenticated contributors get `created_by_user_id` set.

**Request body:**
```json
{
  "target_type": "new_word",
  "target_id": null,
  "field_path": null,
  "proposed_value": {
    "headword": "kuja",
    "part_of_speech": "verb",
    "swahili_translation": "kuja",
    "english_translation": "to come"
  },
  "rationale": "Common verb, missing from the dictionary."
}
```

The shape of `proposed_value` depends on `target_type`:

| `target_type` | `target_id` | `proposed_value` |
|---|---|---|
| `new_word` | null | full new word dict |
| `word` | word UUID | `{ "<field>": "<new value>" }` |
| `translation` | word UUID | `{ "language": "sw"|"en", "text": "...", "sense_id"?: "..." }` |
| `example` | example UUID | `{ "language": "sw"|"en", "text": "..." }` |
| `new_example` | word UUID | `{ "taita_text": "...", "swahili_text"?: "...", "english_text"?: "...", "source_ref"?: "..." }` |
| `variation` | word UUID | `{ "related_word": "<headword|uuid>", "variation_type": "plural" }` |
| `relationship` | word UUID | `{ "related_word": "<headword|uuid>", "relationship_type": "antonym", "direction"?: "bidirectional" }` |

**Response (201):** The created `SuggestionResponse` (with `upvotes=0`,
`downvotes=0`, `user_vote=null`).

**Status codes:**
- `201` — created
- `404` — referenced `target_id` not found
- `409` — `new_word` for a headword that already exists (returns the
  existing word's id in the error detail)
- `422` — invalid `target_type`, missing required field in `proposed_value`

### `GET /api/suggestions/{suggestion_id}`

Get a single suggestion by ID. **none** auth.

**Response (200):** Full `SuggestionResponse` with vote counts.

### `POST /api/suggestions/{suggestion_id}/decide`

Reviewer/admin manually accepts or rejects a suggestion. **reviewer+** auth.

Accepting applies the suggestion to the word graph immediately (same as
auto-promote, but without the voting threshold). Rejecting closes it
without applying. An audit-log row (`action='suggestion.accept'` or
`suggestion.reject`) is written for the decision itself, in addition to
the applied-change log the `_apply_*` helper writes.

**Request body:**
```json
{ "decision": "accept" }
```

**Response (200):**
```json
{
  "id": "sugg-uuid",
  "status": "accepted",
  "decided_at": "2026-11-10T15:00:00+00:00",
  "decided_by": "user-uuid"
}
```

**Status codes:**
- `200` — decided
- `400` — suggestion is already `accepted` or `rejected`
- `404` — suggestion not found
- `422` — `decision` not `accept` or `reject`

---

## Votes

Only authenticated contributors can vote (anon cannot — too easy to game).

### `POST /api/suggestions/{suggestion_id}/vote`

Cast or change a vote. **user** auth. Repeating the same vote removes it
(toggle behavior). After voting, the auto-promote check runs — if the
suggestion meets the threshold, it's accepted and applied.

**Request body:**
```json
{ "vote": "up" }
```

**Response (200):**
```json
{
  "suggestion_id": "sugg-uuid",
  "upvotes": 3,
  "downvotes": 0,
  "user_vote": "up",
  "promoted": false
}
```

**Status codes:**
- `200` — vote cast/changed/removed
- `400` — cannot vote on own suggestion, OR suggestion is not `open`
- `404` — suggestion not found
- `422` — `vote` not `up` or `down`

### `DELETE /api/suggestions/{suggestion_id}/vote`

Remove the current user's vote on a suggestion. **user** auth. Idempotent
(returns 200 even if no vote existed).

**Response (200):** Same shape as POST, with `user_vote=null` and
`promoted=false`.

---

## Admin

All `/api/admin/*` endpoints require the **admin** role. See
[authentication.md](authentication.md#bootstrapping-the-first-admin) for
how to bootstrap the first admin.

### `GET /api/admin/stats`

Dashboard summary. **admin** auth.

**Response (200):**
```json
{
  "total_words": 1248,
  "total_users": 47,
  "total_suggestions": 132,
  "open_suggestions": 21,
  "accepted_suggestions": 87,
  "rejected_suggestions": 24,
  "total_votes": 412,
  "recent_words": [
    {
      "id": "word-uuid",
      "slug": "mlima",
      "headword": "mlima",
      "part_of_speech": "noun",
      "noun_class": null,
      "dialect": "Dawida",
      "swahili_translation": "mlima",
      "english_translation": "mountain",
      "has_relations": true
    }
  ],
  "recent_suggestions": [
    {
      "id": "sugg-uuid",
      "target_type": "new_word",
      "headword": "kuja",
      "status": "open",
      "upvotes": 2,
      "downvotes": 0,
      "created_at": "2026-11-10T14:32:18+00:00"
    }
  ]
}
```

### `GET /api/admin/users`

Paginated list of users. **admin** auth.

**Query params:** `page` (default 1), `size` (default 20, max 100).

**Response (200):**
```json
{
  "items": [
    {
      "id": "user-uuid",
      "email": "mwadime@example.com",
      "display_name": "Mwadime",
      "role": "user",
      "is_blocked": false,
      "created_at": "2026-11-10T14:32:18+00:00",
      "last_seen_at": "2026-11-10T15:00:00+00:00"
    }
  ],
  "total": 47,
  "page": 1,
  "size": 20,
  "has_next": true
}
```

### `PATCH /api/admin/users/{user_id}`

Update a user's role or blocked status. **admin** auth. Cannot modify
your own account (returns 400).

**Request body** (all optional):
```json
{
  "role": "reviewer",
  "is_blocked": false
}
```

Valid roles: `user`, `reviewer`, `admin`.

**Behavior:**
- If only `role` changed: audit-log action = `user.role.change`
- If only `is_blocked` changed to `true`: action = `user.block`
- If only `is_blocked` changed to `false`: action = `user.unblock`
- If both changed: action = `user.role.change` (the more material change)

The `after` payload includes `by_admin: <admin email>` for traceability.

**Response (200):** Updated `AdminUserResponse` (same shape as the list item).

**Status codes:**
- `200` — updated
- `400` — trying to modify your own account
- `404` — user not found
- `422` — invalid role

### `POST /api/admin/suggestions/{suggestion_id}/decide`

Admin accept/reject a suggestion. **admin** auth. Same behavior as the
reviewer `/decide` endpoint above, but admin-only.

### `PATCH /api/admin/words/{word_id}`

Admin edits a word's fields. **admin** auth. Same body shape as
`PATCH /api/words/{word_id}` (reviewer edit), but admin-only and supports
a few extra fields. Translation fields (`swahili_translation`,
`english_translation`) update the corresponding `Translation` rows —
creates them if they don't exist. If `examples` is provided, it REPLACES
the word's example set.

**Response (200):**
```json
{
  "id": "word-uuid",
  "slug": "mlima",
  "updated_fields": ["morphology_notes"]
}
```

### `POST /api/admin/words/{word_id}/hide`

Soft-delete a word (set `status='hidden'`). **admin** auth.

The word is no longer visible in `GET /api/words` or `GET /api/search`,
but the row is kept for audit/restore. Audit-logged as `word.hide`.

**Response (200):**
```json
{ "id": "word-uuid", "status": "hidden" }
```

### `POST /api/admin/words/merge`

Merge source word into target word. **admin** auth.

- Source word's relations are re-pointed to the target
- Source word's translations and examples are moved to the target (if not duplicates)
- Source word is set to `status='merged'` (hidden from lists, but the row remains for audit)

**Request body:**
```json
{
  "source_id": "source-uuid",
  "target_id": "target-uuid"
}
```

**Response (200):**
```json
{
  "id": "target-uuid",
  "status": "merged",
  "merged_from": "source-uuid"
}
```

**Status codes:**
- `200` — merged
- `400` — `source_id == target_id`
- `404` — source or target word not found

### `GET /api/admin/audit-log`

Query the audit log. **admin** auth.

**Query params:**

| Param | Type | Default | Notes |
|---|---|---|---|
| `entity_type` | string | — | `word`, `translation`, `example`, `relation`, `suggestion`, `user`, `sense` |
| `entity_id` | UUID | — | Filter to a specific entity |
| `action` | string | — | Filter by action (accepts both bare and dotted forms — `word.create` or `create`) |
| `page` | int | 1 | 1-indexed |
| `size` | int | 20 | Max 100 |

**Response (200):**
```json
{
  "items": [
    {
      "id": "log-uuid",
      "created_at": "2026-11-10T15:00:00+00:00",
      "actor_id": "user-uuid",
      "actor_email": "admin@example.com",
      "actor_role": "admin",
      "action": "word.create",
      "target_type": "word",
      "target_id": "word-uuid",
      "details": { "headword": "mlima", "slug": "mlima" }
    }
  ],
  "total": 1,
  "page": 1,
  "size": 20,
  "has_next": false
}
```

The audit log stores bare verbs (`create`, `update`, `delete`, `merge`)
for entity-scoped actions, and already-dotted forms
(`user.password_reset`, `suggestion.accept`, etc.) for cross-cutting
actions. The API surfaces both via the `_map_action` helper, and the
`action` filter accepts either form (it ORs them internally).

See [architecture.md](architecture.md#audit-log) for the full action
namespace.

---

## Interactive docs (auto-generated)

FastAPI auto-generates interactive docs from the OpenAPI schema:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`

These are great for trying endpoints in the browser — you can paste a
token into the Authorize dialog and hit any authenticated endpoint.

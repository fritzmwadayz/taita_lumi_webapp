# Architecture

A 10-minute tour of how the backend fits together. Read the code for
details — this is the map.

## The request lifecycle

```
HTTP request
    │
    ▼
FastAPI app (app/main.py)
    │
    ├── CORS middleware
    │
    ▼
Router (app/routes/<surface>.py)
    │  • e.g. /api/auth/*, /api/words/*, /api/admin/*
    │
    ├── Depends(get_db)  ←  yields an AsyncSession per request
    ├── Depends(get_current_user)  ←  decodes the JWT, fetches the User
    │
    ▼
Route handler
    │  • validates the request body via Pydantic
    │  • calls db.execute(select(...)) etc.
    │  • writes audit-log rows where appropriate
    │
    ▼
AsyncSession  (app/db.py)
    │  • asyncpg connection from the pool
    │
    ▼
PostgreSQL  (Neon / local / in-memory launcher)
```

### Where each piece is

| File | Role |
|---|---|
| `app/main.py` | FastAPI app factory, CORS, router registration |
| `app/config.py` | `Settings` class — every env var with defaults |
| `app/db.py` | Async engine + session factory + `get_db` dependency |
| `app/models.py` | SQLAlchemy ORM models (all 11 tables) |
| `app/schemas.py` | Pydantic schemas for words/senses/translations |
| `app/schemas_auth.py` | Pydantic schemas for auth/profile endpoints |
| `app/schemas_suggestion.py` | Pydantic schemas for suggestions |
| `app/schemas_admin.py` | Pydantic schemas for admin endpoints |
| `app/security.py` | Password hashing (bcrypt) + JWT (HS256) |
| `app/deps.py` | `get_current_user`, `require_reviewer`, `require_admin` |
| `app/email.py` | `send_email()` — async, dev-mode + SMTP mode |
| `app/anon.py` | Anonymous sessions + rate limiters (suggestions, password reset) |
| `app/slugs.py` | `generate_unique_slug()` — for word URLs |
| `app/promote.py` | The `_apply_*` helpers — applies accepted suggestions to the word graph |
| `app/routes/auth.py` | `/api/auth/*` — register, login, refresh, me, OAuth, password reset, profile management |
| `app/routes/words.py` | `/api/words/*`, `/api/search`, `/api/senses/*` |
| `app/routes/suggestions.py` | `/api/suggestions/*` |
| `app/routes/votes.py` | `/api/suggestions/{id}/vote` |
| `app/routes/admin.py` | `/api/admin/*` |
| `app/routes/health.py` | `/api/health*` |
| `app/cli/import_data.py` | CLI: bulk import from `lexicon.db` |

## The auth dependency chain

Most endpoints do something like:

```python
@router.get("/me")
async def get_me(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ...
```

`get_current_user` (in `app/deps.py`):

1. Reads `Authorization: Bearer <token>` from the request (via
   `HTTPBearer`)
2. Decodes the JWT with `decode_token(credentials.credentials, expected_type="access")`
   - Verifies signature with `JWT_SECRET`
   - Verifies expiry
   - Verifies `type == "access"`
3. Extracts the `sub` (user_id) and looks up the User
4. If the user is None → 401 (`"User no longer exists"`)
5. If the user is blocked → 403 (`"This account has been blocked"`)
6. Returns the User object

The variants `require_reviewer` and `require_admin` wrap
`get_current_user` and add a role check.

`get_optional_user` is like `get_current_user` but returns None when no
token is provided (instead of raising 401). Used by endpoints that
accept both authed and anon users (e.g. `POST /api/suggestions` —
contributors post as themselves, anon users post via session cookie).

## The data model

11 tables, all UUID-keyed. The full schema is in
`alembic/versions/0001_initial.py` through `0006_*`. Quick summary:

```
users                    — accounts (email, password_hash, oauth_*, role, is_blocked)
anonymous_sessions       — anon visitors (cookie_hash, ip_hash, is_blocked)

words                    — Taita headwords (headword, slug, normalized_form, status, source)
senses                   — distinct meanings of a word (word_id, order_index, definition, notes)
translations             — per-sense translations in sw/en (sense_id, language, text)
examples                 — usage examples per sense (sense_id, taita_text, swahili_text, english_text)
word_variations          — bidirectional links between forms of the same lemma
word_relationships       — typed links between different lemmas (antonym, synonym, derived...)

suggestions              — proposals to add/correct the word graph
votes                    — up/down votes on suggestions (one per user/session per suggestion)

edit_log                 — append-only audit trail (actor, action, entity, before, after)
import_batches           — tracks each bulk import from lexicon.db
```

### Key constraints

- `users.email` is `UNIQUE NOT NULL` — that's why account deletion
  replaces the email with `deleted+<uuid>@anon.lumi` instead of NULL
- `votes` has a CHECK constraint enforcing exactly one of `user_id` /
  `session_id` is set (a vote is by either a user or an anon session,
  never both, never neither)
- `word_variations` and `word_relationships` both have CHECK constraints
  preventing self-links (`word_id <> other_word_id`)
- `word_variations` has a unique index using `LEAST/GREATEST` on
  `(word_id, other_word_id)` so `(A, B, 'plural')` and `(B, A, 'plural')`
  can't both exist — they're the same link
- All UUIDs are generated by Postgres (`gen_random_uuid()`)

## The audit log

Every mutation to the word graph (and to user accounts) writes a row to
`edit_log`. The schema is:

```python
class EditLog(Base):
    id: UUID
    actor_user_id: UUID | None       # who did it
    actor_session_id: UUID | None    # or which anon session
    action: str                      # 'create' | 'update' | 'delete' | 'merge' | 'import' |
                                     # 'suggestion.accept' | 'suggestion.reject' |
                                     # 'user.role.change' | 'user.block' | 'user.unblock' |
                                     # 'user.password_reset_request' | 'user.password_reset' |
                                     # 'user.email_change' | 'user.delete'
    entity_type: str                 # 'word' | 'translation' | 'example' | 'relation' |
                                     # 'suggestion' | 'user' | 'sense'
    entity_id: UUID                  # NOT NULL — the row that was affected
    before: dict | None              # JSONB — state before the change
    after: dict | None               # JSONB — state after the change
    created_at: datetime
```

### The action namespace

There are two conventions:

**Bare verbs** for entity-scoped mutations:

| Stored in DB | Surfaced as (public API) |
|---|---|
| `create` | `word.create`, `translation.create`, `example.update`, etc. |
| `update` | `word.update`, `sense.update`, etc. |
| `delete` | `word.hide` (special case for words — soft-delete is the only delete path) |
| `merge` | `word.merge` |
| `import` | `word.import` |

The `_map_action()` helper in `admin.py` qualifies bare verbs with the
`entity_type` to produce the dotted form on read.

**Already-dotted** for cross-cutting actions:

| Stored in DB | Surfaced as |
|---|---|
| `suggestion.accept` | `suggestion.accept` |
| `suggestion.reject` | `suggestion.reject` |
| `user.role.change` | `user.role.change` |
| `user.block` | `user.block` |
| `user.unblock` | `user.unblock` |
| `user.password_reset_request` | `user.password_reset_request` |
| `user.password_reset` | `user.password_reset` |
| `user.email_change` | `user.email_change` |
| `user.delete` | `user.delete` |

These pass through `_map_action()` unchanged.

### Filtering

The `GET /api/admin/audit-log` endpoint accepts an `action` filter that
works with both forms:

```bash
# Either form works:
curl 'http://localhost:8000/api/admin/audit-log?action=word.create'
curl 'http://localhost:8000/api/admin/audit-log?action=create'

# For already-dotted actions, use the dotted form:
curl 'http://localhost:8000/api/admin/audit-log?action=user.password_reset'
```

Internally, the filter ORs `action == 'word.create' OR action == 'create'`
so both legacy bare-verb rows and new dotted rows are findable.

## The suggestion lifecycle

```
              POST /api/suggestions
                        │
                        ▼
                  status='open'
                        │
              ┌─────────┼─────────┐
              │         │         │
        vote 'up'    vote 'down'  decide (reviewer+)
              │         │         │
              ▼         ▼         ▼
        count up    count down   decision='accept' | 'reject'
              │         │         │
              └─────┬───┘         │
                    ▼             ▼
              auto-promote?   status='accepted' | 'rejected'
              (threshold)         │
                    │             │
                    ▼             ▼
              status='accepted'   (no change to word graph)
                    │
                    ▼
              _apply_* helper applies the change to the word graph
              (creates the word, adds the translation, etc.)
```

### Auto-promote threshold

After every vote, `check_and_promote()` (in `app/promote.py`) checks:

```
status='open'
AND age >= 7 days (created_at is at least 7 days ago)
AND net_votes (up - down) >= 3
AND at least 2 distinct non-anon upvotes
```

If all four conditions are met, the suggestion is auto-promoted to
`accepted` and the `_apply_*` helper applies the change.

### Manual decide

Reviewers and admins can skip the vote via `POST /api/suggestions/{id}/decide`
(or `POST /api/admin/suggestions/{id}/decide` for admin). Same
`_apply_*` helpers run on accept.

### The `_apply_*` helpers

Each `target_type` has a dedicated helper in `app/promote.py`:

| Target type | Helper | What it does |
|---|---|---|
| `new_word` | `_apply_new_word` | Creates a Word + default Sense + translations + examples |
| `word` | `_apply_word_correction` | Updates a single field on an existing Word |
| `translation` | `_apply_translation` | Adds a Translation row to a Sense |
| `example` | `_apply_example` | Adds a translation to an existing Example |
| `new_example` | `_apply_new_example` | Creates a new Example row scoped to a Sense |
| `variation` | `_apply_variation` | Creates a WordVariation row |
| `relationship` | `_apply_relationship` | Creates a WordRelationship row |
| `relation` (legacy) | `_apply_relation` | Dispatches to variation or relationship based on type |

Each helper writes its own audit-log row (e.g. `action='create'`,
`entity_type='word'`) in addition to the `suggestion.accept` row the
decide handler writes.

## The slug generator

Word URLs use slugs (`/api/words/mlima` instead of `/api/words/<uuid>`).
`app/slugs.py` generates them:

1. Lowercase the headword
2. Replace non-alphanumeric runs with `-`
3. Strip leading/trailing `-`
4. If a word with that slug already exists, append `-2`, `-3`, etc.

The `generate_unique_slug(db, headword, exclude_word_id=None)` helper
takes an optional `exclude_word_id` so editing a word's headword doesn't
collide with itself.

## The in-memory test launcher

`scripts/run_local_api.py` is a test harness that backs every model with
a Python dict instead of Postgres. It overrides `get_db` to yield an
`InMemoryDB` instance that implements just enough of the SQLAlchemy
`AsyncSession` API for the routes to work:

- `execute(stmt)` — parses the WHERE clauses (equality, IN, ILIKE, !=
  and the trigram `%` operator) and filters the in-memory store
- `scalar()`, `scalar_one()`, `scalar_one_or_none()`, `scalars().all()`,
  `.first()` — the result-object methods the routes use
- `add(obj)` — inserts into the store, sets a UUID + timestamps, fills
  sensible defaults for NOT NULL fields (e.g. `Word.status='live'`,
  `User.is_blocked=False`)
- `commit()` / `flush()` / `refresh()` — no-ops (in-memory writes are
  immediate)

Special test-harness behavior:
- The **first** registered user is auto-promoted to `admin` (override
  with `LUMI_HARNESS_FIRST_USER_ROLE=user`). Lets `test_full_api.sh`
  exercise promote/demote without external DB manipulation.
- CompoundSelect (UNION queries, used by `/api/admin/stats` for the
  recent-words aggregation) is handled by inspecting the inner selects'
  whereclauses.

The launcher is **not** production code — it's a way to run the full
test suite without spinning up Postgres. It's how the test scripts were
developed and verified end-to-end in this sandbox. For real testing,
use `dev_server.sh --local` (real Postgres) or `--in-memory` (the
launcher).

See [testing.md](testing.md) for the full test workflow.

## See also

- [api-reference.md](api-reference.md) — every endpoint
- [authentication.md](authentication.md) — JWT, roles, password reset
- [testing.md](testing.md) — the 3 test modes
- `alembic/versions/` — the actual schema (read in order)

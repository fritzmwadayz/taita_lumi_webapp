# TaitaLumi API

FastAPI backend for the TaitaLumi dictionary.

## Setup

### 1. Create virtual environment

```bash
cd website/api
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and set `DATABASE_URL` to your Neon connection string.
(Generate a JWT secret with: `python -c "import secrets; print(secrets.token_hex(32))"`)

### 3. Run migrations

```bash
alembic upgrade head
```

This creates all 10 tables in your Postgres database:
`users`, `anonymous_sessions`, `import_batches`, `words`, `glosses`,
`examples`, `word_relations`, `suggestions`, `votes`, `edit_log`.

### 4. Run the dev server

```bash
uvicorn app.main:app --reload --port 8000
```

API docs available at http://localhost:8000/docs

### 5. Run tests

```bash
pytest
```

## Project structure

```
api/
├── alembic/
│   ├── env.py                  — async Alembic config
│   └── versions/
│       └── 0001_initial.py     — all 10 tables + pg_trgm extension
├── app/
│   ├── main.py                 — FastAPI app + CORS
│   ├── config.py               — settings via pydantic-settings
│   ├── db.py                   — async SQLAlchemy engine + session
│   ├── models.py               — all 10 SQLAlchemy models
│   ├── deps.py                 — shared dependencies (get_db, auth stubs)
│   └── routes/
│       └── health.py           — GET /api/health, GET /api/health/ready
├── tests/
│   ├── conftest.py             — pytest fixtures (async test client)
│   └── test_health.py          — basic endpoint test
├── pyproject.toml
├── .env.example
└── alembic.ini
```

## Schema overview

| Table | Purpose |
|-------|---------|
| `users` | Account holders (contributors + admins) |
| `anonymous_sessions` | Anon visitors for rate-limiting + spam control |
| `import_batches` | Tracks each bulk import from lexicon.db |
| `words` | Headwords — the primary unit |
| `glosses` | Swahili + English translations (attach to words) |
| `examples` | Usage examples with parallel text |
| `word_relations` | Edges between words (plural, variant, etc.) |
| `suggestions` | Proposals to add/correct words or related entities |
| `votes` | Up/down votes on suggestions |
| `edit_log` | Append-only audit trail |

**Key design decision:** No `senses` table — glosses attach directly to words.
Voting targets words, not senses. This keeps the model simple for v1.

## Next steps (Phase 1)

- Import script (NDJSON from lexicon.db → Postgres)
- `GET /api/words` (paginated list with filters)
- `GET /api/words/{id}` (full word detail)
- `GET /api/search?q=` (pg_trgm fuzzy search)

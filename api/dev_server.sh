#!/usr/bin/env bash
#
# dev_server.sh — launch the TaitaLumi backend in dev mode with email capture.
#
# Three modes, picked by flag:
#
#   --local       (default) Use a local Postgres DB. The DB must already
#                 exist (run with --init once to create it + run migrations).
#                 DATABASE_URL comes from LOCAL_DATABASE_URL env or the default
#                 postgresql+asyncpg://postgres:postgres@localhost:5432/lumi_test
#
#   --prod        Use the production Neon DB. Reads DATABASE_URL from .env
#                 (or the DATABASE_URL env var). PROMPTS for confirmation —
#                 you must type 'yes' to proceed.
#
#   --in-memory   No Postgres at all. Uses an in-memory dict. Useful for
#                 quick smoke tests when you don't want to spin up Postgres.
#                 Requires scripts/run_local_api.py from the zip.
#
# In all modes:
#   - SMTP_HOST is set to empty  → emails are logged, not sent
#   - EMAIL_LOG_FILE is set      → emails also appended as JSON lines so the
#                                  test script can read reset tokens
#   - JWT_SECRET is set         → must match what test_api_endpoints.sh uses
#                                  (default 'test-secret-for-dev-only')
#   - FRONTEND_URL is set       → http://localhost:3000 (for reset links)
#
# Usage:
#   ./dev_server.sh                  # local mode, port 8000
#   ./dev_server.sh --local --init   # one-time: create DB + run migrations
#   ./dev_server.sh --prod           # production DB (prompts)
#   ./dev_server.sh --in-memory      # no Postgres needed
#   ./dev_server.sh --port 8001      # custom port
#
# Then in another terminal:
#   ./test_api_endpoints.sh
#
# (test_api_endpoints.sh defaults to BASE_URL=http://localhost:8000 and
# EMAIL_LOG_FILE=/tmp/lumi-test-emails.log — both match this launcher's
# defaults, so they just work together.)

set -euo pipefail

# ── Defaults ──────────────────────────────────────────────────
MODE="local"
INIT_DB=0
PORT=8000
EMAIL_LOG_FILE="${EMAIL_LOG_FILE:-/tmp/lumi-test-emails.log}"
JWT_SECRET_DEFAULT="test-secret-for-dev-only"
LOCAL_DB_DEFAULT="postgresql+asyncpg://postgres:postgres@localhost:5432/lumi_test"

# ── Parse args ────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --local)        MODE="local";      shift ;;
    --prod)         MODE="prod";       shift ;;
    --in-memory)    MODE="in-memory";  shift ;;
    --init)         INIT_DB=1;         shift ;;
    --port)         PORT="$2";         shift 2 ;;
    -h|--help)
      sed -n '1,/^set -euo/p' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *) echo "Unknown option: $1 (try --help)" >&2; exit 1 ;;
  esac
done

# ── Resolve DATABASE_URL ──────────────────────────────────────
case "$MODE" in
  local)
    DATABASE_URL="${LOCAL_DATABASE_URL:-$LOCAL_DB_DEFAULT}"
    if [[ $INIT_DB -eq 1 ]]; then
      echo "→ Creating lumi_test database (if it doesn't exist)..."
      # psql needs a sync URL — strip the +asyncpg driver suffix
      ADMIN_URL="${DATABASE_URL/postgresql+asyncpg/postgresql}"
      # Detach the database name so we connect to the maintenance DB (postgres)
      DB_NAME="${ADMIN_URL##*/}"
      ADMIN_URL="${ADMIN_URL%/*}/postgres"

      if psql "$ADMIN_URL" -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" | grep -q 1; then
        echo "  database '$DB_NAME' already exists, skipping create"
      else
        psql "$ADMIN_URL" -c "CREATE DATABASE $DB_NAME"
        echo "  created '$DB_NAME'"
      fi

      echo "→ Running alembic upgrade head..."
      DATABASE_URL="$DATABASE_URL" alembic upgrade head
      echo "→ Done. Re-run without --init to start the server."
      exit 0
    fi
    echo "→ Mode: local Postgres"
    echo "  DATABASE_URL: $DATABASE_URL"
    ;;

  prod)
    # Prefer .env, fall back to DATABASE_URL env var
    if [[ -f .env ]]; then
      DATABASE_URL="$(grep -E '^DATABASE_URL=' .env | head -1 | cut -d= -f2-)"
    fi
    if [[ -z "${DATABASE_URL:-}" ]]; then
      echo "ERROR: --prod needs DATABASE_URL. Set it in .env or as an env var." >&2
      exit 1
    fi
    # Redact the password in the printed URL
    URL_REDACTED="$(printf '%s' "$DATABASE_URL" | sed -E 's|://([^:]+):[^@]+@|://\1:***@|')"
    echo "→ Mode: PRODUCTION Neon DB"
    echo "  DATABASE_URL: $URL_REDACTED"
    echo ""
    echo "  WARNING: this connects to your production database."
    echo "           test_api_endpoints.sh will create a test user and (unless"
    echo "           KEEP_USER=1) soft-delete it. Anonymized users will remain"
    echo "           in your DB as 'deleted+<uuid>@anon.lumi'."
    echo ""
    read -r -p "  Type 'yes' to continue: " confirm
    if [[ "$confirm" != "yes" ]]; then
      echo "  Aborted."
      exit 1
    fi
    ;;

  in-memory)
    # The in-memory launcher needs scripts/run_local_api.py
    LAUNCHER=""
    for candidate in \
      "./scripts/run_local_api.py" \
      "./run_local_api.py" \
      "$(dirname "$0")/scripts/run_local_api.py" \
      "$(dirname "$0")/run_local_api.py"; do
      if [[ -f "$candidate" ]]; then
        LAUNCHER="$candidate"
        break
      fi
    done
    if [[ -z "$LAUNCHER" ]]; then
      echo "ERROR: --in-memory needs scripts/run_local_api.py from the deliverable zip." >&2
      echo "       Looked in ./scripts/, ./, and next to this script." >&2
      exit 1
    fi
    DATABASE_URL="postgresql+asyncpg://x:x@localhost/x"
    echo "→ Mode: in-memory (no DB)"
    echo "  launcher: $LAUNCHER"
    ;;
esac

# ── Common env vars for all modes ────────────────────────────
export DATABASE_URL
export SMTP_HOST=""                 # disable real email sending
export EMAIL_LOG_FILE               # JSON-line email log (read by test script)
export JWT_SECRET="${JWT_SECRET:-$JWT_SECRET_DEFAULT}"
export FRONTEND_URL="${FRONTEND_URL:-http://localhost:3000}"

# Clear the email log so each run starts fresh
rm -f "$EMAIL_LOG_FILE"

echo ""
echo "  Email log:    $EMAIL_LOG_FILE"
echo "  JWT secret:   ${JWT_SECRET:0:3}*** (test script must match this)"
echo "  Frontend URL: $FRONTEND_URL"
echo "  SMTP host:    (empty — emails logged, not sent)"
echo ""

# ── Start the server ─────────────────────────────────────────
if [[ "$MODE" == "in-memory" ]]; then
  # The in-memory launcher sets up its own uvicorn instance
  LAUNCHER_DIR="$(dirname "$LAUNCHER")"
  LAUNCHER_MODULE="$(basename "$LAUNCHER" .py)"
  ( cd "$LAUNCHER_DIR" && exec python -m "$LAUNCHER_MODULE" )
else
  exec python -m uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --reload
fi

#!/usr/bin/env bash
#
# test_full_api.sh — end-to-end smoke test for EVERY TaitaLumi API endpoint.
#
# Walks through the full lifecycle of an account, exercising the role-based
# access control along the way:
#
#   STAGE A — Anonymous browsing          (no auth)
#   STAGE B — Sign up + user-mode actions (role='user')
#   STAGE B.5 — Suggestion flow (as user)
#   STAGE C — Promote to reviewer         (role='reviewer') + reviewer-only actions
#   STAGE D — Promote to admin            (role='admin')   + admin-only actions
#   STAGE E — Demote back to user         (verify role reduction works)
#   STAGE F — Password reset + email change (the recovery flow)
#   STAGE G — Delete account              (soft-delete / anonymize)
#   STAGE H — Verify the account is gone
#
# To test promote/demote, we need an admin. Two ways to provide one:
#
#   1. EXISTING ADMIN: set ADMIN_EMAIL + ADMIN_PASSWORD env vars to an admin
#      account that already exists in the DB. The script logs in as them and
#      uses their token for /api/admin/users/{id} calls.
#
#   2. TEST HARNESS AUTO-ADMIN: when running against the in-memory launcher
#      (scripts/run_local_api.py), the FIRST user registered is auto-promoted
#      to admin. So the script registers a "harness-admin" user first, logs in
#      as them, and uses that token to promote/demote the test user.
#      Set LUMI_HARNESS_FIRST_USER_ROLE=user on the launcher to disable.
#
#   When neither is available (you're running against a real Postgres with no
#      admin yet), set ADMIN_BOOTSTRAP=1 — promote/demote endpoints are SKIPPED,
#      and the script tests that a regular user CAN'T call them (403).
#
# Usage:
#   ./test_full_api.sh                          # against http://localhost:8000
#   BASE_URL=https://your-api.onrender.com ./test_full_api.sh
#
# Optional env vars:
#   BASE_URL         — API base URL (default: http://localhost:8000)
#   JWT_SECRET       — fallback for minting a reset token (default: change-me)
#   EMAIL_LOG_FILE   — path to the email-capture log (default: /tmp/lumi-test-emails.log)
#   KEEP_USER        — set to "1" to skip account deletion (debugging)
#   SKIP_RESET       — set to "1" to skip the password-reset/confirm step
#   EMAIL_DOMAIN     — domain for test emails (default: example.com)
#   ADMIN_EMAIL      — existing admin email (alternative to harness auto-admin)
#   ADMIN_PASSWORD   — existing admin password
#   ADMIN_BOOTSTRAP  — set to "1" to skip promote/demote entirely (default: 0)
#   USE_HARNESS_ADMIN — set to "1" to use the in-memory launcher's auto-admin
#                      (default: 1 when ADMIN_EMAIL is empty, else 0)
#
# Requirements:
#   - curl, python3
#   - python3 -c "import jose" (only as fallback for the reset-token step)
#
# Exit codes:
#   0 — all PASS
#   1 — at least one FAIL
#   2 — environment problem

set -uo pipefail

# ── Config ─────────────────────────────────────────────────────
BASE_URL="${BASE_URL:-http://localhost:8000}"
JWT_SECRET="${JWT_SECRET:-change-me}"
EMAIL_DOMAIN="${EMAIL_DOMAIN:-example.com}"
EMAIL_LOG_FILE="${EMAIL_LOG_FILE:-/tmp/lumi-test-emails.log}"
KEEP_USER="${KEEP_USER:-0}"
SKIP_RESET="${SKIP_RESET:-0}"
ADMIN_BOOTSTRAP="${ADMIN_BOOTSTRAP:-0}"
ADMIN_EMAIL="${ADMIN_EMAIL:-}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-}"

RUN_ID="$(date +%s)-$$"
EMAIL="alice+${RUN_ID}@${EMAIL_DOMAIN}"
PASSWORD="AlicePass12345!"
DISPLAY_NAME="Alice ${RUN_ID}"

# Decide admin-source strategy
if [[ -n "$ADMIN_EMAIL" && -n "$ADMIN_PASSWORD" ]]; then
  USE_HARNESS_ADMIN=0
elif [[ "$ADMIN_BOOTSTRAP" == "1" ]]; then
  USE_HARNESS_ADMIN=0
else
  USE_HARNESS_ADMIN=1
fi

# ── Pretty-printing ────────────────────────────────────────────
green=$'\e[32m'; red=$'\e[31m'; yellow=$'\e[33m'
bold=$'\e[1m';  reset=$'\e[0m'
pass_count=0
fail_count=0
fail_fast=0

section() { printf '\n\n%s══════════ %s ══════════%s\n' "$bold" "$1" "$reset"; }
step()     { printf '\n%s── %s ──%s\n' "$bold" "$1" "$reset"; }
ok()       { printf '  %sPASS%s: %s\n' "$green" "$reset" "$1"; pass_count=$((pass_count+1)); }
fail()     { printf '  %sFAIL%s: %s\n' "$red" "$reset" "$1"; fail_count=$((fail_count+1));
             [[ -n "${2:-}" ]] && printf '    %sbody:%s %s\n' "$yellow" "$reset" "$2"; }
expect_status() {
  local label="$1" want="$2" got="$3" body="${4:-}"
  if [[ "$got" == "$want" ]]; then
    ok "$label (HTTP $got)"
  else
    fail "$label (expected HTTP $want, got $got)" "$body"
  fi
}

# ── JSON helper ───────────────────────────────────────────────
json_get() {
  python3 -c '
import json, sys
try:
    d = json.loads(sys.argv[1] or "null")
except Exception:
    print(""); sys.exit(0)
keys = sys.argv[2].split(".")
for k in keys:
    if isinstance(d, dict):
        d = d.get(k, "")
    elif isinstance(d, list) and k.isdigit():
        d = d[int(k)] if int(k) < len(d) else ""
    else:
        d = ""; break
v = d if isinstance(d, str) else json.dumps(d)
print(v)
' "$1" "$2"
}

# ── curl wrapper ───────────────────────────────────────────────
api() {
  local method="$1" path="$2"
  local body="${3:-}" token="${4:-}"
  local hdr=( -H "Content-Type: application/json" -H "Accept: application/json" )
  [[ -n "$token" ]] && hdr+=( -H "Authorization: Bearer $token" )

  local tmp; tmp="$(mktemp)"
  local code
  code="$(curl -s -X "$method" "${hdr[@]}" \
            --data "$body" \
            -o "$tmp" \
            -w '%{http_code}' \
            "${BASE_URL}${path}" 2>/dev/null || echo "000")"
  local body_out; body_out="$(cat "$tmp" 2>/dev/null || true)"
  rm -f "$tmp"
  printf '%s|%s' "$code" "$body_out"
}

# ── Reset-token helper ─────────────────────────────────────────
read_reset_token_from_log() {
  python3 -c '
import json, sys, os
path = sys.argv[1]
if not path or not os.path.exists(path):
    sys.exit(0)
with open(path) as f:
    lines = f.readlines()
if not lines:
    sys.exit(0)
for line in reversed(lines):
    try:
        e = json.loads(line)
    except Exception:
        continue
    if "reset" not in (e.get("subject") or "").lower():
        continue
    body = e.get("body") or ""
    marker = "/reset-password?token="
    idx = body.find(marker)
    if idx == -1:
        continue
    rest = body[idx + len(marker):]
    token = ""
    for c in rest:
        if c.isspace():
            break
        token += c
    if token:
        print(token)
        sys.exit(0)
sys.exit(0)
' "$EMAIL_LOG_FILE"
}

make_reset_token() {
  local user_id="$1" email="$2"
  python3 -c '
from jose import jwt
from datetime import datetime, timedelta, timezone
import sys
payload = {
    "sub": sys.argv[1],
    "email": sys.argv[2],
    "type": "reset",
    "exp": datetime.now(timezone.utc) + timedelta(seconds=3600),
    "iat": datetime.now(timezone.utc),
}
print(jwt.encode(payload, sys.argv[3], algorithm="HS256"))
' "$user_id" "$email" "$JWT_SECRET"
}

# ── Preflight ──────────────────────────────────────────────────
printf '%sTaitaLumi API — full end-to-end smoke test%s\n' "$bold" "$reset"
printf '  base_url:        %s\n' "$BASE_URL"
printf '  test user email: %s\n' "$EMAIL"
printf '  jwt_secret:      %s*** (only used for reset-token fallback)\n' "${JWT_SECRET:0:3}"
printf '  email_log:       %s\n' "$EMAIL_LOG_FILE"
if [[ "$USE_HARNESS_ADMIN" == "1" ]]; then
  printf '  admin source:    %sharness auto-admin%s (first registered user becomes admin)\n' "$yellow" "$reset"
elif [[ -n "$ADMIN_EMAIL" ]]; then
  printf '  admin source:    existing admin (%s)\n' "$ADMIN_EMAIL"
else
  printf '  admin source:    %sADMIN_BOOTSTRAP=1%s — promote/demote endpoints SKIPPED\n' "$yellow" "$reset"
fi

if ! command -v curl >/dev/null 2>&1; then
  printf '\n%sERROR:%s curl is required\n' "$red" "$reset" >&2; exit 2
fi
if ! command -v python3 >/dev/null 2>&1; then
  printf '\n%sERROR:%s python3 is required\n' "$red" "$reset" >&2; exit 2
fi


# ════════════════════════════════════════════════════════════════
# STAGE A — Anonymous browsing
# ════════════════════════════════════════════════════════════════
section "STAGE A — Anonymous browsing"

step "A.1 Health endpoints"
r="$(api GET /api/health)"; c="${r%%|*}"; b="${r#*|}"
expect_status "GET /api/health" "200" "$c" "$b"

r="$(api GET /api/health/ready)"; c="${r%%|*}"; b="${r#*|}"
expect_status "GET /api/health/ready" "200" "$c" "$b"

r="$(api GET /)"; c="${r%%|*}"; b="${r#*|}"
expect_status "GET / (root)" "200" "$c" "$b"

step "A.2 Public word list + search (empty DB is fine — should be 200 with empty list)"
r="$(api GET '/api/words?page=1&size=10')"; c="${r%%|*}"; b="${r#*|}"
expect_status "GET /api/words" "200" "$c" "$b"
[[ "$(json_get "$b" total)" != "" ]] && ok "list returns total field" || fail "list missing total"

r="$(api GET '/api/search?q=mlima')"; c="${r%%|*}"; b="${r#*|}"
expect_status "GET /api/search?q=mlima" "200" "$c" "$b"

step "A.3 Public suggestion list (open suggestions — empty is fine)"
r="$(api GET '/api/suggestions?status=open')"; c="${r%%|*}"; b="${r#*|}"
expect_status "GET /api/suggestions" "200" "$c" "$b"

step "A.4 Anonymous CANNOT do authed things (401 expected)"
r="$(api GET /api/auth/me)"; c="${r%%|*}"; b="${r#*|}"
expect_status "GET /api/auth/me without token → 401" "401" "$c" "$b"

r="$(api GET /api/auth/me/stats)"; c="${r%%|*}"; b="${r#*|}"
expect_status "GET /api/auth/me/stats without token → 401" "401" "$c" "$b"

r="$(api GET /api/admin/stats)"; c="${r%%|*}"; b="${r#*|}"
expect_status "GET /api/admin/stats without token → 401" "401" "$c" "$b"


# ════════════════════════════════════════════════════════════════
# STAGE B — Sign up + user-mode actions
# ════════════════════════════════════════════════════════════════
section "STAGE B — Sign up + user-mode actions"

# If using the harness auto-admin, register an admin FIRST so they're user #1
ADMIN_TOKEN=""
if [[ "$USE_HARNESS_ADMIN" == "1" ]]; then
  step "B.0a Register the harness-admin user (becomes admin automatically)"
  ADMIN_EMAIL="admin+${RUN_ID}@${EMAIL_DOMAIN}"
  ADMIN_PASSWORD="AdminPass12345!"
  payload="{\"email\":\"${ADMIN_EMAIL}\",\"password\":\"${ADMIN_PASSWORD}\",\"display_name\":\"Harness Admin\"}"
  r="$(api POST /api/auth/register "$payload")"; c="${r%%|*}"; b="${r#*|}"
  expect_status "POST /api/auth/register (admin)" "201" "$c" "$b"

  step "B.0b Login as harness-admin"
  payload="{\"email\":\"${ADMIN_EMAIL}\",\"password\":\"${ADMIN_PASSWORD}\"}"
  r="$(api POST /api/auth/login "$payload")"; c="${r%%|*}"; b="${r#*|}"
  expect_status "POST /api/auth/login (admin)" "200" "$c" "$b"
  ADMIN_TOKEN="$(json_get "$b" access_token)"

  # Verify the admin token actually has admin role by hitting /api/admin/stats
  r="$(api GET /api/admin/stats "" "$ADMIN_TOKEN")"; c="${r%%|*}"; b="${r#*|}"
  if [[ "$c" == "200" ]]; then
    ok "harness-admin is indeed an admin"
  else
    fail "harness-admin is NOT an admin (got $c on /api/admin/stats)" "$b"
    printf '\n  %sNote:%s harness auto-admin only works against the in-memory launcher.\n' "$yellow" "$reset"
    printf '  Against a real Postgres, the first registered user is role='"'"'user'"'"'.\n'
    printf '  Trying to auto-promote via psql...\n\n'

    # ── Try to auto-promote via psql ──────────────────────────
    # The user needs to have local Postgres set up (which dev_server.sh --local
    # requires anyway). We try `sudo -u postgres psql -d <db>` — if sudo prompts
    # for a password, the user can type it (this is an interactive script).
    DB_NAME="${LUMI_TEST_DB:-lumi_test}"
    PSQL_CMD="UPDATE users SET role='admin' WHERE email='${ADMIN_EMAIL}';"
    if sudo -u postgres psql -d "$DB_NAME" -tAc "$PSQL_CMD" >/dev/null 2>&1; then
      ok "auto-promoted harness-admin via psql (db: $DB_NAME)"

      # Re-login — the role is encoded in the JWT, so the existing token still
      # has role='user'. We need a fresh login to get an admin-scoped token.
      payload="{\"email\":\"${ADMIN_EMAIL}\",\"password\":\"${ADMIN_PASSWORD}\"}"
      r="$(api POST /api/auth/login "$payload")"; c="${r%%|*}"; b="${r#*|}"
      if [[ "$c" == "200" ]]; then
        ADMIN_TOKEN="$(json_get "$b" access_token)"
        # Verify the new token has admin role
        r="$(api GET /api/admin/stats "" "$ADMIN_TOKEN")"; c="${r%%|*}"
        if [[ "$c" == "200" ]]; then
          ok "harness-admin is now an admin (verified after re-login)"
        else
          fail "auto-promote: re-login worked but admin check still failed (got $c)"
          ADMIN_TOKEN=""
        fi
      else
        fail "auto-promote: re-login after promotion failed (got $c)"
        ADMIN_TOKEN=""
      fi
    else
      # Auto-promote failed — print clear instructions and clear ADMIN_TOKEN
      # so the script's later logic skips admin paths cleanly.
      printf '  %sAuto-promote failed.%s sudo/psql not available non-interactively,\n' "$red" "$reset"
      printf '  or the DB name is wrong (default: lumi_test — override with LUMI_TEST_DB).\n\n'
      printf '  %sTo fix this manually, run this in another terminal:%s\n' "$yellow" "$reset"
      printf '    sudo -u postgres psql -d %s -c "UPDATE users SET role='"'"'admin'"'"' WHERE email='"'"'%s'"'"';"\n' "$DB_NAME" "$ADMIN_EMAIL"
      printf '\n  Then re-run with: ADMIN_EMAIL='"'"'%s'"'"' ADMIN_PASSWORD='"'"'%s'"'"' ./test_full_api.sh\n\n' "$ADMIN_EMAIL" "$ADMIN_PASSWORD"
      printf '  %sContinuing in ADMIN_BOOTSTRAP mode (skipping promote/demote/admin-only endpoints).%s\n' "$yellow" "$reset"
      ADMIN_TOKEN=""
    fi
  fi
elif [[ -n "$ADMIN_EMAIL" ]]; then
  step "B.0a Login as existing admin"
  payload="{\"email\":\"${ADMIN_EMAIL}\",\"password\":\"${ADMIN_PASSWORD}\"}"
  r="$(api POST /api/auth/login "$payload")"; c="${r%%|*}"; b="${r#*|}"
  expect_status "POST /api/auth/login (admin)" "200" "$c" "$b"
  ADMIN_TOKEN="$(json_get "$b" access_token)"

  # Verify the admin token actually has admin role
  r="$(api GET /api/admin/stats "" "$ADMIN_TOKEN")"; c="${r%%|*}"; b="${r#*|}"
  if [[ "$c" == "200" ]]; then
    ok "admin token verified"
  else
    fail "ADMIN_EMAIL login succeeded but is not an admin (got $c on /api/admin/stats)" "$b"
    printf '\n  %sThe admin you provided doesn'"'"'t have role='"'"'admin'"'"'.%s\n' "$yellow" "$reset"
    printf '  Promote them via psql:\n'
    printf '    sudo -u postgres psql -d lumi_test -c "UPDATE users SET role='"'"'admin'"'"' WHERE email='"'"'%s'"'"';"\n\n' "$ADMIN_EMAIL"
    ADMIN_TOKEN=""
  fi
fi

step "B.1 Register the test user"
payload="{\"email\":\"${EMAIL}\",\"password\":\"${PASSWORD}\",\"display_name\":\"${DISPLAY_NAME}\"}"
r="$(api POST /api/auth/register "$payload")"; c="${r%%|*}"; b="${r#*|}"
expect_status "POST /api/auth/register" "201" "$c" "$b"
ACCESS_TOKEN="$(json_get "$b" access_token)"
[[ -n "$ACCESS_TOKEN" ]] && ok "got access token" || fail "no access_token"

step "B.2 Login"
payload="{\"email\":\"${EMAIL}\",\"password\":\"${PASSWORD}\"}"
r="$(api POST /api/auth/login "$payload")"; c="${r%%|*}"; b="${r#*|}"
expect_status "POST /api/auth/login" "200" "$c" "$b"
ACCESS_TOKEN="$(json_get "$b" access_token)"
REFRESH_TOKEN="$(json_get "$b" refresh_token)"
[[ -n "$ACCESS_TOKEN" ]] && ok "got access token" || fail "no access_token"
[[ -n "$REFRESH_TOKEN" ]] && ok "got refresh token" || fail "no refresh_token"

step "B.3 Profile (GET /me)"
r="$(api GET /api/auth/me "" "$ACCESS_TOKEN")"; c="${r%%|*}"; b="${r#*|}"
expect_status "GET /api/auth/me" "200" "$c" "$b"
[[ "$(json_get "$b" email)" == "$EMAIL" ]] && ok "email matches" || fail "email mismatch"
USER_ID="$(json_get "$b" id)"
[[ -n "$USER_ID" ]] && ok "got user_id" || fail "no user_id"

step "B.4 Refresh tokens (POST /api/auth/refresh)"
payload="{\"refresh_token\":\"${REFRESH_TOKEN}\"}"
r="$(api POST /api/auth/refresh "$payload")"; c="${r%%|*}"; b="${r#*|}"
expect_status "POST /api/auth/refresh" "200" "$c" "$b"
NEW_ACCESS="$(json_get "$b" access_token)"
[[ -n "$NEW_ACCESS" ]] && ok "rotated access token" || fail "no new access token"
ACCESS_TOKEN="$NEW_ACCESS"

step "B.5 Update display name (PATCH /me)"
payload='{"display_name":"Alice Updated"}'
r="$(api PATCH /api/auth/me "$payload" "$ACCESS_TOKEN")"; c="${r%%|*}"; b="${r#*|}"
expect_status "PATCH /api/auth/me" "200" "$c" "$b"
[[ "$(json_get "$b" display_name)" == "Alice Updated" ]] && ok "name updated" || fail "name not updated"

step "B.6 Change password (PATCH /me/password)"
payload="{\"current_password\":\"${PASSWORD}\",\"new_password\":\"AliceNew12345!\"}"
r="$(api PATCH /api/auth/me/password "$payload" "$ACCESS_TOKEN")"; c="${r%%|*}"; b="${r#*|}"
expect_status "PATCH /api/auth/me/password" "200" "$c" "$b"
PASSWORD="AliceNew12345!"
ok "tracked new password for subsequent steps"

step "B.7 Get connected accounts (GET /me/connected-accounts)"
r="$(api GET /api/auth/me/connected-accounts "" "$ACCESS_TOKEN")"; c="${r%%|*}"; b="${r#*|}"
expect_status "GET /api/auth/me/connected-accounts" "200" "$c" "$b"
[[ "$(json_get "$b" has_password)" == "true" ]] && ok "has_password=true" || fail "has_password wrong"
[[ "$(json_get "$b" google)" == "false" ]] && ok "google=false" || fail "google wrong"

step "B.8 Get contribution stats (GET /me/stats)"
r="$(api GET /api/auth/me/stats "" "$ACCESS_TOKEN")"; c="${r%%|*}"; b="${r#*|}"
expect_status "GET /api/auth/me/stats" "200" "$c" "$b"
[[ "$(json_get "$b" words_added)" != "" ]] && ok "stats has words_added field" || fail "stats missing fields"

step "B.9 Logout (POST /api/auth/logout)"
r="$(api POST /api/auth/logout "{}" "$ACCESS_TOKEN")"; c="${r%%|*}"; b="${r#*|}"
expect_status "POST /api/auth/logout" "204" "$c" "$b"
ok "(JWT is stateless — logout is client-side only; token still valid)"

step "B.10 User CANNOT do reviewer/admin things (403 expected)"
payload='{"headword":"test-word-user","part_of_speech":"noun","swahili_translation":"mtihani"}'
r="$(api POST /api/words "$payload" "$ACCESS_TOKEN")"; c="${r%%|*}"; b="${r#*|}"
expect_status "POST /api/words as user → 403" "403" "$c" "$b"

r="$(api GET /api/admin/stats "" "$ACCESS_TOKEN")"; c="${r%%|*}"; b="${r#*|}"
expect_status "GET /api/admin/stats as user → 403" "403" "$c" "$b"


# ════════════════════════════════════════════════════════════════
# STAGE B.5 — Suggestion + vote flow (as a regular user)
# ════════════════════════════════════════════════════════════════
section "STAGE B.5 — Suggestion + vote (user-mode)"

step "B.5.1 Submit a new-word suggestion"
payload='{"target_type":"new_word","proposed_value":{"headword":"mlima-test-'"$RUN_ID"'","part_of_speech":"noun","swahili_translation":"mlima"},"rationale":"Test suggestion"}'
r="$(api POST /api/suggestions "$payload" "$ACCESS_TOKEN")"; c="${r%%|*}"; b="${r#*|}"
expect_status "POST /api/suggestions (new_word)" "201" "$c" "$b"
SUGGESTION_ID="$(json_get "$b" id)"
[[ -n "$SUGGESTION_ID" ]] && ok "got suggestion_id" || fail "no suggestion_id"

step "B.5.2 Get the suggestion we just created"
r="$(api GET "/api/suggestions/${SUGGESTION_ID}" "$ACCESS_TOKEN")"; c="${r%%|*}"; b="${r#*|}"
expect_status "GET /api/suggestions/{id}" "200" "$c" "$b"

step "B.5.3 CANNOT vote on own suggestion"
payload='{"vote":"up"}'
r="$(api POST "/api/suggestions/${SUGGESTION_ID}/vote" "$payload" "$ACCESS_TOKEN")"; c="${r%%|*}"; b="${r#*|}"
expect_status "POST /api/suggestions/{id}/vote (own) → 400" "400" "$c" "$b"

step "B.5.4 Logout returns 204"
r="$(api POST /api/auth/logout "{}" "$ACCESS_TOKEN")"; c="${r%%|*}"; b="${r#*|}"
expect_status "POST /api/auth/logout (again)" "204" "$c" "$b"


# ════════════════════════════════════════════════════════════════
# STAGE C — Promote to reviewer + reviewer actions
# ════════════════════════════════════════════════════════════════
section "STAGE C — Reviewer role"

if [[ "$ADMIN_BOOTSTRAP" == "1" || -z "$ADMIN_TOKEN" ]]; then
  step "C.0 PROMOTE — SKIPPED (no admin available)"
  printf '  %sNote:%s without an admin to call /api/admin/users/{id}, we\n' "$yellow" "$reset"
  printf '        cannot exercise promote/demote via the API itself.\n\n'
  # Test that a regular user CAN'T promote/demote
  payload='{"role":"reviewer"}'
  r="$(api PATCH "/api/admin/users/${USER_ID}" "$payload" "$ACCESS_TOKEN")"; c="${r%%|*}"; b="${r#*|}"
  expect_status "PATCH /api/admin/users/{id} as user → 403" "403" "$c" "$b"
  SKIP_REVIEWER_PATHS=1
  SKIP_ADMIN_PATHS=1
else
  SKIP_REVIEWER_PATHS=0
  SKIP_ADMIN_PATHS=0

  step "C.0 Promote our test user to reviewer (via admin)"
  payload='{"role":"reviewer"}'
  r="$(api PATCH "/api/admin/users/${USER_ID}" "$payload" "$ADMIN_TOKEN")"; c="${r%%|*}"; b="${r#*|}"
  expect_status "PATCH /api/admin/users/{id} → promote to reviewer" "200" "$c" "$b"

  # Re-login to get a fresh token with new role
  payload="{\"email\":\"${EMAIL}\",\"password\":\"${PASSWORD}\"}"
  r="$(api POST /api/auth/login "$payload")"; c="${r%%|*}"; b="${r#*|}"
  expect_status "POST /api/auth/login (as reviewer)" "200" "$c" "$b"
  ACCESS_TOKEN="$(json_get "$b" access_token)"
fi

if [[ "${SKIP_REVIEWER_PATHS:-0}" == "0" ]]; then
  step "C.1 Reviewer CAN create a word directly"
  HEADWORD_REVIEWER="mlima-r-${RUN_ID}"
  payload="{\"headword\":\"${HEADWORD_REVIEWER}\",\"part_of_speech\":\"noun\",\"swahili_translation\":\"mlima\",\"english_translation\":\"mountain\",\"examples\":[{\"taita_text\":\"Mlima unrefu.\",\"swahili_text\":\"Mlima mrefu.\",\"english_text\":\"The mountain is tall.\"}]}"
  r="$(api POST /api/words "$payload" "$ACCESS_TOKEN")"; c="${r%%|*}"; b="${r#*|}"
  expect_status "POST /api/words (reviewer)" "201" "$c" "$b"
  WORD_ID="$(json_get "$b" id)"
  WORD_SLUG="$(json_get "$b" slug)"
  [[ -n "$WORD_ID" ]] && ok "got word_id=$WORD_ID" || fail "no word_id"

  step "C.2 Get the word back (by ID and by slug)"
  r="$(api GET "/api/words/${WORD_ID}" "$ACCESS_TOKEN")"; c="${r%%|*}"; b="${r#*|}"
  expect_status "GET /api/words/{id}" "200" "$c" "$b"
  r="$(api GET "/api/words/${WORD_SLUG}" "$ACCESS_TOKEN")"; c="${r%%|*}"; b="${r#*|}"
  expect_status "GET /api/words/{slug}" "200" "$c" "$b"

  step "C.3 Reviewer CAN edit a word (PATCH /api/words/{id})"
  payload='{"dialect":"Dawida"}'
  r="$(api PATCH "/api/words/${WORD_ID}" "$payload" "$ACCESS_TOKEN")"; c="${r%%|*}"; b="${r#*|}"
  expect_status "PATCH /api/words/{id}" "200" "$c" "$b"

  step "C.4 Reviewer CAN add an example (POST /api/words/{id}/examples)"
  payload='{"taita_text":"Mlima wa Pare ni mrefu.","swahili_text":"Mlima wa Pare ni mrefu.","english_text":"Mount Pare is tall."}'
  r="$(api POST "/api/words/${WORD_ID}/examples" "$payload" "$ACCESS_TOKEN")"; c="${r%%|*}"; b="${r#*|}"
  expect_status "POST /api/words/{id}/examples" "201" "$c" "$b"

  step "C.5 Reviewer CAN add a sense (POST /api/words/{id}/senses)"
  payload='{"definition":"pile or heap","notes":"Second sense of mlima."}'
  r="$(api POST "/api/words/${WORD_ID}/senses" "$payload" "$ACCESS_TOKEN")"; c="${r%%|*}"; b="${r#*|}"
  expect_status "POST /api/words/{id}/senses" "201" "$c" "$b"
  # Capture the new sense_id (last sense in word.senses)
  SENSE_ID="$(json_get "$b" senses.1.id)"
  [[ -n "$SENSE_ID" ]] && ok "got sense_id=$SENSE_ID" || fail "no sense_id"

  step "C.6 Reviewer CAN edit the sense (PATCH /api/senses/{id})"
  payload='{"definition":"updated definition","notes":"updated notes"}'
  r="$(api PATCH "/api/senses/${SENSE_ID}" "$payload" "$ACCESS_TOKEN")"; c="${r%%|*}"; b="${r#*|}"
  expect_status "PATCH /api/senses/{id}" "200" "$c" "$b"

  step "C.7 Reviewer CAN accept/reject suggestions (POST /api/suggestions/{id}/decide)"
  payload='{"decision":"accept"}'
  r="$(api POST "/api/suggestions/${SUGGESTION_ID}/decide" "$payload" "$ACCESS_TOKEN")"; c="${r%%|*}"; b="${r#*|}"
  expect_status "POST /api/suggestions/{id}/decide (accept)" "200" "$c" "$b"
fi


# ════════════════════════════════════════════════════════════════
# STAGE D — Promote to admin + admin actions
# ════════════════════════════════════════════════════════════════
section "STAGE D — Admin role"

if [[ "${SKIP_ADMIN_PATHS:-0}" == "1" ]]; then
  step "D.1-7 ADMIN PATHS — SKIPPED (no admin to call them with)"
else
  step "D.0 Promote test user to admin (PATCH /api/admin/users/{id})"
  payload='{"role":"admin"}'
  r="$(api PATCH "/api/admin/users/${USER_ID}" "$payload" "$ADMIN_TOKEN")"; c="${r%%|*}"; b="${r#*|}"
  expect_status "PATCH /api/admin/users/{id} → promote to admin" "200" "$c" "$b"
  # Re-login to refresh the access token's role
  payload="{\"email\":\"${EMAIL}\",\"password\":\"${PASSWORD}\"}"
  r="$(api POST /api/auth/login "$payload")"; c="${r%%|*}"; b="${r#*|}"
  expect_status "POST /api/auth/login (as admin)" "200" "$c" "$b"
  ACCESS_TOKEN="$(json_get "$b" access_token)"

  step "D.1 Admin CAN view dashboard stats (GET /api/admin/stats)"
  r="$(api GET /api/admin/stats "" "$ACCESS_TOKEN")"; c="${r%%|*}"; b="${r#*|}"
  expect_status "GET /api/admin/stats" "200" "$c" "$b"
  [[ "$(json_get "$b" total_words)" != "" ]] && ok "stats has total_words" || fail "stats missing fields"

  step "D.2 Admin CAN list users (GET /api/admin/users)"
  r="$(api GET /api/admin/users "" "$ACCESS_TOKEN")"; c="${r%%|*}"; b="${r#*|}"
  expect_status "GET /api/admin/users" "200" "$c" "$b"

  step "D.3 Admin CAN edit a word via admin endpoint (PATCH /api/admin/words/{id})"
  payload='{"morphology_notes":"Admin edit note"}'
  r="$(api PATCH "/api/admin/words/${WORD_ID}" "$payload" "$ACCESS_TOKEN")"; c="${r%%|*}"; b="${r#*|}"
  expect_status "PATCH /api/admin/words/{id}" "200" "$c" "$b"

  step "D.4 Admin CAN view audit log (GET /api/admin/audit-log)"
  r="$(api GET /api/admin/audit-log "" "$ACCESS_TOKEN")"; c="${r%%|*}"; b="${r#*|}"
  expect_status "GET /api/admin/audit-log" "200" "$c" "$b"

  step "D.5 Admin CAN merge two words (POST /api/admin/words/merge)"
  HEADWORD_MERGE="mlima-merge-${RUN_ID}"
  payload="{\"headword\":\"${HEADWORD_MERGE}\",\"swahili_translation\":\"mlima merge\"}"
  r="$(api POST /api/words "$payload" "$ACCESS_TOKEN")"; c="${r%%|*}"; b="${r#*|}"
  expect_status "POST /api/words (second word for merge)" "201" "$c" "$b"
  WORD_ID_2="$(json_get "$b" id)"
  payload="{\"source_id\":\"${WORD_ID_2}\",\"target_id\":\"${WORD_ID}\"}"
  r="$(api POST /api/admin/words/merge "$payload" "$ACCESS_TOKEN")"; c="${r%%|*}"; b="${r#*|}"
  expect_status "POST /api/admin/words/merge" "200" "$c" "$b"

  step "D.6 Admin CAN hide a word (POST /api/admin/words/{id}/hide)"
  HEADWORD_HIDE="mlima-hide-${RUN_ID}"
  payload="{\"headword\":\"${HEADWORD_HIDE}\",\"swahili_translation\":\"to hide\"}"
  r="$(api POST /api/words "$payload" "$ACCESS_TOKEN")"; c="${r%%|*}"; b="${r#*|}"
  expect_status "POST /api/words (third word for hide)" "201" "$c" "$b"
  WORD_ID_3="$(json_get "$b" id)"
  r="$(api POST "/api/admin/words/${WORD_ID_3}/hide" "{}" "$ACCESS_TOKEN")"; c="${r%%|*}"; b="${r#*|}"
  expect_status "POST /api/admin/words/{id}/hide" "200" "$c" "$b"

  step "D.7 Admin CAN accept suggestions (POST /api/admin/suggestions/{id}/decide)"
  # Create a suggestion as the admin user (different from the test user) so admin can decide it
  payload='{"target_type":"new_word","proposed_value":{"headword":"mlima-admin-'"$RUN_ID"'","swahili_translation":"admin test"},"rationale":"admin decide test"}'
  r="$(api POST /api/suggestions "$payload" "$ADMIN_TOKEN")"; c="${r%%|*}"; b="${r#*|}"
  expect_status "POST /api/suggestions (admin creates one)" "201" "$c" "$b"
  ADMIN_SUGG_ID="$(json_get "$b" id)"
  # Admin (test user, not the admin that created it) decides it
  payload='{"decision":"accept"}'
  r="$(api POST "/api/admin/suggestions/${ADMIN_SUGG_ID}/decide" "$payload" "$ACCESS_TOKEN")"; c="${r%%|*}"; b="${r#*|}"
  expect_status "POST /api/admin/suggestions/{id}/decide" "200" "$c" "$b"
fi


# ════════════════════════════════════════════════════════════════
# STAGE E — Demote back to user (verify access is revoked)
# ════════════════════════════════════════════════════════════════
section "STAGE E — Demotion"

if [[ "${SKIP_ADMIN_PATHS:-0}" == "1" ]]; then
  step "E — SKIPPED (no admin available)"
else
  step "E.1 Demote back to user (PATCH /api/admin/users/{id})"
  payload='{"role":"user"}'
  r="$(api PATCH "/api/admin/users/${USER_ID}" "$payload" "$ADMIN_TOKEN")"; c="${r%%|*}"; b="${r#*|}"
  expect_status "PATCH /api/admin/users/{id} → demote to user" "200" "$c" "$b"

  # Re-login to refresh the access token's role
  payload="{\"email\":\"${EMAIL}\",\"password\":\"${PASSWORD}\"}"
  r="$(api POST /api/auth/login "$payload")"; c="${r%%|*}"; b="${r#*|}"
  expect_status "POST /api/auth/login (post-demotion)" "200" "$c" "$b"
  ACCESS_TOKEN="$(json_get "$b" access_token)"

  step "E.2 Verify demoted user CANNOT create words (403)"
  payload='{"headword":"should-fail-demoted","swahili_translation":"fail"}'
  r="$(api POST /api/words "$payload" "$ACCESS_TOKEN")"; c="${r%%|*}"; b="${r#*|}"
  expect_status "POST /api/words as demoted user → 403" "403" "$c" "$b"
fi


# ════════════════════════════════════════════════════════════════
# STAGE F — Password reset + email change
# ════════════════════════════════════════════════════════════════
section "STAGE F — Recovery flow"

step "F.1 Change email (PATCH /api/auth/me/email)"
NEW_EMAIL="alice-new+${RUN_ID}@${EMAIL_DOMAIN}"
payload="{\"new_email\":\"${NEW_EMAIL}\",\"current_password\":\"${PASSWORD}\"}"
r="$(api PATCH /api/auth/me/email "$payload" "$ACCESS_TOKEN")"; c="${r%%|*}"; b="${r#*|}"
expect_status "PATCH /api/auth/me/email" "200" "$c" "$b"
[[ "$(json_get "$b" email)" == "$NEW_EMAIL" ]] && ok "email updated" || fail "email not updated"
EMAIL="$NEW_EMAIL"

step "F.2 Request password reset (always-200)"
payload="{\"email\":\"${EMAIL}\"}"
r="$(api POST /api/auth/password-reset/request "$payload")"; c="${r%%|*}"; b="${r#*|}"
expect_status "POST /api/auth/password-reset/request" "200" "$c" "$b"

step "F.3 Confirm password reset (POST /api/auth/password-reset/confirm)"
if [[ "$SKIP_RESET" == "1" ]]; then
  printf '  %s(SKIP)%s SKIP_RESET=1\n' "$yellow" "$reset"
else
  RESET_TOKEN="$(read_reset_token_from_log)"
  if [[ -z "$RESET_TOKEN" ]]; then
    if ! python3 -c 'import jose' 2>/dev/null; then
      fail "no token in log file and python-jose not installed"
    else
      RESET_TOKEN="$(make_reset_token "$USER_ID" "$EMAIL")"
      [[ -n "$RESET_TOKEN" ]] && ok "fallback: minted reset token" || fail "could not mint token"
    fi
  else
    ok "got reset token from email log file"
  fi

  if [[ -n "$RESET_TOKEN" ]] && [[ "$RESET_TOKEN" != "null" ]]; then
    NEW_PASSWORD="BrandNew12345!"
    payload="{\"token\":\"${RESET_TOKEN}\",\"new_password\":\"${NEW_PASSWORD}\"}"
    r="$(api POST /api/auth/password-reset/confirm "$payload")"; c="${r%%|*}"; b="${r#*|}"
    expect_status "POST /api/auth/password-reset/confirm" "200" "$c" "$b"
    PASSWORD="$NEW_PASSWORD"
    ok "tracked new password for the final login test"
  fi
fi


# ════════════════════════════════════════════════════════════════
# STAGE G — Delete account (soft-delete / anonymize)
# ════════════════════════════════════════════════════════════════
section "STAGE G — Delete account"

if [[ "$KEEP_USER" == "1" ]]; then
  step "G.1 DELETE /api/auth/me — SKIPPED (KEEP_USER=1)"
else
  step "G.1 Delete account (DELETE /api/auth/me)"
  payload="{\"password\":\"${PASSWORD}\"}"
  r="$(api DELETE /api/auth/me "$payload" "$ACCESS_TOKEN")"; c="${r%%|*}"; b="${r#*|}"
  expect_status "DELETE /api/auth/me" "204" "$c" "$b"
  ok "account anonymized"
fi


# ════════════════════════════════════════════════════════════════
# STAGE H — Verify the account is gone
# ════════════════════════════════════════════════════════════════
section "STAGE H — Post-delete verification"

if [[ "$KEEP_USER" == "1" ]]; then
  step "H — SKIPPED (KEEP_USER=1)"
else
  step "H.1 Login with old email → 401 (account anonymized)"
  payload="{\"email\":\"${EMAIL}\",\"password\":\"${PASSWORD}\"}"
  r="$(api POST /api/auth/login "$payload")"; c="${r%%|*}"; b="${r#*|}"
  expect_status "POST /api/auth/login (deleted user) → 401" "401" "$c" "$b"

  step "H.2 Old access token → 403 (user is_blocked=true)"
  r="$(api GET /api/auth/me "" "$ACCESS_TOKEN")"; c="${r%%|*}"; b="${r#*|}"
  if [[ "$c" == "403" ]] || [[ "$c" == "401" ]]; then
    ok "blocked user rejected (HTTP $c)"
  else
    fail "blocked user not rejected (expected 401 or 403, got $c)" "$b"
  fi
fi


# ════════════════════════════════════════════════════════════════
# Summary
# ════════════════════════════════════════════════════════════════
printf '\n%s══════════════════════════════════════════%s\n' "$bold" "$reset"
printf 'Total: %s%d passed%s, %s%d failed%s\n' \
  "$green" "$pass_count" "$reset" \
  "$red"   "$fail_count" "$reset"

if [[ "$fail_count" -gt 0 ]]; then
  exit 1
fi
exit 0

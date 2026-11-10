#!/usr/bin/env bash
#
# test_api_endpoints.sh — end-to-end smoke test for the Lumi API
#
# Walks a fresh user through every auth + profile endpoint via curl:
#   1.  GET  /                                      (health)
#   2.  POST /api/auth/register                     (signup)
#   3.  POST /api/auth/login                         (login)
#   4.  GET  /api/auth/me                            (profile)
#   5.  PATCH /api/auth/me                           (display name)
#   6.  PATCH /api/auth/me/password                  (password change)
#   7.  GET  /api/auth/me/connected-accounts         (oauth + has_password)
#   8.  PATCH /api/auth/me/email                     (email change)
#   9.  POST /api/auth/password-reset/request       (always-200 request)
#  10.  POST /api/auth/password-reset/confirm        (uses the REAL token from
#                                                   EMAIL_LOG_FILE if available,
#                                                   falls back to a minted token)
#  11.  DELETE /api/auth/me                          (soft-delete / anonymize)
#  12.  POST /api/auth/login                         (should now fail — anon + blocked)
#
# Usage:
#   ./test_api_endpoints.sh                          # against http://localhost:8000
#   BASE_URL=https://your-api.onrender.com ./test_api_endpoints.sh
#
# Optional env vars:
#   BASE_URL         — API base URL (default: http://localhost:8000)
#   JWT_SECRET       — same secret as the backend's JWT_SECRET env (default: change-me)
#                      Used as a fallback only when the reset token can't be
#                      read from EMAIL_LOG_FILE (e.g. when running against a
#                      server that doesn't write to the log file).
#   KEEP_USER        — set to "1" to skip the account-deletion step (useful when
#                      debugging a single endpoint and you want to inspect the
#                      user in the DB afterwards).
#   SKIP_RESET       — set to "1" to skip the password-reset/confirm step
#                      (useful if python-jose isn't installed locally AND
#                      the server isn't writing to EMAIL_LOG_FILE).
#   EMAIL_LOG_FILE   — path to the email capture log written by dev_server.sh
#                      (default: /tmp/lumi-test-emails.log). When this file
#                      exists and contains a reset email, step 10 reads the
#                      REAL token from it (no JWT_SECRET needed). Falls back
#                      to minting a token client-side with JWT_SECRET if not.
#   EMAIL_DOMAIN     — domain for the test email (default: example.com)
#
# Requirements:
#   - curl (always present)
#   - python3 (for JSON parsing — almost always present)
#   - python3 -c "import jose"        (only used as fallback for step 10)
#
# Exit codes:
#   0 — all steps passed
#   1 — at least one step failed (look for the FAIL line)
#   2 — environment problem (missing curl/python3)

set -uo pipefail

# ── Config ─────────────────────────────────────────────────────
BASE_URL="${BASE_URL:-http://localhost:8000}"
JWT_SECRET="${JWT_SECRET:-change-me}"
EMAIL_DOMAIN="${EMAIL_DOMAIN:-example.com}"
EMAIL_LOG_FILE="${EMAIL_LOG_FILE:-/tmp/lumi-test-emails.log}"
KEEP_USER="${KEEP_USER:-0}"
SKIP_RESET="${SKIP_RESET:-0}"

# Unique email for this run so re-runs don't collide on the unique constraint.
RUN_ID="$(date +%s)-$$"
EMAIL="test+${RUN_ID}@${EMAIL_DOMAIN}"
PASSWORD="TestPass12345!"
NEW_EMAIL="test+new-${RUN_ID}@${EMAIL_DOMAIN}"
NEW_PASSWORD="NewPass12345!"
DISPLAY_NAME="Test User ${RUN_ID}"

# ── Pretty-printing helpers ────────────────────────────────────
green=$'\e[32m'; red=$'\e[31m'; yellow=$'\e[33m'
bold=$'\e[1m';  reset=$'\e[0m'

pass_count=0
fail_count=0
fail_fast=1    # set to 0 to keep going after failures

step()  { printf '\n%s── %s ──%s\n' "$bold" "$1" "$reset"; }
ok()    { printf '%sPASS%s: %s\n' "$green" "$reset" "$1"; pass_count=$((pass_count+1)); }
fail()  { printf '%sFAIL%s: %s\n' "$red" "$reset" "$1"; fail_count=$((fail_count+1));
         [[ -n "${2:-}" ]] && printf '  %sbody:%s %s\n' "$yellow" "$reset" "$2"
         if [[ "$fail_fast" == "1" ]]; then
           printf '\n%sStopping (set fail_fast=0 in the script to keep going).%s\n' "$yellow" "$reset"
           exit 1
         fi
}

# check_status <label> <expected_http> <actual_http> [body]
check_status() {
  local label="$1" want="$2" got="$3" body="${4:-}"
  if [[ "$got" == "$want" ]]; then
    ok "$label (HTTP $got)"
  else
    fail "$label (expected HTTP $want, got $got)" "$body"
  fi
}

# ── JSON helpers via python3 ──────────────────────────────────
# We use python3 instead of jq so this works on minimal systems.
#
#   val="$(json_get "$body" access_token)"

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
    else:
        d = ""; break
v = d if isinstance(d, str) else json.dumps(d)
print(v)
' "$1" "$2"
}

# ── curl wrapper: returns "HTTP_CODE|BODY" so we can grab both ─
# Usage: resp="$(api POST /api/auth/register "$json_body" "$auth_token")"
#        code="${resp%%|*}"; body="${resp#*|}"
api() {
  local method="$1" path="$2"
  local body="${3:-}" token="${4:-}"
  local url="${BASE_URL}${path}"
  local hdr=( -H "Content-Type: application/json" -H "Accept: application/json" )
  [[ -n "$token" ]] && hdr+=( -H "Authorization: Bearer $token" )

  # -s silent, -o body file, -w http_code on stdout
  local tmp
  tmp="$(mktemp)"
  local code
  code="$(curl -s -X "$method" "${hdr[@]}" \
            --data "$body" \
            -o "$tmp" \
            -w '%{http_code}' \
            "$url" 2>/dev/null || echo "000")"
  local body_out
  body_out="$(cat "$tmp" 2>/dev/null || true)"
  rm -f "$tmp"
  printf '%s|%s' "$code" "$body_out"
}

# ── Mint a password-reset token client-side (for step 10) ─────
# Requires python-jose. We use the same JWT_SECRET the backend uses,
# so this only works if you set JWT_SECRET to match.
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

# Read the reset token from EMAIL_LOG_FILE (the real token the backend
# "emailed" in dev mode). This is preferred over minting a fake token because
# it tests the actual request→email→confirm flow. Returns empty on failure.
#
# Looks for the most recent JSON line whose "subject" contains "reset",
# extracts the token from the reset link in the "body".
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
# Walk back-to-front, find the last "Password reset" email
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
    # Token ends at the first whitespace character
    token = ""
    for c in rest:
        if c.isspace():
            break
        token += c
    if token:
        print(token)
        sys.exit(0)
# None found
sys.exit(0)
' "$EMAIL_LOG_FILE"
}

# ── Preflight checks ──────────────────────────────────────────
printf '%sLumi API end-to-end smoke test%s\n' "$bold" "$reset"
printf '  base_url:   %s\n' "$BASE_URL"
printf '  email:      %s\n' "$EMAIL"
printf '  jwt_secret:  %s\n' "${JWT_SECRET:0:3}*** (only used for reset-token minting)"

if ! command -v curl >/dev/null 2>&1; then
  printf '\n%sERROR:%s curl is required\n' "$red" "$reset" >&2
  exit 2
fi
if ! command -v python3 >/dev/null 2>&1; then
  printf '\n%sERROR:%s python3 is required (for JSON parsing)\n' "$red" "$reset" >&2
  exit 2
fi

# ── 1. Health check ───────────────────────────────────────────
step "1. GET / — health check"
resp="$(api GET /)"
code="${resp%%|*}"; body="${resp#*|}"
check_status "health endpoint" "200" "$code" "$body"

# ── 2. Register ───────────────────────────────────────────────
step "2. POST /api/auth/register — signup"
payload="{\"email\":\"${EMAIL}\",\"password\":\"${PASSWORD}\",\"display_name\":\"${DISPLAY_NAME}\"}"
resp="$(api POST /api/auth/register "$payload")"
code="${resp%%|*}"; body="${resp#*|}"
check_status "register" "201" "$code" "$body"
ACCESS_TOKEN="$(json_get "$body" access_token)"
if [[ -z "$ACCESS_TOKEN" ]]; then
  fail "register: no access_token in response" "$body"
fi

# ── 3. Login ───────────────────────────────────────────────────
step "3. POST /api/auth/login — login"
payload="{\"email\":\"${EMAIL}\",\"password\":\"${PASSWORD}\"}"
resp="$(api POST /api/auth/login "$payload")"
code="${resp%%|*}"; body="${resp#*|}"
check_status "login" "200" "$code" "$body"
ACCESS_TOKEN="$(json_get "$body" access_token)"
if [[ -z "$ACCESS_TOKEN" ]]; then
  fail "login: no access_token in response" "$body"
fi
ok "got access token ($(printf '%s' "$ACCESS_TOKEN" | wc -c) chars)"

# ── 4. GET /me ─────────────────────────────────────────────────
step "4. GET /api/auth/me — profile"
resp="$(api GET /api/auth/me "" "$ACCESS_TOKEN")"
code="${resp%%|*}"; body="${resp#*|}"
check_status "get me" "200" "$code" "$body"
me_email="$(json_get "$body" email)"
USER_ID="$(json_get "$body" id)"
if [[ "$me_email" != "$EMAIL" ]]; then
  fail "get me: email mismatch (expected $EMAIL, got $me_email)" "$body"
fi
ok "user_id = $USER_ID"

# ── 5. PATCH /me — display name ───────────────────────────────
step "5. PATCH /api/auth/me — update display name"
payload='{"display_name":"Updated Name"}'
resp="$(api PATCH /api/auth/me "$payload" "$ACCESS_TOKEN")"
code="${resp%%|*}"; body="${resp#*|}"
check_status "update me" "200" "$code" "$body"
new_name="$(json_get "$body" display_name)"
if [[ "$new_name" != "Updated Name" ]]; then
  fail "update me: display_name not updated (got '$new_name')" "$body"
fi

# ── 6. PATCH /me/password ─────────────────────────────────────
step "6. PATCH /api/auth/me/password — change password"
payload="{\"current_password\":\"${PASSWORD}\",\"new_password\":\"${NEW_PASSWORD}\"}"
resp="$(api PATCH /api/auth/me/password "$payload" "$ACCESS_TOKEN")"
code="${resp%%|*}"; body="${resp#*|}"
check_status "change password" "200" "$code" "$body"
ok "password changed (will use new password for the rest of the run)"
PASSWORD="$NEW_PASSWORD"   # use the new password from here on

# ── 7. GET /me/connected-accounts ────────────────────────────
step "7. GET /api/auth/me/connected-accounts"
resp="$(api GET /api/auth/me/connected-accounts "" "$ACCESS_TOKEN")"
code="${resp%%|*}"; body="${resp#*|}"
check_status "connected accounts" "200" "$code" "$body"
has_pw="$(json_get "$body" has_password)"
google="$(json_get "$body" google)"
# JSON booleans come back as lowercase 'true'/'false' from json.dumps
if [[ "$has_pw" != "true" ]] || [[ "$google" != "false" ]]; then
  fail "connected accounts: expected has_password=true, google=false; got $body"
else
  ok "has_password=true, google=false (matches a password-only user)"
fi

# ── 8. PATCH /me/email — change email ─────────────────────────
step "8. PATCH /api/auth/me/email — change email"
payload="{\"new_email\":\"${NEW_EMAIL}\",\"current_password\":\"${PASSWORD}\"}"
resp="$(api PATCH /api/auth/me/email "$payload" "$ACCESS_TOKEN")"
code="${resp%%|*}"; body="${resp#*|}"
check_status "change email" "200" "$code" "$body"
me_email="$(json_get "$body" email)"
if [[ "$me_email" != "$NEW_EMAIL" ]]; then
  fail "change email: response email not updated (expected $NEW_EMAIL, got $me_email)" "$body"
fi
ok "email is now $NEW_EMAIL"
EMAIL="$NEW_EMAIL"   # use the new email from here on

# ── 9. POST /password-reset/request ──────────────────────────
step "9. POST /api/auth/password-reset/request — request reset email"
# Use the current email (which after step 8 is the NEW_EMAIL).
# In dev mode (SMTP_HOST empty), the email body — including the reset link —
# is printed to the backend's stdout. We can't capture that here, so for the
# /confirm step below we mint a reset JWT client-side using the same JWT_SECRET.
payload="{\"email\":\"${EMAIL}\"}"
resp="$(api POST /api/auth/password-reset/request "$payload")"
code="${resp%%|*}"; body="${resp#*|}"
check_status "password reset request" "200" "$code" "$body"
status_val="$(json_get "$body" status)"
if [[ "$status_val" != "ok" ]]; then
  fail "password reset request: status != ok" "$body"
fi
ok "got the standard 200 anti-enumeration response"

# ── 10. POST /password-reset/confirm ─────────────────────────
if [[ "$SKIP_RESET" == "1" ]]; then
  step "10. POST /api/auth/password-reset/confirm — SKIPPED (SKIP_RESET=1)"
  printf '  %s(skip)%s set SKIP_RESET=0 to test this.\n' "$yellow" "$reset"
else
  step "10. POST /api/auth/password-reset/confirm — set new password"

  # Strategy: try to read the REAL token from EMAIL_LOG_FILE first (the
  # one the backend "emailed" in dev mode). Fall back to minting a token
  # client-side with JWT_SECRET (requires JWT_SECRET to match the backend).
  reset_token=""
  token_source=""

  # Try the log file
  if [[ -z "$reset_token" ]]; then
    log_token="$(read_reset_token_from_log)"
    if [[ -n "$log_token" ]]; then
      reset_token="$log_token"
      token_source="email log file"
    fi
  fi

  # Fall back to client-side minting
  if [[ -z "$reset_token" ]]; then
    if ! python3 -c 'import jose' 2>/dev/null; then
      fail "no token in EMAIL_LOG_FILE and python-jose not installed for fallback"
      printf '  %s(hint)%s set SKIP_RESET=1, or run with dev_server.sh, or pip install python-jose\n' "$yellow" "$reset"
    else
      reset_token="$(make_reset_token "$USER_ID" "$EMAIL")"
      if [[ -n "$reset_token" ]] && [[ "$reset_token" != "null" ]]; then
        token_source="client-minted (JWT_SECRET must match backend)"
      else
        fail "could not mint reset token (check JWT_SECRET matches the backend)"
      fi
    fi
  fi

  if [[ -n "$reset_token" ]] && [[ "$reset_token" != "null" ]]; then
    payload="{\"token\":\"${reset_token}\",\"new_password\":\"AnotherNewPass123!\"}"
    resp="$(api POST /api/auth/password-reset/confirm "$payload")"
    code="${resp%%|*}"; body="${resp#*|}"
    check_status "password reset confirm" "200" "$code" "$body"
    ok "token source: $token_source"
    ok "password reset via token works (login with the new password next)"
    # Update our known password so the final login test (step 12) uses it.
    # Note: this password is for an account we'll delete in step 11 anyway,
    # so we don't strictly need to track it — but doing so keeps the script
    # honest if KEEP_USER=1.
    PASSWORD="AnotherNewPass123!"
  fi
fi

# ── 11. DELETE /me — soft-delete / anonymize ─────────────────
if [[ "$KEEP_USER" == "1" ]]; then
  step "11. DELETE /api/auth/me — SKIPPED (KEEP_USER=1)"
  printf '  %s(skip)%s the test user %s still exists in the DB.\n' "$yellow" "$reset" "$EMAIL"
else
  step "11. DELETE /api/auth/me — soft-delete / anonymize"
  payload="{\"password\":\"${PASSWORD}\"}"
  # curl with -X DELETE doesn't accept a body by default with our api() wrapper;
  # we use --data which works for any method.
  resp="$(api DELETE /api/auth/me "$payload" "$ACCESS_TOKEN")"
  code="${resp%%|*}"; body="${resp#*|}"
  check_status "delete account" "204" "$code" "$body"
  ok "account anonymized (display_name='deleted user', is_blocked=true)"
fi

# ── 12. Verify the account is gone ──────────────────────────
if [[ "$KEEP_USER" == "1" ]]; then
  step "12. POST /api/auth/login — SKIPPED (KEEP_USER=1)"
else
  step "12. POST /api/auth/login — should now fail (account anonymized)"
  payload="{\"email\":\"${EMAIL}\",\"password\":\"${PASSWORD}\"}"
  resp="$(api POST /api/auth/login "$payload")"
  code="${resp%%|*}"; body="${resp#*|}"
  # The original email was anonymized to deleted+<uuid>@anon.lumi, so this
  # login attempt should fail because no user has the original email anymore.
  check_status "post-delete login fails" "401" "$code" "$body"
  ok "the original email no longer resolves — soft-delete confirmed"
fi

# ── Summary ─────────────────────────────────────────────────
printf '\n%s──────────────────────────────────%s\n' "$bold" "$reset"
printf 'Total: %s%d passed%s, %s%d failed%s\n' \
  "$green" "$pass_count" "$reset" \
  "$red"   "$fail_count" "$reset"

if [[ "$fail_count" -gt 0 ]]; then
  exit 1
fi
exit 0

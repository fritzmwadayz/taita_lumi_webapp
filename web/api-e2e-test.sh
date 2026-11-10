#!/usr/bin/env bash
#
# Lumi — API End-to-End Test Script
# ============================================================================
#
# Walks through the full user lifecycle via the API:
#   register → login → session → profile → change password → change email
#   → password reset request → password reset confirm → logout
#   → (post-logout 401 checks) → delete account
#
# Uses curl + a cookie jar so the httpOnly session cookie persists across
# requests, exactly like a real browser session.
#
# Tests the endpoints the frontend relies on — including the new ones from
# the UI/UX additions contract (marked NEW):
#   POST   /api/auth/register
#   POST   /api/auth/login
#   POST   /api/auth/logout
#   GET    /api/_auth/session
#   GET    /api/auth/me/stats
#   GET    /api/auth/me/connected-accounts          ← NEW
#   PATCH  /api/auth/me
#   PATCH  /api/auth/me/password
#   PATCH  /api/auth/me/email                       ← NEW
#   POST   /api/auth/password-reset/request         ← NEW
#   POST   /api/auth/password-reset/confirm         ← NEW
#   DELETE /api/auth/me                             ← NEW
#
# ----------------------------------------------------------------------------
# Usage:
#   ./api-e2e-test.sh                              # run against localhost:3000
#   BASE_URL=http://localhost:3000 ./api-e2e-test.sh
#   VERBOSE=1 ./api-e2e-test.sh                    # show response bodies
#   SKIP_DESTRUCTION=1 ./api-e2e-test.sh           # skip delete-account tests
#
# Prerequisites:
#   - Nuxt dev server running (npm run dev) → http://localhost:3000
#   - FastAPI backend running → http://localhost:8000
#   - curl installed
#   - jq or python3 (optional, for pretty-printing JSON responses)
#
# ============================================================================

set -uo pipefail

# ─── Config ─────────────────────────────────────────────────────────────────
BASE_URL="${BASE_URL:-http://localhost:3000}"
TEST_EMAIL_PREFIX="${TEST_EMAIL_PREFIX:-lumi-e2e-}"
INITIAL_PASSWORD="TestPass123!"
VERBOSE="${VERBOSE:-0}"
SKIP_DESTRUCTION="${SKIP_DESTRUCTION:-0}"

# ─── Temp files ─────────────────────────────────────────────────────────────
COOKIE_JAR=$(mktemp)
trap 'rm -f "$COOKIE_JAR"' EXIT

# ─── Colors (disabled if not a TTY) ─────────────────────────────────────────
if [[ -t 1 ]]; then
  GREEN=$'\033[32m'; RED=$'\033[31m'; YELLOW=$'\033[33m'
  CYAN=$'\033[36m'; BOLD=$'\033[1m'; DIM=$'\033[2m'; RESET=$'\033[0m'
else
  GREEN=''; RED=''; YELLOW=''; CYAN=''; BOLD=''; DIM=''; RESET=''
fi

PASS=0; FAIL=0

# ─── Helpers ────────────────────────────────────────────────────────────────

section() {
  echo ""
  echo "${BOLD}${CYAN}──────────────────────────────────────────────────────────────────"
  echo "  $1"
  echo "──────────────────────────────────────────────────────────────────${RESET}"
}

# Pretty-print JSON if jq or python3 is available, else echo raw.
pp() {
  if command -v jq &>/dev/null; then
    echo "$1" | jq . 2>/dev/null || echo "$1"
  elif command -v python3 &>/dev/null; then
    echo "$1" | python3 -m json.tool 2>/dev/null || echo "$1"
  else
    echo "$1"
  fi
}

# request METHOD PATH [JSON_BODY]
# Sets STATUS (http code) and BODY (response text) globals.
request() {
  local method="$1" path="$2" body="${3:-}"
  local url="${BASE_URL}${path}"
  local tmp; tmp=$(mktemp)
  local args=(-s -o "$tmp" -w '%{http_code}'
              -X "$method" "$url"
              -H 'Content-Type: application/json'
              -b "$COOKIE_JAR" -c "$COOKIE_JAR")
  if [[ -n "$body" ]]; then
    args+=(--data-raw "$body")
  fi
  STATUS=$(curl "${args[@]}" 2>/dev/null)
  BODY=$(cat "$tmp")
  rm -f "$tmp"
}

# expect STATUS_CODE [label]  — checks the last request's status.
expect() {
  local expected="$1" label="${2:-}"
  if [[ "$STATUS" == "$expected" ]]; then
    echo "  ${GREEN}✓ PASS${RESET}  ${label:-status $STATUS}  ${DIM}($STATUS)${RESET}"
    PASS=$((PASS + 1))
  else
    echo "  ${RED}✗ FAIL${RESET}  ${label:-status}  ${DIM}(expected $expected, got $STATUS)${RESET}"
    if [[ -n "$BODY" ]]; then
      echo "         ${DIM}body: $(echo "$BODY" | head -c 300)${RESET}"
    fi
    FAIL=$((FAIL + 1))
  fi
}

# show the last response body (only if VERBOSE=1)
show_body() {
  if [[ "$VERBOSE" == "1" && -n "$BODY" ]]; then
    echo "  ${DIM}body: $(pp "$BODY")${RESET}"
  fi
}

# Pre-flight: bail early if the dev server isn't reachable.
preflight() {
  section "Pre-flight — server reachability"
  local code
  code=$(curl -s -o /dev/null -w '%{http_code}' "$BASE_URL/" 2>/dev/null)
  if [[ "$code" == "000" || -z "$code" ]]; then
    echo "  ${RED}✗ Cannot reach $BASE_URL${RESET}"
    echo "  Start the dev server first:  ${BOLD}npm run dev${RESET}"
    exit 1
  fi
  echo "  ${GREEN}✓ Server reachable at $BASE_URL${RESET}  ${DIM}(GET / → $code)${RESET}"
}

# ═══════════════════════════════════════════════════════════════════════════
# TEST FLOW BEGINS
# ═══════════════════════════════════════════════════════════════════════════

preflight

# Timestamp guarantees a fresh user each run (no collision with prior runs).
TS=$(date +%s)
EMAIL_A="${TEST_EMAIL_PREFIX}${TS}@example.com"
EMAIL_B="${TEST_EMAIL_PREFIX}b-${TS}@example.com"
EMAIL_C="${TEST_EMAIL_PREFIX}c-${TS}@example.com"   # for the email-change test
PASSWORD="$INITIAL_PASSWORD"

# ─── 1. Setup — register two test users ─────────────────────────────────────
section "Setup — register test users"
echo "  ${DIM}User A: $EMAIL_A${RESET}"
echo "  ${DIM}User B: $EMAIL_B  (used for the email-taken 409 test)${RESET}"

request POST /api/auth/register \
  "{\"email\":\"$EMAIL_A\",\"password\":\"$PASSWORD\",\"display_name\":\"E2E Tester A\"}"
expect 200 "register user A"

request POST /api/auth/register \
  "{\"email\":\"$EMAIL_B\",\"password\":\"$PASSWORD\",\"display_name\":\"E2E Tester B\"}"
expect 200 "register user B"
show_body

# ─── 2. Auth — login ────────────────────────────────────────────────────────
section "Auth — login"

# Register auto-logged-in as B; explicitly log in as A now.
request POST /api/auth/login "{\"email\":\"$EMAIL_A\",\"password\":\"$PASSWORD\"}"
expect 200 "login with correct credentials"
show_body

# Wrong password → 401
request POST /api/auth/login "{\"email\":\"$EMAIL_A\",\"password\":\"wrongpassword\"}"
expect 401 "login with wrong password → 401"

# ─── 3. Auth — session ──────────────────────────────────────────────────────
section "Auth — session"
request GET /api/_auth/session
expect 200 "fetch session"
if echo "$BODY" | grep -q "$EMAIL_A"; then
  echo "  ${GREEN}✓ PASS${RESET}  session contains user A's email"
  PASS=$((PASS + 1))
else
  echo "  ${RED}✗ FAIL${RESET}  session missing user A's email"
  FAIL=$((FAIL + 1))
fi
show_body

# ─── 4. Profile — connected accounts (NEW) ──────────────────────────────────
section "Profile — connected accounts"
request GET /api/auth/me/connected-accounts
expect 200 "fetch connected accounts"
# Body should report has_password: true, google: false for a password-registered user.
if echo "$BODY" | grep -q '"has_password": *true'; then
  echo "  ${GREEN}✓ PASS${RESET}  has_password = true"
  PASS=$((PASS + 1))
else
  echo "  ${YELLOW}? WARN${RESET}  has_password not true in response"
fi
show_body

# ─── 5. Profile — stats ─────────────────────────────────────────────────────
section "Profile — stats"
request GET /api/auth/me/stats
expect 200 "fetch my stats"
show_body

# ─── 6. Profile — update display name ───────────────────────────────────────
section "Profile — update display name"
request PATCH /api/auth/me '{"display_name":"E2E Renamed"}'
expect 200 "update display name"
show_body

# ─── 7. Security — change password ──────────────────────────────────────────
section "Security — change password"
# Wrong current password → 401
request PATCH /api/auth/me/password \
  '{"current_password":"wrong","new_password":"NewPass456!"}'
expect 401 "change password with wrong current → 401"
# Correct
request PATCH /api/auth/me/password \
  "{\"current_password\":\"$PASSWORD\",\"new_password\":\"NewPass456!\"}"
expect 200 "change password with correct current"
show_body
PASSWORD="NewPass456!"  # track the new password for subsequent tests

# ─── 8. Profile — change email (NEW) ────────────────────────────────────────
section "Profile — change email"
# Wrong password → 401
request PATCH /api/auth/me/email \
  "{\"new_email\":\"$EMAIL_C\",\"current_password\":\"wrong\"}"
expect 401 "change email with wrong password → 401"
# Email already taken (EMAIL_B belongs to user B) → 409
request PATCH /api/auth/me/email \
  "{\"new_email\":\"$EMAIL_B\",\"current_password\":\"$PASSWORD\"}"
expect 409 "change email to an address already in use → 409"
# Valid change → 200
request PATCH /api/auth/me/email \
  "{\"new_email\":\"$EMAIL_C\",\"current_password\":\"$PASSWORD\"}"
expect 200 "change email to a new address → 200"
show_body
EMAIL_A="$EMAIL_C"  # user A's email is now EMAIL_C
echo "  ${DIM}User A's email is now $EMAIL_A${RESET}"

# ─── 9. Password reset — request (NEW) ──────────────────────────────────────
section "Password reset — request"
# Valid email → 200 (always, even if account doesn't exist)
request POST /api/auth/password-reset/request "{\"email\":\"$EMAIL_A\"}"
expect 200 "request reset for existing email"
show_body
# Non-existent email → still 200 (enumeration protection)
request POST /api/auth/password-reset/request \
  '{"email":"definitely-not-a-user-xyz@example.com"}'
expect 200 "request reset for non-existent email → still 200"
show_body
# Invalid email format → 422
request POST /api/auth/password-reset/request '{"email":"not-an-email"}'
expect 422 "request reset with invalid email format → 422"

# ─── 10. Password reset — confirm (NEW) ─────────────────────────────────────
section "Password reset — confirm"
# Bogus token → 400 (invalid/expired)
request POST /api/auth/password-reset/confirm \
  '{"token":"bogus-token-that-does-not-exist","new_password":"AnotherPass789!"}'
expect 400 "confirm with invalid token → 400"
show_body
# Password too short → 422
request POST /api/auth/password-reset/confirm \
  '{"token":"bogus-token","new_password":"short"}'
expect 422 "confirm with too-short password → 422"
# NOTE: testing the happy path requires the real token from the email,
# which this script can't read. See the script header for how to extend.

# ─── 11. Auth — logout ──────────────────────────────────────────────────────
section "Auth — logout"
request POST /api/auth/logout '{}'
expect 200 "logout"
show_body

# ─── 12. Auth — after logout ────────────────────────────────────────────────
section "Auth — after logout (session should be gone)"
request GET /api/auth/me/stats
expect 401 "stats after logout → 401"
request GET /api/auth/me/connected-accounts
expect 401 "connected accounts after logout → 401"

# ─── 13. Danger zone — delete account (NEW) ────────────────────────────────
if [[ "$SKIP_DESTRUCTION" == "1" ]]; then
  section "Danger zone — delete account (SKIPPED via SKIP_DESTRUCTION=1)"
else
  section "Danger zone — delete account"
  # Log back in as A (using the new email + new password)
  request POST /api/auth/login "{\"email\":\"$EMAIL_A\",\"password\":\"$PASSWORD\"}"
  expect 200 "login again for deletion test"
  # Wrong password → 401
  request DELETE /api/auth/me '{"password":"wrong"}'
  expect 401 "delete account with wrong password → 401"
  # Correct password → 204
  request DELETE /api/auth/me "{\"password\":\"$PASSWORD\"}"
  expect 204 "delete account with correct password → 204"
  show_body
  # Account is gone — login should fail
  request POST /api/auth/login "{\"email\":\"$EMAIL_A\",\"password\":\"$PASSWORD\"}"
  expect 401 "login with deleted account → 401"

  # ─── 14. Cleanup — delete user B ──────────────────────────────────────────
  section "Cleanup — delete user B"
  request POST /api/auth/login "{\"email\":\"$EMAIL_B\",\"password\":\"$INITIAL_PASSWORD\"}"
  expect 200 "login as user B for cleanup"
  request DELETE /api/auth/me "{\"password\":\"$INITIAL_PASSWORD\"}"
  expect 204 "delete user B"
fi

# ═══════════════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════════════
TOTAL=$((PASS + FAIL))
echo ""
echo "${BOLD}──────────────────────────────────────────────────────────────────${RESET}"
echo "  Total: $TOTAL    ${GREEN}Passed: $PASS${RESET}    ${RED}Failed: $FAIL${RESET}"
echo ""

if [[ "$FAIL" -gt 0 ]]; then
  echo "${RED}Some tests failed. Re-run with VERBOSE=1 to inspect response bodies.${RESET}"
  exit 1
else
  echo "${GREEN}All tests passed.${RESET}"
  exit 0
fi

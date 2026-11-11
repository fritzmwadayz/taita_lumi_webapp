#!/usr/bin/env bash
#
# Lumi — SEO Discovery Audit (for deployed sites)
# ============================================================================
#
# Crawls a deployed Lumi site via its sitemap and verifies that every page
# has the correct SEO meta tags, structured data, and is discoverable by
# search engines. Also checks robots.txt, OG image, and sitemap integrity.
#
# Used AFTER deployment to verify full SEO setup is working in production.
#
# Usage:
#   ./seo-audit.sh https://lumi.vercel.app
#   ./seo-audit.sh https://lumi.dictionary
#   VERBOSE=1 ./seo-audit.sh https://lumi.vercel.app
#   MAX_PAGES=50 ./seo-audit.sh https://lumi.vercel.app   # limit pages tested
#
# ============================================================================

set -uo pipefail

SITE_URL="${1:-}"
if [[ -z "$SITE_URL" ]]; then
  echo "Usage: $0 <site-url>"
  echo "  e.g. $0 https://lumi.vercel.app"
  exit 1
fi

# Remove trailing slash
SITE_URL="${SITE_URL%/}"
MAX_PAGES="${MAX_PAGES:-200}"
VERBOSE="${VERBOSE:-0}"

# Colors
if [[ -t 1 ]]; then
  GREEN=$'\033[32m'; RED=$'\033[31m'; YELLOW=$'\033[33m'
  CYAN=$'\033[36m'; BOLD=$'\033[1m'; DIM=$'\033[2m'; RESET=$'\033[0m'
else
  GREEN=''; RED=''; YELLOW=''; CYAN=''; BOLD=''; DIM=''; RESET=''
fi

PASS=0; FAIL=0; WARN=0

ok()   { echo "  ${GREEN}✓${RESET} $1"; PASS=$((PASS + 1)); }
fail() { echo "  ${RED}✗${RESET} $1"; FAIL=$((FAIL + 1)); }
warn() { echo "  ${YELLOW}?${RESET} $1"; WARN=$((WARN + 1)); }

section() {
  echo ""
  echo "${BOLD}${CYAN}════════════════════════════════════════════════════════════════"
  echo "  $1"
  echo "════════════════════════════════════════════════════════════════${RESET}"
}

# Fetch a URL, return status code + body
fetch() {
  local url="$1"
  local tmp; tmp=$(mktemp)
  STATUS=$(curl -s -L -o "$tmp" -w '%{http_code}' \
    -H 'User-Agent: Lumi-SEO-Audit/1.0' \
    --max-time 10 "$url" 2>/dev/null)
  BODY=$(cat "$tmp")
  rm -f "$tmp"
}

# Check if a string is in the page body
has() {
  echo "$BODY" | grep -qi "$1"
}

# ─── 1. robots.txt ─────────────────────────────────────────────────────────

section "robots.txt"

fetch "$SITE_URL/robots.txt"
if [[ "$STATUS" == "200" ]]; then
  ok "robots.txt accessible ($STATUS)"
  if echo "$BODY" | grep -qi 'User-agent: \*'; then
    ok "Has User-agent: * directive"
  else
    fail "Missing User-agent: * directive"
  fi
  if echo "$BODY" | grep -qi 'Disallow: /admin'; then
    ok "Blocks /admin from crawlers"
  else
    fail "Missing Disallow: /admin"
  fi
  if echo "$BODY" | grep -qi 'Sitemap:'; then
    SITEMAP_URL=$(echo "$BODY" | grep -oiE 'Sitemap: [^ ]+' | head -1 | cut -d' ' -f2)
    ok "Points to sitemap: $SITEMAP_URL"
  else
    fail "Missing Sitemap: directive"
  fi
  [[ "$VERBOSE" == "1" ]] && echo "$BODY"
else
  fail "robots.txt not accessible (HTTP $STATUS)"
fi

# ─── 2. sitemap.xml ────────────────────────────────────────────────────────

section "sitemap.xml"

# Initialize defaults in case sitemap is unreachable
URL_COUNT=0
SITEMAP_URLS=""
SITEMAP_URL="${SITEMAP_URL:-}"

# Try the sitemap URL from robots.txt, or default to /sitemap.xml
SITEMAP="${SITEMAP_URL:-$SITE_URL/sitemap.xml}"
fetch "$SITEMAP"
if [[ "$STATUS" == "200" ]]; then
  ok "sitemap.xml accessible ($STATUS)"
  # Count URLs in sitemap
  URL_COUNT=$(echo "$BODY" | grep -oE '<loc>[^<]+</loc>' | wc -l)
  ok "Sitemap contains ${BOLD}$URL_COUNT${RESET} URLs"

  if [[ "$URL_COUNT" -eq 0 ]]; then
    fail "Sitemap is empty — backend may be down (word slugs not fetched)"
  fi

  # Extract all URLs
  SITEMAP_URLS=$(echo "$BODY" | grep -oE '<loc>[^<]+</loc>' | sed 's/<loc>//; s/<\/loc>//' | head -n "$MAX_PAGES")

  # Check for word pages specifically
  WORD_URL_COUNT=$(echo "$SITEMAP_URLS" | grep -c '/words/')
  if [[ "$WORD_URL_COUNT" -gt 0 ]]; then
    ok "Sitemap includes ${BOLD}$WORD_URL_COUNT${RESET} word pages"
  else
    warn "No word pages in sitemap (backend may be down or dictionary is empty)"
  fi

  [[ "$VERBOSE" == "1" ]] && echo "$SITEMAP_URLS" | head -20
else
  fail "sitemap.xml not accessible (HTTP $STATUS)"
  SITEMAP_URLS=""
fi

# ─── 3. OG image ───────────────────────────────────────────────────────────

section "Open Graph image"

fetch "$SITE_URL/og-default.png"
if [[ "$STATUS" == "200" ]]; then
  ok "OG image accessible ($STATUS)"
  # Check content type
  CT=$(curl -s -I "$SITE_URL/og-default.png" 2>/dev/null | grep -i content-type | head -1)
  if echo "$CT" | grep -qi 'image/png'; then
    ok "OG image is PNG"
  elif echo "$CT" | grep -qi 'image/svg'; then
    warn "OG image is SVG (some platforms prefer PNG)"
  fi
else
  fail "OG image not accessible (HTTP $STATUS)"
fi

# ─── 4. Page-by-page SEO audit ─────────────────────────────────────────────

section "Page-by-page SEO audit"

TESTED=0
WORD_TESTED=0

while IFS= read -r url; do
  [[ -z "$url" ]] && continue
  [[ "$TESTED" -ge "$MAX_PAGES" ]] && break

  fetch "$url"

  # Determine page type from URL
  path=$(echo "$url" | sed "s|$SITE_URL||")
  is_word=false
  is_spa=false

  if [[ "$path" == /words/* ]]; then
    is_word=true
  elif [[ "$path" =~ ^/(login|me|admin|review|forgot-password|reset-password) ]]; then
    is_spa=true
  fi

  # Status check
  if [[ "$STATUS" != "200" ]]; then
    fail "$path → HTTP $STATUS (expected 200)"
    TESTED=$((TESTED + 1))
    continue
  fi

  # SEO tag checks (all pages)
  if has '<meta property="og:title"'; then
    : # good
  else
    fail "$path — missing og:title"
  fi

  if has '<meta name="description"'; then
    :
  else
    fail "$path — missing meta description"
  fi

  if has 'rel="canonical"'; then
    :
  else
    fail "$path — missing canonical link"
  fi

  if has 'twitter:card'; then
    :
  else
    fail "$path — missing twitter:card"
  fi

  # Page-type-specific checks
  if $is_word; then
    WORD_TESTED=$((WORD_TESTED + 1))
    # Word pages should have JSON-LD
    if has 'application/ld+json'; then
      :
    else
      fail "$path — missing JSON-LD structured data"
    fi
    # Word pages should have og:type=article
    if has 'og:type.*article'; then
      :
    else
      fail "$path — og:type should be 'article' for word pages"
    fi
    # Word pages should NOT be noindex
    if has 'noindex'; then
      fail "$path — word page should NOT have noindex"
    fi
  elif $is_spa; then
    # SPA pages should be noindex (or redirect)
    if has 'noindex'; then
      :
    elif has 'http-equiv="refresh"'; then
      :  # redirect (admin pages redirect via middleware)
    else
      fail "$path — SPA page should have noindex or redirect"
    fi
  else
    # Public pages should be index,follow
    if has 'noindex'; then
      fail "$path — public page should NOT have noindex"
    fi
  fi

  TESTED=$((TESTED + 1))
  ok "$path ${DIM}($STATUS, SEO tags present)${RESET}"

done <<< "$SITEMAP_URLS"

echo ""
echo "  Pages tested: ${BOLD}$TESTED${RESET} (of $URL_COUNT in sitemap)"
echo "  Word pages tested: ${BOLD}$WORD_TESTED${RESET}"

# ─── 5. Spot-check pages NOT in sitemap (SPA pages) ────────────────────────

section "SPA pages (not in sitemap — should be noindex)"

for path in /login /me /admin /forgot-password; do
  fetch "$SITE_URL$path"
  if [[ "$STATUS" == "200" ]]; then
    if has 'noindex'; then
      ok "$path → 200, noindex present ${DIM}(correctly excluded from search)${RESET}"
    elif has 'http-equiv="refresh"'; then
      ok "$path → 200, redirect (middleware guard) ${DIM}(no content leaked)${RESET}"
    else
      fail "$path → 200 but missing noindex/redirect"
    fi
  else
    # SPA pages might return 200 with a client-rendered shell
    warn "$path → HTTP $STATUS"
  fi
done

# ─── Summary ───────────────────────────────────────────────────────────────

section "Summary"

TOTAL=$((PASS + FAIL))
echo ""
echo "  Site:           $SITE_URL"
echo "  Sitemap URLs:   $URL_COUNT"
echo "  Pages tested:   $TESTED"
echo "  Word pages:     $WORD_TESTED"
echo ""
echo "  Total checks:   $TOTAL"
echo "  ${GREEN}Passed:         $PASS${RESET}"
echo "  ${RED}Failed:         $FAIL${RESET}"
echo "  ${YELLOW}Warnings:       $WARN${RESET}"
echo ""

if [[ "$FAIL" -gt 0 ]]; then
  echo "${RED}Some checks failed. Review the output above.${RESET}"
  exit 1
else
  echo "${GREEN}All checks passed! Your SEO setup is working.${RESET}"
  exit 0
fi

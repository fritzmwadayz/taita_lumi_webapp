// ── Lumi — dynamic robots.txt ────────────────────────────────────────────
// GET /robots.txt
//
// Allows all crawlers to access public pages, blocks auth/admin/SPA routes
// (they're noindex anyway, but this is belt-and-suspenders), and points
// crawlers to the sitemap.
//
// The sitemap URL is constructed dynamically from the request headers so it
// works correctly on any deployment (Netlify, custom domain, localhost).

export default defineEventHandler((event) => {
  const headers = getHeaders(event)
  const proto = headers['x-forwarded-proto'] || 'http'
  const host = headers['host'] || 'localhost:3000'
  const baseUrl = `${proto}://${host}`

  const robots = `# Lumi — robots.txt
# Public content: dictionary words, search, contribute, guide
# Blocked: auth flows, admin, reviewer tools, user profiles

User-agent: *
Allow: /
Disallow: /admin
Disallow: /review
Disallow: /me
Disallow: /login
Disallow: /forgot-password
Disallow: /reset-password
Disallow: /suggestions/

Sitemap: ${baseUrl}/sitemap.xml
`

  setHeader(event, 'Content-Type', 'text/plain; charset=utf-8')
  return robots
})

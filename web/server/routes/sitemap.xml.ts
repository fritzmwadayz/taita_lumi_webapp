// ── Lumi — dynamic sitemap.xml ───────────────────────────────────────────
// GET /sitemap.xml
//
// Generates a sitemap listing:
//   - Static public pages (/, /search, /contribute, /guide, /support, /contact)
//   - All word detail pages (/words/<slug>) — fetched from FastAPI
//
// Auth/admin/SPA pages are excluded (they're noindex anyway).
// If the backend is down, the sitemap still serves the static pages.

import type { WordListResponse } from '~/types'

export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig(event)
  const apiBase = config.apiBase

  // ── Determine the site's base URL from request headers ─────────────────
  // On Netlify, x-forwarded-proto is set to 'https' and host is the custom
  // domain (or the netlify.app subdomain).
  const headers = getHeaders(event)
  const proto = headers['x-forwarded-proto'] || 'http'
  const host = headers['host'] || 'localhost:3000'
  const baseUrl = `${proto}://${host}`

  // ── Fetch all word slugs from FastAPI ──────────────────────────────────
  let wordSlugs: string[] = []
  try {
    const response = await $fetch<WordListResponse>(`${apiBase}/api/words`, {
      query: { page: 1, size: 10000 },
    })
    wordSlugs = response.items
      .map((w) => w.slug)
      .filter((s): s is string => Boolean(s))
  } catch (err) {
    // Backend down — still serve the static-page sitemap
    console.error('[sitemap] Failed to fetch words from backend:', err)
  }

  // ── Static pages ───────────────────────────────────────────────────────
  const staticPages = [
    { path: '/', changefreq: 'daily', priority: '1.0' },
    { path: '/search', changefreq: 'daily', priority: '0.8' },
    { path: '/contribute', changefreq: 'weekly', priority: '0.6' },
    { path: '/guide', changefreq: 'monthly', priority: '0.4' },
    { path: '/support', changefreq: 'monthly', priority: '0.3' },
    { path: '/contact', changefreq: 'monthly', priority: '0.3' },
  ]

  // ── Build XML ──────────────────────────────────────────────────────────
  const urls: string[] = []

  for (const page of staticPages) {
    urls.push(
      `  <url>
    <loc>${baseUrl}${page.path}</loc>
    <changefreq>${page.changefreq}</changefreq>
    <priority>${page.priority}</priority>
  </url>`,
    )
  }

  for (const slug of wordSlugs) {
    urls.push(
      `  <url>
    <loc>${baseUrl}/words/${slug}</loc>
    <changefreq>weekly</changefreq>
    <priority>0.7</priority>
  </url>`,
    )
  }

  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls.join('\n')}
</urlset>`

  setHeader(event, 'Content-Type', 'application/xml; charset=utf-8')
  setHeader(event, 'Cache-Control', 'public, max-age=3600') // cache for 1 hour
  return xml
})

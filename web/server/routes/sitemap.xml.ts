// ── Lumi — sitemap.xml from the static snapshot ────────────────────────────
// GET /sitemap.xml
//
// Lists the static public pages plus every word detail page, reading the
// slugs from public/dictionary/sitemap-words.xml (written at export time by
// scripts/export-dictionary.mjs) — no backend call, no DB query. The
// fragment's __BASE__ placeholder is substituted with this deployment's
// origin at request time.
//
// Auth/admin/SPA pages are excluded (they're noindex anyway).

import { readFile } from 'node:fs/promises'

export default defineEventHandler(async (event) => {
  // ── Determine the site's base URL from request headers ─────────────────
  // Works on any deployment (Vercel, custom domain, localhost).
  const headers = getHeaders(event)
  const proto = headers['x-forwarded-proto'] || 'http'
  const host = headers['host'] || 'localhost:3000'
  const baseUrl = `${proto}://${host}`

  // ── Static pages ───────────────────────────────────────────────────────
  const staticPages = [
    { path: '/', changefreq: 'daily', priority: '1.0' },
    { path: '/search', changefreq: 'daily', priority: '0.8' },
    { path: '/contribute', changefreq: 'weekly', priority: '0.6' },
    { path: '/guide', changefreq: 'monthly', priority: '0.4' },
    { path: '/support', changefreq: 'monthly', priority: '0.3' },
    { path: '/contact', changefreq: 'monthly', priority: '0.3' },
  ]

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

  // ── Word pages — from the export-time fragment (no backend call) ───────
  let wordEntries = ''
  try {
    const fragment = await readFile('public/dictionary/sitemap-words.xml', 'utf8')
    // First line is the __BASE__ placeholder line; replace per request.
    wordEntries = fragment.replace('__BASE__PLACEHOLDER__', baseUrl)
  } catch {
    // No snapshot yet — serve the static-page-only sitemap.
  }

  if (wordEntries) {
    urls.push(wordEntries)
  }

  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls.join('\n')}
</urlset>`

  setHeader(event, 'Content-Type', 'application/xml; charset=utf-8')
  setHeader(event, 'Cache-Control', 'public, max-age=3600') // cache for 1 hour
  return xml
})

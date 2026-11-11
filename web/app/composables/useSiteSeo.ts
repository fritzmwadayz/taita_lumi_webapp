// ── Lumi — shared SEO composable ───────────────────────────────────────────
// Wraps useSeoMeta + useHead with site-wide defaults (site name, default OG
// image, canonical URL construction, Twitter cards).
//
// Usage on static pages:
//   useSiteSeo({ title: 'Search', description: 'Browse and search Taita words…' })
//
// For noindex pages (login, admin, etc.):
//   useSiteSeo({ noindex: true })
//
// For pages needing reactive SEO (e.g. word detail with dynamic data), call
// useSeoMeta / useHead directly instead of this composable.

interface SeoOptions {
  /** Page-specific title (without the site name — composable adds " — Lumi"). */
  title?: string
  /** Page-specific description. Falls back to the site default. */
  description?: string
  /** Path for the canonical URL (defaults to the current request path). */
  path?: string
  /** OG image path (relative or absolute). Defaults to /og-default.png. */
  image?: string
  /** OG type — 'website' for most pages, 'article' for word detail. */
  type?: 'website' | 'article'
  /** If true, sets robots: noindex, nofollow. */
  noindex?: boolean
  /** Optional JSON-LD object to inject as a structured-data script. */
  jsonLd?: Record<string, unknown>
}

const SITE_NAME = 'Lumi'
const DEFAULT_DESCRIPTION =
  'A community dictionary of the Taita language. Browse, search, and contribute Taita words with Swahili and English translations.'
const DEFAULT_IMAGE = '/og-default.png'

export function useSiteSeo(options: SeoOptions = {}) {
  const url = useRequestURL()
  const baseUrl = `${url.protocol}//${url.host}`
  const pagePath = options.path ?? url.pathname
  const canonicalUrl = `${baseUrl}${pagePath}`
  const imageUrl = options.image?.startsWith('http')
    ? options.image
    : `${baseUrl}${options.image ?? DEFAULT_IMAGE}`

  const fullTitle = options.title
    ? `${options.title} — ${SITE_NAME}`
    : `${SITE_NAME} — A dictionary of the Taita language`
  const description = options.description ?? DEFAULT_DESCRIPTION
  const robots = options.noindex ? 'noindex, nofollow' : 'index, follow'

  useSeoMeta({
    title: fullTitle,
    description,
    ogTitle: fullTitle,
    ogDescription: description,
    ogSiteName: SITE_NAME,
    ogType: options.type ?? 'website',
    ogUrl: canonicalUrl,
    ogImage: imageUrl,
    twitterCard: 'summary_large_image',
    twitterTitle: fullTitle,
    twitterDescription: description,
    twitterImage: imageUrl,
    robots,
  })

  // Canonical URL — prevents duplicate-content indexing.
  useHead({
    link: [{ rel: 'canonical', href: canonicalUrl }],
  })

  // JSON-LD structured data (optional).
  if (options.jsonLd) {
    useHead({
      script: [
        {
          type: 'application/ld+json',
          innerHTML: JSON.stringify(options.jsonLd),
        },
      ],
    })
  }
}

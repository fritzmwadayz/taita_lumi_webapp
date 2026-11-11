// ── Lumi — pre-render word pages at build time ────────────────────────────
// Nitro plugin that hooks into the prerender phase. At build time, it fetches
// all word slugs from FastAPI and adds them to the pre-render route set, so
// every word page is generated as a static HTML file during `nuxt build`.
//
// This means:
//   - Known words → served as static HTML from the CDN edge (zero DB queries)
//   - New words added after deploy → served via ISR (routeRules) until the
//     next build pre-renders them too
//
// If the backend is down during build, this plugin logs a warning and skips
// silently — the build still succeeds, and ISR handles word pages at runtime.

interface WordListResponse {
  items: { slug: string }[]
  total: number
}

export default defineNitroPlugin((nitro) => {
  nitro.hooks.hook('prerender:routes', async (ctx) => {
    const { apiBase } = useRuntimeConfig()

    // Skip during dev — pre-rendering only happens during `nuxt build`.
    if (import.meta.dev) return

    try {
      console.log('[prerender] Fetching word slugs from FastAPI…')

      // Fetch all words in one request. The backend supports `size` up to
      // 10,000 per page. If the dictionary grows beyond that, we'd paginate
      // here — but for a community dictionary, 10k is plenty.
      const response = await $fetch<WordListResponse>(`${apiBase}/api/words`, {
        query: { page: 1, size: 10000 },
      })

      let added = 0
      for (const word of response.items) {
        if (word.slug) {
          ctx.routes.add(`/words/${word.slug}`)
          added++
        }
      }

      console.log(
        `[prerender] Added ${added} word routes ` +
        `(out of ${response.total} total words from backend).`,
      )
    } catch (err) {
      // Non-fatal — the build continues. Word pages will be served via ISR
      // (see routeRules in nuxt.config.ts) until the next deploy pre-renders them.
      console.warn(
        '[prerender] Could not fetch word slugs from FastAPI ' +
        '(backend may be down during build). Word pages will use ISR fallback.',
        err instanceof Error ? err.message : err,
      )
    }
  })
})

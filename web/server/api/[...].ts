// ── Lumi — catch-all API proxy ────────────────────────────────────────────
// Matches any /api/* route NOT handled by a more specific server/api/ file.
// Auth endpoints (login, register, logout, OAuth) have their own handlers and
// take precedence. This catch-all handles: words, search, suggestions, admin, health.

export default defineEventHandler(async (event) => {
  const path = event.path // e.g. /api/words, /api/words/123, /api/admin/stats

  const method = event.method
  const options: {
    method: string
    query?: Record<string, unknown>
    body?: unknown
  } = { method }

  // Query params
  const query = getQuery(event)
  if (Object.keys(query).length > 0) {
    options.query = query as Record<string, unknown>
  }

  // Body for non-GET requests
  if (method !== 'GET' && method !== 'HEAD') {
    const body = await readBody(event).catch(() => undefined)
    if (body !== undefined) {
      options.body = body
    }
  }

  return await proxyToApi(event, path, options)
})

// ── Lumi — logout endpoint ────────────────────────────────────────────────
// POST /api/auth/logout
// Notifies FastAPI (best-effort), then clears the session cookie.

export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig(event)
  const apiBase = config.apiBase

  // Read the session to get the access token (for the backend logout call)
  const session = await getUserSession(event) as { tokens?: { access_token?: string } }

  // ── Notify the backend (best-effort — 204 or error, we clear locally anyway) ──
  if (session.tokens?.access_token) {
    try {
      await $fetch(`${apiBase}/api/auth/logout`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${session.tokens.access_token}` },
      })
    } catch {
      // Backend logout failed (expired token, network, etc.) — we clear locally anyway
    }
  }

  // ── Clear the session cookie ───────────────────────────────────────────
  await clearUserSession(event)

  return { status: 'ok' }
})

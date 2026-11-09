// ── Lumi — auth middleware ─────────────────────────────────────────────────
// Waits for the session to load before checking authentication.

export default defineNuxtRouteMiddleware(async (to) => {
  const session = useUserSession()

  if (!session.ready.value) {
    await session.fetch()
  }

  const user = session.user.value as { id?: string } | null

  if (!user?.id) {
    return navigateTo({ path: '/login', query: { next: to.fullPath } })
  }
})

// ── Lumi — reviewer middleware ─────────────────────────────────────────────
// Waits for the session to load before checking role.
// Without the await session.fetch(), the middleware runs before nuxt-auth-utils
// has loaded the session from the cookie — so it thinks you're not logged in.

export default defineNuxtRouteMiddleware(async (to) => {
  const session = useUserSession()

  // Ensure the session is fetched before checking auth/role
  if (!session.ready.value) {
    await session.fetch()
  }

  const user = session.user.value as { id?: string; role?: string } | null

  if (!user?.id) {
    return navigateTo({ path: '/login', query: { next: to.fullPath } })
  }

  if (user.role !== 'reviewer' && user.role !== 'admin') {
    return navigateTo('/')
  }
})

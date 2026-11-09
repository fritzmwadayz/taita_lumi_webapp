// ── Lumi — guest middleware ────────────────────────────────────────────────
// Redirects to / if the user is already authenticated.
// Applied to the login page via definePageMeta({ middleware: 'guest' }).

export default defineNuxtRouteMiddleware(() => {
  const session = useUserSession()
  const user = session.value?.user as { id?: string } | undefined

  if (user?.id) {
    return navigateTo('/')
  }
})

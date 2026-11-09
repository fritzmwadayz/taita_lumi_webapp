// ── Lumi — useAuth composable ─────────────────────────────────────────────
// Wraps nuxt-auth-utils' useUserSession to expose:
//  - user, isAuthenticated, isAdmin, isReviewer, displayName
//  - login(email, password), register(...), loginWithGoogle(), logout()
//
// The session is fetched from /api/_auth/session which strips the tokens
// (see server/api/_auth/session.get.ts). The client never sees the JWTs.

import type { User as LumiUser } from '~/types'

declare module '#auth-utils' {
  interface User {
    id: string
    email: string
    display_name: string | null
    role: 'user' | 'reviewer' | 'admin'
    created_at: string
    last_seen_at: string | null
    oauth_provider?: string | null
  }
}

export function useAuth() {
  const session = useUserSession()

  const user = session.user              // ComputedRef<User | null>
  const isAuthenticated = session.loggedIn  // ComputedRef<boolean>

  const isAdmin = computed(() => user.value?.role === 'admin')
  const isReviewer = computed(() =>
    user.value?.role === 'reviewer' || user.value?.role === 'admin',
  )
  const displayName = computed(
    () => user.value?.display_name || user.value?.email?.split('@')[0] || 'User',
  )
  const initial = computed(() => {
    const name = displayName.value
    return name ? name[0].toUpperCase() : '?'
  })

  async function login(email: string, password: string) {
    await $fetch('/api/auth/login', {
      method: 'POST',
      body: { email, password },
    })
    await session.fetch()  // ← CRITICAL: refresh client state after server sets cookie
  }

  async function register(email: string, password: string, displayName: string | null = null) {
    const body: Record<string, unknown> = { email, password }
    if (displayName) body.display_name = displayName
    await $fetch('/api/auth/register', { method: 'POST', body })
    await session.fetch()  // ← CRITICAL
  }

  function loginWithGoogle() {
    navigateTo('/api/auth/oauth/google', { external: true })
  }

  async function logout() {
    await $fetch('/api/auth/logout', { method: 'POST' })
    await session.clear()  // ← CRITICAL: clear client state
    navigateTo('/')
  }

  return {
    user, isAuthenticated, isAdmin, isReviewer,
    displayName, initial,
    loading: computed(() => !session.ready.value),
    login, register, loginWithGoogle, logout,
    session,
  }
}
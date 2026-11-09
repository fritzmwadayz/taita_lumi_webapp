// ── Lumi — auth API wrappers ──────────────────────────────────────────────
// These call the Nitro auth endpoints (server/api/auth/*.ts), NOT the catch-all
// proxy. The Nitro handlers set the session cookie; the catch-all doesn't.
//
// Auto-imported by Nuxt (no explicit import needed in pages/components).

import type { User, UserStats } from '~/types'

/** Update display name. */
export async function updateMe(displayName: string | null): Promise<User> {
  return await $fetch<User>('/api/auth/me', {
    method: 'PATCH',
    body: { display_name: displayName },
  })
}

/** Get the current user's contribution stats. */
export async function fetchMyStats(): Promise<UserStats> {
  return await $fetch<UserStats>('/api/auth/me/stats')
}

/** Change the current user's password. */
export async function changePassword(
  currentPassword: string,
  newPassword: string,
): Promise<{ status: string; message: string }> {
  return await $fetch('/api/auth/me/password', {
    method: 'PATCH',
    body: { current_password: currentPassword, new_password: newPassword },
  })
}

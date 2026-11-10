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

// ── Password reset (forgot / reset flow) ───────────────────────────────────
// These go through the Nitro catch-all proxy → FastAPI. The endpoints are
// public (no session required) — the request body carries the token.

/** Request a password reset email. Always resolves (even if the email is
 *  unknown) — the backend returns the same shape to prevent enumeration. */
export async function requestPasswordReset(
  email: string,
): Promise<{ status: string; message: string }> {
  return await $fetch('/api/auth/password-reset/request', {
    method: 'POST',
    body: { email },
  })
}

/** Confirm a password reset with the token emailed to the user. */
export async function confirmPasswordReset(
  token: string,
  newPassword: string,
): Promise<{ status: string; message: string }> {
  return await $fetch('/api/auth/password-reset/confirm', {
    method: 'POST',
    body: { token, new_password: newPassword },
  })
}

// ── Account management (email change, deletion, connected accounts) ────────

/** Change the current user's email. Requires the current password to
 *  re-verify the user (the session JWT alone isn't enough). On success
 *  the caller should `await session.fetch()` to refresh the cached user. */
export async function changeEmail(
  newEmail: string,
  currentPassword: string,
): Promise<User> {
  return await $fetch<User>('/api/auth/me/email', {
    method: 'PATCH',
    body: { new_email: newEmail, current_password: currentPassword },
  })
}

/** Permanently delete / anonymize the current user's account. Requires the
 *  current password. Returns 204 on success. The caller must clear the
 *  session and redirect to `/` after this resolves. */
export async function deleteAccount(password: string): Promise<void> {
  await $fetch('/api/auth/me', {
    method: 'DELETE',
    body: { password },
  })
}

/** Get which auth methods are linked to the current user. Used by the
 *  "Connected accounts" panel on the profile page. */
export async function getConnectedAccounts(): Promise<{
  google: boolean
  has_password: boolean
}> {
  return await $fetch('/api/auth/me/connected-accounts')
}

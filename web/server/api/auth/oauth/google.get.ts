// ── Lumi — Google OAuth handler ───────────────────────────────────────────
// GET /api/auth/oauth/google
//   - First hit (no ?code): redirects to Google consent screen
//   - Callback (?code=...&state=...): exchanges code for Google tokens,
//     sends the ID token to FastAPI /api/auth/oauth/google to get the Lumi
//     JWT pair, fetches the user profile, sets the session, redirects to /.
//
// Uses nuxt-auth-utils' defineOAuthGoogleEventHandler which handles the
// redirect/callback dance. We request the 'openid' scope so Google returns
// an id_token in the token response — FastAPI expects { id_token } in the body.

import type { User, TokenResponse } from '~/types'
// defineOAuthGoogleEventHandler is auto-imported by nuxt-auth-utils in Nitro context

export default defineOAuthGoogleEventHandler({
  config: {
    scope: ['openid', 'email', 'profile'],
  },
  async onSuccess(event, { tokens }) {
    const config = useRuntimeConfig(event)
    const apiBase = config.apiBase

    // Google's token response includes id_token when 'openid' scope is requested
    const googleIdToken = (tokens as { id_token?: string }).id_token
    if (!googleIdToken) {
      return sendRedirect(event, '/login?error=google_no_id_token')
    }

    // ── Exchange the Google ID token for the Lumi JWT pair ───────────────
    let lumiTokens: TokenResponse
    try {
      lumiTokens = await $fetch<TokenResponse>(`${apiBase}/api/auth/oauth/google`, {
        method: 'POST',
        body: { id_token: googleIdToken },
        headers: { 'Content-Type': 'application/json' },
      })
    } catch (err: unknown) {
      const error = err as { response?: { _data?: { detail?: unknown } } }
      const detail = typeof error.response?._data?.detail === 'string'
        ? error.response._data.detail
        : 'Google sign-in failed.'
      return sendRedirect(event, `/login?error=${encodeURIComponent(detail)}`)
    }

    // ── Fetch the user profile ───────────────────────────────────────────
    let user: User
    try {
      user = await $fetch<User>(`${apiBase}/api/auth/me`, {
        headers: { Authorization: `Bearer ${lumiTokens.access_token}` },
      })
    } catch {
      return sendRedirect(event, '/login?error=profile_fetch_failed')
    }

    // ── Set the session ──────────────────────────────────────────────────
    await setUserSession(event, {
      user,
      tokens: {
        access_token: lumiTokens.access_token,
        refresh_token: lumiTokens.refresh_token,
      },
    })

    // ── Redirect home (Phase 4 can add ?next= support via a pre-OAuth cookie) ──
    return sendRedirect(event, '/')
  },
  onError(event, error) {
    const message = typeof error === 'string' ? error : (error as Error)?.message || 'oauth_failed'
    return sendRedirect(event, `/login?error=${encodeURIComponent(message)}`)
  },
})

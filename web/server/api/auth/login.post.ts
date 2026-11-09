// ── Lumi — login endpoint ─────────────────────────────────────────────────
// POST /api/auth/login { email, password }
// Forwards to FastAPI, gets JWT pair, fetches user profile, sets session.

import type { User, TokenResponse } from '~/types'

export default defineEventHandler(async (event) => {
  const body = await readBody<{ email?: string; password?: string }>(event)

  if (!body?.email || !body?.password) {
    throw createError({ statusCode: 400, message: 'Email and password are required.' })
  }

  const config = useRuntimeConfig(event)
  const apiBase = config.apiBase

  // ── Exchange credentials for JWT pair ──────────────────────────────────
  let tokens: TokenResponse
  try {
    tokens = await $fetch<TokenResponse>(`${apiBase}/api/auth/login`, {
      method: 'POST',
      body: { email: body.email, password: body.password },
      headers: { 'Content-Type': 'application/json' },
    })
  } catch (err: unknown) {
    const error = err as { response?: { status?: number; _data?: { detail?: unknown } } }
    throw createError({
      statusCode: error.response?.status || 500,
      message: typeof error.response?._data?.detail === 'string'
        ? error.response._data.detail
        : 'Login failed.',
    })
  }

  // ── Fetch the user profile ─────────────────────────────────────────────
  let user: User
  try {
    user = await $fetch<User>(`${apiBase}/api/auth/me`, {
      headers: { Authorization: `Bearer ${tokens.access_token}` },
    })
  } catch {
    throw createError({
      statusCode: 401,
      message: 'Logged in but could not fetch profile. Please try again.',
    })
  }

  // ── Set the session (httpOnly encrypted cookie) ────────────────────────
  // The `tokens` field is stripped before returning to the client
  // (see server/api/_auth/session.get.ts).
  await setUserSession(event, {
    user,
    tokens: {
      access_token: tokens.access_token,
      refresh_token: tokens.refresh_token,
    },
  })

  return { user }
})

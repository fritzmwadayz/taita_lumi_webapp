// ── Lumi — register endpoint ──────────────────────────────────────────────
// POST /api/auth/register { email, password, display_name? }
// Forwards to FastAPI, gets JWT pair, fetches user profile, sets session.

import type { User, TokenResponse } from '~/types'

export default defineEventHandler(async (event) => {
  const body = await readBody<{
    email?: string
    password?: string
    display_name?: string | null
  }>(event)

  if (!body?.email || !body?.password) {
    throw createError({ statusCode: 400, message: 'Email and password are required.' })
  }

  const config = useRuntimeConfig(event)
  const apiBase = config.apiBase

  // ── Register via FastAPI ───────────────────────────────────────────────
  const registerBody: Record<string, unknown> = { email: body.email, password: body.password }
  if (body.display_name) registerBody.display_name = body.display_name

  let tokens: TokenResponse
  try {
    tokens = await $fetch<TokenResponse>(`${apiBase}/api/auth/register`, {
      method: 'POST',
      body: registerBody,
      headers: { 'Content-Type': 'application/json' },
    })
  } catch (err: unknown) {
    const error = err as { response?: { status?: number; _data?: { detail?: unknown } } }
    throw createError({
      statusCode: error.response?.status || 500,
      message: typeof error.response?._data?.detail === 'string'
        ? error.response._data.detail
        : 'Registration failed.',
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
      message: 'Registered but could not fetch profile. Please log in.',
    })
  }

  await setUserSession(event, {
    user,
    tokens: {
      access_token: tokens.access_token,
      refresh_token: tokens.refresh_token,
    },
  })

  return { user }
})

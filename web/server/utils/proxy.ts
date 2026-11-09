// ── Lumi — Nitro proxy helper ──────────────────────────────────────────────
// Forwards API requests to the FastAPI backend with:
//  - Authorization: Bearer <access_token> (from session, if logged in)
//  - X-Session-Cookie: <anon_uuid> (always, for rate limiting + audit)
//  - 401 handling: tries refresh once, updates session, retries the request

import type { H3Event } from 'h3'
import type { SessionData, TokenResponse } from '~/types'

const ANON_COOKIE_NAME = 'lumi_anon'

interface ProxyOptions {
  method?: string
  query?: Record<string, unknown>
  body?: unknown
  headers?: Record<string, string>
  /** Internal: marks a request as already retried (prevents infinite refresh loop). */
  _retried?: boolean
}

/**
 * Forward an API request to the FastAPI backend.
 * @param event - The H3 request event
 * @param path - The API path starting with /api/ (e.g. /api/words, /api/words/123)
 * @param options - Request options (method, query, body, headers)
 */
export async function proxyToApi(event: H3Event, path: string, options: ProxyOptions = {}) {
  const config = useRuntimeConfig(event)
  const apiBase = config.apiBase // e.g. http://localhost:8000

  // ── Read session (server-side; returns {} if no session) ───────────────
  const session = await getUserSession(event) as SessionData
  const accessToken = session.tokens?.access_token
  const refreshToken = session.tokens?.refresh_token

  // ── Read or generate anon cookie ───────────────────────────────────────
  let anonCookie = getCookie(event, ANON_COOKIE_NAME)
  if (!anonCookie) {
    anonCookie = generateAnonId()
    setCookie(event, ANON_COOKIE_NAME, anonCookie, {
      httpOnly: true,
      sameSite: 'lax',
      secure: !import.meta.dev,
      maxAge: 60 * 60 * 24 * 365 * 2, // 2 years
      path: '/',
    })
  }

  // ── Build headers ──────────────────────────────────────────────────────
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'X-Session-Cookie': anonCookie,
    ...options.headers,
  }
  if (accessToken) {
    headers.Authorization = `Bearer ${accessToken}`
  }

  // ── Make the request ───────────────────────────────────────────────────
  const url = `${apiBase}${path}`
  const fetchOptions: Record<string, unknown> = {
    method: options.method || 'GET',
    headers,
  }
  if (options.query) fetchOptions.query = options.query
  if (options.body !== undefined) fetchOptions.body = options.body

  try {
    return await $fetch(url, fetchOptions)
  } catch (err: unknown) {
    const error = err as { response?: { status?: number; _data?: { detail?: unknown } }; message?: string }

    // ── 401: try refresh once ────────────────────────────────────────────
    if (
      error.response?.status === 401 &&
      refreshToken &&
      !options._retried &&
      !path.includes('/api/auth/refresh') &&
      !path.includes('/api/auth/login') &&
      !path.includes('/api/auth/register')
    ) {
      try {
        const refreshed = await $fetch<TokenResponse>(`${apiBase}/api/auth/refresh`, {
          method: 'POST',
          body: { refresh_token: refreshToken },
          headers: { 'Content-Type': 'application/json' },
        })
        // Update the session with new tokens
        await setUserSession(event, {
          ...session,
          tokens: {
            access_token: refreshed.access_token,
            refresh_token: refreshed.refresh_token,
          },
        } as SessionData)
        // Retry the original request with the new token
        return await proxyToApi(event, path, { ...options, _retried: true })
      } catch {
        // Refresh failed — clear the session, user must log in again
        await clearUserSession(event)
        throw createError({
          statusCode: 401,
          message: 'Your session has expired. Please log in again.',
        })
      }
    }

    // ── 403: blocked user — clear session and surface the block ──────────
    // The backend returns 403 with "This account has been blocked" when a
    // blocked user tries any authed endpoint. We clear the session so the
    // client doesn't keep retrying with the blocked token.
    if (
      error.response?.status === 403 &&
      typeof error.response?._data?.detail === 'string' &&
      error.response._data.detail.toLowerCase().includes('blocked')
    ) {
      await clearUserSession(event)
      throw createError({
        statusCode: 403,
        message: 'This account has been blocked.',
        data: { blocked: true },
      })
    }

    // ── Re-throw other errors with the backend's detail if available ─────
    throw createError({
      statusCode: error.response?.status || 500,
      message: typeof error.response?._data?.detail === 'string'
        ? error.response._data.detail
        : error.message || 'API request failed',
      data: error.response?._data,
    })
  }
}

/**
 * Generate a v4 UUID for the anon session cookie.
 */
function generateAnonId(): string {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID()
  }
  // Fallback (Node without crypto.randomUUID)
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0
    const v = c === 'x' ? r : (r & 0x3) | 0x8
    return v.toString(16)
  })
}

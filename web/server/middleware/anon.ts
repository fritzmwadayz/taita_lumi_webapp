// ── Lumi — anon session middleware ────────────────────────────────────────
// Runs on every request. Ensures the anon session cookie exists so that:
//  1. The browser has it for subsequent requests
//  2. The proxy (server/utils/proxy.ts) can read it during SSR page renders
//
// The anon cookie is a UUID used by FastAPI for rate limiting + audit.
// It's separate from the auth session cookie (managed by nuxt-auth-utils).

const ANON_COOKIE_NAME = 'lumi_anon'

export default defineEventHandler((event) => {
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
    // Store in event context so the proxy can read it during this same
    // request (the cookie won't be in the request headers until the next round-trip)
    event.context.anonCookie = anonCookie
  }
})

function generateAnonId(): string {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID()
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0
    const v = c === 'x' ? r : (r & 0x3) | 0x8
    return v.toString(16)
  })
}

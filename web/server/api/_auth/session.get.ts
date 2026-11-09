// ── Lumi — session endpoint (overrides nuxt-auth-utils default) ────────────
// GET /api/_auth/session
// Returns the public session (user info) WITHOUT the tokens.
// The tokens stay server-side and are only read by server/utils/proxy.ts.

import type { SessionData } from '~/types'

export default defineEventHandler(async (event) => {
  const session = await getUserSession(event) as SessionData

  // Strip tokens — the client never sees them
  const { tokens: _tokens, ...publicSession } = session
  return publicSession
})

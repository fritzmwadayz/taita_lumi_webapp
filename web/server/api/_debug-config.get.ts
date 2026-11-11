// TEMPORARY — delete after diagnosing. Never ship this; it exposes secret prefixes.
// GET /api/_debug-env  →  JSON report of what the function actually sees at runtime.

export default defineEventHandler((event) => {
  const rc = useRuntimeConfig(event)        // event-scoped — what your handlers use
  const rcGlobal = useRuntimeConfig()       // global — what nuxt-auth-utils v0.6.1 calls

  // Mask: show first 4 + last 4 chars only. Empty if undefined.
  const mask = (v: unknown) => {
    if (v == null || v === '') return '<empty>'
    const s = String(v)
    if (s.length <= 8) return `<too-short:${s.length}>`
    return `${s.slice(0, 4)}…${s.slice(-4)} (len=${s.length})`
  }

  return {
    // Raw env as the function actually received it:
    env: {
      NUXT_OAUTH_GOOGLE_CLIENT_ID:     mask(process.env.NUXT_OAUTH_GOOGLE_CLIENT_ID),
      NUXT_OAUTH_GOOGLE_CLIENT_SECRET: mask(process.env.NUXT_OAUTH_GOOGLE_CLIENT_SECRET),
      NUXT_APP_SECRET:                 mask(process.env.NUXT_APP_SECRET),
      NUXT_API_BASE:                   process.env.NUXT_API_BASE ?? '<unset>',
      NITRO_PRESET:                    process.env.NITRO_PRESET ?? '<unset>',
      NODE_ENV:                        process.env.NODE_ENV ?? '<unset>',
    },
    // What Nuxt's runtime-config override resolved to:
    runtimeConfig_event: {
      clientId:     mask(rc.oauth?.google?.clientId),
      clientSecret: mask(rc.oauth?.google?.clientSecret),
      apiBase:      rc.apiBase,
    },
    runtimeConfig_global: {
      clientId:     mask(rcGlobal.oauth?.google?.clientId),
      clientSecret: mask(rcGlobal.oauth?.google?.clientSecret),
    },
    // "is-not-configured" check, exactly as nuxt-auth-utils runs it:
    oauthHandlerWouldFail: !rcGlobal.oauth?.google?.clientId || !rcGlobal.oauth?.google?.clientSecret,
  }
})
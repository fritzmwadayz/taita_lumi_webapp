// https://nuxt.com/docs/api/configuration/nuxt-config
// Lumi — Nuxt 4 port of the Vue 3 SPA. SSR for public pages, SPA-mode for authed routes.
// Deploy target: Netlify (free tier). Backend on Render, DB on Neon.

export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',
  devtools: { enabled: true },

  // ── Modules ────────────────────────────────────────────────────────────
  modules: [
    '@nuxtjs/tailwindcss', // Tailwind v3 (stays on v3 — deferred migration to v4)
    '@nuxt/fonts',         // Self-host Inter + Source Serif 4
    'nuxt-auth-utils',     // Server-side session, OAuth helpers
  ],

  // ── SSR ────────────────────────────────────────────────────────────────
  // Global SSR on. Authed pages (/login, /me, /admin, /review) opt out via
  // definePageMeta({ ssr: false }) in their page components (Phase 4+).
  ssr: true,

  // ── CSS ────────────────────────────────────────────────────────────────
  // main.css = design tokens + primitives; motion.css = transitions,
  // skeletons, toasts, success overlay (plain CSS, no Tailwind directives).
  css: ['~/assets/css/main.css'],

  // ── Tailwind ───────────────────────────────────────────────────────────
  tailwindcss: {
    configPath: '~/tailwind.config.js',
    cssPath: '~/assets/css/main.css',
    viewer: false, // disable tailwind viewer in dev (not needed)
  },

  // ── Fonts (self-hosted via @nuxt/fonts) ────────────────────────────────
  // Auto-detects font families from CSS/HTML and downloads them locally.
  // Inter + Source Serif 4 are declared in tailwind.config.js → picked up here.
  fonts: {
    families: [
      { name: 'Inter', provider: 'google' },
      { name: 'Source Serif 4', provider: 'google' },
    ],
  },

  // ── Runtime config ─────────────────────────────────────────────────────
  // IMPORTANT: do NOT read process.env.* for secrets here. Values assigned in
  // nuxt.config are BAKED into the Nitro server bundle at build time — so any
  // env var read here ends up in .netlify/functions-internal/.../nitro.mjs,
  // and Netlify's secrets scanner will block the deploy.
  //
  // Instead, leave the defaults empty (or a dev-only localhost fallback) and
  // let Nuxt's runtime override inject the real values at request time:
  //   runtimeConfig.apiBase             ← NUXT_API_BASE
  //   runtimeConfig.oauth.google.clientId     ← NUXT_OAUTH_GOOGLE_CLIENT_ID
  //   runtimeConfig.oauth.google.clientSecret ← NUXT_OAUTH_GOOGLE_CLIENT_SECRET
  //   runtimeConfig.session.password          ← NUXT_SESSION_PASSWORD (nuxt-auth-utils)
  // The bundle ships with empty strings → scanner sees nothing → deploy passes.
  runtimeConfig: {
    // Server-only (never exposed to client). localhost fallback is dev-only;
    // in production NUXT_API_BASE overrides it at runtime.
    apiBase: 'http://localhost:8000',
    // OAuth: nuxt-auth-utils reads these via runtimeConfig.oauth.google.
    // Empty defaults — injected at runtime via NUXT_OAUTH_GOOGLE_* env vars.
    oauth: {
      google: {
        clientId: '',
        clientSecret: '',
      },
    },
    public: {
      // Browser-visible. Empty string = relative URLs, proxied through Nitro.
      apiBase: '',
    },
  },

  // ── App head ───────────────────────────────────────────────────────────
  app: {
    // Page transitions: soft out-in fade (classes in motion.css).
    // Automatically skipped for users with prefers-reduced-motion.
    pageTransition: { name: 'page', mode: 'out-in' },
    head: {
      htmlAttrs: { lang: 'en' },
      title: 'Lumi - A dictionary of the Taita language',
      meta: [
        { charset: 'utf-8' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
        {
          name: 'description',
          content:
            'Lumi is a community dictionary of the Taita language. Browse, search, and contribute Taita words with Swahili and English translations.',
        },
        // Open Graph + Twitter Card defaults. Per-page useSeoMeta() in each
        // page component overrides these with page-specific values.
        { property: 'og:title', content: 'Lumi — A dictionary of the Taita language' },
        { property: 'og:description', content: 'Browse, search, and contribute Taita words with Swahili and English translations.' },
        { property: 'og:type', content: 'website' },
        { property: 'og:image', content: '/og-default.png' },
        { name: 'twitter:card', content: 'summary_large_image' },
      ],
      link: [
        { rel: 'icon', type: 'image/svg+xml', href: '/favicon.svg' },
      ],
    },
  },

  // ── Route rules (hybrid rendering) ─────────────────────────────────────
  // Controls how each route is rendered and cached:
  //   isr: N       — render once, cache at CDN for N seconds, regenerate on
  //                  next request after expiry. Best for word pages: the first
  //                  visitor triggers a server render (one DB query), then the
  //                  cached HTML is served instantly to everyone else.
  //   prerender    — render to static HTML at build time. Served from the CDN
  //                  edge with zero server function, zero DB query. Best for
  //                  static content that rarely changes.
  //   ssr: true    — always render on the server (no caching). Best for pages
  //                  with per-request dynamic content (search results, live lists).
  //
  // Word pages get BOTH: known words are pre-rendered at build time (see
  // nitro.prerender below + server/plugins/prerender-words.ts), and words
  // added after deploy are served via ISR until the next build.
  routeRules: {
    // ISR — cached at CDN, regenerated after 1 hour
    '/words/**':    { isr: 3600 },
    '/':             { isr: 3600 },
    '/sitemap.xml':  { isr: 3600 },

    // SSR — always render fresh (dynamic content)
    '/search':       { ssr: true },
    '/contribute':   { ssr: true },

    // Pre-render at build time — static content, served from CDN edge
    '/guide':        { prerender: true },
    '/support':      { prerender: true },
    '/contact':      { prerender: true },
  },

  // ── Nitro ──────────────────────────────────────────────────────────────
  // No devProxy — all /api/* requests are handled by Nitro server routes
  // (server/api/[...].ts catch-all + specific auth handlers). The proxy.ts
  // utility forwards to FastAPI directly via $fetch with auth + anon cookie.
  // ⚠️ Do NOT add nitro.devProxy — it intercepts /api/* before Nitro handlers
  // can run, bypassing auth and stripping the /api/ prefix.
  nitro: {
    prerender: {
      // Crawl <NuxtLink> from pre-rendered pages to discover more routes
      // (home page links to recent words → those get pre-rendered too).
      crawlLinks: true,

      // Don't fail the build if some routes can't be pre-rendered (e.g.,
      // backend is down during build — ISR will handle them at runtime).
      failOnError: false,

      // Initial routes to pre-render. The word-page slugs are added
      // dynamically by server/plugins/prerender-words.ts, which fetches
      // them from FastAPI at build time.
      routes: ['/', '/guide', '/support', '/contact'],
    },
  },
})

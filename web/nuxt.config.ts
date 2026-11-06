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
  // public.apiBase = "" in both dev and prod — browser calls same-origin /api/*
  // and Nitro's server/api/[...].ts proxy forwards to the FastAPI backend.
  // The FastAPI URL is a server-side secret (never exposed to the browser).
  runtimeConfig: {
    // Server-only (never exposed to client)
    apiBase: process.env.LUMI_API_BASE_URL || 'http://localhost:8000',
    // OAuth: nuxt-auth-utils reads these via runtimeConfig.oauth.google
    // Env vars follow the NUXT_OAUTH_GOOGLE_* convention
    oauth: {
      google: {
        clientId: process.env.NUXT_OAUTH_GOOGLE_CLIENT_ID || '',
        clientSecret: process.env.NUXT_OAUTH_GOOGLE_CLIENT_SECRET || '',
      },
    },
    public: {
      // Browser-visible. Empty string = relative URLs, proxied through Nitro.
      apiBase: process.env.NUXT_PUBLIC_API_BASE || '',
    },
  },

  // ── App head ───────────────────────────────────────────────────────────
  app: {
    head: {
      htmlAttrs: { lang: 'en' },
      title: 'Lumi — A living dictionary of the Taita language',
      meta: [
        { charset: 'utf-8' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
        {
          name: 'description',
          content:
            'Lumi is a community dictionary of the Taita language (Dawida, Sagala, Kasighau). Browse, search, and contribute — Taita to Swahili and English.',
        },
        // Open Graph basics (expanded per-page in Phase 3)
        { property: 'og:title', content: 'Lumi — A living dictionary of the Taita language' },
        { property: 'og:description', content: 'Browse, search, and contribute to the Taita dictionary.' },
        { property: 'og:type', content: 'website' },
      ],
      link: [
        { rel: 'icon', type: 'image/svg+xml', href: '/favicon.svg' },
      ],
    },
  },

  // ── Nitro ──────────────────────────────────────────────────────────────
  // Netlify auto-detects Nuxt and sets the preset. For local production builds
  // you can force it: NITRO_PRESET=netlify npx nuxt build
  nitro: {},
})

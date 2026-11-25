// ── Lumi — static-first word detail loader ─────────────────────────────────
// app/composables/useStaticWord.ts
//
// Replaces the direct /api/words/{id} useFetch on the word detail page.
//
// Order of preference:
//   1. Static snapshot  — public/dictionary/words/<slug>.json, generated at
//      deploy time by scripts/export-dictionary.mjs. On the SERVER (SSR and
//      prerender) it's read from disk (no network, hermetic builds); on the
//      CLIENT it's fetched from the CDN (/dictionary/words/<slug>.json).
//   2. GET /api/words/{slug_or_id} — live fallback for words added since the
//      last export, or if the snapshot is missing entirely.
//
// The initial load is awaited by the caller so SSR/prerender render the
// actual word into the HTML (SEO + no-JS visitors), and refresh() always
// goes live — a reviewer just edited the word and must see it now.
//
// IMPORTANT: do NOT use useRequestFetch()/event.$fetch for the snapshot on
// the server — event.$fetch is plain ofetch there, and relative URLs throw
// "Failed to parse URL". Disk reads sidestep that entirely (and are faster
// than a loopback HTTP hop anyway).

import { ref, watch, type Ref } from 'vue'
import type { WordDetail } from '~/types'

export interface StaticWordState {
  word: Ref<WordDetail | null>
  pending: Ref<boolean>
  error: Ref<{ statusCode?: number; message?: string } | null>
  /** True when the current data came from the static snapshot. */
  wasStatic: Ref<boolean>
  refresh: () => Promise<void>
}

/** A UUID in canonical or dashed-hex form (old /words/{uuid} URLs). */
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
const UUID_NODASH_RE = /^[0-9a-f]{32}$/i

// Server-side snapshot reader — read from public/ once per slug per request
// (Nuxt auto-imports import.meta.server appropriately in this guard).
let serverReadWord: ((slug: string) => Promise<WordDetail | null>) | null = null
if (import.meta.server) {
  serverReadWord = async (slug) => {
    try {
      const { readFile } = await import('node:fs/promises')
      const path = await import('node:path')
      const file = path.resolve('public/dictionary/words', `${slug}.json`)
      const raw = await readFile(file, 'utf8')
      return JSON.parse(raw) as WordDetail
    } catch {
      return null
    }
  }
}

/**
 * Load a word by slug-or-id, static snapshot first, live API second.
 *
 * Pass the route param (a ref or computed) so it reloads on slug changes.
 * Must be awaited in the page's setup (`await useStaticWord(...)`) so SSR
 * renders with the word data instead of the loading state.
 */
export async function useStaticWord(slugOrId: Ref<string> | string): Promise<StaticWordState> {
  const idRef = typeof slugOrId === 'string'
    ? ref(slugOrId)
    : (slugOrId as Ref<string>)

  const word = ref<WordDetail | null>(null)
  const pending = ref(true)
  const error = ref<{ statusCode?: number; message?: string } | null>(null)
  const wasStatic = ref(false)

  async function load(id: string) {
    pending.value = true
    error.value = null

    if (!id) {
      word.value = null
      pending.value = false
      return
    }

    // ── 1. Static snapshot ───────────────────────────────────────────
    // Snapshot files are keyed by slug; the route may carry a UUID (old
    // URLs) — only try the static file when it looks like a slug.
    const looksLikeSlug = !UUID_RE.test(id) && !UUID_NODASH_RE.test(id)
    if (looksLikeSlug) {
      let data: WordDetail | null = null
      if (import.meta.server) {
        data = await serverReadWord!(id)
      } else {
        try {
          data = await $fetch<WordDetail>(`/dictionary/words/${id}.json`, { responseType: 'json' })
        } catch {
          data = null // not in the snapshot — fall through to the live API
        }
      }
      if (data) {
        word.value = data
        wasStatic.value = true
        pending.value = false
        return
      }
    }

    // ── 2. Live API ─────────────────────────────────────────────────
    try {
      word.value = await $fetch<WordDetail>(`/api/words/${id}`, { responseType: 'json' })
      wasStatic.value = false
    } catch (err: unknown) {
      const e = err as { response?: { status?: number }; statusCode?: number; message?: string }
      error.value = {
        statusCode: e?.response?.status ?? e?.statusCode ?? 500,
        message: e?.response ? undefined : e?.message,
      }
      word.value = null
    } finally {
      pending.value = false
    }
  }

  // Initial load — awaited by the caller (suspends SSR/prerender).
  await load(idRef.value)

  // Reload on param change (client-side navigation to another word).
  watch(idRef, (id) => { void load(id) })

  async function refresh() {
    // Post-edit refresh: skip the snapshot — a reviewer just wrote to the
    // live word and must see it now.
    pending.value = true
    try {
      word.value = await $fetch<WordDetail>(`/api/words/${idRef.value}`, { responseType: 'json' })
      wasStatic.value = false
      error.value = null
    } catch (err: unknown) {
      const e = err as { response?: { status?: number }; statusCode?: number; message?: string }
      error.value = {
        statusCode: e?.response?.status ?? e?.statusCode ?? 500,
        message: e?.response ? undefined : e?.message,
      }
    } finally {
      pending.value = false
    }
  }

  return { word, pending, error, wasStatic, refresh }
}

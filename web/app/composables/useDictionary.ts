// ── Lumi — static dictionary index composable ─────────────────────────────
// app/composables/useDictionary.ts
//
// Loads the static snapshot (/dictionary/words.json — generated at deploy
// time by scripts/export-dictionary.mjs) once per browser session and
// exposes:
//   - words: WordListItem[] (the full list index)
//   - rows: precomputed trigram search rows (dictSearch)
//   - search(q, limit): pg_trgm-parity client-side search
//   - findWordByIdOrSlug(slugOrId): list-entry lookup
//
// Why: the home page, browse mode, and autocomplete previously called
// /api/words and /api/search on every render/keystroke. Now those reads
// come from the snapshot — zero Render/Neon load for anonymous traffic.
// Detail pages use the per-word static files (see useStaticWord); the live
// API remains the fallback for anything added after the last export.
//
// On the server the snapshot is read from disk (public/dictionary/) — no
// network during SSR/prerender, and hermetic builds. On the client it's
// fetched from the CDN once per session.
//
// Fail-open design: if the snapshot is missing (never exported, or the
// export failed with no existing snapshot), search reverts to the live
// /api/search so the site stays fully functional.

import { computed, ref } from 'vue'
import type { SearchResultItem, WordListItem } from '~/types'
import { buildDictSearchRows, dictSearch, type DictSearchRow } from '~/utils/dictSearch'

interface WordsIndex {
  exported_at?: string
  total?: number
  items: WordListItem[]
}

// Module-level singleton: every component that calls useDictionary()
// shares one index and one fetch.
const items = ref<WordListItem[]>([])
const rows = ref<DictSearchRow[]>([])
const loaded = ref(false)
const loadFailed = ref(false)
let loadPromise: Promise<void> | null = null

// Server-side disk reader — used during SSR/prerender (import.meta.server).
async function serverReadIndex(): Promise<WordsIndex | null> {
  try {
    const { readFile } = await import('node:fs/promises')
    const path = await import('node:path')
    const raw = await readFile(path.resolve('public/dictionary/words.json'), 'utf8')
    return JSON.parse(raw) as WordsIndex
  } catch {
    return null
  }
}

export function useDictionary() {
  // ── Load (awaited during SSR; once per client session) ──────────────
  function ensureLoaded(): Promise<void> {
    if (loaded.value) return Promise.resolve()
    if (loadPromise) return loadPromise

    loadPromise = (async () => {
      if (import.meta.server) {
        const data = await serverReadIndex()
        if (data && Array.isArray(data.items)) {
          items.value = data.items
          rows.value = buildDictSearchRows(items.value)
        } else {
          loadFailed.value = true
        }
      } else {
        try {
          const data = await $fetch<WordsIndex>('/dictionary/words.json', { responseType: 'json' })
          items.value = Array.isArray(data.items) ? data.items : []
          rows.value = buildDictSearchRows(items.value)
        } catch {
          // Snapshot missing — callers fall back to the live API.
          loadFailed.value = true
        }
      }
    })().finally(() => {
      loaded.value = true
    })

    return loadPromise
  }

  void ensureLoaded()

  // ── Search: static-first, live fallback ──────────────────────────────
  /**
   * Mirror of the old searchWords() util. Returns pg_trgm-ranked results
   * from the static index; if the snapshot failed to load, falls back to
   * GET /api/search so search still works.
   */
  async function search(q: string, limit = 20): Promise<{ items: SearchResultItem[]; total: number }> {
    if (!q.trim()) return { items: [], total: 0 }
    await ensureLoaded()
    if (loadFailed.value) {
      return await $fetch<{ items: SearchResultItem[]; total: number }>('/api/search', {
        params: { q, limit },
      })
    }
    return dictSearch(rows.value, q, limit)
  }

  // ── List lookup helpers ──────────────────────────────────────────────
  function findWordByIdOrSlug(slugOrId: string): WordListItem | undefined {
    return items.value.find(
      (w) => w.slug === slugOrId || w.id === slugOrId,
    )
  }

  const total = computed(() => items.value.length)
  const ready = computed(() => loaded.value && !loadFailed.value)

  return {
    words: items,
    rows,
    total,
    ready,
    loadFailed,
    ensureLoaded,
    search,
    findWordByIdOrSlug,
  }
}

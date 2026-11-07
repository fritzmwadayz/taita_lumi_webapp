// ── Lumi — useRecentSearches composable ───────────────────────────────────
// Recent search terms for the anonymous browsing experience, persisted in
// localStorage (key: lumi:recent-searches). Max 8 entries, deduplicated
// case-insensitively, newest first.
//
//   const { recent, add, remove, clear } = useRecentSearches()
//   // on submit: add(query)
//   // in template: <button v-for="q in recent" @click="runSearch(q)">{{ q }}</button>

const STORAGE_KEY = 'lumi:recent-searches'
const MAX_ITEMS = 8

export function useRecentSearches() {
  const recent = ref<string[]>([])

  function read(): string[] {
    if (!import.meta.client) return []
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      const parsed = raw ? JSON.parse(raw) : []
      return Array.isArray(parsed) ? parsed.filter(x => typeof x === 'string').slice(0, MAX_ITEMS) : []
    } catch {
      return []
    }
  }

  function write(items: string[]) {
    if (!import.meta.client) return
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(items))
    } catch {
      // Private mode / storage full — silently ignore
    }
    recent.value = items
  }

  // Populate after mount (SSR-safe: localStorage only exists client-side)
  onMounted(() => {
    recent.value = read()
  })

  function add(term: string) {
    const t = term.trim()
    if (!t) return
    const next = [
      t,
      ...read().filter(x => x.toLowerCase() !== t.toLowerCase()),
    ].slice(0, MAX_ITEMS)
    write(next)
  }

  function remove(term: string) {
    write(read().filter(x => x !== term))
  }

  function clear() {
    write([])
  }

  return { recent, add, remove, clear }
}

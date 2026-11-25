<template>
  <div>
    <!-- Search bar — uses /api/search for autocomplete dropdown -->
    <section class="px-8 py-6 border-b border-cream-200">
      <SearchBar
        v-model="searchQuery"
        size="md"
        clearable
        wrapper-class="max-w-3xl"
        placeholder="Tafuta neno... / Search a word..."
        @submit="runSearch"
        @select="goToWord"
        @clear="clearSearch"
      />
    </section>

    <!-- Recent searches (when query is empty) -->
    <section v-if="!debouncedQuery && recent.length" class="px-8 py-3 flex flex-wrap items-center gap-2">
      <span class="text-[10px] uppercase tracking-widest text-stone-light font-semibold">Recent:</span>
      <button
        v-for="q in recent"
        :key="q"
        class="focus-ring inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs bg-cream-100 text-stone-dark hover:bg-cream-200 transition"
        @click="applyRecent(q)"
      >
        {{ q }}
        <span class="text-stone-light hover:text-terracotta" @click.stop="remove(q)">×</span>
      </button>
      <button class="focus-ring text-[10px] text-stone-light hover:text-terracotta underline" @click="clear()">Clear</button>
    </section>

    <!-- Layout: sidebar + results -->
    <section class="px-8 py-8 grid grid-cols-1 md:grid-cols-12 gap-8">
      <!-- Mobile: collapsible filter toggle (browse mode only) -->
      <div v-if="!searchMode" class="md:hidden mb-4">
        <button
          class="focus-ring inline-flex items-center gap-1.5 text-sm font-medium text-stone-dark"
          :aria-expanded="filtersOpen"
          @click="filtersOpen = !filtersOpen"
        >
          Filters
          <svg class="w-4 h-4 transition-transform" :class="{ 'rotate-180': filtersOpen }" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" /></svg>
        </button>
      </div>

      <!-- Filter sidebar — only in browse mode (search mode hides it; /api/search doesn't accept pos/dialect) -->
      <aside v-if="!searchMode" :class="['col-span-3', filtersOpen ? 'block' : 'hidden', 'md:block']">
        <h3 class="text-xs font-semibold uppercase tracking-widest text-stone mb-4">Filter</h3>

        <div class="space-y-5 text-sm">
          <div>
            <p class="text-xs font-semibold text-ink-soft mb-2">Part of speech</p>
            <div class="space-y-1.5 text-xs text-stone">
              <label class="flex items-center gap-2 cursor-pointer">
                <input type="radio" v-model="filters.pos" :value="null" class="accent-forest" />
                All
              </label>
              <label
                v-for="pos in posOptions"
                :key="pos.value"
                class="flex items-center gap-2 cursor-pointer"
              >
                <input type="radio" v-model="filters.pos" :value="pos.value" class="accent-forest" />
                {{ pos.label }}
              </label>
            </div>
          </div>

          <div>
            <p class="text-xs font-semibold text-ink-soft mb-2">Dialect</p>
            <div class="space-y-1.5 text-xs text-stone">
              <label class="flex items-center gap-2 cursor-pointer">
                <input type="radio" v-model="filters.dialect" :value="null" class="accent-forest" />
                All
              </label>
              <label
                v-for="d in dialectOptions"
                :key="d"
                class="flex items-center gap-2 cursor-pointer"
              >
                <input type="radio" v-model="filters.dialect" :value="d" class="accent-forest" />
                {{ d }}
              </label>
            </div>
          </div>

          <div class="pt-4 border-t border-cream-200">
            <button class="focus-ring text-xs text-stone hover:text-forest underline" @click="clearFilters">
              Clear filters
            </button>
          </div>
        </div>
      </aside>

      <!-- Search-mode sidebar replacement: a small info panel -->
      <aside v-else class="col-span-3 hidden md:block">
        <h3 class="text-xs font-semibold uppercase tracking-widest text-stone mb-4">Search</h3>
        <div class="bg-cream-50 border border-cream-200 rounded-lg p-3 text-xs text-stone leading-relaxed">
          <p class="text-stone-dark mb-1">Ranked by similarity to "{{ debouncedQuery }}".</p>
          <p class="text-stone-light">Filters are available in <button class="text-forest hover:underline focus-ring rounded" @click="clearSearch">browse mode</button>.</p>
        </div>
      </aside>

      <!-- Results -->
      <div :class="searchMode ? 'col-span-12 md:col-span-9' : 'col-span-9'">
        <div class="flex items-center justify-between mb-4">
          <p class="text-xs text-stone">
            <span v-if="dictLoading">Searching...</span>
            <span v-else>
              <span class="font-semibold text-ink">{{ total }}</span>
              {{ total === 1 ? 'word' : 'words' }}
              <span v-if="debouncedQuery"> for "{{ debouncedQuery }}"</span>
            </span>
          </p>
          <div v-if="searchMode" class="flex items-center gap-2 text-xs text-stone">
            <span>Sort:</span>
            <button class="font-semibold text-forest">Relevance</button>
          </div>
        </div>

        <!-- Loading (skeletons) — only while the static index loads -->
        <div v-if="dictLoading" class="grid grid-cols-1 md:grid-cols-2 gap-3" aria-busy="true">
          <div v-for="i in 6" :key="i" class="bg-cream-50 border border-cream-200 rounded-xl p-4">
            <UiSkeleton height="1.25rem" width="33%" class="rounded mb-2" />
            <UiSkeleton height="0.875rem" width="66%" class="rounded mb-1" />
            <UiSkeleton height="0.75rem" width="50%" class="rounded" />
          </div>
        </div>

        <!-- Empty -->
        <div
          v-else-if="words.length === 0"
          class="bg-cream-100 border border-cream-200 rounded-xl p-12 text-center"
        >
          <p class="font-serif text-xl text-forest-dark mb-2">No words found</p>
          <p class="text-sm text-stone mb-6">Try a different search or fewer filters.</p>
          <NuxtLink to="/contribute" class="focus-ring btn btn-primary btn-md">
            Suggest a new word
          </NuxtLink>
        </div>

        <!-- Results grid -->
        <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-3">
          <WordCard
            v-for="word in words"
            :key="word.id"
            :word="word"
            :show-similarity="searchMode"
          />
        </div>

        <!-- Search mode: no pagination (matches are capped at 50) -->
        <div v-if="!dictLoading && searchMode && words.length > 0" class="mt-4 bg-cream-100 border border-cream-200 rounded-lg p-2.5 text-[10px] text-stone-light text-center">
          Showing {{ words.length }} of {{ total }} match{{ total === 1 ? '' : 'es' }} · search returns up to 50 — no pagination
        </div>

        <!-- Load more — browse mode only -->
        <div v-if="!searchMode && hasMore && !dictLoading" class="mt-6 text-center">
          <button class="focus-ring btn btn-secondary btn-md" @click="loadMore">
            Load more
          </button>
          <p class="text-[10px] text-stone-light mt-2">
            Showing {{ words.length }} of {{ total }}
          </p>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import type { SearchResultItem, WordListItem } from '~/types'
import { dictSearch } from '~/utils/dictSearch'

// ── SEO ───────────────────────────────────────────────────────────────────
useSiteSeo({
  title: 'Search',
  description: 'Search and browse the Lumi Taita dictionary. Find Taita words with Swahili and English translations, filter by part of speech and dialect.',
})

// ── Recent searches (localStorage, max 8, deduped) ─────────────────────────
const { recent, add, remove, clear } = useRecentSearches()

// ── Mobile collapsible filters ─────────────────────────────────────────────
const filtersOpen = ref(false)

const route = useRoute()
const router = useRouter()

// ── Search state ───────────────────────────────────────────────────────────
const searchQuery = ref((route.query.q as string) || '')
const debouncedQuery = ref(searchQuery.value)
const page = ref(1)
const pageSize = 20
const SEARCH_LIMIT = 50
const allWords = ref<Array<WordListItem | SearchResultItem>>([])

const filters = reactive({
  pos: (route.query.pos as string) || null,
  dialect: null as string | null,
})

const posOptions = [
  { value: 'noun', label: 'Noun' },
  { value: 'verb', label: 'Verb' },
  { value: 'adjective', label: 'Adjective' },
  { value: 'phrase', label: 'Phrase' },
]

const dialectOptions = ['Dawida', 'Sagala', 'Kasighau']

// ── Mode: search (q non-empty → client-side trigram search over the static
// index) vs browse (q empty → static words.json list, filtered + paginated
// client-side). Both paths are zero-backend for anonymous traffic — the
// snapshot in /dictionary/words.json is generated at deploy time
// (scripts/export-dictionary.mjs). The composable falls back to the live
// API when the snapshot is missing.
const dict = useDictionary()
const searchMode = computed(() => !!debouncedQuery.value.trim())
const dictLoading = computed(() => !dict.ready.value && !dict.loadFailed.value)

// ── Results (computed, not fetched) ───────────────────────────────────────
// Browse mode: filter the static index by pos/dialect, "Load more" pages
// client-side. Search mode: pg_trgm-parity ranking (dictSearch).
const words = computed<Array<WordListItem | SearchResultItem>>(() => {
  if (searchMode.value) {
    return dictSearch(rows(), debouncedQuery.value.trim(), SEARCH_LIMIT).items
  }
  const filtered = dict.words.value.filter(matchesFilters)
  // Page 1 replaces, page 2+ appends — same UX as the paginated API.
  return page.value === 1 ? filtered : [...allWords.value, ...filtered]
})

const total = computed(() =>
  searchMode.value
    ? dictSearch(rows(), debouncedQuery.value.trim(), SEARCH_LIMIT).total
    : dict.words.value.filter(matchesFilters).length,
)

const hasMore = computed(() =>
  !searchMode.value && page.value * pageSize < total.value,
)

function matchesFilters(w: WordListItem): boolean {
  if (filters.pos && w.part_of_speech !== filters.pos) return false
  if (filters.dialect && w.dialect !== filters.dialect) return false
  return true
}

// ── Search triggers ────────────────────────────────────────────────────────
// SearchBar v-model updates searchQuery immediately; debouncedQuery mirrors
// it on a 250ms debounce so ranking doesn't run on every keystroke.
let searchDebounce: ReturnType<typeof setTimeout> | null = null

// Lazy search rows — the composable builds trigram sets once the index loads.
function rows() {
  return dict.rows.value
}

// Watch searchQuery (which SearchBar updates) → debounce → run search
watch(searchQuery, (val) => {
  if (searchDebounce) clearTimeout(searchDebounce)
  searchDebounce = setTimeout(() => {
    debouncedQuery.value = val
    runSearch()
  }, 250)
})

function runSearch(q?: string) {
  // SearchBar emits 'submit' with the query string — update both refs
  // synchronously so the URL/mode switch happens immediately (not after
  // the 250ms typing debounce). Also cancel any pending debounce so we
  // don't re-run the search twice.
  if (typeof q === 'string') {
    if (q !== searchQuery.value) searchQuery.value = q
    debouncedQuery.value = q
    if (searchDebounce) {
      clearTimeout(searchDebounce)
      searchDebounce = null
    }
  }
  page.value = 1
  allWords.value = []
  if (debouncedQuery.value.trim()) add(debouncedQuery.value.trim())
  // Results are computed — no fetch to trigger; ensureLoaded() runs once
  // in the composable and the computed re-evaluates when the index lands.
}

function applyRecent(q: string) {
  searchQuery.value = q
  debouncedQuery.value = q
  runSearch()
}

function goToWord(item: SearchResultItem) {
  // User selected a dropdown result — navigate straight to word detail.
  router.push(`/words/${item.slug}`)
}

// ── Load more — browse mode only (client-side pagination) ─────────────────
function loadMore() {
  if (searchMode.value) return
  // Save current items before paging (the computed appends from page 2 on).
  allWords.value = words.value as Array<WordListItem | SearchResultItem>
  page.value++
}

// ── Clear actions ──────────────────────────────────────────────────────────
function clearSearch() {
  searchQuery.value = ''
  debouncedQuery.value = ''
  page.value = 1
  allWords.value = []
}

function clearFilters() {
  filters.pos = null
  filters.dialect = null
  runSearch()
}

// ── Refetch when filters change (browse mode) ──────────────────────────────
watch(
  () => [filters.pos, filters.dialect],
  () => {
    if (!searchMode.value) runSearch()
  },
)

// ── Update URL when search changes (shareable links) ───────────────────────
watch(
  debouncedQuery,
  (q) => {
    const query: Record<string, string> = {}
    if (q) query.q = q
    if (filters.pos) query.pos = filters.pos
    router.replace({ path: '/search', query })
  },
)
</script>

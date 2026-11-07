<template>
  <div>
    <!-- Hero: 2-column -->
    <section class="px-4 md:px-12 py-16 grid grid-cols-1 md:grid-cols-12 gap-6 md:gap-12 items-center">
      <div class="col-span-7">
        <p class="text-xs font-semibold tracking-widest uppercase text-ochre mb-3">
          Kamusi ya Kidawida
        </p>
        <h1 class="font-serif text-3xl md:text-5xl text-forest-dark leading-tight mb-4">
          A living dictionary of the Taita language.
        </h1>
        <p class="text-base text-stone leading-relaxed mb-8 max-w-lg">
          Built by and for speakers of Dawida, Sagala, and Kasighau. Browse,
          search, and contribute — Taita to Swahili and English.
        </p>

        <!-- Search bar -->
        <div
          class="flex items-center gap-3 bg-cream-50 border border-cream-300 rounded-xl px-5 py-4 max-w-xl"
        >
          <svg class="w-5 h-5 text-stone" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M21 21l-4.35-4.35M11 18a7 7 0 100-14 7 7 0 000 14z"
            />
          </svg>
          <input
            v-model="searchQuery"
            type="text"
            placeholder="Tafuta neno... / Search a word..."
            class="flex-1 bg-transparent text-base text-ink placeholder-stone-light outline-none"
            @keyup.enter="goToSearch"
          />
          <kbd class="text-[10px] font-mono text-stone-light bg-cream-100 px-1.5 py-0.5 rounded border border-cream-200">↵</kbd>
        </div>

        <div class="flex flex-wrap gap-2 mt-4">
          <button
            v-for="filter in quickFilters"
            :key="filter"
            class="focus-ring text-xs px-3 py-1.5 bg-cream-100 hover:bg-cream-200 text-ink-soft rounded-full border border-cream-200 transition"
            @click="goToSearchWithFilter(filter)"
          >
            {{ filter }}
          </button>
        </div>
      </div>

      <!-- Word of the Day -->
      <div class="col-span-5">
        <div class="flex items-baseline justify-between mb-3">
          <h3 class="font-serif text-base text-forest-dark">Word of the day</h3>
          <span class="text-[10px] text-stone-light uppercase tracking-wider">
            {{ todayLabel }}
          </span>
        </div>
        <div v-if="wordOfDay" class="bg-forest text-cream rounded-2xl p-6 relative overflow-hidden tri-pattern">
          <div class="relative">
            <div class="flex items-baseline gap-3 mb-3">
              <h4 class="font-serif text-4xl text-cream font-semibold">{{ wordOfDay.headword }}</h4>
              <PosBadge v-if="wordOfDay.part_of_speech" :pos="wordOfDay.part_of_speech" />
            </div>
            <p v-if="wordOfDay.swahili_translation" class="text-base text-cream/90 font-medium mb-1">
              {{ wordOfDay.swahili_translation }}
            </p>
            <p v-if="wordOfDay.english_translation" class="text-sm text-cream/70 mb-4">
              {{ wordOfDay.english_translation }}
            </p>
            <NuxtLink
              :to="`/words/${wordOfDay.slug}`"
              class="focus-ring inline-flex items-center gap-1 text-xs font-semibold text-ochre-light hover:text-cream transition"
            >
              View full entry
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
              </svg>
            </NuxtLink>
          </div>
        </div>
        <div v-else class="bg-cream-100 border border-cream-200 rounded-2xl p-6 text-sm text-stone">
          Loading word of the day...
        </div>
      </div>
    </section>

    <!-- Recently Added -->
    <section class="px-4 md:px-12 py-10 border-t border-cream-200">
      <div class="flex items-baseline justify-between mb-6">
        <h3 class="font-serif text-xl text-forest-dark">Recently added</h3>
        <NuxtLink to="/search" class="text-xs font-semibold text-forest hover:underline focus-ring rounded">
          See all →
        </NuxtLink>
      </div>

      <div v-if="pending" class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div
          v-for="i in 4"
          :key="i"
          class="bg-cream-50 border border-cream-200 rounded-xl p-5 animate-pulse"
        >
          <div class="h-5 bg-cream-200 rounded w-1/3 mb-2"></div>
          <div class="h-4 bg-cream-200 rounded w-2/3 mb-1"></div>
          <div class="h-3 bg-cream-100 rounded w-1/2"></div>
        </div>
      </div>

      <div v-else-if="error" class="bg-cream-100 border border-cream-200 rounded-xl p-6 text-sm text-stone">
        <p class="font-medium text-terracotta mb-1">Couldn't load words</p>
        <p class="text-xs text-stone-light">{{ error.message }}</p>
      </div>

      <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <WordCard v-for="word in recentWords" :key="word.id" :word="word" />
      </div>
    </section>

    <!-- Stats -->
    <section class="px-4 md:px-12 py-8 border-t border-cream-200 bg-cream-50">
      <div class="grid grid-cols-2 md:grid-cols-4 gap-6 text-center mb-6">
        <div>
          <p class="font-serif text-3xl text-forest-dark font-semibold">
            {{ totalWords.toLocaleString() }}
          </p>
          <p class="text-[10px] uppercase tracking-wider text-stone">Words</p>
        </div>
        <div>
          <p class="font-serif text-3xl text-forest-dark font-semibold">3</p>
          <p class="text-[10px] uppercase tracking-wider text-stone">Dialects</p>
        </div>
        <div>
          <p class="font-serif text-3xl text-forest-dark font-semibold">Dawida</p>
          <p class="text-[10px] uppercase tracking-wider text-stone">· Sagala · Kasighau</p>
        </div>
        <div>
          <p class="font-serif text-3xl text-forest-dark font-semibold">Open</p>
          <p class="text-[10px] uppercase tracking-wider text-stone">
            <NuxtLink to="/contribute" class="text-forest hover:underline">Contribute →</NuxtLink>
          </p>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { WordListItem } from '~/types'

// ── Search bar ─────────────────────────────────────────────────────────────
const searchQuery = ref('')
const quickFilters = ['All', 'Nouns', 'Verbs', 'Phrases']
const router = useRouter()

function goToSearch() {
  if (searchQuery.value.trim()) {
    router.push({ path: '/search', query: { q: searchQuery.value } })
  } else {
    router.push('/search')
  }
}

function goToSearchWithFilter(filter: string) {
  const posMap: Record<string, string> = { Nouns: 'noun', Verbs: 'verb', Phrases: 'phrase' }
  const pos = posMap[filter]
  if (pos) {
    router.push({ path: '/search', query: { pos } })
  } else {
    router.push('/search')
  }
}

// ── Word of the day label ──────────────────────────────────────────────────
const todayLabel = computed(() =>
  new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }),
)

// ── Data: ONE fetch for recent words + word-of-the-day + total count ──────
const { data: wordsData, pending, error } = await useFetch('/api/words', {
  params: { size: 20, include_relations: false },
})

const recentWords = computed<WordListItem[]>(() => (wordsData.value?.items || []).slice(0, 4))
const totalWords = computed(() => wordsData.value?.total || 0)

// Word of the day — stable per day (indexed by day of year)
const wordOfDay = computed<WordListItem | null>(() => {
  const items = wordsData.value?.items
  if (!items?.length) return null
  const dayOfYear = Math.floor(
    (Date.now() - new Date(new Date().getFullYear(), 0, 0).getTime()) / 86400000,
  )
  return items[dayOfYear % items.length]
})
</script>

<template>
  <div>
    <!-- Search bar -->
    <section class="px-8 py-6 border-b border-cream-200">
      <div
        class="search-bar flex items-center gap-3 bg-cream-50 border border-cream-300 rounded-xl px-5 py-3 max-w-3xl"
      >
        <svg class="w-5 h-5 text-stone" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            d="M21 21l-4.35-4.35M11 18a7 7 0 100-14 7 7 0 000 14z" />
        </svg>
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Tafuta neno... / Search a word..."
          class="flex-1 bg-transparent text-sm text-ink placeholder-stone-light outline-none"
          @input="onSearchInput"
          @keyup.enter="runSearch"
        />
        <button
          v-if="searchQuery"
          @click="clearSearch"
          class="text-stone hover:text-terracotta"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </section>

    <!-- Layout: sidebar + results -->
    <section class="px-8 py-8 grid grid-cols-1 md:grid-cols-12 gap-8">
      <!-- Filter sidebar -->
      <aside class="col-span-3">
        <h3 class="text-xs font-semibold uppercase tracking-widest text-stone mb-4">Filter</h3>

        <div class="space-y-5 text-sm">
          <div>
            <p class="text-xs font-semibold text-ink-soft mb-2">Part of speech</p>
            <div class="space-y-1.5 text-xs text-stone">
              <label class="flex items-center gap-2 cursor-pointer">
                <input type="radio" v-model="filters.pos" :value="null" class="accent-forest" />
                All
              </label>
              <label v-for="pos in posOptions" :key="pos.value" class="flex items-center gap-2 cursor-pointer">
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
              <label v-for="d in dialectOptions" :key="d" class="flex items-center gap-2 cursor-pointer">
                <input type="radio" v-model="filters.dialect" :value="d" class="accent-forest" />
                {{ d }}
              </label>
            </div>
          </div>

          <div class="pt-4 border-t border-cream-200">
            <button
              @click="clearFilters"
              class="text-xs text-stone hover:text-forest underline"
            >
              Clear filters
            </button>
          </div>
        </div>
      </aside>

      <!-- Results -->
      <div class="col-span-9">
        <div class="flex items-center justify-between mb-4">
          <p class="text-xs text-stone">
            <span v-if="loading">Searching...</span>
            <span v-else>
              <span class="font-semibold text-ink">{{ total }}</span> {{ total === 1 ? 'word' : 'words' }}
              <span v-if="searchQuery"> for "{{ searchQuery }}"</span>
            </span>
          </p>
          <div class="flex items-center gap-2 text-xs text-stone">
            <span>Sort:</span>
            <button class="font-semibold text-forest">Relevance</button>
          </div>
        </div>

        <!-- Loading -->
        <div v-if="loading" class="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div v-for="i in 6" :key="i" class="bg-cream-50 border border-cream-200 rounded-xl p-4 animate-pulse">
            <div class="h-5 bg-cream-200 rounded w-1/3 mb-2"></div>
            <div class="h-4 bg-cream-200 rounded w-2/3 mb-1"></div>
            <div class="h-3 bg-cream-100 rounded w-1/2"></div>
          </div>
        </div>

        <!-- Error -->
        <div v-else-if="error" class="bg-cream-100 border border-cream-200 rounded-xl p-6 text-sm text-stone">
          <p class="font-medium text-terracotta mb-1">Couldn't load results</p>
          <p class="text-xs text-stone-light">{{ error }}</p>
        </div>

        <!-- Empty -->
        <div v-else-if="words.length === 0" class="bg-cream-100 border border-cream-200 rounded-xl p-12 text-center">
          <p class="font-serif text-xl text-forest-dark mb-2">No words found</p>
          <p class="text-sm text-stone mb-6">
            Try a different search or fewer filters.
          </p>
          <RouterLink
            to="/suggest"
            class="inline-block bg-forest hover:bg-forest-dark text-cream font-semibold text-sm px-5 py-2.5 rounded-lg transition"
          >
            Suggest a new word
          </RouterLink>
        </div>

        <!-- Results grid -->
        <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-3">
          <WordCard v-for="word in words" :key="word.id" :word="word" />
        </div>

        <!-- Load more -->
        <div v-if="hasMore" class="mt-6 text-center">
          <button
            @click="loadMore"
            :disabled="loadingMore"
            class="text-sm font-semibold text-forest border border-forest rounded-lg px-5 py-2 hover:bg-forest hover:text-cream transition disabled:opacity-50"
          >
            {{ loadingMore ? 'Loading...' : 'Load more' }}
          </button>
          <p class="text-[10px] text-stone-light mt-2">
            Showing {{ words.length }} of {{ total }}
          </p>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, reactive, watch, onMounted } from "vue";
import { useRoute, useRouter, RouterLink } from "vue-router";
import { listWords, searchWords } from "../api/words";
import WordCard from "../components/WordCard.vue";

const route = useRoute();
const router = useRouter();

const searchQuery = ref("");
const words = ref([]);
const total = ref(0);
const loading = ref(false);
const loadingMore = ref(false);
const error = ref("");
const page = ref(1);
const pageSize = 20;
const hasMore = ref(false);

const filters = reactive({
  pos: null,
  dialect: null,
});

const posOptions = [
  { value: "noun", label: "Noun" },
  { value: "verb", label: "Verb" },
  { value: "adjective", label: "Adjective" },
  { value: "phrase", label: "Phrase" },
];

const dialectOptions = ["Dawida", "Sagala", "Kasighau"];

let searchDebounce = null;

function onSearchInput() {
  clearTimeout(searchDebounce);
  searchDebounce = setTimeout(() => {
    runSearch();
  }, 300);
}

async function runSearch() {
  page.value = 1;
  await fetchWords();
}

async function fetchWords() {
  loading.value = true;
  error.value = "";
  try {
    const params = {
      page: page.value,
      size: pageSize,
    };
    if (searchQuery.value.trim()) params.q = searchQuery.value.trim();
    if (filters.pos) params.pos = filters.pos;
    if (filters.dialect) params.dialect = filters.dialect;

    const data = await listWords(params);
    words.value = page.value === 1 ? data.items : [...words.value, ...data.items];
    total.value = data.total;
    hasMore.value = data.has_next;
  } catch (err) {
    error.value = err.message || "Unknown error";
  } finally {
    loading.value = false;
  }
}

async function loadMore() {
  loadingMore.value = true;
  page.value++;
  await fetchWords();
  loadingMore.value = false;
}

function clearSearch() {
  searchQuery.value = "";
  runSearch();
}

function clearFilters() {
  filters.pos = null;
  filters.dialect = null;
  runSearch();
}

// Re-fetch when filters change
watch(() => [filters.pos, filters.dialect], () => {
  runSearch();
});

// Read initial query from URL
onMounted(() => {
  const q = route.query.q;
  const pos = route.query.pos;
  if (q) searchQuery.value = q;
  if (pos) filters.pos = pos;
  fetchWords();
});
</script>

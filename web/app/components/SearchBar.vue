<template>
  <div class="relative" :class="wrapperClass">
    <!-- Input row -->
    <div
      class="flex items-center gap-3 rounded-xl transition-colors"
      :class="[
        size === 'lg'
          ? 'bg-cream-50 border border-cream-300 px-5 py-4'
          : 'bg-cream-50 border border-cream-300 px-4 py-3',
        dropdownOpen && results.length ? 'border-forest border-2 -my-px' : '',
      ]"
    >
      <svg class="w-5 h-5 text-stone flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-4.35-4.35M11 18a7 7 0 100-14 7 7 0 000 14z" />
      </svg>
      <input
        ref="inputEl"
        v-model="query"
        type="text"
        :placeholder="placeholder"
        class="flex-1 bg-transparent text-base text-ink placeholder-stone-light outline-none min-w-0"
        :class="size === 'lg' ? 'text-base' : 'text-sm'"
        role="combobox"
        :aria-expanded="dropdownOpen"
        aria-controls="search-dropdown"
        :aria-activedescendant="activeDescendant"
        @input="onInput"
        @focus="onFocus"
        @blur="onBlur"
        @keydown="onKeydown"
      />
      <span v-if="query" class="text-[10px] text-stone-light flex-shrink-0">
        {{ dropdownOpen && results.length ? `${results.length} result${results.length === 1 ? '' : 's'}` : '' }}
      </span>
      <button
        v-if="query && clearable"
        class="text-stone hover:text-terracotta flex-shrink-0 focus-ring rounded"
        aria-label="Clear search"
        @mousedown.prevent="clear"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
      <kbd
        v-if="size === 'lg' && !query"
        class="text-[10px] font-mono text-stone-light bg-cream-100 px-1.5 py-0.5 rounded border border-cream-200 flex-shrink-0"
      >↵</kbd>
    </div>

    <!-- Dropdown -->
    <Transition name="dropdown">
      <div
        v-if="dropdownOpen && results.length"
        id="search-dropdown"
        class="absolute left-0 right-0 mt-1 bg-white border border-cream-200 rounded-xl shadow-lift overflow-hidden z-30"
        @mousedown.prevent
      >
        <a
          v-for="(item, idx) in results"
          :key="item.id"
          :href="`/words/${item.slug}`"
          class="block px-4 py-2.5 cursor-pointer border-l-2 transition-colors"
          :class="idx === activeIndex ? 'bg-forest-tint border-forest' : 'border-transparent hover:bg-cream-50'"
          :id="`search-item-${idx}`"
          @click="selectItem(item)"
          @mouseenter="activeIndex = idx"
        >
          <div class="flex items-baseline justify-between gap-3">
            <div class="flex items-baseline gap-2 min-w-0">
              <span class="font-serif text-base text-ink font-semibold">{{ item.headword }}</span>
              <PosBadge v-if="item.part_of_speech" :pos="item.part_of_speech" />
              <span v-if="item.noun_class" class="nclass-badge">{{ item.noun_class }}</span>
            </div>
            <!-- Similarity bar -->
            <div v-if="item.similarity !== null" class="flex items-center gap-1.5 flex-shrink-0">
              <div class="w-12 h-1 bg-cream-200 rounded-full overflow-hidden">
                <div
                  class="h-full bg-forest"
                  :style="{ width: `${Math.round((item.similarity ?? 0) * 100)}%` }"
                ></div>
              </div>
              <span class="text-[9px] text-stone-light font-mono">{{ (item.similarity ?? 0).toFixed(2) }}</span>
            </div>
          </div>
          <p class="text-xs text-stone truncate mt-0.5">
            <template v-if="item.swahili_translation">SW: {{ item.swahili_translation }}</template>
            <template v-if="item.swahili_translation && item.english_translation"> · </template>
            <template v-if="item.english_translation">EN: {{ item.english_translation }}</template>
          </p>
        </a>
        <div class="border-t border-cream-200 px-4 py-2 bg-cream-50">
          <p class="text-[10px] text-stone-light">
            Press <kbd class="font-mono bg-cream-100 px-1 py-0.5 rounded border border-cream-200">↵</kbd> for all results
          </p>
        </div>
      </div>
    </Transition>

    <!-- Loading spinner (subtle, right-side) -->
    <div
      v-if="loading"
      class="absolute right-12 top-1/2 -translate-y-1/2"
      aria-hidden="true"
    >
      <svg class="w-4 h-4 text-stone-light animate-spin" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
      </svg>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import type { SearchResultItem } from '~/types'

const props = withDefaults(defineProps<{
  modelValue: string
  placeholder?: string
  /** 'lg' for the home hero (px-5 py-4), 'md' for the search page (px-4 py-3). */
  size?: 'lg' | 'md'
  /** Show the × clear button when query is non-empty. */
  clearable?: boolean
  /** Wrapper class — pass through so callers can set max-width etc. */
  wrapperClass?: string
  /** Debounce ms (default 250). */
  debounceMs?: number
}>(), {
  placeholder: 'Tafuta neno... / Search a word...',
  size: 'lg',
  clearable: false,
  wrapperClass: '',
  debounceMs: 250,
})

const emit = defineEmits<{
  'update:modelValue': [value: string]
  /** Enter pressed without a highlighted dropdown item — caller navigates to /search?q=. */
  submit: [query: string]
  /** User clicked or pressed Enter on a dropdown item — caller navigates to /words/<slug>. */
  select: [item: SearchResultItem]
  /** Query was cleared via the × button. */
  clear: []
}>()

// ── Local state ───────────────────────────────────────────────────────────
const query = ref(props.modelValue)
const results = ref<SearchResultItem[]>([])
const loading = ref(false)
const dropdownOpen = ref(false)
const activeIndex = ref(-1)
const inputEl = ref<HTMLInputElement | null>(null)

// Keep local query in sync if parent updates modelValue externally (e.g. URL sync)
watch(() => props.modelValue, (v) => {
  if (v !== query.value) {
    query.value = v
    if (!v) {
      results.value = []
      dropdownOpen.value = false
    }
  }
})

// Emit modelValue updates whenever local query changes
watch(query, (v) => emit('update:modelValue', v))

const activeDescendant = computed(() =>
  activeIndex.value >= 0 ? `search-item-${activeIndex.value}` : undefined,
)

// ── Debounced fetch ───────────────────────────────────────────────────────
let debounceTimer: ReturnType<typeof setTimeout> | null = null
let lastRequestId = 0

async function fetchResults(q: string) {
  const trimmed = q.trim()
  if (!trimmed) {
    results.value = []
    dropdownOpen.value = false
    return
  }
  loading.value = true
  const reqId = ++lastRequestId
  try {
    const data = await searchWords(trimmed, 10)
    // Drop stale responses — only the latest request's results matter
    if (reqId === lastRequestId) {
      results.value = data.items || []
      dropdownOpen.value = results.value.length > 0
      activeIndex.value = -1
    }
  } catch {
    if (reqId === lastRequestId) {
      results.value = []
      dropdownOpen.value = false
    }
  } finally {
    if (reqId === lastRequestId) loading.value = false
  }
}

function onInput() {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    fetchResults(query.value)
  }, props.debounceMs)
}

function onFocus() {
  if (results.value.length > 0 && query.value.trim()) {
    dropdownOpen.value = true
  }
}

// Delay blur so click events on dropdown items fire first
let blurTimer: ReturnType<typeof setTimeout> | null = null
function onBlur() {
  if (blurTimer) clearTimeout(blurTimer)
  blurTimer = setTimeout(() => {
    dropdownOpen.value = false
  }, 150)
}

// ── Keyboard nav ──────────────────────────────────────────────────────────
function onKeydown(e: KeyboardEvent) {
  if (!dropdownOpen.value || results.value.length === 0) {
    // No dropdown — Enter submits the query (caller navigates to /search)
    if (e.key === 'Enter' && query.value.trim()) {
      e.preventDefault()
      emit('submit', query.value.trim())
    }
    return
  }

  if (e.key === 'ArrowDown') {
    e.preventDefault()
    activeIndex.value = (activeIndex.value + 1) % results.value.length
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    activeIndex.value = (activeIndex.value - 1 + results.value.length) % results.value.length
  } else if (e.key === 'Enter') {
    e.preventDefault()
    const item = activeIndex.value >= 0 ? results.value[activeIndex.value] : undefined
    if (item) {
      selectItem(item)
    } else if (query.value.trim()) {
      emit('submit', query.value.trim())
    }
  } else if (e.key === 'Escape') {
    e.preventDefault()
    dropdownOpen.value = false
    activeIndex.value = -1
  }
}

function selectItem(item: SearchResultItem) {
  dropdownOpen.value = false
  activeIndex.value = -1
  emit('select', item)
}

function clear() {
  query.value = ''
  results.value = []
  dropdownOpen.value = false
  emit('update:modelValue', '')
  emit('clear')
  inputEl.value?.focus()
}

// Allow parent to focus the input programmatically (e.g. when clicking the
// hero search affordance)
defineExpose({ focus: () => inputEl.value?.focus() })

onBeforeUnmount(() => {
  if (debounceTimer) clearTimeout(debounceTimer)
  if (blurTimer) clearTimeout(blurTimer)
})
</script>

<style scoped>
.dropdown-enter-active,
.dropdown-leave-active {
  transition: opacity 0.12s ease, transform 0.12s ease;
}
.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>

<template>
  <div class="p-6 md:p-8">
    <header class="mb-6">
      <p class="text-xs font-semibold tracking-widest uppercase text-ochre mb-2">Admin · Words</p>
      <h1 class="font-serif text-2xl text-forest-dark">Word management</h1>
      <p class="text-sm text-stone mt-1">Search, edit, hide, or merge words.</p>
    </header>

    <!-- Search bar -->
    <div class="flex items-center gap-3 bg-cream-50 border border-cream-300 rounded-xl px-4 py-3 mb-6 max-w-xl">
      <svg class="w-5 h-5 text-stone" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-4.35-4.35M11 18a7 7 0 100-14 7 7 0 000 14z" />
      </svg>
      <input
        v-model="searchQuery"
        type="text"
        placeholder="Search words by headword or gloss..."
        class="flex-1 bg-transparent text-sm text-ink placeholder-stone-light outline-none"
        @input="onSearch"
      />
    </div>

    <!-- Results -->
    <div v-if="pending" class="space-y-2">
      <div v-for="i in 5" :key="i" class="h-12 bg-cream-100 rounded-lg animate-pulse"></div>
    </div>

    <div v-else-if="words.length === 0 && searchQuery" class="bg-cream-100 border border-cream-200 rounded-xl p-8 text-center text-sm text-stone">
      No words found for "{{ searchQuery }}".
    </div>

    <div v-else class="bg-cream-50 border border-cream-200 rounded-xl overflow-hidden">
      <table class="w-full text-sm">
        <thead class="bg-cream-100 text-[10px] uppercase tracking-wider text-stone-light">
          <tr>
            <th class="text-left px-4 py-3 font-semibold">Word</th>
            <th class="text-left px-4 py-3 font-semibold hidden md:table-cell">Gloss</th>
            <th class="text-left px-4 py-3 font-semibold hidden md:table-cell">Dialect</th>
            <th class="text-right px-4 py-3 font-semibold">Actions</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-cream-200 bg-white">
          <tr v-for="word in words" :key="word.id" class="hover:bg-cream-50 transition">
            <td class="px-4 py-3">
              <div class="flex items-baseline gap-2">
                <NuxtLink :to="`/words/${word.id}`" class="font-serif text-base text-ink font-medium hover:underline">{{ word.headword }}</NuxtLink>
                <PosBadge v-if="word.part_of_speech" :pos="word.part_of_speech" />
              </div>
            </td>
            <td class="px-4 py-3 text-xs text-stone hidden md:table-cell">{{ word.swahili_gloss || '—' }}</td>
            <td class="px-4 py-3 text-xs text-stone-light hidden md:table-cell">{{ word.dialect || '—' }}</td>
            <td class="px-4 py-3 text-right">
              <div class="flex items-center justify-end gap-1.5">
                <NuxtLink :to="`/words/${word.id}`" class="focus-ring text-[10px] font-medium text-forest-dark bg-forest-tint hover:bg-forest/20 px-2 py-1 rounded transition">Edit</NuxtLink>
                <button
                  class="focus-ring text-[10px] font-medium text-terracotta-dark bg-terracotta-tint hover:bg-terracotta/20 px-2 py-1 rounded transition"
                  :disabled="hidingId === word.id"
                  @click="hideWord(word.id, word.headword)"
                >{{ hidingId === word.id ? '...' : 'Hide' }}</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Merge tool (placeholder) -->
    <section class="mt-8">
      <h2 class="font-serif text-base text-forest-dark mb-3">Merge words</h2>
      <div class="bg-cream-50 border border-cream-200 rounded-xl p-4">
        <p class="text-xs text-stone mb-3">Merge two duplicate words. The source word is removed; its relations and glosses are transferred to the target.</p>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <label class="field-label">Source word ID</label>
            <input v-model="mergeSource" type="text" class="field" placeholder="UUID of the word to merge FROM" />
          </div>
          <div>
            <label class="field-label">Target word ID</label>
            <input v-model="mergeTarget" type="text" class="field" placeholder="UUID of the word to merge INTO" />
          </div>
        </div>
        <button
          class="focus-ring btn btn-primary btn-sm mt-3"
          :disabled="!mergeSource || !mergeTarget || merging"
          @click="doMerge"
        >{{ merging ? 'Merging...' : 'Merge words' }}</button>
        <p v-if="mergeError" class="text-xs text-terracotta mt-2">{{ mergeError }}</p>
        <p v-if="mergeSuccess" class="text-xs text-forest mt-2">Merge complete.</p>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import type { WordListItem } from '~/types'

definePageMeta({
  ssr: false,
  middleware: 'admin',
})

const searchQuery = ref('')
const hidingId = ref<string | null>(null)
let searchDebounce: ReturnType<typeof setTimeout> | null = null

const { data, pending, refresh } = await useFetch<{ items: WordListItem[]; total: number }>('/api/words', {
  params: { size: 20 },
})

const words = computed(() => data.value?.items || [])

function onSearch() {
  if (searchDebounce) clearTimeout(searchDebounce)
  searchDebounce = setTimeout(() => {
    refresh()
  }, 300)
}

// Override params when searching
watch(searchQuery, (q) => {
  // useFetch doesn't auto-update params, so we use $fetch directly for search
})

// Actually, let's use a simpler approach: search via listWords()
async function performSearch() {
  if (!searchQuery.value.trim()) {
    await refresh()
    return
  }
  try {
    const result = await listWords({ q: searchQuery.value.trim(), size: 20 })
    data.value = result
  } catch (err) {
    console.error('Search failed:', err)
  }
}

// Debounced search
watch(searchQuery, () => {
  if (searchDebounce) clearTimeout(searchDebounce)
  searchDebounce = setTimeout(performSearch, 300)
})

async function hideWord(id: string, headword: string) {
  if (!confirm(`Hide "${headword}"? This soft-deletes it from the dictionary.`)) return
  hidingId.value = id
  try {
    await adminHideWord(id)
    await performSearch()
  } catch (err) {
    console.error('Failed to hide word:', err)
  } finally {
    hidingId.value = null
  }
}

// Merge
const mergeSource = ref('')
const mergeTarget = ref('')
const merging = ref(false)
const mergeError = ref('')
const mergeSuccess = ref(false)

async function doMerge() {
  merging.value = true
  mergeError.value = ''
  mergeSuccess.value = false
  try {
    await adminMergeWords(mergeSource.value.trim(), mergeTarget.value.trim())
    mergeSuccess.value = true
    mergeSource.value = ''
    mergeTarget.value = ''
  } catch (err: unknown) {
    const e = err as { response?: { _data?: { detail?: string } } }
    mergeError.value = e.response?._data?.detail || 'Merge failed.'
  } finally {
    merging.value = false
  }
}
</script>

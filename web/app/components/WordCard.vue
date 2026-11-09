<template>
  <NuxtLink
    :to="`/words/${word.slug}`"
    class="focus-ring block bg-cream-50 hover:bg-white border border-cream-200 hover:border-forest/30 rounded-xl p-4 hover:shadow-card transition"
  >
    <div class="flex items-baseline justify-between mb-1">
      <div class="flex items-baseline gap-2 min-w-0">
        <span class="font-serif text-lg text-ink font-semibold">{{ word.headword }}</span>
        <PosBadge :pos="word.part_of_speech" />
        <span v-if="word.noun_class" class="nclass-badge">{{ word.noun_class }}</span>
      </div>
      <!-- Similarity bar — shown only on search results (when showSimilarity is true and similarity is a number) -->
      <div v-if="showSimilarity" class="flex items-center gap-1.5 flex-shrink-0">
        <div class="w-10 h-1 bg-cream-200 rounded-full overflow-hidden">
          <div
            class="h-full bg-forest"
            :style="{ width: `${Math.round(similarityScore * 100)}%` }"
          ></div>
        </div>
        <span class="text-[9px] text-stone-light font-mono">{{ similarityScore.toFixed(2) }}</span>
      </div>
      <div v-else-if="word.dialect" class="text-[10px] text-stone-light">{{ word.dialect }}</div>
    </div>
    <p v-if="word.swahili_translation" class="text-sm text-stone">{{ word.swahili_translation }}</p>
    <p v-if="word.english_translation" class="text-sm text-stone-light mt-0.5">{{ word.english_translation }}</p>
  </NuxtLink>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { SearchResultItem, WordListItem } from '~/types'

const props = defineProps<{
  word: WordListItem | SearchResultItem
  /** When true (search mode), render the similarity bar from word.similarity. */
  showSimilarity?: boolean
}>()

// Extract similarity as a number (0..1) when present, else 0.
const similarityScore = computed<number>(() => {
  if (!props.showSimilarity) return 0
  const sim = (props.word as SearchResultItem).similarity
  return typeof sim === 'number' ? sim : 0
})

const showSimilarity = computed(() =>
  props.showSimilarity === true && typeof (props.word as SearchResultItem).similarity === 'number',
)
</script>

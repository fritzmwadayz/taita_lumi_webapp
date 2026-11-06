<template>
  <span v-if="pos" :class="['pos-badge', badgeClass]">
    <svg class="w-3 h-3" viewBox="0 0 12 12" :fill="symbolFill" :stroke="symbolStroke">
      <component :is="symbolComponent" />
    </svg>
    {{ pos }}
  </span>
  <span v-else class="text-[10px] text-stone-light italic">no POS yet</span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ pos: string | null }>()

const badgeClass = computed(() => {
  switch (props.pos) {
    case 'noun': return 'pos-noun'
    case 'verb': return 'pos-verb'
    case 'adjective':
    case 'adj': return 'pos-adj'
    case 'phrase': return 'pos-phrase'
    case 'adverb': return 'pos-adverb'
    default: return 'pos-noun'
  }
})

// Symbol shape per POS — color-blind friendly (shape distinguishes even in grayscale)
const symbolFill = computed(() => 'currentColor')
const symbolStroke = computed(() => 'none')

// Render different SVG shapes per POS type
const symbolComponent = computed(() => {
  switch (props.pos) {
    case 'noun':
      // Square
      return { template: '<rect x="2" y="2" width="8" height="8" rx="1"/>' }
    case 'verb':
      // Triangle (up)
      return { template: '<path d="M2 2 L10 2 L6 10 Z"/>' }
    case 'adjective':
    case 'adj':
      // Circle
      return { template: '<circle cx="6" cy="6" r="4"/>' }
    case 'phrase':
      // Checkmark
      return {
        template: '<path d="M2 6 L5 9 L10 3" fill="none" stroke="currentColor" stroke-width="1.5"/>',
      }
    case 'adverb':
      // Diamond
      return { template: '<path d="M6 2 L10 6 L6 10 L2 6 Z"/>' }
    default:
      return { template: '<rect x="2" y="2" width="8" height="8" rx="1"/>' }
  }
})
</script>

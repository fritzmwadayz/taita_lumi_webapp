<template>
  <span
    class="audio-placeholder"
    :class="[sizeClass, toneClass]"
    :title="tooltip"
    role="img"
    :aria-label="tooltip"
  >
    <svg :class="iconClass" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.536 8.464a5 5 0 010 7.072M12.707 11.293a3 3 0 010 4.242M9.879 14.121a1 1 0 010 1.414" />
    </svg>
    <span class="audio-tooltip">{{ tooltip }}</span>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  /** Icon + circle size. */
  size?: 'sm' | 'md' | 'lg'
  /** 'light' = for cream backgrounds (default); 'onDark' = for the forest-green hero. */
  tone?: 'light' | 'onDark'
  /** Tooltip text. */
  tooltip?: string
}>(), {
  size: 'md',
  tone: 'light',
  tooltip: 'No audio yet',
})

const sizeClass = computed(() => ({
  sm: 'w-8 h-8',
  md: 'w-9 h-9',
  lg: 'w-10 h-10',
}[props.size]))

const iconClass = computed(() => ({
  sm: 'w-4 h-4',
  md: 'w-5 h-5',
  lg: 'w-6 h-6',
}[props.size]))

const toneClass = computed(() => props.tone === 'onDark'
  ? 'audio-on-dark'
  : 'audio-light')
</script>

<style scoped>
.audio-placeholder {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 9999px;
  cursor: not-allowed;
  position: relative;
  flex-shrink: 0;
}

/* Light tone (cream backgrounds) */
.audio-light {
  color: #9CA3AF;
  background: transparent;
  border: 1.5px dashed #D8CBA8;
}

/* On-dark tone (forest hero) */
.audio-on-dark {
  color: rgba(251, 247, 240, 0.5);
  background: transparent;
  border: 1.5px dashed rgba(251, 247, 240, 0.3);
}

/* Tooltip */
.audio-placeholder:hover .audio-tooltip {
  opacity: 1;
}
.audio-tooltip {
  position: absolute;
  bottom: calc(100% + 6px);
  left: 50%;
  transform: translateX(-50%);
  background: #1F2937;
  color: #FBF7F0;
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
  font-size: 0.625rem;
  white-space: nowrap;
  opacity: 0;
  transition: opacity 0.15s;
  pointer-events: none;
}
.audio-tooltip::after {
  content: '';
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  border: 3px solid transparent;
  border-top-color: #1F2937;
}
</style>

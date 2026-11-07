<template>
  <!-- class/style fall through automatically (single root) -->
  <div class="skeleton" :style="{ height, width }" aria-hidden="true" />
</template>

<script setup lang="ts">
// Shimmering skeleton block. Size it with the height/width props or with
// Tailwind classes: <UiSkeleton class="h-3 w-1/4 rounded" />
withDefaults(defineProps<{
  height?: string
  width?: string
}>(), {
  height: '1rem',
  width: '100%',
})
</script>

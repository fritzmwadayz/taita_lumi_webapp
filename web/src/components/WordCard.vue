<template>
  <RouterLink
    :to="`/words/${word.id}`"
    class="block bg-cream-50 hover:bg-white border border-cream-200 rounded-xl p-4 md:p-5 transition"
  >
    <div class="flex items-baseline justify-between mb-1">
      <div class="flex items-baseline gap-2">
        <span class="font-serif text-xl text-ink font-semibold">{{ word.headword }}</span>
        <PosBadge :pos="word.part_of_speech" />
        <span v-if="word.noun_class" class="nclass-badge">{{ word.noun_class }}</span>
      </div>
      <div v-if="word.dialect" class="text-[10px] text-stone-light">{{ word.dialect }}</div>
    </div>
    <p v-if="word.swahili_gloss" class="text-sm text-stone">{{ word.swahili_gloss }}</p>
    <p v-if="word.english_gloss" class="text-sm text-stone-light mt-0.5">{{ word.english_gloss }}</p>
    <div v-if="word.has_relations" class="flex items-center gap-1 mt-2 text-[10px] text-stone-light">
      <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"/></svg>
      <span>related words</span>
    </div>
  </RouterLink>
</template>

<script setup>
import { RouterLink } from "vue-router";
import PosBadge from "./PosBadge.vue";
defineProps({ word: { type: Object, required: true } });
</script>

<style scoped>
.nclass-badge {
  display: inline-flex;
  padding: 1px 8px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 500;
  background: #f5efe3;
  color: #6b7280;
  border: 1px solid #e8dfc8;
}
</style>

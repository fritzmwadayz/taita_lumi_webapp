<template>
  <div>
    <!-- Back link -->
    <div class="px-8 py-4">
      <RouterLink to="/search" class="inline-flex items-center gap-1.5 text-sm text-stone hover:text-forest">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
        </svg>
        Back to search
      </RouterLink>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="max-w-[680px] mx-auto px-8 py-24 text-center">
      <div class="animate-pulse">
        <div class="h-16 bg-cream-200 rounded w-1/2 mx-auto mb-4"></div>
        <div class="h-4 bg-cream-100 rounded w-1/3 mx-auto"></div>
      </div>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="max-w-[680px] mx-auto px-8 py-24 text-center">
      <p class="font-serif text-3xl text-forest-dark mb-4">Word not found</p>
      <p class="text-sm text-stone mb-8">{{ error }}</p>
      <RouterLink
        to="/search"
        class="inline-block bg-forest hover:bg-forest-dark text-cream font-semibold text-sm px-5 py-2.5 rounded-lg transition"
      >
        Back to search
      </RouterLink>
    </div>

    <!-- Word detail (sparse layout) -->
    <article v-else-if="word" class="max-w-[680px] mx-auto px-8">
      <!-- Word header -->
      <header class="pt-12 pb-16">
        <div class="flex items-baseline gap-4 mb-4">
          <h1 class="font-serif text-6xl text-forest-dark font-semibold tracking-tight">
            {{ word.headword }}
          </h1>
        </div>
        <div class="flex flex-wrap items-center gap-3 mb-10">
          <PosBadge v-if="word.part_of_speech" :pos="word.part_of_speech" />
          <span v-if="word.noun_class" class="nclass-badge">{{ word.noun_class }}</span>
          <template v-if="word.dialect">
            <span class="text-xs text-stone-light">·</span>
            <span class="text-xs text-stone">{{ word.dialect }} dialect</span>
          </template>
        </div>

        <!-- Share -->
        <ShareButtons :headword="word.headword" :word-id="word.id" />
      </header>

      <!-- Glosses — Swahili FIRST, then English -->
      <section v-if="word.glosses.length > 0" class="py-12 border-t border-cream-200">
        <h2 class="text-xs font-semibold uppercase tracking-widest text-stone mb-6">Translations</h2>

        <div class="space-y-8">
          <!-- Swahili (primary) -->
          <div v-if="swahiliGloss" class="flex gap-6">
            <span class="text-xs font-bold text-forest w-12 mt-1">SW</span>
            <div>
              <p class="font-serif text-2xl text-ink font-medium mb-1">{{ swahiliGloss.text }}</p>
            </div>
          </div>
          <!-- English (secondary) -->
          <div v-if="englishGloss" class="flex gap-6">
            <span class="text-xs font-bold text-terracotta w-12 mt-1">EN</span>
            <div>
              <p class="font-serif text-xl text-ink-soft font-medium mb-1">{{ englishGloss.text }}</p>
            </div>
          </div>
          <!-- No glosses -->
          <div v-if="!swahiliGloss && !englishGloss" class="text-sm text-stone-light italic">
            No translations yet. <RouterLink to="/suggest" class="text-forest hover:underline">Suggest one</RouterLink>.
          </div>
        </div>
      </section>

      <!-- Literal translation (only if present) -->
      <section v-if="word.literal_translation" class="py-12 border-t border-cream-200 bg-cream-50 -mx-8 px-8">
        <div class="max-w-[680px] mx-auto">
          <h2 class="text-xs font-semibold uppercase tracking-widest text-stone mb-3">Literal translation</h2>
          <p class="font-serif text-base italic text-ink-soft mb-2">"{{ word.literal_translation }}"</p>
          <p v-if="word.morphology_notes" class="text-xs text-stone leading-relaxed">{{ word.morphology_notes }}</p>
        </div>
      </section>

      <!-- Relations -->
      <section v-if="word.relations.length > 0" class="py-12 border-t border-cream-200">
        <h2 class="text-xs font-semibold uppercase tracking-widest text-stone mb-6">Related words</h2>

        <div class="space-y-4">
          <div
            v-for="rel in groupedRelations"
            :key="`${rel.other_word_id}-${rel.relation_type}`"
            class="flex items-baseline gap-4"
          >
            <span class="text-[10px] font-medium text-stone-light uppercase w-24">{{ rel.relation_type }}</span>
            <RouterLink
              :to="`/words/${rel.other_word_id}`"
              class="font-serif text-lg text-forest hover:underline"
            >
              {{ rel.other_headword }}
            </RouterLink>
          </div>
        </div>
      </section>

      <!-- Metadata footer -->
      <footer class="py-10 border-t border-cream-200">
        <div class="flex flex-wrap items-center gap-x-4 gap-y-1 text-[10px] text-stone-light">
          <span>Entry ID: {{ word.id.slice(0, 8) }}...</span>
          <span>·</span>
          <span>Added {{ formatDate(word.created_at) }}</span>
          <span>·</span>
          <span>Status: {{ word.status }}</span>
        </div>
      </footer>
    </article>
  </div>
</template>

<script setup>
import { ref, computed, watch } from "vue";
import { useRoute, RouterLink } from "vue-router";
import { getWord } from "../api/words";
import PosBadge from "../components/PosBadge.vue";
import ShareButtons from "../components/ShareButtons.vue";

const route = useRoute();
const word = ref(null);
const loading = ref(true);
const error = ref("");

const swahiliGloss = computed(() =>
  word.value?.glosses?.find((g) => g.language === "sw")
);
const englishGloss = computed(() =>
  word.value?.glosses?.find((g) => g.language === "en")
);

// Group relations by type for display
const groupedRelations = computed(() => {
  if (!word.value?.relations) return [];
  // Deduplicate by (other_word_id, relation_type)
  const seen = new Set();
  return word.value.relations.filter((rel) => {
    const key = `${rel.other_word_id}-${rel.relation_type}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
});

function formatDate(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

async function fetchWord(id) {
  loading.value = true;
  error.value = "";
  try {
    word.value = await getWord(id);
  } catch (err) {
    if (err.response?.status === 404) {
      error.value = "This word doesn't exist or has been removed.";
    } else {
      error.value = err.message || "Failed to load word";
    }
    word.value = null;
  } finally {
    loading.value = false;
  }
}

// Fetch on mount
watch(
  () => route.params.id,
  (newId) => {
    if (newId) fetchWord(newId);
  },
  { immediate: true }
);
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

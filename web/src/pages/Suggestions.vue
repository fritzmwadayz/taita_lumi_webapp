<template>
  <div>
    <!-- Header -->
    <section class="px-12 py-10 border-b border-cream-200">
      <h1 class="font-serif text-4xl text-forest-dark mb-2">Suggestions</h1>
      <p class="text-base text-stone">Help review and improve the dictionary.</p>
    </section>

    <!-- Filter tabs -->
    <section class="px-12 py-4 flex items-center justify-between border-b border-cream-200">
      <div class="flex items-center gap-1">
        <button
          v-for="tab in tabs"
          :key="tab.value"
          @click="activeStatus = tab.value"
          :class="['tab-pill', activeStatus === tab.value && 'active']"
        >
          {{ tab.label }}
        </button>
      </div>
      <div class="flex items-center gap-3 text-xs text-stone">
        <span>Sort:</span>
        <button class="font-semibold text-forest">Most recent</button>
      </div>
    </section>

    <!-- Suggestion cards -->
    <section class="px-12 py-8">
      <!-- Loading -->
      <div v-if="loading" class="grid grid-cols-2 gap-4">
        <div
          v-for="i in 4"
          :key="i"
          class="bg-white border border-cream-200 rounded-xl p-5 animate-pulse"
        >
          <div class="h-3 bg-cream-200 rounded w-1/3 mb-2"></div>
          <div class="h-6 bg-cream-200 rounded w-1/2 mb-3"></div>
          <div class="h-4 bg-cream-100 rounded w-2/3 mb-1"></div>
          <div class="h-3 bg-cream-100 rounded w-1/2"></div>
        </div>
      </div>

      <!-- Error -->
      <div
        v-else-if="error"
        class="bg-cream-100 border border-cream-200 rounded-xl p-6 text-sm text-stone"
      >
        <p class="font-medium text-terracotta mb-1">Couldn't load suggestions</p>
        <p class="text-xs text-stone-light">{{ error }}</p>
      </div>

      <!-- Empty -->
      <div
        v-else-if="suggestions.length === 0"
        class="bg-cream-100 border border-cream-200 rounded-xl p-12 text-center"
      >
        <p class="font-serif text-xl text-forest-dark mb-2">No suggestions here</p>
        <p class="text-sm text-stone mb-6">
          {{ activeStatus === "open" ? "Be the first to suggest a word." : "Nothing to show." }}
        </p>
        <RouterLink
          to="/suggest"
          class="inline-block bg-forest hover:bg-forest-dark text-cream font-semibold text-sm px-5 py-2.5 rounded-lg transition"
        >
          Suggest a word
        </RouterLink>
      </div>

      <!-- Grid of cards -->
      <div v-else class="grid grid-cols-2 gap-4">
        <SuggestionCard
          v-for="s in suggestions"
          :key="s.id"
          :suggestion="s"
          @voted="onVoted"
        />
      </div>

      <!-- Load more -->
      <div v-if="hasMore" class="mt-6 text-center">
        <button
          @click="loadMore"
          :disabled="loadingMore"
          class="text-sm font-semibold text-forest border border-forest rounded-lg px-5 py-2 hover:bg-forest hover:text-cream transition disabled:opacity-50"
        >
          {{ loadingMore ? "Loading..." : "Load more" }}
        </button>
        <p class="text-[10px] text-stone-light mt-2">
          Showing {{ suggestions.length }} of {{ total }}
        </p>
      </div>
    </section>

    <!-- Footer CTA -->
    <section class="px-12 py-8 bg-cream-100 border-t border-cream-200 flex items-center justify-between">
      <div>
        <p class="text-base text-ink-soft font-medium">Have a word to add?</p>
        <p class="text-xs text-stone">
          Read the
          <RouterLink to="/guide" class="text-forest hover:underline">Reading Guide</RouterLink>
          first if you're new.
        </p>
      </div>
      <RouterLink
        to="/suggest"
        class="bg-forest hover:bg-forest-dark text-cream font-semibold text-sm px-5 py-2.5 rounded-lg transition"
      >
        Suggest a word
      </RouterLink>
    </section>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from "vue";
import { RouterLink } from "vue-router";
import { listSuggestions } from "../api/suggestions";
import SuggestionCard from "../components/SuggestionCard.vue";

const tabs = [
  { value: "open", label: "Open" },
  { value: "accepted", label: "Accepted" },
  { value: "rejected", label: "Rejected" },
];

const activeStatus = ref("open");
const suggestions = ref([]);
const total = ref(0);
const loading = ref(false);
const loadingMore = ref(false);
const error = ref("");
const page = ref(1);
const pageSize = 20;
const hasMore = ref(false);

async function fetchSuggestions() {
  loading.value = true;
  error.value = "";
  try {
    const data = await listSuggestions({
      status: activeStatus.value,
      page: page.value,
      size: pageSize,
    });
    suggestions.value = page.value === 1 ? data.items : [...suggestions.value, ...data.items];
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
  await fetchSuggestions();
  loadingMore.value = false;
}

/**
 * Handle vote events from SuggestionCard — update local state.
 * If the vote triggered auto-promotion, the suggestion moves from
 * "open" to "accepted", so we refresh the list to reflect that.
 */
function onVoted({ id, upvotes, downvotes, user_vote, promoted }) {
  const s = suggestions.value.find((x) => x.id === id);
  if (s) {
    s.upvotes = upvotes;
    s.downvotes = downvotes;
    s.user_vote = user_vote;
    if (promoted) {
      // Suggestion was auto-promoted — refresh the list after a short delay
      // so the user sees the "Accepted" badge
      setTimeout(() => fetchSuggestions(), 1500);
    }
  }
}

watch(activeStatus, () => {
  page.value = 1;
  fetchSuggestions();
});

onMounted(() => {
  fetchSuggestions();
});
</script>

<style scoped>
.tab-pill {
  padding: 8px 14px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.15s;
}
.tab-pill.active {
  background: #1f2937;
  color: #fbf7f0;
}
.tab-pill:hover:not(.active) {
  background: #f5efe3;
}
</style>

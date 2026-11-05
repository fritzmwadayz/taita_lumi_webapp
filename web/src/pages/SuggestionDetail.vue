<template>
  <div>
    <!-- Back link -->
    <div class="px-8 py-4">
      <RouterLink to="/suggestions" class="inline-flex items-center gap-1.5 text-sm text-stone hover:text-forest">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
        </svg>
        Back to suggestions
      </RouterLink>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="max-w-[680px] mx-auto px-8 py-24 text-center">
      <div class="animate-pulse">
        <div class="h-8 bg-cream-200 rounded w-1/3 mx-auto mb-4"></div>
        <div class="h-4 bg-cream-100 rounded w-1/2 mx-auto"></div>
      </div>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="max-w-[680px] mx-auto px-8 py-24 text-center">
      <p class="font-serif text-3xl text-forest-dark mb-4">Suggestion not found</p>
      <p class="text-sm text-stone mb-8">{{ error }}</p>
      <RouterLink
        to="/suggestions"
        class="inline-block bg-forest hover:bg-forest-dark text-cream font-semibold text-sm px-5 py-2.5 rounded-lg transition"
      >
        Back to suggestions
      </RouterLink>
    </div>

    <!-- Suggestion detail -->
    <article v-else-if="suggestion" class="max-w-[680px] mx-auto px-8">
      <!-- Header -->
      <header class="pt-8 pb-8 border-b border-cream-200">
        <div class="flex items-center gap-3 mb-4">
          <span class="type-badge">{{ typeLabel }}</span>
          <span
            v-if="suggestion.status === 'open'"
            class="status-badge status-open"
          >Open</span>
          <span
            v-else-if="suggestion.status === 'accepted'"
            class="status-badge status-accepted"
          >Accepted</span>
          <span
            v-else-if="suggestion.status === 'rejected'"
            class="status-badge status-rejected"
          >Rejected</span>
        </div>

        <!-- New word: show proposed word -->
        <h1 v-if="suggestion.target_type === 'new_word'" class="font-serif text-3xl md:text-5xl text-forest-dark font-semibold mb-4">
          {{ suggestion.proposed_value.headword }}
        </h1>

        <!-- Correction: show field being changed -->
        <h1 v-else class="font-serif text-3xl text-forest-dark mb-4">
          Update: {{ suggestion.field_path }}
        </h1>

        <p class="text-sm text-stone">
          Proposed by <span class="font-medium text-ink">{{ suggestion.author_display || "anonymous" }}</span>
          · {{ formatDate(suggestion.created_at) }}
        </p>
      </header>

      <!-- Proposed value (for new_word) -->
      <section v-if="suggestion.target_type === 'new_word'" class="py-8 border-b border-cream-200">
        <h2 class="text-xs font-semibold uppercase tracking-widest text-stone mb-6">Proposed translations</h2>

        <div class="space-y-6">
          <!-- Swahili -->
          <div v-if="suggestion.proposed_value.swahili_gloss" class="flex gap-6">
            <span class="text-xs font-bold text-forest w-12 mt-1">SW</span>
            <p class="font-serif text-xl text-ink font-medium">
              {{ suggestion.proposed_value.swahili_gloss }}
            </p>
          </div>
          <!-- English -->
          <div v-if="suggestion.proposed_value.english_gloss" class="flex gap-6">
            <span class="text-xs font-bold text-terracotta w-12 mt-1">EN</span>
            <p class="font-serif text-lg text-ink-soft font-medium">
              {{ suggestion.proposed_value.english_gloss }}
            </p>
          </div>
        </div>

        <!-- Metadata -->
        <div class="mt-8 grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div v-if="suggestion.proposed_value.part_of_speech">
            <p class="text-[10px] uppercase tracking-wider text-stone-light mb-1">Part of speech</p>
            <p class="text-ink">{{ suggestion.proposed_value.part_of_speech }}</p>
          </div>
          <div v-if="suggestion.proposed_value.dialect">
            <p class="text-[10px] uppercase tracking-wider text-stone-light mb-1">Dialect</p>
            <p class="text-ink">{{ suggestion.proposed_value.dialect }}</p>
          </div>
          <div v-if="suggestion.proposed_value.noun_class">
            <p class="text-[10px] uppercase tracking-wider text-stone-light mb-1">Noun class</p>
            <p class="text-ink">{{ suggestion.proposed_value.noun_class }}</p>
          </div>
          <div v-if="suggestion.proposed_value.literal_translation">
            <p class="text-[10px] uppercase tracking-wider text-stone-light mb-1">Literal translation</p>
            <p class="text-ink italic">"{{ suggestion.proposed_value.literal_translation }}"</p>
          </div>
        </div>
      </section>

      <!-- Proposed value (for word correction) -->
      <section v-else-if="suggestion.target_type === 'word'" class="py-8 border-b border-cream-200">
        <h2 class="text-xs font-semibold uppercase tracking-widest text-stone mb-4">Proposed change</h2>
        <p class="text-base text-ink">
          Change <code class="font-mono text-sm bg-cream-100 px-1.5 py-0.5 rounded">{{ suggestion.field_path }}</code>
          to:
        </p>
        <p class="font-serif text-xl text-forest font-medium mt-2">
          {{ formatValue(suggestion.proposed_value) }}
        </p>
      </section>

      <!-- Rationale -->
      <section v-if="suggestion.rationale" class="py-8 border-b border-cream-200 bg-cream-50 -mx-8 px-8">
        <div class="max-w-[680px] mx-auto">
          <h2 class="text-xs font-semibold uppercase tracking-widest text-stone mb-3">Author's note</h2>
          <p class="text-base text-ink-soft leading-relaxed italic">"{{ suggestion.rationale }}"</p>
        </div>
      </section>

      <!-- Vote section -->
      <section class="py-8 border-b border-cream-200">
        <h2 class="text-xs font-semibold uppercase tracking-widest text-stone mb-6">Community votes</h2>

        <!-- Reviewer/admin decide buttons -->
        <div
          v-if="authStore.isReviewer && suggestion.status === 'open'"
          class="bg-forest/5 border border-forest/20 rounded-lg p-4 mb-4"
        >
          <p class="text-xs font-semibold text-forest-dark mb-3">Reviewer actions</p>
          <div class="flex gap-2">
            <button
              @click="decide('accept')"
              :disabled="deciding"
              class="bg-forest hover:bg-forest-dark text-cream text-xs font-semibold px-4 py-2 rounded-lg transition disabled:opacity-50"
            >
              {{ deciding ? "Processing..." : "Accept & apply" }}
            </button>
            <button
              @click="decide('reject')"
              :disabled="deciding"
              class="bg-terracotta hover:bg-terracotta-dark text-cream text-xs font-semibold px-4 py-2 rounded-lg transition disabled:opacity-50"
            >
              Reject
            </button>
          </div>
          <div v-if="decideError" class="text-xs text-terracotta mt-2">{{ decideError }}</div>
        </div>

        <!-- Promotion celebration banner -->
        <div
          v-if="justPromoted"
          class="bg-forest text-cream rounded-lg p-4 mb-4 flex items-center gap-3"
        >
          <svg class="w-6 h-6 text-ochre-light flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.539 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
          </svg>
          <div>
            <p class="font-semibold text-sm">Suggestion accepted!</p>
            <p class="text-xs text-cream/80">
              This suggestion met the community threshold and has been added to the dictionary.
            </p>
          </div>
        </div>

        <!-- Vote buttons + counts -->
        <div class="flex items-center gap-3">
          <button
            @click="vote('up')"
            :disabled="voting || !canVote"
            :class="['vote-btn', suggestion.user_vote === 'up' && 'voted-up']"
          >
            <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path d="M5 10l5-5 5 5H5z" />
            </svg>
            <span>{{ suggestion.upvotes }}</span>
            <span class="text-xs ml-1 opacity-75">up</span>
          </button>
          <button
            @click="vote('down')"
            :disabled="voting || !canVote"
            :class="['vote-btn', suggestion.user_vote === 'down' && 'voted-down']"
          >
            <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path d="M5 10l5 5 5-5H5z" />
            </svg>
            <span>{{ suggestion.downvotes }}</span>
            <span class="text-xs ml-1 opacity-75">down</span>
          </button>

          <!-- Vote status / call to action -->
          <div class="ml-auto text-right">
            <p v-if="voteError" class="text-xs text-terracotta">{{ voteError }}</p>
            <p v-else-if="!authStore.isAuthenticated" class="text-xs text-stone-light">
              <RouterLink
                :to="{ path: '/login', query: { next: $route.fullPath } }"
                class="text-forest hover:underline font-medium"
              >Sign in</RouterLink>
              to vote
            </p>
            <p v-else-if="isOwnSuggestion" class="text-xs text-stone-light italic">
              You can't vote on your own suggestion
            </p>
            <p v-else-if="suggestion.status !== 'open'" class="text-xs text-stone-light italic">
              Voting closed
            </p>
            <p v-else-if="suggestion.user_vote === 'up'" class="text-xs text-forest">
              You voted up · click again to remove
            </p>
            <p v-else-if="suggestion.user_vote === 'down'" class="text-xs text-terracotta">
              You voted down · click again to remove
            </p>
            <p v-else class="text-xs text-stone-light">Click to vote</p>
          </div>
        </div>

        <!-- Net score -->
        <p class="text-xs text-stone-light mt-4">
          Net score: <span class="font-semibold text-ink">{{ suggestion.upvotes - suggestion.downvotes }}</span>
          <span v-if="suggestion.status === 'open'">
            · Needs 3 net upvotes + 7 days age to auto-promote
          </span>
        </p>
      </section>

      <!-- Metadata -->
      <footer class="py-8">
        <div class="flex flex-wrap items-center gap-x-4 gap-y-1 text-[10px] text-stone-light">
          <span>Suggestion ID: {{ suggestion.id.slice(0, 8) }}...</span>
          <span>·</span>
          <span>Status: {{ suggestion.status }}</span>
          <span v-if="suggestion.decided_at">·</span>
          <span v-if="suggestion.decided_at">
            Decided {{ formatDate(suggestion.decided_at) }}
          </span>
        </div>
      </footer>
    </article>
  </div>
</template>

<script setup>
import { ref, computed, watch } from "vue";
import { useRoute, useRouter, RouterLink } from "vue-router";
import { getSuggestion, castVote, decideSuggestion } from "../api/suggestions";
import { useAuthStore } from "../stores/auth";

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();

const suggestion = ref(null);
const loading = ref(true);
const error = ref("");
const voting = ref(false);
const voteError = ref("");
const justPromoted = ref(false);
const deciding = ref(false);
const decideError = ref("");

const canVote = computed(() => {
  if (!suggestion.value) return false;
  if (!authStore.isAuthenticated) return false;
  if (isOwnSuggestion.value) return false;
  return suggestion.value.status === "open";
});

const isOwnSuggestion = computed(() => {
  if (!suggestion.value || !authStore.user) return false;
  return suggestion.value.created_by_user_id === authStore.user.id;
});

const typeLabel = computed(() => {
  if (!suggestion.value) return "";
  switch (suggestion.value.target_type) {
    case "new_word":
      return "New word";
    case "word":
      return `Correction · ${suggestion.value.field_path}`;
    case "gloss":
      return "Gloss update";
    case "example":
      return "New example";
    case "relation":
      return "New relation";
    default:
      return suggestion.value.target_type;
  }
});

function formatValue(proposed) {
  if (typeof proposed === "string") return proposed;
  if (proposed.value) return proposed.value;
  if (proposed.text) return proposed.text;
  return JSON.stringify(proposed);
}

function formatDate(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

async function fetchSuggestion(id) {
  loading.value = true;
  error.value = "";
  try {
    suggestion.value = await getSuggestion(id);
  } catch (err) {
    if (err.response?.status === 404) {
      error.value = "This suggestion doesn't exist or has been removed.";
    } else {
      error.value = err.message || "Failed to load suggestion";
    }
    suggestion.value = null;
  } finally {
    loading.value = false;
  }
}

async function vote(voteType) {
  if (!authStore.isAuthenticated) {
    // Redirect to login with return URL
    router.push({
      path: "/login",
      query: { next: `/suggestions/${suggestion.value.id}` },
    });
    return;
  }

  voting.value = true;
  voteError.value = "";
  justPromoted.value = false;

  try {
    const result = await castVote(suggestion.value.id, voteType);

    // Update local state
    suggestion.value.upvotes = result.upvotes;
    suggestion.value.downvotes = result.downvotes;
    suggestion.value.user_vote = result.user_vote;

    if (result.promoted) {
      justPromoted.value = true;
      suggestion.value.status = "accepted";
      suggestion.value.applied_at = new Date().toISOString();
    }
  } catch (err) {
    if (err.response?.status === 400) {
      voteError.value = err.response.data.detail || "Cannot vote on this suggestion.";
    } else if (err.response?.status === 401) {
      voteError.value = "Please sign in to vote.";
    } else {
      voteError.value = "Vote failed. Please try again.";
    }
  } finally {
    voting.value = false;
  }
}

// ── Reviewer decide (accept/reject) ───────────────────────────
async function decide(decision) {
  deciding.value = true;
  decideError.value = "";

  try {
    const result = await decideSuggestion(suggestion.value.id, decision);
    suggestion.value.status = result.status;
    suggestion.value.decided_at = result.decided_at;
    if (decision === "accept") {
      justPromoted.value = true;
      suggestion.value.applied_at = result.decided_at;
    }
  } catch (err) {
    decideError.value = err.response?.data?.detail || "Failed to process. Please try again.";
  } finally {
    deciding.value = false;
  }
}

watch(
  () => route.params.id,
  (newId) => {
    if (newId) {
      justPromoted.value = false;
      fetchSuggestion(newId);
    }
  },
  { immediate: true }
);
</script>

<style scoped>
.type-badge {
  display: inline-flex;
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  background: #e8dfc8;
  color: #2d5a3d;
}
.status-badge {
  display: inline-flex;
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.status-open {
  background: #f5efe3;
  color: #6b7280;
}
.status-accepted {
  background: #e8f0ea;
  color: #2d5a3d;
}
.status-rejected {
  background: #faeae5;
  color: #c75b39;
}
.vote-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  border: 1px solid #e8dfc8;
  background: #fdfbf6;
  color: #374151;
  cursor: pointer;
  transition: all 0.15s;
}
.vote-btn:hover:not(:disabled) {
  border-color: #2d5a3d;
  background: #f5efe3;
}
.vote-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.vote-btn.voted-up {
  background: #2d5a3d;
  border-color: #2d5a3d;
  color: #fbf7f0;
}
.vote-btn.voted-down {
  background: #c75b39;
  border-color: #c75b39;
  color: #fbf7f0;
}
</style>

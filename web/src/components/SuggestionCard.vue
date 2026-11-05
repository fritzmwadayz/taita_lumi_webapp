<template>
  <RouterLink
    :to="`/suggestions/${suggestion.id}`"
    class="block bg-white border border-cream-200 rounded-xl p-5 hover:border-forest transition"
  >
    <!-- Type badge + timestamp -->
    <div class="flex items-baseline justify-between mb-2">
      <p class="text-[10px] uppercase tracking-wider text-stone-light">
        {{ typeLabel }}
      </p>
      <span class="text-[10px] text-stone-light">{{ timeAgo(suggestion.created_at) }}</span>
    </div>

    <!-- New word: show headword + gloss -->
    <template v-if="suggestion.target_type === 'new_word'">
      <h3 class="font-serif text-2xl text-ink font-semibold mb-1">
        {{ suggestion.proposed_value.headword }}
      </h3>
      <p v-if="suggestion.proposed_value.swahili_gloss" class="text-sm text-ink-soft mb-1">
        <span class="font-medium">{{ suggestion.proposed_value.swahili_gloss }}</span>
        <span class="text-stone-light text-xs ml-1">(Kiswahili)</span>
      </p>
      <p v-if="suggestion.proposed_value.english_gloss" class="text-xs text-stone">
        {{ suggestion.proposed_value.english_gloss }}
      </p>
    </template>

    <!-- Word correction: show field change -->
    <template v-else-if="suggestion.target_type === 'word'">
      <h3 class="font-serif text-base text-ink mb-2">
        Update {{ suggestion.field_path }}
      </h3>
      <p class="text-sm text-ink-soft mb-1">
        <span class="font-medium text-forest">
          {{ formatValue(suggestion.proposed_value) }}
        </span>
      </p>
    </template>

    <!-- Rationale -->
    <p
      v-if="suggestion.rationale"
      class="text-xs text-stone mt-3 italic line-clamp-2"
    >
      "{{ suggestion.rationale }}"
    </p>

    <!-- Author -->
    <p class="text-xs text-stone-light italic mt-3 mb-3">
      Proposed by {{ suggestion.author_display || "anonymous" }}
    </p>

    <!-- Vote counts (clickable — needs auth) -->
    <div class="flex items-center gap-2 pt-3 border-t border-cream-200" @click.prevent="onVoteClick">
      <button
        @click.stop="vote('up')"
        :disabled="voting || !canVote"
        :class="['vote-pill', 'vote-up', suggestion.user_vote === 'up' && 'voted']"
        :title="canVote ? 'Vote up' : 'Sign in to vote'"
      >
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
          <path d="M5 10l5-5 5 5H5z" />
        </svg>
        {{ suggestion.upvotes }}
      </button>
      <button
        @click.stop="vote('down')"
        :disabled="voting || !canVote"
        :class="['vote-pill', 'vote-down', suggestion.user_vote === 'down' && 'voted']"
        :title="canVote ? 'Vote down' : 'Sign in to vote'"
      >
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
          <path d="M5 10l5 5 5-5H5z" />
        </svg>
        {{ suggestion.downvotes }}
      </button>
      <span
        v-if="suggestion.status === 'accepted'"
        class="ml-auto text-[10px] text-forest font-medium"
      >
        Accepted
      </span>
      <span
        v-else-if="suggestion.status === 'rejected'"
        class="ml-auto text-[10px] text-terracotta font-medium"
      >
        Rejected
      </span>
    </div>
  </RouterLink>
</template>

<script setup>
import { RouterLink, useRouter } from "vue-router";
import { computed, ref } from "vue";
import { useAuthStore } from "../stores/auth";
import { castVote } from "../api/suggestions";

const router = useRouter();
const authStore = useAuthStore();

const props = defineProps({
  suggestion: { type: Object, required: true },
});

const emit = defineEmits(["voted"]);

const voting = ref(false);

const canVote = computed(() => authStore.isAuthenticated);

const typeLabel = computed(() => {
  switch (props.suggestion.target_type) {
    case "new_word":
      return "New word";
    case "word":
      return `Correction · ${props.suggestion.field_path}`;
    case "gloss":
      return "Gloss update";
    case "example":
      return "New example";
    case "relation":
      return "New relation";
    default:
      return props.suggestion.target_type;
  }
});

function formatValue(proposed) {
  if (typeof proposed === "string") return proposed;
  if (proposed.value) return proposed.value;
  if (proposed.text) return proposed.text;
  return JSON.stringify(proposed);
}

function timeAgo(iso) {
  if (!iso) return "";
  const date = new Date(iso);
  const now = new Date();
  const seconds = Math.floor((now - date) / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  if (days < 30) return `${Math.floor(days / 7)}w ago`;
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function onVoteClick() {
  // Clicking the vote row shouldn't navigate to the detail page
  // — handled by @click.prevent on the container
}

async function vote(voteType) {
  if (!canVote.value) {
    // Redirect to login with return URL
    router.push({
      path: "/login",
      query: { next: `/suggestions/${props.suggestion.id}` },
    });
    return;
  }

  // Don't vote on closed suggestions
  if (props.suggestion.status !== "open") return;

  voting.value = true;
  try {
    const result = await castVote(props.suggestion.id, voteType);
    // Update local counts + user_vote
    emit("voted", {
      id: props.suggestion.id,
      upvotes: result.upvotes,
      downvotes: result.downvotes,
      user_vote: result.user_vote,
      promoted: result.promoted,
    });
  } catch (err) {
    // Silently fail on the card — the detail page shows errors better
    console.error("Vote failed:", err);
  } finally {
    voting.value = false;
  }
}
</script>

<style scoped>
.vote-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  border: 1px solid #e8dfc8;
  cursor: pointer;
  transition: all 0.15s;
}
.vote-pill:disabled {
  cursor: not-allowed;
  opacity: 0.7;
}
.vote-up {
  background: #f0f7f1;
  color: #2d5a3d;
  border-color: #c8d8c8;
}
.vote-up:hover:not(:disabled) {
  background: #d8ead9;
  border-color: #2d5a3d;
}
.vote-up.voted {
  background: #2d5a3d;
  color: #fbf7f0;
  border-color: #2d5a3d;
}
.vote-down {
  background: #faf0eb;
  color: #c75b39;
  border-color: #e8c8b8;
}
.vote-down:hover:not(:disabled) {
  background: #f5ddd3;
  border-color: #c75b39;
}
.vote-down.voted {
  background: #c75b39;
  color: #fbf7f0;
  border-color: #c75b39;
}
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>

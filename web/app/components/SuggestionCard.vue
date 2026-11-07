<template>
  <NuxtLink
    :to="`/suggestions/${suggestion.id}`"
    class="focus-ring block bg-white border border-cream-200 hover:border-forest/30 rounded-xl p-5 hover:shadow-card transition"
  >
    <!-- Type badge + timestamp -->
    <div class="flex items-baseline justify-between mb-2">
      <p class="text-[10px] uppercase tracking-wider text-stone-light font-semibold">
        {{ typeLabel }}
      </p>
      <span class="text-[10px] text-stone-light">{{ timeAgo(suggestion.created_at) }}</span>
    </div>

    <!-- New word: show headword + translation -->
    <template v-if="suggestion.target_type === 'new_word'">
      <h3 class="font-serif text-2xl text-ink font-semibold mb-1">
        {{ (suggestion.proposed_value as Record<string, unknown>).headword }}
      </h3>
      <p
        v-if="(suggestion.proposed_value as Record<string, unknown>).swahili_translation"
        class="text-sm text-ink-soft mb-1"
      >
        <span class="font-medium">{{ (suggestion.proposed_value as Record<string, unknown>).swahili_translation }}</span>
        <span class="text-stone-light text-xs ml-1">(Kiswahili)</span>
      </p>
      <p
        v-if="(suggestion.proposed_value as Record<string, unknown>).english_translation"
        class="text-xs text-stone"
      >
        {{ (suggestion.proposed_value as Record<string, unknown>).english_translation }}
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
      Proposed by {{ suggestion.author_display || 'anonymous' }}
    </p>

    <!-- Vote counts (clickable — needs auth) -->
    <div
      class="flex items-center gap-2 pt-3 border-t border-cream-200"
      @click.prevent
    >
      <button
        class="focus-ring vote-pill vote-up"
        :class="{ voted: suggestion.user_vote === 'up' }"
        :disabled="voting || !canVote"
        :title="canVote ? 'Vote up' : 'Sign in to vote'"
        @click.prevent="vote('up')"
      >
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 12 12">
          <path d="M2 4 L6 0 L10 4 Z" />
        </svg>
        {{ suggestion.upvotes }}
      </button>
      <button
        class="focus-ring-terra vote-pill vote-down"
        :class="{ voted: suggestion.user_vote === 'down' }"
        :disabled="voting || !canVote"
        :title="canVote ? 'Vote down' : 'Sign in to vote'"
        @click.prevent="vote('down')"
      >
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 12 12">
          <path d="M2 8 L6 12 L10 8 Z" />
        </svg>
        {{ suggestion.downvotes }}
      </button>
      <span
        v-if="suggestion.status === 'accepted'"
        class="ml-auto status-badge status-accepted"
      >
        Accepted
      </span>
      <span
        v-else-if="suggestion.status === 'rejected'"
        class="ml-auto status-badge status-rejected"
      >
        Rejected
      </span>
    </div>
  </NuxtLink>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { SuggestionListItem } from '~/types'

const props = defineProps<{ suggestion: SuggestionListItem }>()
const emit = defineEmits<{
  voted: [payload: {
    id: string
    upvotes: number
    downvotes: number
    user_vote: 'up' | 'down' | null
    promoted: boolean
  }]
}>()

const router = useRouter()
const { isAuthenticated } = useAuth()
const voting = ref(false)

const canVote = computed(() => isAuthenticated.value)

const typeLabel = computed(() => {
  switch (props.suggestion.target_type) {
    case 'new_word': return 'New word'
    case 'word': return `Correction · ${props.suggestion.field_path}`
    case 'translation': return 'Translation update'
    case 'example': return 'New example'
    case 'relation': return 'New relation'
    default: return props.suggestion.target_type
  }
})

function formatValue(proposed: unknown): string {
  if (typeof proposed === 'string') return proposed
  if (typeof proposed === 'object' && proposed !== null) {
    const obj = proposed as Record<string, unknown>
    if (obj.value) return String(obj.value)
    if (obj.text) return String(obj.text)
  }
  return JSON.stringify(proposed)
}

function timeAgo(iso: string): string {
  if (!iso) return ''
  const date = new Date(iso)
  const now = new Date()
  const seconds = Math.floor((now.getTime() - date.getTime()) / 1000)
  if (seconds < 60) return 'just now'
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  if (days < 7) return `${days}d ago`
  if (days < 30) return `${Math.floor(days / 7)}w ago`
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

async function vote(voteType: 'up' | 'down') {
  if (!canVote.value) {
    router.push({
      path: '/login',
      query: { next: `/suggestions/${props.suggestion.id}` },
    })
    return
  }

  if (props.suggestion.status !== 'open') return

  voting.value = true
  try {
    const result = await castVote(props.suggestion.id, voteType)
    emit('voted', {
      id: props.suggestion.id,
      upvotes: result.upvotes,
      downvotes: result.downvotes,
      user_vote: result.user_vote,
      promoted: result.promoted,
    })
  } catch (err) {
    console.error('Vote failed:', err)
  } finally {
    voting.value = false
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
</style>

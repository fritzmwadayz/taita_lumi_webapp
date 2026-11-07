<template>
  <div>
    <div class="px-8 py-4">
      <NuxtLink to="/contribute" class="focus-ring inline-flex items-center gap-1.5 text-sm text-stone hover:text-forest rounded">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
        </svg>
        Back to suggestions
      </NuxtLink>
    </div>

    <div v-if="pending" class="max-w-[680px] mx-auto px-8 py-24 text-center">
      <div class="animate-pulse">
        <div class="h-8 bg-cream-200 rounded w-1/3 mx-auto mb-4"></div>
        <div class="h-4 bg-cream-100 rounded w-1/2 mx-auto"></div>
      </div>
    </div>

    <div v-else-if="error || !suggestion" class="max-w-[680px] mx-auto px-8 py-24 text-center">
      <p class="font-serif text-3xl text-forest-dark mb-4">Suggestion not found</p>
      <p class="text-sm text-stone mb-8">
        {{ error?.statusCode === 404 ? "This suggestion doesn't exist or has been removed." : 'Failed to load suggestion.' }}
      </p>
      <NuxtLink to="/contribute" class="focus-ring btn btn-primary btn-md">Back to suggestions</NuxtLink>
    </div>

    <article v-else class="max-w-[680px] mx-auto px-8">
      <header class="pt-8 pb-8 border-b border-cream-200">
        <div class="flex items-center gap-3 mb-4">
          <span class="status-badge status-open" :class="statusBadgeClass">{{ suggestion.status }}</span>
        </div>

        <h1 v-if="suggestion.target_type === 'new_word'" class="font-serif text-3xl md:text-5xl text-forest-dark font-semibold mb-4">
          {{ (suggestion.proposed_value as Record<string, unknown>).headword }}
        </h1>
        <h1 v-else class="font-serif text-3xl text-forest-dark mb-4">Update: {{ suggestion.field_path }}</h1>

        <p class="text-sm text-stone">
          Proposed by <span class="font-medium text-ink">{{ suggestion.author_display || 'anonymous' }}</span>
          · {{ formatDate(suggestion.created_at) }}
        </p>
      </header>

      <!-- Proposed value for new_word -->
      <section v-if="suggestion.target_type === 'new_word'" class="py-8 border-b border-cream-200">
        <h2 class="text-xs font-semibold uppercase tracking-widest text-stone mb-6">Proposed translations</h2>
        <div class="space-y-6">
          <div v-if="(suggestion.proposed_value as Record<string, unknown>).swahili_translation" class="flex gap-6">
            <span class="text-xs font-bold text-forest w-12 mt-1">SW</span>
            <p class="font-serif text-xl text-ink font-medium">{{ (suggestion.proposed_value as Record<string, unknown>).swahili_translation }}</p>
          </div>
          <div v-if="(suggestion.proposed_value as Record<string, unknown>).english_translation" class="flex gap-6">
            <span class="text-xs font-bold text-terracotta w-12 mt-1">EN</span>
            <p class="font-serif text-lg text-ink-soft font-medium">{{ (suggestion.proposed_value as Record<string, unknown>).english_translation }}</p>
          </div>
        </div>
        <div class="mt-8 grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div v-if="(suggestion.proposed_value as Record<string, unknown>).part_of_speech"><p class="text-[10px] uppercase tracking-wider text-stone-light mb-1">Part of speech</p><p class="text-ink">{{ (suggestion.proposed_value as Record<string, unknown>).part_of_speech }}</p></div>
          <div v-if="(suggestion.proposed_value as Record<string, unknown>).dialect"><p class="text-[10px] uppercase tracking-wider text-stone-light mb-1">Dialect</p><p class="text-ink">{{ (suggestion.proposed_value as Record<string, unknown>).dialect }}</p></div>
        </div>
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

        <!-- Reviewer decide -->
        <div v-if="isReviewer && suggestion.status === 'open'" class="bg-forest/5 border border-forest/20 rounded-lg p-4 mb-4">
          <p class="text-xs font-semibold text-forest-dark mb-3">Reviewer actions</p>
          <div class="flex gap-2">
            <button :disabled="deciding" class="focus-ring btn btn-primary btn-sm" @click="decide('accept')">{{ deciding ? 'Processing...' : 'Accept & apply' }}</button>
            <button :disabled="deciding" class="focus-ring btn btn-danger btn-sm" @click="decide('reject')">Reject</button>
          </div>
          <div v-if="decideError" class="text-xs text-terracotta mt-2">{{ decideError }}</div>
        </div>

        <!-- Promotion banner -->
        <div v-if="justPromoted" class="bg-forest text-cream rounded-lg p-4 mb-4 flex items-center gap-3">
          <svg class="w-6 h-6 text-ochre-light flex-shrink-0" fill="currentColor" viewBox="0 0 20 20"><path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.539 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" /></svg>
          <div><p class="font-semibold text-sm">Suggestion accepted!</p><p class="text-xs text-cream/80">This suggestion met the community threshold and has been added to the dictionary.</p></div>
        </div>

        <!-- Vote buttons -->
        <div class="flex items-center gap-3">
          <button :disabled="voting || !canVote" :class="['focus-ring vote-btn', suggestion.user_vote === 'up' && 'voted-up']" @click="vote('up')">
            <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 12 12"><path d="M2 4 L6 0 L10 4 Z" /></svg>
            <span>{{ suggestion.upvotes }}</span><span class="text-xs ml-1 opacity-75">up</span>
          </button>
          <button :disabled="voting || !canVote" :class="['focus-ring-terra vote-btn', suggestion.user_vote === 'down' && 'voted-down']" @click="vote('down')">
            <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 12 12"><path d="M2 8 L6 12 L10 8 Z" /></svg>
            <span>{{ suggestion.downvotes }}</span><span class="text-xs ml-1 opacity-75">down</span>
          </button>
          <div class="ml-auto text-right">
            <p v-if="voteError" class="text-xs text-terracotta">{{ voteError }}</p>
            <p v-else-if="!isAuthenticated" class="text-xs text-stone-light"><NuxtLink :to="{ path: '/login', query: { next: route.fullPath } }" class="text-forest hover:underline font-medium">Sign in</NuxtLink> to vote</p>
            <p v-else-if="suggestion.status !== 'open'" class="text-xs text-stone-light italic">Voting closed</p>
            <p v-else-if="suggestion.user_vote === 'up'" class="text-xs text-forest">You voted up · click again to remove</p>
            <p v-else-if="suggestion.user_vote === 'down'" class="text-xs text-terracotta">You voted down · click again to remove</p>
            <p v-else class="text-xs text-stone-light">Click to vote</p>
          </div>
        </div>
        <p class="text-xs text-stone-light mt-4">Net score: <span class="font-semibold text-ink">{{ suggestion.upvotes - suggestion.downvotes }}</span><span v-if="suggestion.status === 'open'"> · Needs 3 net upvotes + 7 days age to auto-promote</span></p>
      </section>

      <footer class="py-8">
        <div class="flex flex-wrap items-center gap-x-4 gap-y-1 text-[10px] text-stone-light">
          <span>Suggestion ID: {{ suggestion.id.slice(0, 8) }}...</span><span>·</span>
          <span>Status: {{ suggestion.status }}</span>
          <template v-if="suggestion.decided_at"><span>·</span><span>Decided {{ formatDate(suggestion.decided_at) }}</span></template>
        </div>
      </footer>
    </article>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { SuggestionListItem } from '~/types'

const route = useRoute()
const router = useRouter()
const { isAuthenticated, isReviewer, user } = useAuth()

const { data: suggestion, pending, error, refresh } = await useFetch<SuggestionListItem>(
  () => `/api/suggestions/${route.params.id}`,
  { watch: [() => route.params.id] },
)

const voting = ref(false)
const voteError = ref('')
const justPromoted = ref(false)
const deciding = ref(false)
const decideError = ref('')

const canVote = computed(() => {
  if (!suggestion.value || !isAuthenticated.value) return false
  if (suggestion.value.created_by_user_id && user.value?.id === suggestion.value.created_by_user_id) return false
  return suggestion.value.status === 'open'
})

const statusBadgeClass = computed(() => {
  switch (suggestion.value?.status) {
    case 'accepted': return 'status-accepted'
    case 'rejected': return 'status-rejected'
    default: return 'status-open'
  }
})

async function vote(voteType: 'up' | 'down') {
  if (!isAuthenticated.value) {
    router.push({ path: '/login', query: { next: `/suggestions/${suggestion.value!.id}` } })
    return
  }
  voting.value = true; voteError.value = ''; justPromoted.value = false
  try {
    const result = await castVote(suggestion.value!.id, voteType)
    suggestion.value!.upvotes = result.upvotes
    suggestion.value!.downvotes = result.downvotes
    suggestion.value!.user_vote = result.user_vote
    if (result.promoted) {
      justPromoted.value = true
      suggestion.value!.status = 'accepted'
    }
  } catch (err: unknown) {
    const e = err as { response?: { status?: number; _data?: { detail?: string } } }
    if (e.response?.status === 400) voteError.value = e.response?._data?.detail || 'Cannot vote on this suggestion.'
    else if (e.response?.status === 401) voteError.value = 'Please sign in to vote.'
    else voteError.value = 'Vote failed. Please try again.'
  } finally { voting.value = false }
}

async function decide(decision: 'accept' | 'reject') {
  deciding.value = true; decideError.value = ''
  try {
    const result = await decideSuggestion(suggestion.value!.id, decision)
    suggestion.value!.status = result.status
    if (decision === 'accept') justPromoted.value = true
  } catch (err: unknown) {
    const e = err as { response?: { _data?: { detail?: string } } }
    decideError.value = e.response?._data?.detail || 'Failed to process.'
  } finally { deciding.value = false }
}

function formatDate(iso: string): string {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}
</script>

<style scoped>
.vote-btn {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 8px 16px; border-radius: 8px; font-size: 14px;
  font-weight: 500; border: 1px solid #e8dfc8;
  background: #fdfbf6; color: #374151; cursor: pointer; transition: all 0.15s;
}
.vote-btn:hover:not(:disabled) { border-color: #2d5a3d; background: #f5efe3; }
.vote-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.vote-btn.voted-up { background: #2d5a3d; border-color: #2d5a3d; color: #fbf7f0; }
.vote-btn.voted-down { background: #c75b39; border-color: #c75b39; color: #fbf7f0; }
</style>

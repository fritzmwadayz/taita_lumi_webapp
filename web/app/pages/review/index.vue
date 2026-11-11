<template>
  <div>
    <!-- Header -->
    <header class="px-4 md:px-8 py-6 md:py-8 border-b border-cream-200 bg-cream-50 tri-pattern-ochre">
      <div class="flex items-start justify-between flex-wrap gap-4">
        <div>
          <p class="text-xs font-semibold tracking-widest uppercase text-ochre-dark mb-2">Review queue</p>
          <h1 class="font-serif text-3xl md:text-4xl text-forest-dark mb-1">
            Welcome back, {{ displayName }}.
          </h1>
          <p class="text-sm text-stone">
            {{ openCount }} suggestions awaiting review
          </p>
        </div>
        <!-- Reviewer stats -->
        <div class="flex gap-6 text-right">
          <div>
            <p class="font-serif text-2xl text-forest-dark font-semibold">{{ openCount }}</p>
            <p class="text-[10px] uppercase tracking-wider text-stone-light">Open now</p>
          </div>
          <div>
            <p class="font-serif text-2xl text-forest font-semibold">{{ acceptedCount }}</p>
            <p class="text-[10px] uppercase tracking-wider text-stone-light">Accepted</p>
          </div>
        </div>
      </div>
    </header>

    <!-- Tabs (underline style) -->
    <div class="px-4 md:px-8 pt-4 border-b border-cream-200 bg-cream-50">
      <div class="flex items-center gap-1 overflow-x-auto">
        <button :class="['tab-underline whitespace-nowrap', activeTab === 'queue' && 'tab-underline-active']" @click="activeTab = 'queue'">
          Open queue
          <span v-if="openCount > 0" class="ml-1.5 inline-flex items-center justify-center text-[10px] font-bold text-cream bg-terracotta rounded-full px-1.5 min-w-[18px] h-[16px]">{{ openCount }}</span>
        </button>
        <button :class="['tab-underline whitespace-nowrap', activeTab === 'corrections' && 'tab-underline-active']" @click="activeTab = 'corrections'">
          Pending corrections
          <span v-if="correctionsCount > 0" class="ml-1.5 text-[10px] text-stone-light">{{ correctionsCount }}</span>
        </button>
        <button :class="['tab-underline whitespace-nowrap', activeTab === 'triage' && 'tab-underline-active']" @click="activeTab = 'triage'">
          New word triage
          <span v-if="triageCount > 0" class="ml-1.5 inline-flex items-center justify-center text-[10px] font-bold text-terracotta bg-terracotta-wash rounded-full px-1.5 min-w-[18px] h-[16px]">{{ triageCount }}</span>
        </button>
        <button :class="['tab-underline whitespace-nowrap', activeTab === 'add' && 'tab-underline-active']" @click="activeTab = 'add'">
          Quick add word
        </button>
      </div>
    </div>

    <!-- ═══ OPEN QUEUE ═══ -->
    <div v-show="activeTab === 'queue'" class="px-4 md:px-8 py-6 bg-white">
      <!-- Filter bar -->
      <div class="flex flex-wrap items-center justify-between gap-3 mb-5">
        <div class="flex items-center gap-2 flex-wrap">
          <span class="text-[10px] uppercase tracking-widest text-stone-light font-semibold mr-1">Type:</span>
          <button
            v-for="f in typeFilters"
            :key="f.value"
            class="focus-ring inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium transition"
            :class="activeTypeFilter === f.value ? 'bg-forest text-cream' : 'text-stone-dark bg-cream-100 hover:bg-cream-200'"
            @click="activeTypeFilter = f.value"
          >
            {{ f.label }}
            <span v-if="f.count !== null" class="text-[10px] opacity-75">{{ f.count }}</span>
          </button>
        </div>
        <div class="flex items-center gap-2 text-xs">
          <span class="text-stone-light">Sort:</span>
          <select v-model="sortBy" class="focus-ring px-2 py-1 rounded-md border border-cream-200 bg-cream-50 text-xs text-ink">
            <option value="oldest">Oldest first</option>
            <option value="newest">Newest first</option>
            <option value="upvoted">Most upvoted</option>
          </select>
        </div>
      </div>

      <!-- Loading -->
      <div v-if="queuePending" class="space-y-3">
        <div v-for="i in 4" :key="i" class="bg-cream-50 border border-cream-200 rounded-xl p-4 animate-pulse">
          <div class="h-3 bg-cream-200 rounded w-1/4 mb-2"></div>
          <div class="h-6 bg-cream-200 rounded w-1/2 mb-3"></div>
          <div class="h-4 bg-cream-100 rounded w-2/3"></div>
        </div>
      </div>

      <!-- Error -->
      <div v-else-if="queueError" class="bg-cream-100 border border-cream-200 rounded-xl p-6 text-sm text-stone">
        <p class="font-medium text-terracotta mb-1">Couldn't load suggestions</p>
        <p class="text-xs text-stone-light">{{ queueError.message }}</p>
      </div>

      <!-- Empty -->
      <div v-else-if="filteredQueue.length === 0" class="bg-cream-100 border border-cream-200 rounded-xl p-12 text-center">
        <p class="font-serif text-lg text-forest-dark mb-2">No suggestions to review</p>
        <p class="text-sm text-stone">The queue is clear. Nice work!</p>
      </div>

      <!-- Suggestion cards with inline accept/reject -->
      <div v-else class="space-y-3">
        <article
          v-for="s in filteredQueue"
          :key="s.id"
          class="bg-cream-50 border border-cream-200 rounded-xl p-4 md:p-5 hover:border-forest/30 hover:shadow-card transition"
        >
          <div class="flex items-start justify-between gap-4 flex-wrap">
            <!-- Left: suggestion details -->
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 mb-1.5">
                <span class="text-[10px] uppercase tracking-wider text-stone-light font-semibold">{{ typeLabel(s) }}</span>
                <span class="text-[10px] text-stone-light">·</span>
                <span class="text-[10px] text-stone-light">{{ timeAgo(s.created_at) }}</span>
                <!-- Near-threshold badge -->
                <span
                  v-if="s.upvotes - s.downvotes >= 2 && s.status === 'open'"
                  class="ml-1 inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[10px] font-semibold bg-ochre-tint text-ochre-dark"
                >
                  <span class="w-1 h-1 rounded-full bg-ochre"></span>near threshold
                </span>
              </div>

              <!-- New word suggestion -->
              <template v-if="s.target_type === 'new_word'">
                <div class="flex items-baseline gap-2 mb-1">
                  <h4 class="font-serif text-2xl text-ink font-semibold">{{ (s.proposed_value as Record<string, unknown>).headword }}</h4>
                  <PosBadge v-if="(s.proposed_value as Record<string, unknown>).part_of_speech" :pos="(s.proposed_value as Record<string, unknown>).part_of_speech as string" />
                  <span v-if="(s.proposed_value as Record<string, unknown>).dialect" class="text-[10px] text-stone-light">{{ (s.proposed_value as Record<string, unknown>).dialect }}</span>
                </div>
                <p v-if="(s.proposed_value as Record<string, unknown>).swahili_translation" class="text-sm text-ink-soft mb-1">
                  <span class="font-medium">{{ (s.proposed_value as Record<string, unknown>).swahili_translation }}</span>
                  <span class="text-stone-light text-xs ml-1">(Kiswahili)</span>
                </p>
                <p v-if="(s.proposed_value as Record<string, unknown>).english_translation" class="text-xs text-stone">
                  {{ (s.proposed_value as Record<string, unknown>).english_translation }}
                </p>
              </template>

              <!-- Translation update -->
              <template v-else-if="s.target_type === 'translation'">
                <p class="text-sm text-ink mb-1">
                  Update translation for
                  <NuxtLink :to="`/words/${s.target_id}`" class="text-forest hover:underline font-medium">{{ s.field_path || 'word' }}</NuxtLink>
                </p>
                <p class="font-serif text-lg text-forest font-medium">{{ formatValue(s.proposed_value) }}</p>
              </template>

              <!-- Relation -->
              <template v-else-if="s.target_type === 'relation'">
                <p class="text-sm text-ink mb-1">
                  Suggested relation for
                  <NuxtLink :to="`/words/${s.target_id}`" class="text-forest hover:underline font-medium">word</NuxtLink>
                </p>
                <p class="text-sm text-ink-soft">{{ formatValue(s.proposed_value) }}</p>
              </template>

              <!-- Word correction -->
              <template v-else-if="s.target_type === 'word'">
                <p class="text-sm text-ink mb-1">Update {{ s.field_path }}</p>
                <p class="font-serif text-base text-forest font-medium">{{ formatValue(s.proposed_value) }}</p>
              </template>

              <!-- Rationale -->
              <p v-if="s.rationale" class="text-xs text-stone mt-2 italic line-clamp-2">"{{ s.rationale }}"</p>

              <!-- Vote counts -->
              <div class="flex items-center gap-1.5 mt-2 text-xs">
                <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-forest-wash text-forest border border-forest/20">
                  <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 12 12"><path d="M2 4 L6 0 L10 4 Z" /></svg>{{ s.upvotes }}
                </span>
                <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-terracotta-wash text-terracotta border border-terracotta/20">
                  <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 12 12"><path d="M2 8 L6 12 L10 8 Z" /></svg>{{ s.downvotes }}
                </span>
                <span class="text-[10px] text-stone-light ml-1">net: {{ s.upvotes - s.downvotes }}</span>
              </div>
            </div>

            <!-- Right: actions -->
            <div class="flex items-center gap-2 flex-shrink-0">
              <NuxtLink :to="`/suggestions/${s.id}`" class="focus-ring text-xs font-medium text-forest hover:underline">View detail →</NuxtLink>
              <button
                :disabled="decidingId === s.id"
                class="focus-ring-terra btn btn-danger btn-sm"
                @click="decide(s.id, 'reject')"
              >
                {{ decidingId === s.id ? '...' : 'Reject' }}
              </button>
              <button
                :disabled="decidingId === s.id"
                class="focus-ring btn btn-primary btn-sm"
                @click="decide(s.id, 'accept')"
              >
                <svg v-if="decidingId !== s.id" class="w-3 h-3" fill="currentColor" viewBox="0 0 12 12"><path d="M2 6 L5 9 L10 3" /></svg>
                {{ decidingId === s.id ? '...' : 'Accept' }}
              </button>
            </div>
          </div>
        </article>
      </div>

      <!-- Load more -->
      <div v-if="queueHasMore" class="mt-6 text-center">
        <button :disabled="loadingMore" class="focus-ring btn btn-secondary btn-md" @click="loadMoreQueue">
          {{ loadingMore ? 'Loading...' : 'Load more' }}
        </button>
      </div>
    </div>

    <!-- ═══ PENDING CORRECTIONS ═══ -->
    <div v-show="activeTab === 'corrections'" class="px-4 md:px-8 py-6 bg-white">
      <p class="text-xs text-stone mb-4">
        Suggestions targeting existing words (corrections, translation updates, relations). These need reviewer attention.
      </p>
      <div v-if="queuePending" class="space-y-2">
        <div v-for="i in 3" :key="i" class="bg-cream-50 border border-cream-200 rounded-xl p-4 animate-pulse">
          <div class="h-4 bg-cream-200 rounded w-3/4 mb-2"></div>
          <div class="h-3 bg-cream-100 rounded w-1/2"></div>
        </div>
      </div>
      <div v-else-if="corrections.length === 0" class="bg-cream-100 border border-cream-200 rounded-xl p-8 text-center">
        <p class="text-sm text-stone">No pending corrections. All clear!</p>
      </div>
      <div v-else class="space-y-3">
        <article
          v-for="s in corrections"
          :key="s.id"
          class="bg-cream-50 border border-cream-200 rounded-xl p-4 flex items-center justify-between gap-4"
        >
          <div class="flex-1 min-w-0">
            <p class="text-sm font-medium text-ink">{{ typeLabel(s) }}</p>
            <p class="text-xs text-stone mt-0.5">{{ formatValue(s.proposed_value) }}</p>
            <p class="text-[10px] text-stone-light mt-1">{{ timeAgo(s.created_at) }} · net: {{ s.upvotes - s.downvotes }}</p>
          </div>
          <div class="flex items-center gap-2 flex-shrink-0">
            <NuxtLink v-if="s.target_id" :to="`/words/${s.target_id}`" class="focus-ring text-xs text-forest hover:underline">View word →</NuxtLink>
            <button :disabled="decidingId === s.id" class="focus-ring btn btn-primary btn-sm" @click="decide(s.id, 'accept')">Accept</button>
            <button :disabled="decidingId === s.id" class="focus-ring-terra btn btn-danger btn-sm" @click="decide(s.id, 'reject')">Reject</button>
          </div>
        </article>
      </div>
    </div>

    <!-- ═══ NEW WORD TRIAGE ═══ -->
    <div v-show="activeTab === 'triage'" class="px-4 md:px-8 py-6 bg-white">
      <p class="text-xs text-stone mb-4">
        Recently added words that might need verification — missing relations, missing translations, or status flags.
      </p>
      <div v-if="triagePending" class="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div v-for="i in 4" :key="i" class="bg-cream-50 border border-cream-200 rounded-xl p-4 animate-pulse">
          <div class="h-5 bg-cream-200 rounded w-1/3 mb-2"></div>
          <div class="h-3 bg-cream-100 rounded w-2/3"></div>
        </div>
      </div>
      <div v-else-if="triageWords.length === 0" class="bg-cream-100 border border-cream-200 rounded-xl p-8 text-center">
        <p class="text-sm text-stone">No words need triage right now.</p>
      </div>
      <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-3">
        <NuxtLink
          v-for="w in triageWords"
          :key="w.id"
          :to="`/words/${w.slug}`"
          class="focus-ring bg-cream-50 border border-cream-200 rounded-xl p-4 hover:border-forest/30 transition"
        >
          <div class="flex items-baseline justify-between mb-1">
            <span class="font-serif text-lg text-ink font-semibold">{{ w.headword }}</span>
            <PosBadge v-if="w.part_of_speech" :pos="w.part_of_speech" />
          </div>
          <p v-if="w.swahili_translation" class="text-xs text-stone">{{ w.swahili_translation }}</p>
          <!-- Triage flags -->
          <div class="flex flex-wrap gap-1.5 mt-2">
            <span v-if="!w.has_relations" class="text-[10px] text-ochre-dark bg-ochre-tint px-1.5 py-0.5 rounded font-medium">no relations</span>
            <span v-if="!w.swahili_translation && !w.english_translation" class="text-[10px] text-terracotta-dark bg-terracotta-tint px-1.5 py-0.5 rounded font-medium">no translations</span>
            <span v-if="!w.part_of_speech" class="text-[10px] text-stone-dark bg-cream-200 px-1.5 py-0.5 rounded font-medium">no POS</span>
          </div>
        </NuxtLink>
      </div>
    </div>

    <!-- ═══ QUICK ADD WORD ═══ -->
    <div v-show="activeTab === 'add'" class="px-4 md:px-8 py-6 bg-white">
      <p class="text-xs text-stone mb-4">
        As a reviewer, words you add go <strong>live immediately</strong>. Use the toggle to suggest instead (enters the review queue).
      </p>

      <!-- Mode toggle -->
      <div class="flex bg-cream-100 rounded-lg p-1 max-w-md mb-6">
        <button
          class="flex-1 px-3 py-2 rounded-md text-sm font-medium transition"
          :class="addMode === 'direct' ? 'bg-ink text-cream' : 'text-stone hover:text-ink'"
          @click="addMode = 'direct'"
        >Add directly (live)</button>
        <button
          class="flex-1 px-3 py-2 rounded-md text-sm font-medium transition"
          :class="addMode === 'suggest' ? 'bg-ink text-cream' : 'text-stone hover:text-ink'"
          @click="addMode = 'suggest'"
        >Suggest (queue)</button>
      </div>

      <!-- Form -->
      <form class="max-w-3xl" @submit.prevent="onQuickAdd">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-4">
          <div>
            <label class="field-label">Word <span class="text-terracotta">*</span></label>
            <input v-model="addForm.headword" type="text" class="field" placeholder="e.g. mlima" :disabled="addSubmitting" />
          </div>
          <div>
            <label class="field-label">Dialect</label>
            <select v-model="addForm.dialect" class="field" :disabled="addSubmitting">
              <option value="">— Any / Unknown —</option>
              <option>Dawida</option><option>Sagala</option><option>Kasighau</option>
            </select>
          </div>
          <div>
            <label class="field-label">Part of speech</label>
            <select v-model="addForm.part_of_speech" class="field" :disabled="addSubmitting">
              <option value="">— Skip —</option>
              <option>noun</option><option>verb</option><option>adjective</option><option>adverb</option><option>phrase</option>
            </select>
          </div>
          <div>
            <label class="field-label">Noun class</label>
            <select v-model="addForm.noun_class" class="field" :disabled="addSubmitting">
              <option value="">—</option>
              <option>1/2 — person/people</option><option>3/4 — tree/things</option>
              <option>5/6 — fruit/collective</option><option>7/8 — object/objects</option>
              <option>9/10 — animal/animals</option><option>11 — long things</option>
              <option>14 — abstraction</option><option>15 — infinitive</option>
            </select>
          </div>
          <div>
            <label class="field-label">Swahili translation</label>
            <input v-model="addForm.swahili_translation" type="text" class="field" placeholder="mf. mlima, kilima — enter * if unsure" :disabled="addSubmitting" />
          </div>
          <div>
            <label class="field-label">English translation</label>
            <input v-model="addForm.english_translation" type="text" class="field" placeholder="e.g. mountain, hill" :disabled="addSubmitting" />
          </div>
          <div class="md:col-span-2">
            <label class="field-label">Literal translation</label>
            <input v-model="addForm.literal_translation" type="text" class="field" :disabled="addSubmitting" />
          </div>
          <div v-if="addMode === 'suggest'" class="md:col-span-2">
            <label class="field-label">Notes for reviewers</label>
            <textarea v-model="addRationale" rows="2" class="field" :disabled="addSubmitting"></textarea>
          </div>
        </div>

        <!-- Examples section -->
        <div class="mt-6 border-t border-cream-200 pt-6">
          <ExampleEditor v-model="addExamples" :disabled="addSubmitting" :max="5" />
        </div>

        <div v-if="addError" class="mt-4 bg-terracotta/10 border border-terracotta/30 rounded-lg p-3 text-sm text-terracotta-dark">{{ addError }}</div>
        <div v-if="addSuccess" class="mt-4 bg-forest/10 border border-forest/30 rounded-lg p-3 text-sm text-forest-dark">
          <p class="font-semibold mb-1">{{ addMode === 'direct' ? 'Word added!' : 'Suggestion submitted!' }}</p>
          <p class="text-xs">
            <template v-if="addMode === 'direct'">The word is now live in the dictionary.</template>
            <template v-else>Your suggestion is now in the review queue.</template>
          </p>
        </div>

        <div class="mt-6">
          <button type="submit" :disabled="addSubmitting" class="focus-ring btn btn-primary btn-lg">
            {{ addSubmitting ? 'Submitting...' : addMode === 'direct' ? 'Add word to dictionary' : 'Submit suggestion' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import type { SuggestionListItem, WordListItem } from '~/types'
import type { ExampleInput } from '~/utils/words'

definePageMeta({
  ssr: false,
  middleware: 'reviewer',
})

// ── SEO ───────────────────────────────────────────────────────────────────
useSiteSeo({ noindex: true })

const { displayName } = useAuth()

// ═══ OPEN QUEUE ═══
const activeTab = ref('queue')
const activeTypeFilter = ref<string | null>(null)
const sortBy = ref<'oldest' | 'newest' | 'upvoted'>('oldest')
const queuePage = ref(1)
const queuePageSize = 20
const loadingMore = ref(false)
const allQueueItems = ref<SuggestionListItem[]>([])
const decidingId = ref<string | null>(null)

const { data: queueData, pending: queuePending, error: queueError, refresh: refreshQueue } = await useFetch('/api/suggestions', {
  params: computed(() => ({
    status: 'open',
    page: queuePage.value,
    size: queuePageSize,
    ...(activeTypeFilter.value ? { target_type: activeTypeFilter.value } : {}),
  })),
})

const queueItems = computed<SuggestionListItem[]>(() => {
  const items = queueData.value?.items || []
  return queuePage.value === 1 ? items : [...allQueueItems.value, ...items]
})

const openCount = computed(() => queueData.value?.total || 0)
const queueHasMore = computed(() => queueData.value?.has_next || false)

// Type filter chips with counts
const typeFilters = computed(() => {
  const items = queueData.value?.items || []
  const counts: Record<string, number> = {}
  for (const s of items) {
    counts[s.target_type] = (counts[s.target_type] || 0) + 1
  }
  return [
    { value: null, label: 'All', count: openCount.value || null },
    { value: 'new_word', label: 'New word', count: counts['new_word'] || null },
    { value: 'translation', label: 'Translation', count: counts['translation'] || null },
    { value: 'relation', label: 'Relation', count: counts['relation'] || null },
    { value: 'word', label: 'Correction', count: counts['word'] || null },
  ]
})

// Filter + sort the queue
const filteredQueue = computed(() => {
  let items = [...queueItems.value]
  // Type filter (client-side, for types not supported by the API filter)
  if (activeTypeFilter.value) {
    items = items.filter(s => s.target_type === activeTypeFilter.value)
  }
  // Sort
  if (sortBy.value === 'newest') {
    items.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
  } else if (sortBy.value === 'upvoted') {
    items.sort((a, b) => b.upvotes - a.upvotes)
  } else {
    // Oldest first (default)
    items.sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime())
  }
  return items
})

async function loadMoreQueue() {
  loadingMore.value = true
  allQueueItems.value = queueItems.value
  queuePage.value++
  await refreshQueue()
  loadingMore.value = false
}

// ═══ PENDING CORRECTIONS ═══
const corrections = computed(() =>
  queueItems.value.filter(s => s.target_type !== 'new_word' && s.status === 'open'),
)
const correctionsCount = computed(() => corrections.value.length)

// ═══ ACCEPTED COUNT (for header stat) ═══
const { data: acceptedData } = await useFetch('/api/suggestions', {
  params: { status: 'accepted', size: 1 },
})
const acceptedCount = computed(() => acceptedData.value?.total || 0)

// ═══ NEW WORD TRIAGE ═══
const { data: triageData, pending: triagePending } = await useFetch('/api/words', {
  params: { size: 20 },
})

const triageWords = computed<WordListItem[]>(() => {
  const items = triageData.value?.items || []
  // Words that might need attention: no relations, no translations, or no POS
  return items.filter(w =>
    !w.has_relations ||
    (!w.swahili_translation && !w.english_translation) ||
    !w.part_of_speech,
  )
})
const triageCount = computed(() => triageWords.value.length)

// ═══ DECIDE (accept/reject) ═══
async function decide(id: string, decision: 'accept' | 'reject') {
  decidingId.value = id
  try {
    await decideSuggestion(id, decision)
    // Refresh the queue to remove the decided suggestion
    await refreshQueue()
  } catch (err) {
    console.error('Decide failed:', err)
  } finally {
    decidingId.value = null
  }
}

// ═══ QUICK ADD WORD ═══
const addMode = ref<'direct' | 'suggest'>('direct')
const addForm = reactive({
  headword: '', dialect: '', part_of_speech: '', noun_class: '',
  swahili_translation: '', english_translation: '', literal_translation: '',
})
const addRationale = ref('')
const addExamples = ref<ExampleInput[]>([])
const addSubmitting = ref(false)
const addError = ref('')
const addSuccess = ref(false)

async function onQuickAdd() {
  addError.value = ''
  addSuccess.value = false
  if (!addForm.headword.trim()) { addError.value = 'Please enter the Taita word.'; return }
  // Swahili translation is optional — enter * if unsure. Reviewers handle validation.

  // Normalize examples: drop rows with no taita_text, null out empty optionals.
  const cleanExamples = addExamples.value
    .map(ex => ({
      taita_text: ex.taita_text.trim(),
      swahili_text: ex.swahili_text?.trim() || null,
      english_text: ex.english_text?.trim() || null,
      source_ref: ex.source_ref?.trim() || null,
    }))
    .filter(ex => ex.taita_text.length > 0)
  const examplesPayload = cleanExamples.length > 0 ? cleanExamples : null

  // Swahili-required validation (only if there are any examples)
  if (cleanExamples.length > 0) {
    const missingSw = cleanExamples.findIndex(ex => !ex.swahili_text)
    if (missingSw !== -1) {
      addError.value = `Example ${missingSw + 1} is missing its Swahili translation. Please add one before submitting.`
      return
    }
  }

  addSubmitting.value = true
  try {
    if (addMode.value === 'direct') {
      await createWord({
        headword: addForm.headword.trim(),
        part_of_speech: addForm.part_of_speech || null,
        noun_class: addForm.noun_class || null,
        dialect: addForm.dialect || null,
        literal_translation: addForm.literal_translation || null,
        swahili_translation: addForm.swahili_translation.trim(),
        english_translation: addForm.english_translation.trim() || null,
        examples: examplesPayload,
      })
    } else {
      await createSuggestion({
        target_type: 'new_word',
        proposed_value: {
          headword: addForm.headword.trim(),
          part_of_speech: addForm.part_of_speech || null,
          noun_class: addForm.noun_class || null,
          dialect: addForm.dialect || null,
          literal_translation: addForm.literal_translation || null,
          swahili_translation: addForm.swahili_translation.trim(),
          english_translation: addForm.english_translation.trim() || null,
          examples: examplesPayload,
        },
        rationale: addRationale.value.trim() || null,
      })
    }
    addSuccess.value = true
    Object.assign(addForm, { headword: '', dialect: '', part_of_speech: '', noun_class: '', swahili_translation: '', english_translation: '', literal_translation: '' })
    addRationale.value = ''
    addExamples.value = []
  } catch (err: unknown) {
    const e = err as { response?: { _data?: { detail?: string } }; message?: string }
    addError.value = (e.response?._data?.detail as string) || 'Something went wrong.'
  } finally {
    addSubmitting.value = false
  }
}

// Reset page when type filter changes
watch(activeTypeFilter, () => {
  queuePage.value = 1
  allQueueItems.value = []
})

// ═══ UTILITIES ═══
function typeLabel(s: SuggestionListItem): string {
  switch (s.target_type) {
    case 'new_word': return 'New word'
    case 'word': return `Correction · ${s.field_path}`
    case 'translation': return 'Translation suggestion'
    case 'example': return 'Example suggestion'
    case 'relation': return 'Relation suggestion'
    default: return s.target_type
  }
}

function formatValue(proposed: unknown): string {
  if (typeof proposed === 'string') return proposed
  if (typeof proposed === 'object' && proposed !== null) {
    const obj = proposed as Record<string, unknown>
    if (obj.value) return String(obj.value)
    if (obj.text) return String(obj.text)
    if (obj.headword) return String(obj.headword)
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
</script>

<template>
  <div>
    <!-- Header -->
    <section class="px-4 md:px-12 py-8 md:py-12 border-b border-cream-200">
      <div class="max-w-3xl">
        <p class="text-xs font-semibold tracking-widest uppercase text-ochre mb-2">Contribute</p>
        <h1 class="font-serif text-3xl md:text-4xl text-forest-dark mb-3">
          {{ activeTab === "suggest" ? (isReviewer ? "Add a new word" : "Suggest a new word") : "Community suggestions" }}
        </h1>
        <p class="text-sm md:text-base text-stone leading-relaxed">
          <template v-if="activeTab === 'suggest'">
            <template v-if="isReviewer">
              As a reviewer, words you add go <strong>live immediately</strong>.
            </template>
            <template v-else>
              Your suggestion will be reviewed by the community.
              <RouterLink
                v-if="!isAuthed"
                :to="{ path: '/login', query: { next: '/contribute' } }"
                class="text-forest font-medium hover:underline"
              >Sign in</RouterLink>
              <template v-if="!isAuthed"> for a higher rate limit.</template>
            </template>
          </template>
          <template v-else>
            Help review and improve the dictionary. Vote on suggestions or (if you're a reviewer) accept them directly.
          </template>
        </p>
      </div>
    </section>

    <!-- Tab switcher -->
    <section class="px-4 md:px-12 py-4 border-b border-cream-200 sticky top-[57px] bg-cream/95 backdrop-blur z-10">
      <div class="flex bg-cream-100 rounded-lg p-1 max-w-md">
        <button
          @click="activeTab = 'suggest'"
          :class="['flex-1 tab-pill', activeTab === 'suggest' && 'active']"
        >
          {{ isReviewer ? "Add word" : "Suggest word" }}
        </button>
        <button
          @click="activeTab = 'suggestions'"
          :class="['flex-1 tab-pill', activeTab === 'suggestions' && 'active']"
        >
          Review suggestions
          <span v-if="openCount > 0" class="ml-1 text-[10px] opacity-70">{{ openCount }}</span>
        </button>
      </div>
    </section>

    <!-- ── SUGGEST TAB ──────────────────────────────────────── -->
    <div v-show="activeTab === 'suggest'">
      <!-- First-time contributor nudge -->
      <div
        v-if="showGuideNudge"
        class="mx-4 md:mx-12 mt-4 md:mt-6 bg-ochre/15 border border-ochre/40 rounded-xl p-4 md:p-5 flex items-start gap-3 md:gap-4"
      >
        <svg class="w-5 h-5 md:w-6 md:h-6 text-ochre flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
        </svg>
        <div class="flex-1">
          <p class="text-sm font-semibold text-ink mb-1">First time contributing?</p>
          <p class="text-xs text-stone leading-relaxed mb-3">
            The Reading Guide explains how Taita words are written in this dictionary. It takes 2 minutes.
          </p>
          <div class="flex items-center gap-3">
            <RouterLink to="/guide" class="text-xs font-semibold text-forest hover:underline">
              Read the guide →
            </RouterLink>
            <button @click="dismissNudge" class="text-xs text-stone-light hover:text-stone">
              I'll skip it for now
            </button>
          </div>
        </div>
      </div>

      <!-- Mode toggle (reviewers only) -->
      <section v-if="isReviewer" class="px-4 md:px-12 py-4">
        <div class="flex bg-cream-100 rounded-lg p-1 max-w-md">
          <button
            @click="mode = 'direct'"
            :class="['flex-1 tab-pill', mode === 'direct' && 'active']"
          >
            Add directly (live)
          </button>
          <button
            @click="mode = 'suggest'"
            :class="['flex-1 tab-pill', mode === 'suggest' && 'active']"
          >
            Suggest (queue)
          </button>
        </div>
        <p class="text-xs text-stone-light mt-2 ml-1">
          <template v-if="mode === 'direct'">Word goes live immediately.</template>
          <template v-else>Word enters the suggestion queue for community review.</template>
        </p>
      </section>

      <!-- Suggest form -->
      <form @submit.prevent="onSubmit" class="px-4 md:px-12 py-6 md:py-10 max-w-5xl">
        <input
          v-model="honeypot"
          type="text"
          name="website"
          style="position: absolute; left: -9999px; opacity: 0; pointer-events: none"
          tabindex="-1"
          autocomplete="off"
        />

        <div class="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-6">
          <div>
            <label class="field-label">Word <span class="text-terracotta">*</span></label>
            <input v-model="form.headword" type="text" class="field" placeholder="e.g. mlima" :disabled="submitting" />
          </div>

          <div>
            <label class="field-label">Dialect <span class="text-stone-light font-normal">(optional)</span></label>
            <select v-model="form.dialect" class="field" :disabled="submitting">
              <option value="">— Any / Unknown —</option>
              <option>Dawida</option><option>Sagala</option><option>Kasighau</option>
            </select>
          </div>

          <div>
            <label class="field-label">Part of speech <span class="text-stone-light font-normal">(optional)</span></label>
            <select v-model="form.part_of_speech" class="field" :disabled="submitting">
              <option value="">— Skip —</option>
              <option>noun</option><option>verb</option><option>adjective</option><option>adverb</option><option>phrase</option>
            </select>
          </div>

          <div>
            <label class="field-label">Noun class <span class="text-stone-light font-normal">(optional)</span></label>
            <select v-model="form.noun_class" class="field" :disabled="submitting">
              <option value="">—</option>
              <option>1/2 — person/people</option><option>3/4 — tree/things</option>
              <option>5/6 — fruit/collective</option><option>7/8 — object/objects</option>
              <option>9/10 — animal/animals</option><option>11 — long things</option>
              <option>14 — abstraction</option><option>15 — infinitive</option>
            </select>
          </div>

          <div>
            <label class="field-label">Swahili gloss <span class="text-terracotta">*</span></label>
            <input v-model="form.swahili_gloss" type="text" class="field" placeholder="mf. mlima, kilima" :disabled="submitting" />
          </div>

          <div>
            <label class="field-label">English gloss <span class="text-stone-light font-normal">(optional)</span></label>
            <input v-model="form.english_gloss" type="text" class="field" placeholder="e.g. mountain, hill" :disabled="submitting" />
          </div>

          <div class="md:col-span-2">
            <label class="field-label">Literal translation <span class="text-stone-light font-normal">(optional)</span></label>
            <input v-model="form.literal_translation" type="text" class="field" placeholder="e.g. 'I have climbed for him/her'" :disabled="submitting" />
          </div>

          <div v-if="useSuggestPath" class="md:col-span-2">
            <label class="field-label">Notes for reviewers <span class="text-stone-light font-normal">(optional)</span></label>
            <textarea v-model="rationale" rows="3" class="field" placeholder="Why is this word needed?" :disabled="submitting"></textarea>
          </div>
        </div>

        <!-- Rate-limit notice -->
        <div
          v-if="!isReviewer"
          class="mt-6 md:mt-8 bg-cream-100 border border-cream-200 rounded-lg p-4 flex gap-3 items-start max-w-3xl"
        >
          <svg class="w-5 h-5 text-ochre mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p class="text-xs text-ink-soft leading-relaxed">
            <template v-if="!isAuthed">
              You can suggest <strong>5 words per hour</strong> as an anonymous user.
              <RouterLink :to="{ path: '/login', query: { next: '/contribute' } }" class="text-forest font-medium hover:underline">Sign in</RouterLink> for 15/hour.
            </template>
            <template v-else>
              You can suggest <strong>15 words per hour</strong>. Become a reviewer for unlimited suggestions.
            </template>
          </p>
        </div>

        <!-- Error / success -->
        <div v-if="error" class="mt-6 bg-terracotta/10 border border-terracotta/30 rounded-lg p-4 text-sm text-terracotta-dark">
          {{ error }}
          <div v-if="duplicateWord" class="mt-2">
            <RouterLink :to="`/words/${duplicateWord.id}`" class="text-forest hover:underline font-medium">
              See "{{ duplicateWord.headword }}" →
            </RouterLink>
          </div>
        </div>

        <div v-if="success" class="mt-6 bg-forest/10 border border-forest/30 rounded-lg p-4 text-sm text-forest-dark">
          <p class="font-semibold mb-1">{{ useSuggestPath ? "Suggestion submitted!" : "Word added!" }}</p>
          <p class="text-xs">
            <template v-if="useSuggestPath">
              Your suggestion is now open for community review.
              <button @click="activeTab = 'suggestions'" class="text-forest hover:underline font-medium">View it →</button>
            </template>
            <template v-else>
              The word is now live in the dictionary.
              <RouterLink :to="`/words/${successId}`" class="text-forest hover:underline font-medium">View it →</RouterLink>
            </template>
          </p>
        </div>

        <div class="mt-6 md:mt-8 flex items-center gap-4">
          <button
            type="submit"
            :disabled="submitting"
            class="bg-forest hover:bg-forest-dark text-cream font-semibold text-sm px-6 py-3 rounded-lg transition disabled:opacity-50"
          >
            {{ submitting ? "Submitting..." : useSuggestPath ? "Submit suggestion" : "Add word to dictionary" }}
          </button>
        </div>
      </form>
    </div>

    <!-- ── SUGGESTIONS TAB ──────────────────────────────────── -->
    <div v-show="activeTab === 'suggestions'">
      <!-- Filter tabs -->
      <section class="px-4 md:px-12 py-4 flex items-center justify-between border-b border-cream-200">
        <div class="flex items-center gap-1 overflow-x-auto">
          <button
            v-for="tab in statusTabs"
            :key="tab.value"
            @click="activeStatus = tab.value"
            :class="['tab-pill whitespace-nowrap', activeStatus === tab.value && 'active']"
          >
            {{ tab.label }}
          </button>
        </div>
      </section>

      <!-- Suggestion cards -->
      <section class="px-4 md:px-12 py-6 md:py-8">
        <div v-if="loading" class="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div v-for="i in 4" :key="i" class="bg-white border border-cream-200 rounded-xl p-5 animate-pulse">
            <div class="h-3 bg-cream-200 rounded w-1/3 mb-2"></div>
            <div class="h-6 bg-cream-200 rounded w-1/2 mb-3"></div>
            <div class="h-4 bg-cream-100 rounded w-2/3"></div>
          </div>
        </div>

        <div v-else-if="error" class="bg-cream-100 border border-cream-200 rounded-xl p-6 text-sm text-stone">
          <p class="font-medium text-terracotta mb-1">Couldn't load suggestions</p>
          <p class="text-xs text-stone-light">{{ error }}</p>
        </div>

        <div v-else-if="suggestions.length === 0" class="bg-cream-100 border border-cream-200 rounded-xl p-8 md:p-12 text-center">
          <p class="font-serif text-lg md:text-xl text-forest-dark mb-2">No suggestions here</p>
          <p class="text-sm text-stone mb-6">
            {{ activeStatus === 'open' ? "Be the first to suggest a word." : "Nothing to show." }}
          </p>
          <button
            @click="activeTab = 'suggest'"
            class="inline-block bg-forest hover:bg-forest-dark text-cream font-semibold text-sm px-5 py-2.5 rounded-lg transition"
          >
            Suggest a word
          </button>
        </div>

        <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-3">
          <SuggestionCard
            v-for="s in suggestions"
            :key="s.id"
            :suggestion="s"
            @voted="onVoted"
          />
        </div>

        <div v-if="hasMore" class="mt-6 text-center">
          <button
            @click="loadMore"
            :disabled="loadingMore"
            class="text-sm font-semibold text-forest border border-forest rounded-lg px-5 py-2 hover:bg-forest hover:text-cream transition disabled:opacity-50"
          >
            {{ loadingMore ? "Loading..." : "Load more" }}
          </button>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted } from "vue";
import { RouterLink } from "vue-router";
import { useAuthStore } from "../stores/auth";
import { createSuggestion, listSuggestions } from "../api/suggestions";
import { createWord } from "../api/words";
import SuggestionCard from "../components/SuggestionCard.vue";

const authStore = useAuthStore();

const activeTab = ref("suggest");
const activeStatus = ref("open");

const statusTabs = [
  { value: "open", label: "Open" },
  { value: "accepted", label: "Accepted" },
  { value: "rejected", label: "Rejected" },
];

// ── Guide nudge ───────────────────────────────────────────────
const GUIDE_NUDGE_KEY = "taitalumi_guide_nudge_dismissed";
const nudgeDismissed = ref(localStorage.getItem(GUIDE_NUDGE_KEY) === "true");
const showGuideNudge = computed(() => !nudgeDismissed.value);

function dismissNudge() {
  nudgeDismissed.value = true;
  localStorage.setItem(GUIDE_NUDGE_KEY, "true");
}

onMounted(() => {
  if (localStorage.getItem("taitalumi_guide_visited") === "true") {
    nudgeDismissed.value = true;
  }
  fetchSuggestions();
});

// ── Auth + mode ───────────────────────────────────────────────
const isReviewer = computed(
  () => authStore.isAuthenticated && (authStore.user?.role === "reviewer" || authStore.user?.role === "admin")
);
const isAuthed = computed(() => authStore.isAuthenticated);
const mode = ref("direct");
const useSuggestPath = computed(() => {
  if (!isReviewer.value) return true;
  return mode.value === "suggest";
});

// ── Suggest form ──────────────────────────────────────────────
const form = reactive({
  headword: "", dialect: "", part_of_speech: "", noun_class: "",
  swahili_gloss: "", english_gloss: "", literal_translation: "",
});
const rationale = ref("");
const honeypot = ref("");
const submitting = ref(false);
const error = ref("");
const success = ref(false);
const successId = ref(null);
const duplicateWord = ref(null);

async function onSubmit() {
  error.value = "";
  success.value = false;
  duplicateWord.value = null;

  if (!form.headword.trim()) { error.value = "Please enter the Taita word."; return; }
  if (!form.swahili_gloss.trim()) { error.value = "Please enter the Swahili translation."; return; }

  submitting.value = true;
  try {
    if (honeypot.value) { success.value = true; successId.value = "fake-id"; return; }

    if (useSuggestPath.value) {
      const payload = {
        target_type: "new_word",
        proposed_value: {
          headword: form.headword.trim(),
          part_of_speech: form.part_of_speech || null,
          noun_class: form.noun_class || null,
          dialect: form.dialect || null,
          literal_translation: form.literal_translation || null,
          swahili_gloss: form.swahili_gloss.trim(),
          english_gloss: form.english_gloss.trim() || null,
        },
        rationale: rationale.value.trim() || null,
      };
      const result = await createSuggestion(payload);
      success.value = true;
      successId.value = result.id;
    } else {
      const payload = {
        headword: form.headword.trim(),
        part_of_speech: form.part_of_speech || null,
        noun_class: form.noun_class || null,
        dialect: form.dialect || null,
        literal_translation: form.literal_translation || null,
        swahili_gloss: form.swahili_gloss.trim(),
        english_gloss: form.english_gloss.trim() || null,
      };
      const result = await createWord(payload);
      success.value = true;
      successId.value = result.id;
    }

    form.headword = ""; form.dialect = ""; form.part_of_speech = "";
    form.noun_class = ""; form.swahili_gloss = ""; form.english_gloss = "";
    form.literal_translation = ""; rationale.value = "";
  } catch (err) {
    if (err.response?.status === 429) {
      error.value = "Rate limit exceeded. Try again later or sign in.";
    } else if (err.response?.status === 409) {
      const detail = err.response?.data?.detail;
      if (detail && typeof detail === "object" && detail.existing_word_id) {
        duplicateWord.value = { id: detail.existing_word_id, headword: detail.existing_headword };
        error.value = detail.message || "This word already exists.";
      } else {
        error.value = typeof detail === "string" ? detail : "A word with this spelling already exists.";
      }
    } else if (err.response?.status === 401) {
      error.value = "Please sign in to add words directly.";
    } else {
      error.value = err.response?.data?.detail || "Something went wrong. Please try again.";
    }
  } finally {
    submitting.value = false;
  }
}

// ── Suggestions list ──────────────────────────────────────────
const suggestions = ref([]);
const total = ref(0);
const openCount = ref(0);
const loading = ref(false);
const loadingMore = ref(false);
const page = ref(1);
const pageSize = 20;
const hasMore = ref(false);

async function fetchSuggestions() {
  loading.value = true;
  error.value = "";
  try {
    const data = await listSuggestions({ status: activeStatus.value, page: page.value, size: pageSize });
    suggestions.value = page.value === 1 ? data.items : [...suggestions.value, ...data.items];
    total.value = data.total;
    hasMore.value = data.has_next;
    if (activeStatus.value === "open") openCount.value = data.total;
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

function onVoted({ id, upvotes, downvotes, user_vote, promoted }) {
  const s = suggestions.value.find((x) => x.id === id);
  if (s) {
    s.upvotes = upvotes;
    s.downvotes = downvotes;
    s.user_vote = user_vote;
    if (promoted) setTimeout(() => fetchSuggestions(), 1500);
  }
}

watch(activeStatus, () => {
  page.value = 1;
  fetchSuggestions();
});

// Fetch open count on mount for the badge
onMounted(async () => {
  try {
    const data = await listSuggestions({ status: "open", size: 1 });
    openCount.value = data.total;
  } catch {}
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
.field {
  width: 100%;
  padding: 10px 14px;
  border: 1px solid #e8dfc8;
  border-radius: 8px;
  background: #fdfbf6;
  font-size: 14px;
  color: #1f2937;
  font-family: "Inter", sans-serif;
}
.field:focus {
  outline: none;
  border-color: #2d5a3d;
  box-shadow: 0 0 0 3px rgba(45, 90, 61, 0.1);
}
.field:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.field-label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: #374151;
  margin-bottom: 6px;
  letter-spacing: 0.02em;
}
</style>

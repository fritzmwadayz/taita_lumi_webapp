<template>
  <div>
    <!-- Header -->
    <section class="px-12 py-12 border-b border-cream-200">
      <div class="max-w-3xl">
        <h1 class="font-serif text-4xl text-forest-dark mb-3">
          {{ isAuthed ? "Add a new word" : "Suggest a new word" }}
        </h1>
        <p class="text-base text-stone leading-relaxed">
          <template v-if="isAuthed">
            As a contributor, words you add go <strong>live immediately</strong>.
            The community can still suggest corrections later.
          </template>
          <template v-else>
            Your suggestion will be reviewed by the community.
            <RouterLink
              :to="{ path: '/login', query: { next: '/suggest' } }"
              class="text-forest font-medium hover:underline"
            >Sign in</RouterLink>
            to add words directly without waiting for votes.
          </template>
        </p>
        <p class="text-xs text-stone-light mt-3">
          New to contributing? Read the
          <RouterLink to="/guide" class="text-forest hover:underline">Reading Guide</RouterLink>
          first.
        </p>
      </div>
    </section>

    <!-- Mode toggle (only for authed users — they can choose either path) -->
    <section v-if="isAuthed" class="px-12 py-4 border-b border-cream-200">
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
        <template v-if="mode === 'direct'">
          Word goes live immediately. Use for words you're confident about.
        </template>
        <template v-else>
          Word enters the suggestion queue for community review. Use if unsure.
        </template>
      </p>
    </section>

    <!-- Form -->
    <form @submit.prevent="onSubmit" class="px-12 py-10 max-w-5xl">
      <!-- Honeypot (hidden from humans) -->
      <input
        v-model="honeypot"
        type="text"
        name="website"
        style="position: absolute; left: -9999px; opacity: 0; pointer-events: none"
        tabindex="-1"
        autocomplete="off"
      />

      <div class="grid grid-cols-2 gap-x-8 gap-y-6">
        <!-- Word -->
        <div>
          <label class="field-label">Word <span class="text-terracotta">*</span></label>
          <input
            v-model="form.headword"
            type="text"
            class="field"
            placeholder="e.g. mlima"
            :disabled="submitting"
          />
          <p class="text-[10px] text-stone-light mt-1">The Taita word, exactly as written.</p>
        </div>

        <!-- Dialect -->
        <div>
          <label class="field-label">
            Dialect <span class="text-stone-light font-normal">(optional)</span>
          </label>
          <select v-model="form.dialect" class="field" :disabled="submitting">
            <option value="">— Any / Unknown —</option>
            <option>Dawida</option>
            <option>Sagala</option>
            <option>Kasighau</option>
          </select>
        </div>

        <!-- Part of speech (optional) -->
        <div>
          <label class="field-label">
            Part of speech
            <span class="text-stone-light font-normal">(optional — skip if unsure)</span>
          </label>
          <select v-model="form.part_of_speech" class="field" :disabled="submitting">
            <option value="">— Skip —</option>
            <option>noun</option>
            <option>verb</option>
            <option>adjective</option>
            <option>adverb</option>
            <option>phrase</option>
          </select>
          <p class="text-[10px] text-stone-light mt-1">
            Leaving this blank is fine. Reviewers can add it later.
          </p>
        </div>

        <!-- Noun class -->
        <div>
          <label class="field-label">
            Noun class
            <span class="text-stone-light font-normal">(optional, for nouns)</span>
          </label>
          <select v-model="form.noun_class" class="field" :disabled="submitting">
            <option value="">—</option>
            <option>1/2 — person/people</option>
            <option>3/4 — tree/things</option>
            <option>5/6 — fruit/collective</option>
            <option>7/8 — object/objects</option>
            <option>9/10 — animal/animals</option>
            <option>11 — long things</option>
            <option>14 — abstraction</option>
            <option>15 — infinitive</option>
          </select>
        </div>

        <!-- Swahili gloss (primary) -->
        <div>
          <label class="field-label">Swahili gloss <span class="text-terracotta">*</span></label>
          <input
            v-model="form.swahili_gloss"
            type="text"
            class="field"
            placeholder="mf. mlima, kilima"
            :disabled="submitting"
          />
          <p class="text-[10px] text-stone-light mt-1">The Kiswahili translation — primary.</p>
        </div>

        <!-- English gloss -->
        <div>
          <label class="field-label">
            English gloss
            <span class="text-stone-light font-normal">(optional)</span>
          </label>
          <input
            v-model="form.english_gloss"
            type="text"
            class="field"
            placeholder="e.g. mountain, hill"
            :disabled="submitting"
          />
        </div>

        <!-- Literal translation -->
        <div class="col-span-2">
          <label class="field-label">
            Literal translation
            <span class="text-stone-light font-normal">(optional, for whole-sentence words)</span>
          </label>
          <input
            v-model="form.literal_translation"
            type="text"
            class="field"
            placeholder="e.g. 'I have climbed for him/her'"
            :disabled="submitting"
          />
          <p class="text-[10px] text-stone-light mt-1">
            For Taita words that translate to a full sentence, give the plain meaning here.
          </p>
        </div>

        <!-- Rationale (only for suggest mode) -->
        <div v-if="useSuggestPath" class="col-span-2">
          <label class="field-label">
            Notes for reviewers
            <span class="text-stone-light font-normal">(optional)</span>
          </label>
          <textarea
            v-model="rationale"
            rows="3"
            class="field"
            placeholder="Why is this word needed? Any context that helps reviewers..."
            :disabled="submitting"
          ></textarea>
        </div>
      </div>

      <!-- Anon rate-limit notice -->
      <div
        v-if="!isAuthed"
        class="mt-8 bg-cream-100 border border-cream-200 rounded-lg p-4 flex gap-3 items-start max-w-3xl"
      >
        <svg
          class="w-5 h-5 text-ochre mt-0.5 flex-shrink-0"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
        <p class="text-xs text-ink-soft leading-relaxed">
          You can suggest <strong>5 words per hour</strong> as an anonymous user.
          <RouterLink
            :to="{ path: '/login', query: { next: '/suggest' } }"
            class="text-forest font-medium hover:underline"
          >Sign in</RouterLink>
          for unlimited suggestions.
        </p>
      </div>

      <!-- Error / success messages -->
      <div
        v-if="error"
        class="mt-6 bg-terracotta/10 border border-terracotta/30 rounded-lg p-4 text-sm text-terracotta-dark"
      >
        {{ error }}
      </div>

      <div
        v-if="success"
        class="mt-6 bg-forest/10 border border-forest/30 rounded-lg p-4 text-sm text-forest-dark"
      >
        <p class="font-semibold mb-1">
          {{ useSuggestPath ? "Suggestion submitted!" : "Word added!" }}
        </p>
        <p class="text-xs">
          <template v-if="useSuggestPath">
            Your suggestion is now open for community review.
            <RouterLink :to="`/suggestions/${successId}`" class="text-forest hover:underline font-medium">
              View it →
            </RouterLink>
          </template>
          <template v-else>
            The word is now live in the dictionary.
            <RouterLink :to="`/words/${successId}`" class="text-forest hover:underline font-medium">
              View it →
            </RouterLink>
          </template>
        </p>
      </div>

      <!-- Submit -->
      <div class="mt-8 flex items-center gap-4">
        <button
          type="submit"
          :disabled="submitting"
          class="bg-forest hover:bg-forest-dark text-cream font-semibold text-sm px-6 py-3 rounded-lg transition disabled:opacity-50"
        >
          {{ submitting
            ? "Submitting..."
            : useSuggestPath ? "Submit suggestion" : "Add word to dictionary" }}
        </button>
        <RouterLink
          to="/"
          class="text-sm text-stone hover:text-ink px-4 py-3"
        >
          Cancel
        </RouterLink>
      </div>
    </form>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from "vue";
import { RouterLink } from "vue-router";
import { useAuthStore } from "../stores/auth";
import { createSuggestion } from "../api/suggestions";
import { createWord } from "../api/words";

const authStore = useAuthStore();

const isAuthed = computed(() => authStore.isAuthenticated);

// Authed users can choose between direct add or suggest.
// Anon users can only suggest.
const mode = ref("direct"); // 'direct' or 'suggest'

const useSuggestPath = computed(() => {
  if (!isAuthed.value) return true; // anon always suggests
  return mode.value === "suggest";
});

const form = reactive({
  headword: "",
  dialect: "",
  part_of_speech: "",
  noun_class: "",
  swahili_gloss: "",
  english_gloss: "",
  literal_translation: "",
});

const rationale = ref("");
const honeypot = ref(""); // bots fill this; humans don't
const submitting = ref(false);
const error = ref("");
const success = ref(false);
const successId = ref(null);

async function onSubmit() {
  error.value = "";
  success.value = false;

  // ── Basic validation ───────────────────────────────────────
  if (!form.headword.trim()) {
    error.value = "Please enter the Taita word.";
    return;
  }
  if (!form.swahili_gloss.trim()) {
    error.value = "Please enter the Swahili translation.";
    return;
  }

  // ── Submit ─────────────────────────────────────────────────
  submitting.value = true;
  try {
    // Honeypot: if filled, silently succeed without actually submitting
    if (honeypot.value) {
      success.value = true;
      successId.value = "fake-id";
      return;
    }

    if (useSuggestPath.value) {
      // ── Suggest path → POST /api/suggestions ──────────────
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
      // ── Direct add path → POST /api/words ─────────────────
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

    // Reset form
    form.headword = "";
    form.dialect = "";
    form.part_of_speech = "";
    form.noun_class = "";
    form.swahili_gloss = "";
    form.english_gloss = "";
    form.literal_translation = "";
    rationale.value = "";
  } catch (err) {
    if (err.response?.status === 429) {
      error.value =
        "Rate limit exceeded: you've submitted too many suggestions recently. Try again later or sign in for unlimited suggestions.";
    } else if (err.response?.status === 409) {
      error.value = "A word with this spelling already exists in the dictionary.";
    } else if (err.response?.status === 401) {
      error.value = "Please sign in to add words directly.";
    } else {
      error.value = err.response?.data?.detail || "Something went wrong. Please try again.";
    }
  } finally {
    submitting.value = false;
  }
}
</script>

<style scoped>
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

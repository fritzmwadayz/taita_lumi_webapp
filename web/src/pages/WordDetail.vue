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
          <!-- Edit + Delete buttons (reviewers + admins) -->
          <div v-if="authStore.isReviewer" class="flex items-center gap-2">
            <button
              @click="openEditForm"
              class="flex items-center gap-1.5 text-sm text-stone hover:text-forest px-2 py-1 rounded transition"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
              Edit
            </button>
            <button
              v-if="authStore.isAdmin"
              @click="confirmDelete"
              class="flex items-center gap-1.5 text-sm text-stone hover:text-terracotta px-2 py-1 rounded transition"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
              Delete
            </button>
          </div>
        </div>

        <!-- Delete confirmation -->
        <div v-if="deleteConfirmOpen" class="bg-terracotta/10 border border-terracotta/30 rounded-xl p-5 mb-6">
          <p class="text-sm font-semibold text-ink mb-1">Delete this word?</p>
          <p class="text-xs text-stone mb-4">
            "{{ word.headword }}" will be hidden from the dictionary. This can be undone later.
          </p>
          <div v-if="deleteError" class="text-xs text-terracotta mb-3">{{ deleteError }}</div>
          <div class="flex gap-2">
            <button
              @click="doDelete"
              :disabled="deleting"
              class="bg-terracotta hover:bg-terracotta-dark text-cream text-sm font-semibold px-4 py-2 rounded-lg transition disabled:opacity-50"
            >
              {{ deleting ? "Deleting..." : "Yes, delete" }}
            </button>
            <button
              @click="cancelDelete"
              class="text-sm text-stone hover:text-ink px-4 py-2"
            >
              Cancel
            </button>
          </div>
        </div>

        <!-- Inline edit form -->
        <div v-if="editFormOpen" class="bg-cream-50 border border-cream-200 rounded-xl p-6 mb-6">
          <p class="text-xs font-semibold text-ink mb-4">Edit word</p>
          <div class="grid grid-cols-2 gap-4 mb-4">
            <div>
              <label class="text-[10px] font-semibold text-stone uppercase tracking-wider">Word</label>
              <input v-model="editForm.headword" type="text" class="field" />
            </div>
            <div>
              <label class="text-[10px] font-semibold text-stone uppercase tracking-wider">Dialect</label>
              <select v-model="editForm.dialect" class="field">
                <option value="">—</option>
                <option>Dawida</option>
                <option>Sagala</option>
                <option>Kasighau</option>
              </select>
            </div>
            <div>
              <label class="text-[10px] font-semibold text-stone uppercase tracking-wider">Part of speech</label>
              <select v-model="editForm.part_of_speech" class="field">
                <option value="">—</option>
                <option>noun</option>
                <option>verb</option>
                <option>adjective</option>
                <option>adverb</option>
                <option>phrase</option>
              </select>
            </div>
            <div>
              <label class="text-[10px] font-semibold text-stone uppercase tracking-wider">Noun class</label>
              <input v-model="editForm.noun_class" type="text" class="field" placeholder="e.g. 3/4" />
            </div>
            <div>
              <label class="text-[10px] font-semibold text-stone uppercase tracking-wider">Swahili gloss</label>
              <input v-model="editForm.swahili_gloss" type="text" class="field" />
            </div>
            <div>
              <label class="text-[10px] font-semibold text-stone uppercase tracking-wider">English gloss</label>
              <input v-model="editForm.english_gloss" type="text" class="field" />
            </div>
            <div class="col-span-2">
              <label class="text-[10px] font-semibold text-stone uppercase tracking-wider">Literal translation</label>
              <input v-model="editForm.literal_translation" type="text" class="field" />
            </div>
            <div class="col-span-2">
              <label class="text-[10px] font-semibold text-stone uppercase tracking-wider">Morphology notes</label>
              <textarea v-model="editForm.morphology_notes" rows="2" class="field"></textarea>
            </div>
          </div>
          <div v-if="editFormError" class="text-xs text-terracotta mb-3">{{ editFormError }}</div>
          <div class="flex gap-2">
            <button
              @click="saveEdit"
              :disabled="editFormSaving"
              class="bg-forest hover:bg-forest-dark text-cream text-sm font-semibold px-4 py-2 rounded-lg transition disabled:opacity-50"
            >
              {{ editFormSaving ? "Saving..." : "Save changes" }}
            </button>
            <button
              @click="closeEditForm"
              class="text-sm text-stone hover:text-ink px-4 py-2"
            >
              Cancel
            </button>
          </div>
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
          <div v-if="!swahiliGloss && !englishGloss" class="text-sm text-stone-light italic mb-4">
            No translations yet.
          </div>
        </div>

        <!-- Suggest missing translation buttons -->
        <div class="mt-6 flex flex-wrap gap-2">
          <button
            v-if="!swahiliGloss"
            @click="openGlossForm('sw')"
            class="text-xs font-semibold text-forest border border-forest rounded-lg px-3 py-1.5 hover:bg-forest hover:text-cream transition"
          >
            + Suggest Swahili translation
          </button>
          <button
            v-if="!englishGloss"
            @click="openGlossForm('en')"
            class="text-xs font-semibold text-forest border border-forest rounded-lg px-3 py-1.5 hover:bg-forest hover:text-cream transition"
          >
            + Suggest English translation
          </button>
        </div>

        <!-- Inline gloss suggestion form -->
        <div v-if="glossFormOpen" class="mt-4 bg-cream-50 border border-cream-200 rounded-lg p-4">
          <p class="text-xs font-semibold text-ink mb-3">
            Suggest {{ glossFormLanguage === "sw" ? "Swahili" : "English" }} translation for "{{ word.headword }}"
          </p>
          <input
            v-model="glossFormText"
            type="text"
            class="field mb-3"
            :placeholder="glossFormLanguage === 'sw' ? 'mf. mlima, kilima' : 'e.g. mountain, hill'"
            @keyup.enter="submitGlossSuggestion"
          />
          <div v-if="glossFormError" class="text-xs text-terracotta mb-2">{{ glossFormError }}</div>
          <div v-if="glossFormSuccess" class="text-xs text-forest mb-2">
            Suggestion submitted! It'll appear once the community votes on it.
          </div>
          <div class="flex gap-2">
            <button
              @click="submitGlossSuggestion"
              :disabled="glossFormSubmitting"
              class="bg-forest hover:bg-forest-dark text-cream text-xs font-semibold px-4 py-1.5 rounded-lg transition disabled:opacity-50"
            >
              {{ glossFormSubmitting ? "Submitting..." : "Submit" }}
            </button>
            <button
              @click="closeGlossForm"
              class="text-xs text-stone hover:text-ink px-3 py-1.5"
            >
              Cancel
            </button>
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
      <section class="py-12 border-t border-cream-200">
        <h2 class="text-xs font-semibold uppercase tracking-widest text-stone mb-6">Related words</h2>

        <div v-if="word.relations.length > 0" class="space-y-4 mb-4">
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
        <div v-else class="text-sm text-stone-light italic mb-4">
          No related words yet.
        </div>

        <!-- Suggest a variation button -->
        <button
          @click="openRelationForm"
          class="text-xs font-semibold text-forest border border-forest rounded-lg px-3 py-1.5 hover:bg-forest hover:text-cream transition"
        >
          + Suggest a related word
        </button>

        <!-- Inline relation suggestion form -->
        <div v-if="relationFormOpen" class="mt-4 bg-cream-50 border border-cream-200 rounded-lg p-4">
          <p class="text-xs font-semibold text-ink mb-3">
            Suggest a related word for "{{ word.headword }}"
          </p>
          <div class="grid grid-cols-2 gap-3 mb-3">
            <div>
              <label class="text-[10px] font-semibold text-stone uppercase tracking-wider">Related word</label>
              <input
                v-model="relationFormWord"
                type="text"
                class="field"
                placeholder="e.g. milima"
              />
            </div>
            <div>
              <label class="text-[10px] font-semibold text-stone uppercase tracking-wider">Relation type</label>
              <select v-model="relationFormType" class="field">
                <option value="variant">Variant (different spelling/dialect)</option>
                <option value="plural">Plural</option>
                <option value="singular">Singular</option>
                <option value="conjugation">Conjugation (different tense/person)</option>
                <option value="antonym">Opposite</option>
                <option value="derived">Derived from</option>
                <option value="see_also">See also</option>
              </select>
            </div>
          </div>
          <div v-if="relationFormError" class="text-xs text-terracotta mb-2">{{ relationFormError }}</div>
          <div v-if="relationFormSuccess" class="text-xs text-forest mb-2">
            Suggestion submitted! It'll appear once the community votes on it.
          </div>
          <div class="flex gap-2">
            <button
              @click="submitRelationSuggestion"
              :disabled="relationFormSubmitting"
              class="bg-forest hover:bg-forest-dark text-cream text-xs font-semibold px-4 py-1.5 rounded-lg transition disabled:opacity-50"
            >
              {{ relationFormSubmitting ? "Submitting..." : "Submit" }}
            </button>
            <button
              @click="closeRelationForm"
              class="text-xs text-stone hover:text-ink px-3 py-1.5"
            >
              Cancel
            </button>
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
import { ref, computed, watch, reactive } from "vue";
import { useRoute, RouterLink } from "vue-router";
import { getWord, editWord, deleteWord } from "../api/words";
import { createSuggestion } from "../api/suggestions";
import { useAuthStore } from "../stores/auth";
import PosBadge from "../components/PosBadge.vue";
import ShareButtons from "../components/ShareButtons.vue";

const route = useRoute();
const authStore = useAuthStore();
const word = ref(null);
const loading = ref(true);
const error = ref("");

// ── Edit form state (reviewers + admins) ──────────────────────
const editFormOpen = ref(false);
const editFormSaving = ref(false);
const editFormError = ref("");
const editForm = reactive({
  headword: "",
  dialect: "",
  part_of_speech: "",
  noun_class: "",
  swahili_gloss: "",
  english_gloss: "",
  literal_translation: "",
  morphology_notes: "",
});

// ── Delete state (admins only) ────────────────────────────────
const deleteConfirmOpen = ref(false);
const deleting = ref(false);
const deleteError = ref("");

// ── Gloss suggestion form state ───────────────────────────────
const glossFormOpen = ref(false);
const glossFormLanguage = ref("sw");
const glossFormText = ref("");
const glossFormSubmitting = ref(false);
const glossFormError = ref("");
const glossFormSuccess = ref(false);

// ── Relation suggestion form state ────────────────────────────
const relationFormOpen = ref(false);
const relationFormWord = ref("");
const relationFormType = ref("variant");
const relationFormSubmitting = ref(false);
const relationFormError = ref("");
const relationFormSuccess = ref(false);

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

// ── Edit form functions (reviewers + admins) ──────────────────
function openEditForm() {
  const sw = word.value?.glosses?.find((g) => g.language === "sw");
  const en = word.value?.glosses?.find((g) => g.language === "en");
  editForm.headword = word.value?.headword || "";
  editForm.dialect = word.value?.dialect || "";
  editForm.part_of_speech = word.value?.part_of_speech || "";
  editForm.noun_class = word.value?.noun_class || "";
  editForm.swahili_gloss = sw?.text || "";
  editForm.english_gloss = en?.text || "";
  editForm.literal_translation = word.value?.literal_translation || "";
  editForm.morphology_notes = word.value?.morphology_notes || "";
  editFormError.value = "";
  editFormOpen.value = true;
}

function closeEditForm() {
  editFormOpen.value = false;
  editFormError.value = "";
}

async function saveEdit() {
  editFormSaving.value = true;
  editFormError.value = "";

  try {
    const updated = await editWord(word.value.id, {
      headword: editForm.headword.trim(),
      part_of_speech: editForm.part_of_speech || null,
      noun_class: editForm.noun_class || null,
      dialect: editForm.dialect || null,
      literal_translation: editForm.literal_translation || null,
      morphology_notes: editForm.morphology_notes || null,
      swahili_gloss: editForm.swahili_gloss || null,
      english_gloss: editForm.english_gloss || null,
    });
    word.value = updated;
    editFormOpen.value = false;
  } catch (err) {
    editFormError.value = err.response?.data?.detail || "Failed to save. Please try again.";
  } finally {
    editFormSaving.value = false;
  }
}

// ── Delete functions (admins only) ────────────────────────────
function confirmDelete() {
  deleteConfirmOpen.value = true;
  deleteError.value = "";
}

function cancelDelete() {
  deleteConfirmOpen.value = false;
  deleteError.value = "";
}

async function doDelete() {
  deleting.value = true;
  deleteError.value = "";

  try {
    await deleteWord(word.value.id);
    // Redirect to search after successful delete
    window.location.href = "/search";
  } catch (err) {
    deleteError.value = err.response?.data?.detail || "Failed to delete. Please try again.";
  } finally {
    deleting.value = false;
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

// ── Gloss suggestion functions ────────────────────────────────
function openGlossForm(lang) {
  glossFormLanguage.value = lang;
  glossFormText.value = "";
  glossFormError.value = "";
  glossFormSuccess.value = false;
  glossFormOpen.value = true;
}

function closeGlossForm() {
  glossFormOpen.value = false;
  glossFormText.value = "";
  glossFormError.value = "";
  glossFormSuccess.value = false;
}

async function submitGlossSuggestion() {
  if (!glossFormText.value.trim()) {
    glossFormError.value = "Please enter a translation.";
    return;
  }

  glossFormSubmitting.value = true;
  glossFormError.value = "";
  glossFormSuccess.value = false;

  try {
    await createSuggestion({
      target_type: "gloss",
      target_id: word.value.id,
      proposed_value: {
        language: glossFormLanguage.value,
        text: glossFormText.value.trim(),
      },
    });
    glossFormSuccess.value = true;
    glossFormText.value = "";
  } catch (err) {
    glossFormError.value = err.response?.data?.detail || "Failed to submit. Please try again.";
  } finally {
    glossFormSubmitting.value = false;
  }
}

// ── Relation suggestion functions ─────────────────────────────
function openRelationForm() {
  relationFormWord.value = "";
  relationFormType.value = "variant";
  relationFormError.value = "";
  relationFormSuccess.value = false;
  relationFormOpen.value = true;
}

function closeRelationForm() {
  relationFormOpen.value = false;
  relationFormWord.value = "";
  relationFormError.value = "";
  relationFormSuccess.value = false;
}

async function submitRelationSuggestion() {
  if (!relationFormWord.value.trim()) {
    relationFormError.value = "Please enter the related word.";
    return;
  }

  relationFormSubmitting.value = true;
  relationFormError.value = "";
  relationFormSuccess.value = false;

  try {
    await createSuggestion({
      target_type: "relation",
      target_id: word.value.id,
      proposed_value: {
        related_word: relationFormWord.value.trim(),
        relation_type: relationFormType.value,
      },
    });
    relationFormSuccess.value = true;
    relationFormWord.value = "";
  } catch (err) {
    relationFormError.value = err.response?.data?.detail || "Failed to submit. Please try again.";
  } finally {
    relationFormSubmitting.value = false;
  }
}
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
.field {
  width: 100%;
  padding: 8px 12px;
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
</style>

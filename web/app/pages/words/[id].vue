<template>
  <div>
    <div class="px-8 py-4">
      <NuxtLink to="/search" class="focus-ring inline-flex items-center gap-1.5 text-sm text-stone hover:text-forest rounded">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
        </svg>
        Back to search
      </NuxtLink>
    </div>

    <div v-if="pending" class="max-w-[680px] mx-auto px-8 py-24 text-center">
      <div class="animate-pulse">
        <div class="h-16 bg-cream-200 rounded w-1/2 mx-auto mb-4"></div>
        <div class="h-4 bg-cream-100 rounded w-1/3 mx-auto"></div>
      </div>
    </div>

    <div v-else-if="error || !word" class="max-w-[680px] mx-auto px-8 py-24 text-center">
      <p class="font-serif text-3xl text-forest-dark mb-4">Word not found</p>
      <p class="text-sm text-stone mb-8">
        {{ error?.statusCode === 404 ? "This word doesn't exist or has been removed." : 'Failed to load word.' }}
      </p>
      <NuxtLink to="/search" class="focus-ring btn btn-primary btn-md">Back to search</NuxtLink>
    </div>

    <article v-else class="max-w-[680px] mx-auto px-8">
      <header class="pt-12 pb-16">
        <div class="flex items-baseline gap-4 mb-4">
          <h1 class="font-serif text-6xl text-forest-dark font-semibold tracking-tight">{{ word.headword }}</h1>
          <div v-if="isReviewer" class="flex items-center gap-2">
            <button class="focus-ring btn btn-ghost btn-sm" @click="openEditForm">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>Edit
            </button>
            <button v-if="isAdmin" class="focus-ring btn btn-ghost btn-sm text-terracotta hover:text-terracotta-dark" @click="confirmDelete">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>Delete
            </button>
          </div>
        </div>

        <div v-if="deleteConfirmOpen" class="bg-terracotta/10 border border-terracotta/30 rounded-xl p-5 mb-6">
          <p class="text-sm font-semibold text-ink mb-1">Delete this word?</p>
          <p class="text-xs text-stone mb-4">"{{ word.headword }}" will be hidden from the dictionary. This can be undone later.</p>
          <div v-if="deleteError" class="text-xs text-terracotta mb-3">{{ deleteError }}</div>
          <div class="flex gap-2">
            <button :disabled="deleting" class="focus-ring btn btn-danger btn-sm" @click="doDelete">{{ deleting ? 'Deleting...' : 'Yes, delete' }}</button>
            <button class="focus-ring btn btn-ghost btn-sm" @click="cancelDelete">Cancel</button>
          </div>
        </div>

        <div v-if="editFormOpen" class="bg-cream-50 border border-cream-200 rounded-xl p-6 mb-6">
          <p class="text-xs font-semibold text-ink mb-4">Edit word</p>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div><label class="field-label">Word</label><input v-model="editForm.headword" type="text" class="field" /></div>
            <div><label class="field-label">Dialect</label><select v-model="editForm.dialect" class="field"><option value="">—</option><option>Dawida</option><option>Sagala</option><option>Kasighau</option></select></div>
            <div><label class="field-label">Part of speech</label><select v-model="editForm.part_of_speech" class="field"><option value="">—</option><option>noun</option><option>verb</option><option>adjective</option><option>adverb</option><option>phrase</option></select></div>
            <div><label class="field-label">Noun class</label><input v-model="editForm.noun_class" type="text" class="field" placeholder="e.g. 3/4" /></div>
            <div><label class="field-label">Swahili translation</label><input v-model="editForm.swahili_translation" type="text" class="field" /></div>
            <div><label class="field-label">English translation</label><input v-model="editForm.english_translation" type="text" class="field" /></div>
            <div class="col-span-2"><label class="field-label">Literal translation</label><input v-model="editForm.literal_translation" type="text" class="field" /></div>
            <div class="col-span-2"><label class="field-label">Morphology notes</label><textarea v-model="editForm.morphology_notes" rows="2" class="field"></textarea></div>
          </div>
          <div v-if="editFormError" class="text-xs text-terracotta mb-3">{{ editFormError }}</div>
          <div class="flex gap-2">
            <button :disabled="editFormSaving" class="focus-ring btn btn-primary btn-sm" @click="saveEdit">{{ editFormSaving ? 'Saving...' : 'Save changes' }}</button>
            <button class="focus-ring btn btn-ghost btn-sm" @click="closeEditForm">Cancel</button>
          </div>
        </div>

        <div class="flex flex-wrap items-center gap-3 mb-10">
          <PosBadge v-if="word.part_of_speech" :pos="word.part_of_speech" />
          <span v-if="word.noun_class" class="nclass-badge">{{ word.noun_class }}</span>
          <template v-if="word.dialect"><span class="text-xs text-stone-light">·</span><span class="text-xs text-stone">{{ word.dialect }} dialect</span></template>
        </div>
        <ShareButtons :headword="word.headword" :word-slug="word.slug" />
      </header>

      <section v-if="word.translations && word.translations.length > 0" class="py-12 border-t border-cream-200">
        <h2 class="text-xs font-semibold uppercase tracking-widest text-stone mb-6">Translations</h2>
        <div class="space-y-8">
          <div v-if="swahiliTranslation" class="flex gap-6"><span class="text-xs font-bold text-forest w-12 mt-1">SW</span><p class="font-serif text-2xl text-ink font-medium mb-1">{{ swahiliTranslation.text }}</p></div>
          <div v-if="englishTranslation" class="flex gap-6"><span class="text-xs font-bold text-terracotta w-12 mt-1">EN</span><p class="font-serif text-xl text-ink-soft font-medium mb-1">{{ englishTranslation.text }}</p></div>
          <div v-if="!swahiliTranslation && !englishTranslation" class="text-sm text-stone-light italic mb-4">No translations yet.</div>
        </div>
        <div class="mt-6 flex flex-wrap gap-2">
          <button v-if="!swahiliTranslation" class="focus-ring btn btn-secondary btn-sm" @click="openTranslationForm('sw')">+ Suggest Swahili translation</button>
          <button v-if="!englishTranslation" class="focus-ring btn btn-secondary btn-sm" @click="openTranslationForm('en')">+ Suggest English translation</button>
        </div>
        <div v-if="translationFormOpen" class="mt-4 bg-cream-50 border border-cream-200 rounded-lg p-4">
          <p class="text-xs font-semibold text-ink mb-3">Suggest {{ translationFormLanguage === 'sw' ? 'Swahili' : 'English' }} translation for "{{ word.headword }}"</p>
          <input v-model="translationFormText" type="text" class="field mb-3" :placeholder="translationFormLanguage === 'sw' ? 'mf. mlima, kilima' : 'e.g. mountain, hill'" @keyup.enter="submitTranslationSuggestion" />
          <div v-if="translationFormError" class="text-xs text-terracotta mb-2">{{ translationFormError }}</div>
          <div v-if="translationFormSuccess" class="text-xs text-forest mb-2">Suggestion submitted! It'll appear once the community votes on it.</div>
          <div class="flex gap-2">
            <button :disabled="translationFormSubmitting" class="focus-ring btn btn-primary btn-sm" @click="submitTranslationSuggestion">{{ translationFormSubmitting ? 'Submitting...' : 'Submit' }}</button>
            <button class="focus-ring btn btn-ghost btn-sm" @click="closeTranslationForm">Cancel</button>
          </div>
        </div>
      </section>

      <section v-if="word.literal_translation" class="py-12 border-t border-cream-200 bg-cream-50 -mx-8 px-8">
        <div class="max-w-[680px] mx-auto">
          <h2 class="text-xs font-semibold uppercase tracking-widest text-stone mb-3">Literal translation</h2>
          <p class="font-serif text-base italic text-ink-soft mb-2">"{{ word.literal_translation }}"</p>
          <p v-if="word.morphology_notes" class="text-xs text-stone leading-relaxed">{{ word.morphology_notes }}</p>
        </div>
      </section>

      <section class="py-12 border-t border-cream-200">
        <h2 class="text-xs font-semibold uppercase tracking-widest text-stone mb-6">Related words</h2>
        <div v-if="word.relations && word.relations.length > 0" class="space-y-4 mb-4">
          <div v-for="rel in groupedRelations" :key="`${rel.other_slug}-${rel.relation_type}`" class="flex items-baseline gap-4">
            <span class="text-[10px] font-medium text-stone-light uppercase w-24">{{ rel.relation_type }}</span>
            <NuxtLink :to="`/words/${rel.other_slug}`" class="font-serif text-lg text-forest hover:underline focus-ring rounded">{{ rel.other_headword }}</NuxtLink>
          </div>
        </div>
        <div v-else class="text-sm text-stone-light italic mb-4">No related words yet.</div>
        <button class="focus-ring btn btn-secondary btn-sm" @click="openRelationForm">+ Suggest a related word</button>

        <!-- Rich inline variation form -->
        <div v-if="relationFormOpen" class="mt-4 bg-cream-50 border border-cream-200 rounded-xl p-5">
          <div class="flex items-center justify-between mb-4">
            <p class="text-sm font-semibold text-ink">Suggest a variant of <span class="font-serif text-base text-forest">{{ word.headword }}</span></p>
            <button class="focus-ring text-stone hover:text-terracotta p-1 rounded" aria-label="Collapse form" @click="closeRelationForm">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" /></svg>
            </button>
          </div>
          <p class="text-xs text-stone mb-4 leading-relaxed">A variant is a different spelling, dialect form, or conjugation. Provide as much detail as you'd give a new word — it goes into the community review queue.</p>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div><label class="field-label">Variant word <span class="text-terracotta">*</span></label><input v-model="relationForm.headword" type="text" class="field" placeholder="e.g. bhaka" /></div>
            <div><label class="field-label">Relation type <span class="text-terracotta">*</span></label><select v-model="relationForm.relation_type" class="field"><option value="variant">Variant (different spelling/dialect)</option><option value="plural">Plural</option><option value="singular">Singular</option><option value="conjugation">Conjugation (different tense/person)</option><option value="antonym">Opposite</option><option value="derived">Derived from</option><option value="see_also">See also</option></select></div>
            <div><label class="field-label">Dialect</label><select v-model="relationForm.dialect" class="field"><option value="">— Any / Unknown —</option><option>Dawida</option><option>Sagala</option><option>Kasighau</option></select></div>
            <div><label class="field-label">Part of speech</label><select v-model="relationForm.part_of_speech" class="field"><option value="">— Skip —</option><option>noun</option><option>verb</option><option>adjective</option><option>adverb</option><option>phrase</option></select></div>
            <div><label class="field-label">Noun class</label><select v-model="relationForm.noun_class" class="field"><option value="">—</option><option>1/2 — person/people</option><option>3/4 — tree/things</option><option>5/6 — fruit/collective</option><option>7/8 — object/objects</option><option>9/10 — animal/animals</option><option>11 — long things</option><option>14 — abstraction</option><option>15 — infinitive</option></select></div>
            <div><label class="field-label">Swahili translation <span class="text-terracotta">*</span></label><input v-model="relationForm.swahili_translation" type="text" class="field" placeholder="mf. amekuja" /></div>
            <div class="md:col-span-2"><label class="field-label">English translation <span class="text-stone-light font-normal">(optional)</span></label><input v-model="relationForm.english_translation" type="text" class="field" placeholder="e.g. he/she has come" /></div>
            <div class="md:col-span-2"><label class="field-label">Literal translation <span class="text-stone-light font-normal">(optional)</span></label><input v-model="relationForm.literal_translation" type="text" class="field" placeholder="e.g. 'he has come hither'" /></div>
            <div class="md:col-span-2"><label class="field-label">Notes for reviewers <span class="text-stone-light font-normal">(optional)</span></label><textarea v-model="relationForm.rationale" rows="2" class="field" placeholder="Why does this variant belong here?"></textarea></div>
          </div>
          <div v-if="relationFormError" class="text-xs text-terracotta mb-3">{{ relationFormError }}</div>
          <div v-if="relationFormSuccess" class="text-xs text-forest mb-3">Suggestion submitted! It'll appear once the community votes on it.</div>
          <div class="flex items-center gap-3 pt-2 border-t border-cream-200">
            <button :disabled="relationFormSubmitting" class="focus-ring btn btn-primary btn-sm" @click="submitRelationSuggestion">{{ relationFormSubmitting ? 'Submitting...' : 'Submit suggestion' }}</button>
            <button class="focus-ring btn btn-ghost btn-sm" @click="closeRelationForm">Cancel</button>
            <p class="ml-auto text-[10px] text-stone-light">Goes into the community review queue.</p>
          </div>
        </div>
      </section>

      <footer class="py-10 border-t border-cream-200">
        <div class="flex flex-wrap items-center gap-x-4 gap-y-1 text-[10px] text-stone-light">
          <span>Entry ID: {{ word.id.slice(0, 8) }}...</span><span>·</span>
          <span>Added {{ formatDate(word.created_at) }}</span><span>·</span>
          <span>Status: {{ word.status }}</span>
        </div>
      </footer>
    </article>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import type { WordDetail } from '~/types'

const route = useRoute()
const router = useRouter()
const { isReviewer, isAdmin } = useAuth()

const { data: word, pending, error, refresh } = await useFetch<WordDetail>(
  () => `/api/words/${route.params.id}`,
  { watch: [() => route.params.id] },
)

const swahiliTranslation = computed(() => word.value?.translations?.find((g) => g.language === 'sw'))
const englishTranslation = computed(() => word.value?.translations?.find((g) => g.language === 'en'))
const groupedRelations = computed(() => {
  if (!word.value?.relations) return []
  const seen = new Set<string>()
  return word.value.relations.filter((rel) => {
    const key = `${rel.other_slug}-${rel.relation_type}`
    if (seen.has(key)) return false
    seen.add(key)
    return true
  })
})

// Edit form
const editFormOpen = ref(false)
const editFormSaving = ref(false)
const editFormError = ref('')
const editForm = reactive({ headword: '', dialect: '', part_of_speech: '', noun_class: '', swahili_translation: '', english_translation: '', literal_translation: '', morphology_notes: '' })

function openEditForm() {
  const sw = word.value?.translations?.find((g) => g.language === 'sw')
  const en = word.value?.translations?.find((g) => g.language === 'en')
  Object.assign(editForm, {
    headword: word.value?.headword || '', dialect: word.value?.dialect || '',
    part_of_speech: word.value?.part_of_speech || '', noun_class: word.value?.noun_class || '',
    swahili_translation: sw?.text || '', english_translation: en?.text || '',
    literal_translation: word.value?.literal_translation || '', morphology_notes: word.value?.morphology_notes || '',
  })
  editFormError.value = ''
  editFormOpen.value = true
}
function closeEditForm() { editFormOpen.value = false; editFormError.value = '' }

async function saveEdit() {
  editFormSaving.value = true; editFormError.value = ''
  try {
    await editWord(word.value!.id, {
      headword: editForm.headword.trim(),
      part_of_speech: editForm.part_of_speech || null,
      noun_class: editForm.noun_class || null,
      dialect: editForm.dialect || null,
      literal_translation: editForm.literal_translation || null,
      morphology_notes: editForm.morphology_notes || null,
      swahili_translation: editForm.swahili_translation || null,
      english_translation: editForm.english_translation || null,
    })
    await refresh()
    editFormOpen.value = false
  } catch (err: unknown) {
    const e = err as { response?: { _data?: { detail?: string } }; message?: string }
    editFormError.value = e.response?._data?.detail || 'Failed to save.'
  } finally { editFormSaving.value = false }
}

// Delete
const deleteConfirmOpen = ref(false)
const deleting = ref(false)
const deleteError = ref('')
function confirmDelete() { deleteConfirmOpen.value = true; deleteError.value = '' }
function cancelDelete() { deleteConfirmOpen.value = false; deleteError.value = '' }

async function doDelete() {
  deleting.value = true; deleteError.value = ''
  try {
    await deleteWord(word.value!.id)
    router.push('/search') // FIX: original used window.location.href (full reload)
  } catch (err: unknown) {
    const e = err as { response?: { _data?: { detail?: string } }; message?: string }
    deleteError.value = e.response?._data?.detail || 'Failed to delete.'
  } finally { deleting.value = false }
}

// Translation form
const translationFormOpen = ref(false)
const translationFormLanguage = ref('sw')
const translationFormText = ref('')
const translationFormSubmitting = ref(false)
const translationFormError = ref('')
const translationFormSuccess = ref(false)

function openTranslationForm(lang: string) {
  translationFormLanguage.value = lang; translationFormText.value = ''
  translationFormError.value = ''; translationFormSuccess.value = false; translationFormOpen.value = true
}
function closeTranslationForm() {
  translationFormOpen.value = false; translationFormText.value = ''
  translationFormError.value = ''; translationFormSuccess.value = false
}

async function submitTranslationSuggestion() {
  if (!translationFormText.value.trim()) { translationFormError.value = 'Please enter a translation.'; return }
  translationFormSubmitting.value = true; translationFormError.value = ''; translationFormSuccess.value = false
  try {
    await createSuggestion({
      target_type: 'translation', target_id: word.value!.id,
      proposed_value: { language: translationFormLanguage.value, text: translationFormText.value.trim() },
    })
    translationFormSuccess.value = true; translationFormText.value = ''
  } catch (err: unknown) {
    const e = err as { response?: { _data?: { detail?: string } }; message?: string }
    translationFormError.value = e.response?._data?.detail || 'Failed to submit.'
  } finally { translationFormSubmitting.value = false }
}

// Rich relation/variation form
const relationFormOpen = ref(false)
const relationFormSubmitting = ref(false)
const relationFormError = ref('')
const relationFormSuccess = ref(false)
const relationForm = reactive({
  headword: '', relation_type: 'variant', dialect: '', part_of_speech: '',
  noun_class: '', swahili_translation: '', english_translation: '', literal_translation: '', rationale: '',
})

function openRelationForm() {
  Object.assign(relationForm, {
    headword: '', relation_type: 'variant', dialect: '', part_of_speech: '',
    noun_class: '', swahili_translation: '', english_translation: '', literal_translation: '', rationale: '',
  })
  relationFormError.value = ''; relationFormSuccess.value = false; relationFormOpen.value = true
}
function closeRelationForm() {
  relationFormOpen.value = false; relationFormError.value = ''; relationFormSuccess.value = false
}

async function submitRelationSuggestion() {
  if (!relationForm.headword.trim()) { relationFormError.value = 'Please enter the variant word.'; return }
  if (!relationForm.swahili_translation.trim()) { relationFormError.value = 'Please enter the Swahili translation.'; return }
  relationFormSubmitting.value = true; relationFormError.value = ''; relationFormSuccess.value = false
  try {
    await createSuggestion({
      target_type: 'relation', target_id: word.value!.id,
      proposed_value: {
        related_word: relationForm.headword.trim(),
        relation_type: relationForm.relation_type,
        headword: relationForm.headword.trim(),
        part_of_speech: relationForm.part_of_speech || null,
        noun_class: relationForm.noun_class || null,
        dialect: relationForm.dialect || null,
        swahili_translation: relationForm.swahili_translation.trim(),
        english_translation: relationForm.english_translation.trim() || null,
        literal_translation: relationForm.literal_translation || null,
      },
      rationale: relationForm.rationale.trim() || null,
    })
    relationFormSuccess.value = true
    relationForm.headword = ''; relationForm.swahili_translation = ''
    relationForm.english_translation = ''; relationForm.literal_translation = ''; relationForm.rationale = ''
  } catch (err: unknown) {
    const e = err as { response?: { _data?: { detail?: string } }; message?: string }
    relationFormError.value = e.response?._data?.detail || 'Failed to submit.'
  } finally { relationFormSubmitting.value = false }
}

function formatDate(iso: string): string {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}
</script>

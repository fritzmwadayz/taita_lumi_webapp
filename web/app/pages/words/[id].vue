<template>
  <div>
    <!-- Back to search (above the flex container) -->
    <div class="max-w-[820px] mx-auto px-6 sm:px-8 pt-4">
      <NuxtLink to="/search" class="focus-ring inline-flex items-center gap-1.5 text-sm text-stone hover:text-forest rounded">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
        </svg>
        Back to search
      </NuxtLink>
    </div>

    <!-- Loading state -->
    <div v-if="pending" class="max-w-[680px] mx-auto px-8 py-24 text-center">
      <div class="animate-pulse">
        <div class="h-16 bg-cream-200 rounded w-1/2 mx-auto mb-4"></div>
        <div class="h-4 bg-cream-100 rounded w-1/3 mx-auto"></div>
      </div>
    </div>

    <!-- Error state -->
    <div v-else-if="error || !word" class="max-w-[680px] mx-auto px-8 py-24 text-center">
      <p class="font-serif text-3xl text-forest-dark mb-4">Word not found</p>
      <p class="text-sm text-stone mb-8">
        {{ error?.statusCode === 404 ? "This word doesn't exist or has been removed." : 'Failed to load word.' }}
      </p>
      <NuxtLink to="/search" class="focus-ring btn btn-primary btn-md">Back to search</NuxtLink>
    </div>

    <!-- ═════════════════════════════════════════════════════════════════ -->
    <!-- CONCEPT C — SCROLL STRIP                                          -->
    <!-- Inline action cluster in the header (scrolls with content) +      -->
    <!-- a slim sticky strip that slides down from the top of the viewport  -->
    <!-- when the user scrolls past the hero. The strip hides again when    -->
    <!-- the hero comes back into view. No mobile bottom bar.               -->
    <!-- ═════════════════════════════════════════════════════════════════ -->
    <div v-else class="max-w-[820px] mx-auto px-6 sm:px-8 pb-16">

      <!-- ─── Scroll strip (fixed at top, appears after hero scrolls away) ─── -->
      <!-- Always present in the DOM; translated off-screen when the hero is
           visible. pointer-events: none when hidden so it never blocks clicks. -->
      <div
        class="scroll-strip fixed top-0 left-0 right-0 z-30 bg-cream-50/95 backdrop-blur border-b border-cream-200 shadow-strip"
        :class="{ 'scroll-strip--hidden': !stripVisible }"
        aria-hidden="!stripVisible ? 'true' : 'false'"
      >
        <div class="max-w-[820px] mx-auto px-6 sm:px-8">
          <div class="max-w-[680px] mx-auto flex items-center justify-between py-2 gap-3">
            <!-- Compact headword recap -->
            <div class="flex items-baseline gap-2.5 min-w-0">
              <span class="font-serif text-lg text-forest-dark font-semibold truncate">{{ word.headword }}</span>
              <PosBadge v-if="word.part_of_speech" :pos="word.part_of_speech" />
              <span v-if="swahiliTranslation" class="hidden sm:inline text-xs text-stone truncate">— {{ swahiliTranslation.text }}</span>
            </div>
            <!-- Compact actions -->
            <div class="flex items-center gap-1 flex-shrink-0">
              <AudioPlaceholder size="sm" tooltip="No audio yet" />
              <span class="w-px h-4 bg-cream-200 mx-0.5"></span>
              <ShareButtons
                variant="bar"
                :headword="word.headword"
                :word-slug="word.slug"
              />
            </div>
          </div>
        </div>
      </div>

      <article class="max-w-[680px] mx-auto">

        <!-- ═══════════════════════════════════════════════════════════════ -->
        <!-- HEADER — word hero + inline action cluster                       -->
        <!-- ═══════════════════════════════════════════════════════════════ -->
        <header ref="heroHeader" class="pt-6 pb-2">
          <!-- Headword + reviewer actions -->
          <div class="flex items-baseline gap-4 mb-3">
            <h1 class="font-serif text-5xl sm:text-6xl text-forest-dark font-semibold tracking-tight">{{ word.headword }}</h1>
            <div v-if="isReviewer" class="ml-auto flex items-center gap-2">
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

          <!-- Delete confirm panel -->
          <div v-if="deleteConfirmOpen" class="bg-terracotta/10 border border-terracotta/30 rounded-xl p-5 mb-6">
            <p class="text-sm font-semibold text-ink mb-1">Delete this word?</p>
            <p class="text-xs text-stone mb-4">"{{ word.headword }}" will be hidden from the dictionary. This can be undone later.</p>
            <div v-if="deleteError" class="text-xs text-terracotta mb-3">{{ deleteError }}</div>
            <div class="flex gap-2">
              <button :disabled="deleting" class="focus-ring btn btn-danger btn-sm" @click="doDelete">{{ deleting ? 'Deleting...' : 'Yes, delete' }}</button>
              <button class="focus-ring btn btn-ghost btn-sm" @click="cancelDelete">Cancel</button>
            </div>
          </div>

          <!-- Edit word form (reviewer+ inline) -->
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

          <!-- POS / noun class / dialect row -->
          <div class="flex flex-wrap items-center gap-3 mb-3">
            <PosBadge v-if="word.part_of_speech" :pos="word.part_of_speech" />
            <span v-if="word.noun_class" class="nclass-badge">{{ word.noun_class }}</span>
            <template v-if="word.dialect">
              <span class="text-xs text-stone-light">·</span>
              <span class="text-xs text-stone">{{ word.dialect }} dialect</span>
            </template>
          </div>

          <!-- Compact word-level translations (summary) -->
          <div v-if="swahiliTranslation || englishTranslation" class="flex flex-wrap items-baseline gap-x-6 gap-y-1 mb-2">
            <div v-if="swahiliTranslation" class="flex items-baseline gap-1.5">
              <span class="text-[10px] font-bold text-forest uppercase tracking-wider">SW</span>
              <span class="font-serif text-base text-ink font-medium">{{ swahiliTranslation.text }}</span>
            </div>
            <div v-if="englishTranslation" class="flex items-baseline gap-1.5">
              <span class="text-[10px] font-bold text-terracotta uppercase tracking-wider">EN</span>
              <span class="font-serif text-sm text-ink-soft font-medium">{{ englishTranslation.text }}</span>
            </div>
          </div>
          <p v-else class="text-sm text-stone-light italic mb-2">No translations yet.</p>

          <!-- ─── Inline action cluster (Concept C — lives in the header) ─── -->
          <!-- Audio + share icons inline; scrolls with the page. The strip  -->
          <!-- above duplicates them when the user scrolls past this point.    -->
          <div class="flex items-center gap-1 py-1.5 mt-1 border-t border-cream-100">
            <AudioPlaceholder size="sm" tooltip="No audio yet" />
            <span class="hidden sm:inline text-[10px] text-stone-light ml-1 mr-2">No audio yet</span>
            <span class="w-px h-5 bg-cream-200 mx-1"></span>
            <ShareButtons
              variant="bar"
              :headword="word.headword"
              :word-slug="word.slug"
            />
          </div>
        </header>

        <!-- ═══════════════════════════════════════════════════════════════ -->
        <!-- MEANINGS SECTION (continuous numbered senses)                    -->
        <!-- ═══════════════════════════════════════════════════════════════ -->
        <section v-if="hasStructuredSenses" class="py-6 border-t border-cream-200">
          <div class="flex items-baseline justify-between mb-5">
            <h2 class="text-xs font-semibold uppercase tracking-widest text-stone">Meanings</h2>
            <button
              v-if="isReviewer && !addSenseFormOpen"
              class="focus-ring btn btn-secondary btn-sm"
              @click="openAddSenseForm"
            >
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
              </svg>
              Add sense
            </button>
          </div>

          <!-- Add-sense form (above the entries, when open) -->
          <Transition name="expand">
            <div v-if="addSenseFormOpen" class="mb-6">
              <SenseForm
                mode="add"
                :word-id="word.id"
                :headword="word.headword"
                :next-order-index="nextSenseOrderIndex"
                @saved="onSenseSaved"
                @cancel="closeAddSenseForm"
              />
            </div>
          </Transition>

          <!-- Sense entries — continuous numbered list, no boxed cards -->
          <div class="space-y-8">
            <div v-for="sense in word.senses" :key="sense.id">
              <div class="flex gap-4">
                <!-- Number badge -->
                <span class="sense-num flex-shrink-0">{{ sense.order_index }}</span>

                <!-- Body -->
                <div class="flex-1 min-w-0">
                  <!-- SenseForm (edit mode) replaces the body when editing -->
                  <SenseForm
                    v-if="editingSenseId === sense.id"
                    mode="edit"
                    :sense="sense"
                    :all-senses="word.senses"
                    @saved="onSenseSaved"
                    @cancel="closeSenseEdit"
                  />
                  <template v-else>
                    <!-- Definition line + pencil -->
                    <div class="flex items-start justify-between gap-3 mb-2">
                      <div class="flex-1 min-w-0">
                        <p v-if="sense.definition" class="font-serif text-lg text-ink italic leading-snug">{{ sense.definition }}</p>
                        <p v-else class="font-serif text-lg text-stone-light italic leading-snug">No definition recorded.</p>
                        <div class="flex items-center gap-2 mt-1.5 flex-wrap">
                          <PosBadge v-if="sense.part_of_speech" :pos="sense.part_of_speech" />
                          <p v-if="sense.notes" class="text-xs text-stone leading-relaxed">{{ sense.notes }}</p>
                        </div>
                      </div>
                      <!-- Pencil edit (reviewer+ only, hidden when another sense is being edited) -->
                      <button
                        v-if="isReviewer && editingSenseId !== sense.id"
                        class="focus-ring text-stone-light hover:text-forest p-1 rounded flex-shrink-0"
                        title="Edit sense"
                        @click="openSenseEdit(sense.id)"
                      >
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                        </svg>
                      </button>
                    </div>

                    <!-- Per-sense translations inline -->
                    <div v-if="sense.translations.length > 0" class="flex flex-wrap items-baseline gap-x-6 gap-y-1 mb-3">
                      <div
                        v-for="t in sense.translations"
                        :key="t.language"
                        class="flex items-baseline gap-2"
                      >
                        <span class="lang-chip" :class="t.language === 'sw' ? 'lang-sw' : 'lang-en'">{{ t.language === 'sw' ? 'SW' : 'EN' }}</span>
                        <p
                          class="font-serif font-medium"
                          :class="t.language === 'sw' ? 'text-base text-ink' : 'text-sm text-ink-soft'"
                        >{{ t.text }}</p>
                      </div>
                    </div>
                    <p v-else class="text-xs text-stone-light italic mb-3">No translations yet for this sense.</p>

                    <!-- Examples — indented quoted lines, no boxed cards -->
                    <div v-if="sense.examples.length > 0" class="mt-2 pl-4 border-l-2 border-cream-200 space-y-3">
                      <div v-for="ex in sense.examples" :key="ex.id">
                        <p class="font-serif text-base text-ink italic leading-snug">&ldquo;{{ ex.taita_text }}&rdquo;</p>
                        <p v-if="ex.swahili_text" class="text-xs text-stone mt-0.5">
                          <span class="font-semibold text-forest">SW:</span> {{ ex.swahili_text }}
                        </p>
                        <p v-if="ex.english_text" class="text-xs text-stone-light mt-0.5">
                          <span class="font-semibold text-terracotta">EN:</span> {{ ex.english_text }}
                        </p>
                        <p v-if="ex.source_ref" class="text-[10px] text-stone-light mt-0.5 italic">Source: {{ ex.source_ref }}</p>
                      </div>
                    </div>

                    <!-- Per-sense example button (when no examples) -->
                    <button
                      v-if="sense.examples.length === 0 && !exampleFormOpen"
                      class="focus-ring btn btn-ghost btn-sm text-forest mt-3"
                      @click="openExampleForm(sense.id)"
                    >
                      <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
                      </svg>
                      {{ isReviewer ? 'Add example sentence for this sense' : 'Suggest example sentence for this sense' }}
                    </button>
                  </template>
                </div>
              </div>
            </div>
          </div>

          <!-- ExampleForm (word-level, when open) -->
          <Transition name="expand">
            <div v-if="exampleFormOpen" class="mt-6">
              <ExampleForm
                :word-id="word.id"
                :senses="word.senses"
                :default-sense-id="exampleFormDefaultSenseId"
                :mode="isReviewer ? 'direct' : 'suggest'"
                @saved="onExampleSaved"
                @cancel="closeExampleForm"
              />
            </div>
          </Transition>

          <!-- Word-level action buttons -->
          <div class="mt-8 flex flex-wrap gap-2">
            <button
              v-if="!exampleFormOpen && !addSenseFormOpen"
              class="focus-ring btn btn-secondary btn-sm"
              @click="openExampleForm()"
            >
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
              </svg>
              {{ isReviewer ? 'Add example sentence' : 'Suggest example sentence' }}
            </button>
            <button
              v-if="!swahiliTranslation && !translationFormOpen"
              class="focus-ring btn btn-secondary btn-sm"
              @click="openTranslationForm('sw')"
            >+ Suggest Swahili translation</button>
            <button
              v-if="!englishTranslation && !translationFormOpen"
              class="focus-ring btn btn-secondary btn-sm"
              @click="openTranslationForm('en')"
            >+ Suggest English translation</button>
          </div>

          <!-- Translation suggestion form -->
          <div v-if="translationFormOpen" class="mt-4 bg-cream-50 border border-cream-200 rounded-lg p-4">
            <p class="text-xs font-semibold text-ink mb-3">Suggest {{ translationFormLanguage === 'sw' ? 'Swahili' : 'English' }} translation for "{{ word.headword }}"</p>
            <input
              v-model="translationFormText"
              type="text"
              class="field mb-3"
              :placeholder="translationFormLanguage === 'sw' ? 'mf. mlima, kilima' : 'e.g. mountain, hill'"
              @keyup.enter="submitTranslationSuggestion"
            />
            <div v-if="translationFormError" class="text-xs text-terracotta mb-2">{{ translationFormError }}</div>
            <div v-if="translationFormSuccess" class="text-xs text-forest mb-2">Suggestion submitted! It'll appear once the community votes on it.</div>
            <div class="flex gap-2">
              <button :disabled="translationFormSubmitting" class="focus-ring btn btn-primary btn-sm" @click="submitTranslationSuggestion">{{ translationFormSubmitting ? 'Submitting...' : 'Submit' }}</button>
              <button class="focus-ring btn btn-ghost btn-sm" @click="closeTranslationForm">Cancel</button>
            </div>
          </div>
        </section>

        <!-- ═══════════════════════════════════════════════════════════════ -->
        <!-- LEGACY FLAT TRANSLATIONS (fallback for single-sense words)       -->
        <!-- ═══════════════════════════════════════════════════════════════ -->
        <section v-else class="py-6 border-t border-cream-200">
          <!-- Examples (flat list) -->
          <div v-if="word.examples && word.examples.length > 0" class="mb-6">
            <h3 class="text-xs font-semibold uppercase tracking-widest text-stone mb-4">Example sentences</h3>
            <div class="pl-4 border-l-2 border-cream-200 space-y-3">
              <div v-for="ex in word.examples" :key="ex.id">
                <p class="font-serif text-base text-ink italic leading-snug">&ldquo;{{ ex.taita_text }}&rdquo;</p>
                <p v-if="ex.swahili_text" class="text-xs text-stone mt-0.5">
                  <span class="font-semibold text-forest">SW:</span> {{ ex.swahili_text }}
                </p>
                <p v-if="ex.english_text" class="text-xs text-stone-light mt-0.5">
                  <span class="font-semibold text-terracotta">EN:</span> {{ ex.english_text }}
                </p>
                <p v-if="ex.source_ref" class="text-[10px] text-stone-light mt-0.5 italic">Source: {{ ex.source_ref }}</p>
              </div>
            </div>
          </div>

          <!-- Action buttons -->
          <div class="mt-8 flex flex-wrap gap-2">
            <button
              v-if="!exampleFormOpen"
              class="focus-ring btn btn-secondary btn-sm"
              @click="openExampleForm()"
            >
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
              </svg>
              {{ isReviewer ? 'Add example sentence' : 'Suggest example sentence' }}
            </button>
            <button v-if="!swahiliTranslation && !translationFormOpen" class="focus-ring btn btn-secondary btn-sm" @click="openTranslationForm('sw')">+ Suggest Swahili translation</button>
            <button v-if="!englishTranslation && !translationFormOpen" class="focus-ring btn btn-secondary btn-sm" @click="openTranslationForm('en')">+ Suggest English translation</button>
          </div>

          <!-- ExampleForm (when open) -->
          <Transition name="expand">
            <div v-if="exampleFormOpen" class="mt-4">
              <ExampleForm
                :word-id="word.id"
                :senses="word.senses"
                :default-sense-id="exampleFormDefaultSenseId"
                :mode="isReviewer ? 'direct' : 'suggest'"
                @saved="onExampleSaved"
                @cancel="closeExampleForm"
              />
            </div>
          </Transition>

          <!-- Translation suggestion form -->
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

        <!-- ═══════════════════════════════════════════════════════════════ -->
        <!-- LITERAL TRANSLATION + MORPHOLOGY                                  -->
        <!-- ═══════════════════════════════════════════════════════════════ -->
        <section v-if="word.literal_translation" class="py-8 border-t border-cream-200">
          <h2 class="text-xs font-semibold uppercase tracking-widest text-stone mb-3">Literal translation</h2>
          <p class="font-serif text-base italic text-ink-soft mb-2">&ldquo;{{ word.literal_translation }}&rdquo;</p>
          <p v-if="word.morphology_notes" class="text-xs text-stone leading-relaxed">{{ word.morphology_notes }}</p>
        </section>

        <!-- ═══════════════════════════════════════════════════════════════ -->
        <!-- RELATED WORDS                                                    -->
        <!-- ═══════════════════════════════════════════════════════════════ -->
        <section class="py-8 border-t border-cream-200">
          <h2 class="text-xs font-semibold uppercase tracking-widest text-stone mb-6">Related words</h2>
          <div v-if="groupedRelations.length > 0" class="space-y-3 mb-4">
            <div v-for="rel in groupedRelations" :key="`${rel.other_slug}-${rel.relation_type}`" class="flex items-baseline gap-4">
              <span class="text-[10px] font-medium text-stone-light uppercase w-24 flex-shrink-0">{{ rel.relation_type }}</span>
              <NuxtLink :to="`/words/${rel.other_slug}`" class="font-serif text-lg text-forest hover:underline focus-ring rounded">{{ rel.other_headword }}</NuxtLink>
            </div>
          </div>
          <div v-else class="text-sm text-stone-light italic mb-4">No related words yet.</div>
          <button class="focus-ring btn btn-secondary btn-sm" @click="openRelationForm">+ Suggest a related word</button>

          <!-- Rich inline variation form -->
          <Transition name="expand">
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
                <div><label class="field-label">Relation type <span class="text-stone-light font-normal">(optional — leave blank if unsure)</span></label><select v-model="relationForm.relation_type" class="field"><option value="">— Not sure —</option><option value="variant">Variant — different spelling or dialect</option><option value="plural">Plural — more than one</option><option value="singular">Singular — one</option><option value="conjugation">Conjugation — different tense or form of a verb</option><option value="antonym">Antonym — opposite meaning</option><option value="derived">Derived from — comes from this word</option><option value="see_also">See also — related but different</option></select></div>
                <div><label class="field-label">Dialect</label><select v-model="relationForm.dialect" class="field"><option value="">— Any / Unknown —</option><option>Dawida</option><option>Sagala</option><option>Kasighau</option></select></div>
                <div><label class="field-label">Part of speech</label><select v-model="relationForm.part_of_speech" class="field"><option value="">— Skip —</option><option>noun</option><option>verb</option><option>adjective</option><option>adverb</option><option>phrase</option></select></div>
                <div><label class="field-label">Noun class</label><select v-model="relationForm.noun_class" class="field"><option value="">—</option><option>1/2 — person/people</option><option>3/4 — tree/things</option><option>5/6 — fruit/collective</option><option>7/8 — object/objects</option><option>9/10 — animal/animals</option><option>11 — long things</option><option>14 — abstraction</option><option>15 — infinitive</option></select></div>
                <div><label class="field-label">Swahili translation</label><input v-model="relationForm.swahili_translation" type="text" class="field" placeholder="mf. amekuja — enter * if unsure" /></div>
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
          </Transition>
        </section>

        <!-- ═══════════════════════════════════════════════════════════════ -->
        <!-- FOOTER                                                            -->
        <!-- ═══════════════════════════════════════════════════════════════ -->
        <footer class="py-10 border-t border-cream-200">
          <div class="flex flex-wrap items-center gap-x-4 gap-y-1 text-[10px] text-stone-light">
            <span>Entry ID: {{ word.id.slice(0, 8) }}...</span><span>·</span>
            <span>Added {{ formatDate(word.created_at) }}</span><span>·</span>
            <span>Status: {{ word.status }}</span>
          </div>
        </footer>
      </article>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import type { WordDetail } from '~/types'

const route = useRoute()
const router = useRouter()
const { isReviewer, isAdmin } = useAuth()

// ── Fetch word detail ───────────────────────────────────────────────────
const { data: word, pending, error, refresh } = await useFetch<WordDetail>(
  () => `/api/words/${route.params.id}`,
  { watch: [() => route.params.id] },
)

// ── Derived data ─────────────────────────────────────────────────────────
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

// ── Sense-aware rendering: structured vs flat fallback ───────────────────
// Structured = more than one sense, OR the single sense has a definition or
// notes. Otherwise collapse to the legacy flat SW/EN layout (avoids visual
// noise on legacy single-sense words).
const hasStructuredSenses = computed(() => {
  const senses = word.value?.senses
  if (!senses || senses.length === 0) return false
  if (senses.length > 1) return true
  const s = senses[0]
  return Boolean(s?.definition?.trim() || s?.notes?.trim())
})

// Next sense order_index = max(existing) + 1 (for the SenseForm add hint).
const nextSenseOrderIndex = computed(() => {
  const senses = word.value?.senses
  if (!senses || senses.length === 0) return 1
  return Math.max(...senses.map(s => s.order_index)) + 1
})

// ── Scroll strip: appears when the hero header scrolls out of view ───────
// IntersectionObserver watches the hero header element. When it leaves the
// top ~15% of the viewport, the strip slides down. When the hero scrolls
// back into view (e.g., user scrolls up), the strip hides again.
const heroHeader = ref<HTMLElement | null>(null)
const stripVisible = ref(false)
let stripObserver: IntersectionObserver | null = null

function setupStripObserver() {
  if (!heroHeader.value || typeof IntersectionObserver === 'undefined') return
  teardownStripObserver()
  // Negative bottom rootMargin shrinks the observation box to the top 15%
  // of the viewport. The strip appears as soon as the hero leaves that band.
  stripObserver = new IntersectionObserver(
    ([entry]) => {
      stripVisible.value = !entry.isIntersecting
    },
    { rootMargin: '0px 0px -85% 0px', threshold: 0 },
  )
  stripObserver.observe(heroHeader.value)
}

function teardownStripObserver() {
  if (stripObserver) {
    stripObserver.disconnect()
    stripObserver = null
  }
}

onMounted(() => {
  // Wait for the DOM to settle (useFetch may have resolved between mount
  // and the v-else branch rendering the header).
  nextTick(() => setupStripObserver())
})

onBeforeUnmount(() => {
  teardownStripObserver()
})

// Re-attach the observer whenever the loaded word changes (route param
// changes), so the strip resets for the new entry.
watch(
  () => word.value?.id,
  async () => {
    teardownStripObserver()
    stripVisible.value = false
    await nextTick()
    setupStripObserver()
  },
)

// ── Sense edit form state ────────────────────────────────────────────────
const editingSenseId = ref<string | null>(null)

function openSenseEdit(senseId: string) {
  editingSenseId.value = senseId
}
function closeSenseEdit() {
  editingSenseId.value = null
}

// ── Add-sense form state ─────────────────────────────────────────────────
const addSenseFormOpen = ref(false)

function openAddSenseForm() {
  // Close any other open forms to keep focus clear
  exampleFormOpen.value = false
  translationFormOpen.value = false
  addSenseFormOpen.value = true
}
function closeAddSenseForm() {
  addSenseFormOpen.value = false
}

// ── Example form state ───────────────────────────────────────────────────
const exampleFormOpen = ref(false)
const exampleFormDefaultSenseId = ref<string | null>(null)

function openExampleForm(senseId?: string) {
  // Close other open forms
  addSenseFormOpen.value = false
  translationFormOpen.value = false
  exampleFormDefaultSenseId.value = senseId ?? null
  exampleFormOpen.value = true
}
function closeExampleForm() {
  exampleFormOpen.value = false
  exampleFormDefaultSenseId.value = null
}

// ── Form-saved handlers (refresh the word detail + close the form) ───────
async function onSenseSaved() {
  editingSenseId.value = null
  addSenseFormOpen.value = false
  await refresh()
}

async function onExampleSaved() {
  exampleFormOpen.value = false
  exampleFormDefaultSenseId.value = null
  await refresh()
}

// ── Edit word form (reviewer+ edits word metadata) ───────────────────────
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

// ── Delete word (admin hide) ─────────────────────────────────────────────
const deleteConfirmOpen = ref(false)
const deleting = ref(false)
const deleteError = ref('')
function confirmDelete() { deleteConfirmOpen.value = true; deleteError.value = '' }
function cancelDelete() { deleteConfirmOpen.value = false; deleteError.value = '' }

async function doDelete() {
  deleting.value = true; deleteError.value = ''
  try {
    await deleteWord(word.value!.id)
    router.push('/search')
  } catch (err: unknown) {
    const e = err as { response?: { _data?: { detail?: string } }; message?: string }
    deleteError.value = e.response?._data?.detail || 'Failed to delete.'
  } finally { deleting.value = false }
}

// ── Translation suggestion form ──────────────────────────────────────────
const translationFormOpen = ref(false)
const translationFormLanguage = ref('sw')
const translationFormText = ref('')
const translationFormSubmitting = ref(false)
const translationFormError = ref('')
const translationFormSuccess = ref(false)

function openTranslationForm(lang: string) {
  // Close other open forms
  addSenseFormOpen.value = false
  exampleFormOpen.value = false
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

// ── Rich relation/variation suggestion form ──────────────────────────────
const relationFormOpen = ref(false)
const relationFormSubmitting = ref(false)
const relationFormError = ref('')
const relationFormSuccess = ref(false)
const relationForm = reactive({
  headword: '', relation_type: '', dialect: '', part_of_speech: '',
  noun_class: '', swahili_translation: '', english_translation: '', literal_translation: '', rationale: '',
})

function openRelationForm() {
  Object.assign(relationForm, {
    headword: '', relation_type: '', dialect: '', part_of_speech: '',
    noun_class: '', swahili_translation: '', english_translation: '', literal_translation: '', rationale: '',
  })
  relationFormError.value = ''; relationFormSuccess.value = false; relationFormOpen.value = true
}
function closeRelationForm() {
  relationFormOpen.value = false; relationFormError.value = ''; relationFormSuccess.value = false
}

async function submitRelationSuggestion() {
  if (!relationForm.headword.trim()) { relationFormError.value = 'Please enter the variant word.'; return }
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

// ── Helpers ──────────────────────────────────────────────────────────────
function formatDate(iso: string): string {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}
</script>

<style scoped>
/* ─── Numbered sense badge — same forest palette as the brand ─────────── */
.sense-num {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.75rem;
  height: 1.75rem;
  border-radius: 9999px;
  background: #2D5A3D;
  color: #FBF7F0;
  font-family: 'Source Serif 4', Georgia, serif;
  font-weight: 600;
  font-size: 0.875rem;
  flex-shrink: 0;
}

/* ─── Language chip — small colored square indicating language ────────── */
.lang-chip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 1.75rem;
  height: 1.5rem;
  padding: 0 0.35rem;
  border-radius: 0.25rem;
  font-size: 0.625rem;
  font-weight: 700;
  flex-shrink: 0;
}
.lang-sw { background: #E8F0EA; color: #1F4129; } /* forest tint / forest dark */
.lang-en { background: #F5DDD3; color: #A8492B; } /* terracotta tint / terracotta dark */

/* ─── Scroll strip — slide transition ─────────────────────────────────── */
/* The strip is always in the DOM (so the IntersectionObserver has a stable
   target to read). When `--hidden` is applied, it translates up and out of
   view, and pointer-events are disabled so it never blocks clicks while
   invisible. */
.scroll-strip {
  transition: transform 0.25s ease, opacity 0.2s ease;
  transform: translateY(0);
  opacity: 1;
}
.scroll-strip--hidden {
  transform: translateY(-100%);
  opacity: 0;
  pointer-events: none;
}

/* ─── Expand transition for the inline forms ───────────────────────────── */
.expand-enter-active,
.expand-leave-active {
  transition: opacity 0.2s ease, max-height 0.2s ease;
  overflow: hidden;
}
.expand-enter-from,
.expand-leave-to {
  opacity: 0;
  max-height: 0;
}
.expand-enter-to,
.expand-leave-from {
  opacity: 1;
  max-height: 2000px;
}
</style>

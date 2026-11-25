<template>
  <!-- ─────────────────────────────────────────────────────────────────────
       SuggestionChange — type-aware rendering of a suggestion's proposed_value.
       Shared by the review corrections tab, the open-queue cards, and the
       suggestion detail page so every surface renders changes consistently.

       variant="compact" → one-liner(s) for list cards
       variant="full"    → diff panel / detail block for the detail page
       ───────────────────────────────────────────────────────────────────── -->

  <!-- ═══ COMPACT ═══ -->
  <div v-if="variant === 'compact'" class="sgc-compact">
    <!-- Target word line -->
    <p v-if="showTargetLine && targetHeadword" class="text-sm text-ink mb-1">
      <template v-if="isRelation || isExample">On <NuxtLink :to="targetLink" class="text-forest hover:underline font-medium">{{ targetHeadword }}</NuxtLink></template>
      <template v-else>On <NuxtLink :to="targetLink" class="text-forest hover:underline font-medium">{{ targetHeadword }}</NuxtLink></template>
    </p>

    <!-- Translation update: SW/EN chip + current → proposed -->
    <p v-if="isTranslation" class="text-sm text-ink flex flex-wrap items-baseline gap-x-2 gap-y-1">
      <span class="sgc-chip" :class="lang === 'sw' ? 'sgc-lang-sw' : 'sgc-lang-en'">{{ lang === 'sw' ? 'SW' : 'EN' }}</span>
      <template v-if="currentText">
        <span class="font-serif text-base text-stone-light line-through">{{ currentText }}</span>
        <span class="sgc-arrow">→</span>
      </template>
      <span class="font-serif text-lg text-forest font-medium">{{ proposedText }}</span>
    </p>

    <!-- Word field correction: field label + current → proposed -->
    <p v-else-if="isFieldCorrection" class="text-sm text-ink flex flex-wrap items-baseline gap-x-2 gap-y-1">
      <span class="text-stone-dark font-medium">{{ fieldLabelText }}:</span>
      <template v-if="currentText">
        <span class="font-serif text-base text-stone-light line-through">{{ currentText }}</span>
        <span class="sgc-arrow">→</span>
      </template>
      <span class="font-serif text-lg text-forest font-medium">{{ proposedText }}</span>
    </p>

    <!-- Relation / variation: "Adds [type] headword + meta chips" -->
    <p v-else-if="isRelation" class="text-sm text-ink flex flex-wrap items-baseline gap-x-2 gap-y-1">
      Adds
      <span class="sgc-chip sgc-rel">{{ relationLabel }}</span>
      <span class="font-serif text-lg text-forest-dark font-semibold">{{ relatedHeadword }}</span>
      <span v-if="relationMeta.pos" class="sgc-chip sgc-meta">{{ relationMeta.pos }}</span>
      <span v-if="relationMeta.nounClass" class="sgc-chip sgc-meta">{{ relationMeta.nounClass }}</span>
      <span v-if="relationMeta.dialect" class="sgc-chip sgc-meta">{{ relationMeta.dialect }}</span>
      <span v-if="relationMeta.sw" class="text-xs text-stone">SW: {{ relationMeta.sw }}</span>
    </p>

    <!-- Example: quoted sentence + SW -->
    <p v-else-if="isExample" class="text-sm text-ink">
      Adds <span class="font-serif text-base text-ink italic">“{{ exampleFields.taitaText }}”</span>
      <span v-if="exampleFields.swahili" class="text-xs text-stone ml-1">SW: {{ exampleFields.swahili }}</span>
    </p>

    <!-- New word: mini entry -->
    <template v-else-if="isNewWord">
      <p class="text-sm text-ink flex flex-wrap items-baseline gap-x-2 gap-y-1">
        <span class="font-serif text-lg text-forest-dark font-semibold">{{ newWordFields.headword }}</span>
        <span v-if="newWordFields.pos" class="sgc-chip sgc-meta">{{ newWordFields.pos }}</span>
        <span v-if="newWordFields.dialect" class="sgc-chip sgc-meta">{{ newWordFields.dialect }}</span>
      </p>
      <p v-if="newWordFields.sw" class="text-xs text-ink-soft">{{ newWordFields.sw }} <span class="text-stone-light">(Kiswahili)</span></p>
      <p v-if="newWordFields.en" class="text-xs text-stone">{{ newWordFields.en }}</p>
    </template>

    <!-- Unknown shape: raw JSON fallback -->
    <p v-else class="text-xs text-stone break-all">{{ fallbackJson }}</p>
  </div>

  <!-- ═══ FULL ═══ -->
  <div v-else class="sgc-full">
    <!-- Before → after diff (only when we know the current value) -->
    <div v-if="showDiff" class="sgc-diff">
      <div class="sgc-col sgc-col-current">
        <h5>Current · {{ diffLabel }}</h5>
        <p v-if="currentText" class="font-serif text-lg text-stone">{{ currentText }}</p>
        <p v-else class="text-sm text-stone-light italic">None yet</p>
      </div>
      <div class="sgc-mid" aria-hidden="true">→</div>
      <div class="sgc-col sgc-col-proposed">
        <h5>Proposed</h5>
        <p class="font-serif text-lg text-forest-dark font-semibold">{{ proposedText }}</p>
      </div>
    </div>

    <!-- Relation / variation block -->
    <div v-else-if="isRelation" class="sgc-block">
      <p class="flex flex-wrap items-baseline gap-x-2 gap-y-1 mb-2">
        <span class="sgc-chip sgc-rel">{{ relationLabel }}</span>
        <span class="font-serif text-2xl text-forest-dark font-semibold">{{ relatedHeadword }}</span>
        <span v-if="relationMeta.pos" class="sgc-chip sgc-meta">{{ relationMeta.pos }}</span>
        <span v-if="relationMeta.nounClass" class="sgc-chip sgc-meta">{{ relationMeta.nounClass }}</span>
        <span v-if="relationMeta.dialect" class="sgc-chip sgc-meta">{{ relationMeta.dialect }}</span>
      </p>
      <p v-if="relationMeta.sw" class="text-sm text-ink mb-1"><span class="sgc-chip sgc-lang-sw">SW</span> <span class="font-serif text-base">{{ relationMeta.sw }}</span></p>
      <p v-if="relationMeta.en" class="text-sm text-ink-soft mb-1"><span class="sgc-chip sgc-lang-en">EN</span> <span class="font-serif text-base">{{ relationMeta.en }}</span></p>
      <p v-if="relationMeta.literal" class="text-xs text-stone italic">Literal: {{ relationMeta.literal }}</p>
      <p v-if="targetHeadword" class="text-xs text-stone-light mt-3">
        Will be linked from “<NuxtLink :to="targetLink" class="text-forest hover:underline font-medium">{{ targetHeadword }}</NuxtLink>” as <b>{{ relationLabel.toLowerCase() }}</b> when accepted. If the related word doesn't exist yet, accepting creates it first.
      </p>
    </div>

    <!-- Example block -->
    <div v-else-if="isExample" class="sgc-block">
      <p class="font-serif text-lg text-ink italic mb-2">“{{ exampleFields.taitaText }}”</p>
      <p v-if="exampleFields.swahili" class="text-sm text-stone"><span class="sgc-chip sgc-lang-sw">SW</span> {{ exampleFields.swahili }}</p>
      <p v-if="exampleFields.english" class="text-sm text-stone-light"><span class="sgc-chip sgc-lang-en">EN</span> {{ exampleFields.english }}</p>
      <p v-if="exampleFields.source" class="text-xs text-stone-light italic mt-1">Source: {{ exampleFields.source }}</p>
    </div>

    <!-- New word block -->
    <div v-else-if="isNewWord" class="sgc-block">
      <p class="flex flex-wrap items-baseline gap-x-2 gap-y-1 mb-2">
        <span class="font-serif text-2xl text-forest-dark font-semibold">{{ newWordFields.headword }}</span>
        <span v-if="newWordFields.pos" class="sgc-chip sgc-meta">{{ newWordFields.pos }}</span>
        <span v-if="newWordFields.dialect" class="sgc-chip sgc-meta">{{ newWordFields.dialect }}</span>
      </p>
      <p v-if="newWordFields.sw" class="text-sm text-ink mb-1"><span class="sgc-chip sgc-lang-sw">SW</span> <span class="font-serif text-base">{{ newWordFields.sw }}</span></p>
      <p v-if="newWordFields.en" class="text-sm text-ink-soft mb-1"><span class="sgc-chip sgc-lang-en">EN</span> <span class="font-serif text-base">{{ newWordFields.en }}</span></p>
      <p v-if="newWordFields.literal" class="text-xs text-stone italic">Literal: {{ newWordFields.literal }}</p>
    </div>

    <!-- Fallback (unknown shape, no diff available) -->
    <div v-else class="sgc-block">
      <p class="text-sm text-stone-dark mb-1"><b>{{ fieldLabelText || 'Proposed' }}:</b></p>
      <p class="font-serif text-lg text-forest-dark font-semibold">{{ proposedText }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { SuggestionTargetType, WordDetail } from '~/types'

// ── Props ─────────────────────────────────────────────────────────────────
const props = withDefaults(defineProps<{
  targetType: SuggestionTargetType | string
  fieldPath?: string | null
  proposedValue: unknown
  /** Enrichment: the targeted word's detail (for headword + current values). */
  currentWord?: WordDetail | null
  targetId?: string | null
  variant?: 'compact' | 'full'
  /** Compact variant only: render the "On <headword>" line. */
  showTargetLine?: boolean
}>(), {
  fieldPath: null,
  currentWord: null,
  targetId: null,
  variant: 'compact',
  showTargetLine: false,
})

// ── Type buckets ──────────────────────────────────────────────────────────
const RELATION_TYPES = ['relation', 'variation', 'relationship']
const isRelation = computed(() => RELATION_TYPES.includes(props.targetType as string))
const isExample = computed(() => props.targetType === 'example' || props.targetType === 'new_example')
const isNewWord = computed(() => props.targetType === 'new_word')
const isFieldCorrection = computed(() => props.targetType === 'word')
// 'translation' today; 'gloss' is the v1.3 legacy alias (kept for in-flight suggestions).
const isTranslation = computed(() => {
  if (props.targetType === 'translation' || props.targetType === 'gloss') return true
  return props.fieldPath === 'gloss' && lang.value !== null
})

// ── Proposed value extraction ─────────────────────────────────────────────
const pv = computed<Record<string, unknown>>(() =>
  (props.proposedValue && typeof props.proposedValue === 'object' && !Array.isArray(props.proposedValue))
    ? props.proposedValue as Record<string, unknown>
    : {},
)

const lang = computed<string | null>(() => {
  const l = pv.value.language
  return typeof l === 'string' ? l : null
})

const proposedText = computed<string>(() => {
  if (typeof props.proposedValue === 'string') return props.proposedValue
  if (isTranslation.value) {
    const t = pv.value.text
    return typeof t === 'string' ? t : ''
  }
  // Field corrections may carry {value}, bare text, or the field name itself.
  if (typeof pv.value.value === 'string') return pv.value.value
  if (props.fieldPath && typeof pv.value[props.fieldPath] === 'string') return pv.value[props.fieldPath] as string
  if (typeof pv.value.text === 'string') return pv.value.text
  if (typeof pv.value.headword === 'string') return pv.value.headword
  return ''
})

// ── Current value (from the enriched target word) ─────────────────────────
const currentText = computed<string | null>(() => {
  const w = props.currentWord
  if (!w) return null
  if (isTranslation.value) {
    return w.translations?.find(t => t.language === (lang.value || 'sw'))?.text ?? null
  }
  if (isFieldCorrection.value && props.fieldPath) {
    return wordFieldValue(w, props.fieldPath)
  }
  return null
})

/** Read a (legacy-aliased) field off a WordDetail. Returns null for unknown paths. */
function wordFieldValue(w: WordDetail, path: string): string | null {
  const p = path.toLowerCase()
  if (p === 'swahili_translation' || p === 'swahili_gloss') return w.translations?.find(t => t.language === 'sw')?.text ?? null
  if (p === 'english_translation' || p === 'english_gloss') return w.translations?.find(t => t.language === 'en')?.text ?? null
  if (p === 'gloss') return w.translations?.find(t => t.language === 'sw')?.text ?? null
  switch (p) {
    case 'headword': return w.headword
    case 'part_of_speech': return w.part_of_speech
    case 'noun_class': return w.noun_class
    case 'dialect': return w.dialect
    case 'literal_translation': return w.literal_translation
    case 'morphology_notes': return w.morphology_notes
    case 'definition': return w.senses?.[0]?.definition ?? null
    case 'notes': return w.senses?.[0]?.notes ?? null
    default: return null
  }
}

// ── Field label (humanized, legacy aliases normalized) ────────────────────
const FIELD_LABELS: Record<string, string> = {
  headword: 'Headword',
  part_of_speech: 'Part of speech',
  noun_class: 'Noun class',
  dialect: 'Dialect',
  literal_translation: 'Literal translation',
  morphology_notes: 'Morphology notes',
  swahili_translation: 'Swahili translation',
  english_translation: 'English translation',
  swahili_gloss: 'Swahili translation',
  english_gloss: 'English translation',
  gloss: 'Translation',
  definition: 'Definition',
  notes: 'Notes',
}
const fieldLabelText = computed(() => props.fieldPath ? (FIELD_LABELS[props.fieldPath.toLowerCase()] || props.fieldPath) : '')
const diffLabel = computed(() => isTranslation.value ? (lang.value === 'en' ? 'English translation' : 'Swahili translation') : fieldLabelText.value)

// ── Relation rendering ────────────────────────────────────────────────────
const RELATION_LABELS: Record<string, string> = {
  variant: 'Variant', plural: 'Plural', singular: 'Singular', conjugation: 'Conjugation',
  diminutive: 'Diminutive', augmentative: 'Augmentative',
  antonym: 'Antonym', synonym: 'Synonym', see_also: 'See also', derived: 'Derived from', etymological: 'Etymological',
}
const relationLabel = computed(() => {
  const t = typeof pv.value.relation_type === 'string' ? pv.value.relation_type : ''
  return RELATION_LABELS[t] || (t ? t.replace(/_/g, ' ') : 'Variant')
})
const relatedHeadword = computed(() => {
  const rw = pv.value.related_word
  const hw = pv.value.headword
  return (typeof rw === 'string' && rw) || (typeof hw === 'string' && hw) || '—'
})
const relationMeta = computed(() => ({
  pos: str(pv.value.part_of_speech),
  nounClass: str(pv.value.noun_class),
  dialect: str(pv.value.dialect),
  sw: str(pv.value.swahili_translation),
  en: str(pv.value.english_translation),
  literal: str(pv.value.literal_translation),
}))

// ── Example rendering ─────────────────────────────────────────────────────
const exampleFields = computed(() => ({
  taitaText: str(pv.value.taita_text) || '—',
  swahili: str(pv.value.swahili_text),
  english: str(pv.value.english_text),
  source: str(pv.value.source_ref),
}))

// ── New word rendering ────────────────────────────────────────────────────
const newWordFields = computed(() => ({
  headword: str(pv.value.headword) || '—',
  pos: str(pv.value.part_of_speech),
  dialect: str(pv.value.dialect),
  sw: str(pv.value.swahili_translation),
  en: str(pv.value.english_translation),
  literal: str(pv.value.literal_translation),
}))

function str(v: unknown): string | null {
  return typeof v === 'string' && v.trim() ? v : null
}

// ── Diff visibility (full variant) ────────────────────────────────────────
const showDiff = computed(() =>
  (isTranslation.value || isFieldCorrection.value) && props.currentWord !== null,
)

// ── Target word link ──────────────────────────────────────────────────────
const targetHeadword = computed(() => props.currentWord?.headword ?? null)
const targetLink = computed(() =>
  props.currentWord ? `/words/${props.currentWord.slug || props.currentWord.id}` : (props.targetId ? `/words/${props.targetId}` : '#'),
)

// ── Fallback ──────────────────────────────────────────────────────────────
const fallbackJson = computed(() => JSON.stringify(props.proposedValue))
</script>

<style scoped>
.sgc-arrow { color: #9CA3AF; font-size: 14px; }

/* Chips — mirror the word page's lang-chip / PosBadge palette */
.sgc-chip {
  display: inline-flex; align-items: center;
  min-width: 1.6rem; height: 1.35rem; padding: 0 0.4rem;
  border-radius: 0.25rem; font-size: 0.625rem; font-weight: 700;
  flex-shrink: 0; letter-spacing: 0.03em;
}
.sgc-lang-sw { background: #E8F0EA; color: #1F4129; } /* forest tint / dark */
.sgc-lang-en { background: #F5DDD3; color: #A8492B; } /* terracotta tint / dark */
.sgc-meta { background: #F5EFE3; color: #4B5563; border: 1px solid #E8DFC8; font-weight: 600; }
.sgc-rel { background: #F7EBD3; color: #8C6A2F; }     /* ochre tint / dark */

/* Full-variant diff panel */
.sgc-diff { display: flex; gap: 12px; align-items: stretch; flex-wrap: wrap; }
.sgc-col {
  flex: 1 1 200px; min-width: 0;
  background: #FDFBF6; border: 1px solid #E8DFC8; border-radius: 10px;
  padding: 12px 14px;
}
.sgc-col-proposed { border-color: #2D5A3D; background: #F0F7F1; }
.sgc-col h5 { margin: 0 0 6px; font-size: 10px; text-transform: uppercase; letter-spacing: 0.1em; color: #9CA3AF; font-weight: 700; }
.sgc-col-proposed h5 { color: #1F4129; }
.sgc-mid { align-self: center; color: #9CA3AF; font-size: 18px; }
@media (max-width: 560px) {
  .sgc-mid { transform: rotate(90deg); margin: -6px auto; }
}

/* Full-variant block (additive changes) */
.sgc-block {
  background: #FDFBF6; border: 1px solid #E8DFC8; border-radius: 10px;
  padding: 16px;
}
</style>

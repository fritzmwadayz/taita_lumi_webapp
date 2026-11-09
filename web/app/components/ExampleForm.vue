<template>
  <div class="bg-cream-50 border border-cream-200 rounded-xl p-6">
    <!-- Header -->
    <div class="flex items-center justify-between mb-4">
      <p class="text-sm font-semibold text-ink">
        {{ mode === 'direct' ? 'Add an example sentence' : 'Suggest an example sentence' }}
      </p>
      <button
        class="focus-ring text-stone hover:text-terracotta p-1 rounded"
        aria-label="Collapse form"
        @click="$emit('cancel')"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    <p class="text-xs text-stone mb-4 leading-relaxed">
      An example shows how the word is used in context. Taita and Swahili are required —
      English is optional. {{ mode === 'direct'
        ? 'Goes live immediately.'
        : 'Goes into the community review queue.' }}
    </p>

    <!-- Honeypot — visually hidden via CSS, NOT display:none, so bots fill it. -->
    <input
      v-model="honeypot"
      type="text"
      name="website"
      style="position: absolute; left: -9999px; opacity: 0; pointer-events: none"
      tabindex="-1"
      autocomplete="off"
      aria-hidden="true"
    />

    <!-- Form fields -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
      <!-- Taita sentence (required) -->
      <div class="md:col-span-2">
        <label class="field-label">Taita sentence <span class="text-terracotta">*</span></label>
        <input
          v-model="form.taita_text"
          type="text"
          class="field"
          :class="{ 'field-error': errors.taita_text }"
          placeholder="e.g. Mlima u mrefu sana."
          :disabled="submitting"
          @keyup.enter="submit"
        />
        <p v-if="errors.taita_text" class="text-[10px] text-terracotta mt-1">{{ errors.taita_text }}</p>
      </div>
      <!-- Swahili translation (required) -->
      <div>
        <label class="field-label">Swahili translation <span class="text-terracotta">*</span></label>
        <input
          v-model="form.swahili_text"
          type="text"
          class="field"
          :class="{ 'field-error': errors.swahili_text }"
          placeholder="Mlima ni mrefu sana..."
          :disabled="submitting"
        />
        <p v-if="errors.swahili_text" class="text-[10px] text-terracotta mt-1">{{ errors.swahili_text }}</p>
      </div>
      <!-- English translation (optional) -->
      <div>
        <label class="field-label">English translation <span class="text-stone-light font-normal">(optional)</span></label>
        <input
          v-model="form.english_text"
          type="text"
          class="field"
          placeholder="The mountain is very tall..."
          :disabled="submitting"
        />
      </div>
      <!-- Sense selector — only show if the word has more than one sense -->
      <div v-if="senses.length > 1">
        <label class="field-label">Sense <span class="text-stone-light font-normal">(which meaning)</span></label>
        <select v-model="form.sense_id" class="field" :disabled="submitting">
          <option
            v-for="sense in senses"
            :key="sense.id"
            :value="sense.id"
          >Sense {{ sense.order_index }} — {{ senseLabel(sense) }}</option>
        </select>
      </div>
      <div :class="senses.length > 1 ? '' : 'md:col-span-2'">
        <label class="field-label">Source reference <span class="text-stone-light font-normal">(optional)</span></label>
        <input
          v-model="form.source_ref"
          type="text"
          class="field"
          placeholder="e.g. Mwadime 1987, p.42"
          :disabled="submitting"
        />
      </div>
    </div>

    <!-- Error / success messaging -->
    <div v-if="error" class="text-xs text-terracotta mb-3 bg-terracotta-wash border border-terracotta/30 rounded-md px-3 py-2">
      {{ error }}
    </div>
    <div v-if="successMessage" class="text-xs text-forest mb-3 bg-forest-wash border border-forest/30 rounded-md px-3 py-2">
      {{ successMessage }}
    </div>

    <!-- Actions -->
    <div class="flex items-center gap-3 pt-3 border-t border-cream-200">
      <button
        :disabled="submitting"
        class="focus-ring btn btn-primary btn-sm"
        @click="submit"
      >{{ submitting ? 'Saving...' : (mode === 'direct' ? 'Save example sentence' : 'Submit suggestion') }}</button>
      <button
        :disabled="submitting"
        class="focus-ring btn btn-ghost btn-sm"
        @click="$emit('cancel')"
      >Cancel</button>
      <p class="ml-auto text-[10px] text-stone-light">
        {{ mode === 'direct' ? 'Goes live immediately — reviewer action.' : 'Community vote needed before it appears.' }}
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import type { Sense } from '~/types'

const props = withDefaults(defineProps<{
  wordId: string
  /** The word's senses — used to populate the sense selector dropdown. */
  senses: Sense[]
  /** Optional default sense ID (e.g. when "Add example for this sense" is clicked). */
  defaultSenseId?: string | null
  /** 'direct' (reviewer+: POST /api/words/:id/examples, goes live immediately)
   *  or 'suggest' (anyone: POST /api/suggestions with target_type='new_example',
   *  goes to the review queue). */
  mode?: 'direct' | 'suggest'
}>(), {
  defaultSenseId: null,
  mode: 'direct',
})

const emit = defineEmits<{
  /** Saved successfully — caller should refresh the word detail (direct mode)
   *  or just close the form (suggest mode, suggestion is in the queue). */
  saved: []
  /** Cancel button clicked. */
  cancel: []
}>()

const toast = useToast()

// ── Form state ────────────────────────────────────────────────────────────
const honeypot = ref('')
const submitting = ref(false)
const error = ref('')
const successMessage = ref('')

const form = reactive({
  taita_text: '',
  swahili_text: '',
  english_text: '',
  source_ref: '',
  sense_id: (props.defaultSenseId ?? props.senses[0]?.id ?? null) as string | null,
})

// Per-field validation errors
const errors = reactive<{ taita_text: string; swahili_text: string }>({
  taita_text: '',
  swahili_text: '',
})

function senseLabel(s: Sense): string {
  const def = s.definition?.trim()
  if (def && def.length > 60) return def.slice(0, 57) + '...'
  if (def) return def
  return s.notes?.trim().slice(0, 60) || 'no definition'
}

// ── Validation ────────────────────────────────────────────────────────────
function validate(): boolean {
  errors.taita_text = ''
  errors.swahili_text = ''
  let ok = true
  if (!form.taita_text.trim()) {
    errors.taita_text = 'Please enter the Taita sentence.'
    ok = false
  }
  if (!form.swahili_text.trim()) {
    errors.swahili_text = 'Swahili translation is required.'
    ok = false
  }
  return ok
}

// ── Submit ────────────────────────────────────────────────────────────────
async function submit() {
  error.value = ''
  successMessage.value = ''

  if (!validate()) return

  // Honeypot tripped — silently "succeed" without sending (matches contribute.vue pattern)
  if (honeypot.value) {
    emit('saved')
    return
  }

  submitting.value = true
  try {
    const payload = {
      taita_text: form.taita_text.trim(),
      swahili_text: form.swahili_text.trim(),
      english_text: form.english_text.trim() || null,
      source_ref: form.source_ref.trim() || null,
      sense_id: form.sense_id || null,
    }

    if (props.mode === 'direct') {
      // Reviewer+: direct add, goes live immediately
      await addExample(props.wordId, payload)
      toast.success('Example sentence added')
    } else {
      // Anyone: suggestion queue, target_type='new_example'
      await createSuggestion({
        target_type: 'new_example',
        target_id: props.wordId,
        proposed_value: payload,
      })
      toast.success('Suggestion submitted')
    }
    emit('saved')
  } catch (err: unknown) {
    const e = err as { response?: { status?: number; _data?: { detail?: string } }; message?: string }
    if (e.response?.status === 403) {
      error.value = 'Reviewer access required to add examples directly.'
    } else if (e.response?.status === 404) {
      error.value = 'This word could not be found. It may have been removed.'
    } else if (e.response?.status === 429) {
      error.value = 'Rate limit exceeded. Try again later or sign in for a higher limit.'
    } else {
      error.value = e.response?._data?.detail || 'Failed to save. Please try again.'
    }
  } finally {
    submitting.value = false
  }
}
</script>

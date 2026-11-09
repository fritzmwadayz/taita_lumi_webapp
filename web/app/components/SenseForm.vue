<template>
  <div class="bg-white border border-cream-300 rounded-lg p-4">
    <!-- Header -->
    <div class="flex items-center justify-between mb-4">
      <p class="text-xs font-semibold text-ink">
        <template v-if="mode === 'add'">
          Add a new sense for <span class="font-serif text-base text-forest">{{ headword }}</span>
        </template>
        <template v-else>
          Edit sense #{{ form.order_index }}
        </template>
      </p>
      <button
        class="focus-ring text-stone hover:text-terracotta p-1 rounded"
        aria-label="Close form"
        @click="$emit('cancel')"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    <!-- Hint text -->
    <p v-if="mode === 'add'" class="text-xs text-stone mb-4 leading-relaxed">
      A sense is a distinct meaning of the word. Use it when the same headword has multiple unrelated
      meanings, different parts of speech, or regional variation.
      <span v-if="nextOrderIndex" class="block text-stone-light mt-1">This will be sense #{{ nextOrderIndex }}.</span>
    </p>

    <!-- Fields -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
      <div>
        <label class="field-label">Part of speech <span class="text-stone-light font-normal">(optional)</span></label>
        <select v-model="form.part_of_speech" class="field" :disabled="submitting">
          <option value="">— Same as word —</option>
          <option value="noun">noun</option>
          <option value="verb">verb</option>
          <option value="adjective">adjective</option>
          <option value="adverb">adverb</option>
          <option value="phrase">phrase</option>
        </select>
      </div>
      <!-- Order field — only visible in edit mode. Warn about uniqueness. -->
      <div v-if="mode === 'edit'">
        <label class="field-label">Order <span class="text-stone-light font-normal">(rarely changed)</span></label>
        <input
          v-model.number="form.order_index"
          type="number"
          min="1"
          class="field"
          :disabled="submitting"
        />
        <p v-if="orderConflict" class="text-[10px] text-terracotta mt-1">
          Another sense already uses this number — backend will reject it.
        </p>
      </div>
      <div class="md:col-span-2">
        <label class="field-label">Definition <span class="text-stone-light font-normal">(optional, max 500 chars)</span></label>
        <input
          v-model="form.definition"
          type="text"
          class="field"
          :placeholder="mode === 'add' ? 'e.g. Figurative — a difficulty or challenge to overcome.' : ''"
          :disabled="submitting"
          maxlength="500"
        />
      </div>
      <div class="md:col-span-2">
        <label class="field-label">Notes for reviewers <span class="text-stone-light font-normal">(optional)</span></label>
        <textarea
          v-model="form.notes"
          rows="2"
          class="field"
          placeholder="Usage context, dialect notes, source..."
          :disabled="submitting"
          maxlength="2000"
        ></textarea>
      </div>
    </div>

    <!-- Next-step hint (add mode only — new senses start empty) -->
    <div v-if="mode === 'add'" class="bg-ochre-wash border border-ochre/30 rounded-lg p-3 mb-3 text-xs text-ink-soft leading-relaxed">
      <p class="font-semibold text-ochre-dark mb-1">After adding this sense:</p>
      <ul class="list-disc list-inside space-y-0.5 text-stone">
        <li>Use "+ Add example" to attach example sentences to it.</li>
        <li>Use "+ Suggest a translation" to add SW/EN translations (currently only via the suggestion flow).</li>
      </ul>
    </div>

    <!-- Error -->
    <div v-if="error" class="text-xs text-terracotta mb-3 bg-terracotta-wash border border-terracotta/30 rounded-md px-3 py-2">
      {{ error }}
    </div>

    <!-- Actions -->
    <div class="flex items-center gap-2 pt-3 border-t border-cream-200">
      <button
        :disabled="submitting || orderConflict"
        class="focus-ring btn btn-primary btn-sm"
        @click="submit"
      >{{ submitting ? 'Saving...' : mode === 'add' ? 'Add sense' : 'Save changes' }}</button>
      <button
        :disabled="submitting"
        class="focus-ring btn btn-ghost btn-sm"
        @click="$emit('cancel')"
      >Cancel</button>
      <p v-if="mode === 'edit'" class="ml-auto text-[10px] text-stone-light">
        Other fields (translations, examples) are edited separately.
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import type { Sense } from '~/types'

type Mode = 'add' | 'edit'

const props = withDefaults(defineProps<{
  mode: Mode
  /** For add mode: the word ID and headword (display + API call). */
  wordId?: string
  headword?: string
  /** For add mode: the next order_index (max(existing) + 1) — shown as a hint. */
  nextOrderIndex?: number
  /** For edit mode: the sense being edited. */
  sense?: Sense | null
  /** For edit mode: all senses (used to validate order_index uniqueness). */
  allSenses?: Sense[]
}>(), {
  wordId: '',
  headword: '',
  nextOrderIndex: 0,
  sense: null,
  allSenses: () => [],
})

const emit = defineEmits<{
  saved: []
  cancel: []
}>()

const toast = useToast()

// ── Form state ────────────────────────────────────────────────────────────
const submitting = ref(false)
const error = ref('')

const form = reactive({
  order_index: 0,
  part_of_speech: '',
  definition: '',
  notes: '',
})

// Initialize form fields based on mode
function initForm() {
  if (props.mode === 'edit' && props.sense) {
    form.order_index = props.sense.order_index
    form.part_of_speech = props.sense.part_of_speech || ''
    form.definition = props.sense.definition || ''
    form.notes = props.sense.notes || ''
  } else {
    // Add mode
    form.order_index = props.nextOrderIndex || 1
    form.part_of_speech = ''
    form.definition = ''
    form.notes = ''
  }
  error.value = ''
}

// Run on setup + when the sense prop changes (e.g. when editing different senses)
watch(() => props.sense, initForm, { immediate: true })
watch(() => props.mode, initForm)

// ── Order uniqueness check (edit mode only) ───────────────────────────────
const orderConflict = computed(() => {
  if (props.mode !== 'edit') return false
  if (!form.order_index) return false
  // Another sense (different id) uses the same order_index?
  return props.allSenses.some(
    s => s.id !== props.sense?.id && s.order_index === form.order_index,
  )
})

// ── Submit ────────────────────────────────────────────────────────────────
async function submit() {
  error.value = ''

  if (props.mode === 'add' && !props.wordId) {
    error.value = 'Missing word ID.'
    return
  }
  if (props.mode === 'edit' && !props.sense) {
    error.value = 'Missing sense to edit.'
    return
  }
  if (orderConflict.value) {
    error.value = 'Another sense already uses this order number.'
    return
  }

  submitting.value = true
  try {
    const posValue = form.part_of_speech.trim() || null
    const defValue = form.definition.trim() || null
    const notesValue = form.notes.trim() || null

    if (props.mode === 'add') {
      await addSense(props.wordId!, {
        part_of_speech: posValue,
        definition: defValue,
        notes: notesValue,
      })
      toast.success('Sense added')
    } else {
      await editSense(props.sense!.id, {
        // Only send order_index if it actually changed
        ...(form.order_index !== props.sense!.order_index
          ? { order_index: form.order_index }
          : {}),
        part_of_speech: posValue,
        definition: defValue,
        notes: notesValue,
      })
      toast.success('Sense updated')
    }
    emit('saved')
  } catch (err: unknown) {
    const e = err as { response?: { status?: number; _data?: { detail?: string } }; message?: string }
    if (e.response?.status === 403) {
      error.value = 'Reviewer access required.'
    } else if (e.response?.status === 404) {
      error.value = props.mode === 'edit' ? 'This sense could not be found.' : 'This word could not be found.'
    } else if (e.response?.status === 500 && orderConflict.value) {
      // Defensive: backend CHECK constraint can also 500 on duplicate order_index
      error.value = 'Another sense already uses this order number.'
    } else {
      error.value = e.response?._data?.detail || 'Failed to save. Please try again.'
    }
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="md:col-span-2">
    <!-- Section header -->
    <div class="flex items-baseline justify-between mb-3">
      <label class="field-label mb-0">
        Example sentences
        <span class="text-stone-light font-normal">(optional — show how the word is used)</span>
      </label>
      <span v-if="modelValue.length > 0" class="text-[10px] text-stone-light">{{ modelValue.length }}/{{ max }}</span>
    </div>

    <!-- Existing example rows -->
    <div class="space-y-3">
      <div
        v-for="(ex, idx) in modelValue"
        :key="idx"
        class="bg-cream-50 border border-cream-200 rounded-lg p-4 relative"
      >
        <!-- Remove button -->
        <button
          type="button"
          class="focus-ring absolute top-2 right-2 text-stone-light hover:text-terracotta p-1 rounded"
          :aria-label="`Remove example ${idx + 1}`"
          :disabled="disabled"
          @click="removeExample(idx)"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>

        <p class="text-[10px] font-semibold uppercase tracking-wider text-stone-light mb-3">Example {{ idx + 1 }}</p>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
          <!-- Taita (required) -->
          <div class="md:col-span-2">
            <label class="field-label">
              Taita <span class="text-terracotta">*</span>
            </label>
            <input
              :value="ex.taita_text"
              @input="updateField(idx, 'taita_text', ($event.target as HTMLInputElement).value)"
              type="text"
              class="field"
              placeholder="e.g. Mlima u mrefu sana."
              :disabled="disabled"
              maxlength="2000"
            />
          </div>
          <!-- Swahili (required) -->
          <div>
            <label class="field-label">Swahili <span class="text-terracotta">*</span></label>
            <input
              :value="ex.swahili_text || ''"
              @input="updateField(idx, 'swahili_text', ($event.target as HTMLInputElement).value)"
              type="text"
              class="field"
              placeholder="Mlima ni mrefu..."
              :disabled="disabled"
              maxlength="2000"
            />
          </div>
          <!-- English -->
          <div>
            <label class="field-label">English <span class="text-stone-light font-normal">(optional)</span></label>
            <input
              :value="ex.english_text || ''"
              @input="updateField(idx, 'english_text', ($event.target as HTMLInputElement).value)"
              type="text"
              class="field"
              placeholder="The mountain is tall..."
              :disabled="disabled"
              maxlength="2000"
            />
          </div>
          <!-- Source ref -->
          <div class="md:col-span-2">
            <label class="field-label">Source <span class="text-stone-light font-normal">(optional — where you found it)</span></label>
            <input
              :value="ex.source_ref || ''"
              @input="updateField(idx, 'source_ref', ($event.target as HTMLInputElement).value)"
              type="text"
              class="field"
              placeholder="e.g. Mwadime 1987, p.42"
              :disabled="disabled"
              maxlength="500"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- Add-example button (shown when under the max) -->
    <button
      v-if="modelValue.length < max"
      type="button"
      class="focus-ring btn btn-secondary btn-sm mt-3"
      :disabled="disabled"
      @click="addExample"
    >
      <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
      </svg>
      {{ modelValue.length === 0 ? 'Add an example sentence' : 'Add another example' }}
    </button>

    <!-- Hint when no examples yet -->
    <p v-if="modelValue.length === 0" class="text-[11px] text-stone-light mt-2 leading-relaxed">
      Examples help learners see the word in context. Each example needs a Taita sentence and a Swahili
      translation. You can add up to {{ max }} — leave blank if you don't have one.
    </p>
  </div>
</template>

<script setup lang="ts">
import type { ExampleInput } from '~/utils/words'

const props = withDefaults(defineProps<{
  modelValue: ExampleInput[]
  disabled?: boolean
  max?: number
}>(), {
  disabled: false,
  max: 5,
})

const emit = defineEmits<{
  'update:modelValue': [value: ExampleInput[]]
}>()

function addExample() {
  if (props.modelValue.length >= props.max) return
  // Emit a new array (Vue v-model requires a new reference for reactivity)
  emit('update:modelValue', [
    ...props.modelValue,
    { taita_text: '', swahili_text: '', english_text: '', source_ref: '' },
  ])
}

function removeExample(idx: number) {
  const next = props.modelValue.slice()
  next.splice(idx, 1)
  emit('update:modelValue', next)
}

function updateField<K extends keyof ExampleInput>(idx: number, field: K, value: string) {
  const next = props.modelValue.slice()
  // Build the updated row. Cast because TS can't verify that a computed key
  // assignment produces a valid ExampleInput when field is a union of keys —
  // but we know it does (taita_text is always preserved from the current row).
  next[idx] = { ...next[idx], [field]: value } as ExampleInput
  emit('update:modelValue', next)
}
</script>

<template>
  <!-- Client-only: toasts only ever appear after client-side actions, and
       Teleport+TransitionGroup SSR hydration mismatches on the hidden
       placeholder (comment vs div). -->
  <ClientOnly>
    <Teleport to="body">
    <!-- Toast stack: bottom-right on desktop, bottom-center on mobile -->
    <div
      class="fixed bottom-4 inset-x-4 sm:inset-x-auto sm:right-6 z-[60] flex flex-col items-center sm:items-end gap-2 pointer-events-none"
      aria-live="polite"
    >
      <TransitionGroup name="toast">
        <div
          v-for="t in toasts"
          :key="t.id"
          role="alert"
          class="pointer-events-auto w-full sm:w-auto sm:min-w-[280px] sm:max-w-sm flex items-start gap-3 bg-white border rounded-xl shadow-lift px-4 py-3"
          :class="borderClass(t.type)"
        >
          <!-- Icon -->
          <span class="flex-shrink-0 mt-0.5" aria-hidden="true">
            <!-- success: check in circle -->
            <svg v-if="t.type === 'success'" class="w-5 h-5 text-forest" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <!-- error: alert -->
            <svg v-else-if="t.type === 'error'" class="w-5 h-5 text-terracotta" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <!-- info: dot in circle -->
            <svg v-else class="w-5 h-5 text-stone-dark" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </span>

          <!-- Message + optional action -->
          <div class="flex-1 min-w-0">
            <p class="text-sm text-ink leading-snug">{{ t.message }}</p>
            <button
              v-if="t.action"
              class="focus-ring mt-1.5 text-xs font-semibold text-forest hover:text-forest-dark hover:underline"
              @click="runAction(t)"
            >
              {{ t.action.label }}
            </button>
          </div>

          <!-- Close -->
          <button
            class="focus-ring flex-shrink-0 p-0.5 rounded text-stone-light hover:text-ink transition"
            aria-label="Dismiss notification"
            @click="dismiss(t.id)"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </TransitionGroup>
    </div>
    </Teleport>
  </ClientOnly>
</template>

<script setup lang="ts">
import type { ToastItem, ToastType } from '~/composables/useToast'

const { toasts, dismiss } = useToast()

function borderClass(type: ToastType): string {
  if (type === 'success') return 'border-forest/25'
  if (type === 'error') return 'border-terracotta/30'
  return 'border-cream-300'
}

function runAction(t: ToastItem) {
  dismiss(t.id)
  t.action?.fn()
}
</script>

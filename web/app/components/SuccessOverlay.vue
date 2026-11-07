<template>
  <!-- Client-only: the overlay only ever appears after a client-side
       login/register, and Teleport+Transition SSR hydration can mismatch
       on the hidden placeholder. Nothing is lost for SSR/SEO. -->
  <ClientOnly>
    <Teleport to="body">
      <Transition name="fade">
        <div
          v-if="show"
          class="fixed inset-0 z-[70] flex items-center justify-center bg-cream/95 backdrop-blur-sm cursor-pointer"
          role="status"
          aria-live="polite"
          @click="emit('close')"
        >
          <div class="text-center px-6">
            <!-- Animated ring + check (stroke-dash draw) -->
            <svg class="w-24 h-24 mx-auto mb-5" viewBox="0 0 104 104" fill="none" aria-hidden="true">
              <circle
                class="success-ring"
                cx="52"
                cy="52"
                r="48"
                stroke="#2D5A3D"
                stroke-width="3"
                stroke-linecap="round"
                stroke-dasharray="302"
                stroke-dashoffset="302"
                transform="rotate(-90 52 52)"
              />
              <path
                class="success-check"
                d="M34 54 L47 67 L71 41"
                stroke="#2D5A3D"
                stroke-width="4"
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-dasharray="60"
                stroke-dashoffset="60"
              />
            </svg>

            <h2 class="anim-fade-up anim-delay-2 font-serif text-2xl md:text-3xl text-forest-dark font-semibold mb-2">
              {{ title }}
            </h2>
            <p v-if="subtitle" class="anim-fade-up anim-delay-3 text-sm text-stone">{{ subtitle }}</p>
          </div>
        </div>
      </Transition>
    </Teleport>
  </ClientOnly>
</template>

<script setup lang="ts">
// Full-screen success moment for login / register.
// Usage (see INTEGRATION.md → login.vue patch):
//   <SuccessOverlay :show="showSuccess" title="Karibu tena!" :subtitle="`Signed in as ${email}`" @close="finishSuccess" />
//   ...after a successful login(): showSuccess.value = true; setTimeout(finishSuccess, 1400)
//   Clicking anywhere on the overlay emits `close` — the parent then navigates
//   immediately (nice for impatient users).
const emit = defineEmits<{ close: [] }>()

withDefaults(defineProps<{
  show: boolean
  title?: string
  subtitle?: string
}>(), {
  title: 'Karibu!',
  subtitle: '',
})
</script>

<style scoped>
/* The ring/check draw animations — start from the full offset each time
   the overlay appears (dasharray/dashoffset are set as SVG attributes). */
.success-ring {
  animation: lumi-ring-draw 0.7s cubic-bezier(0.65, 0, 0.35, 1) forwards;
}
.success-check {
  animation: lumi-check-draw 0.35s ease-out 0.55s forwards;
}
</style>

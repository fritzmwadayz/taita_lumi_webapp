<template>
  <section class="grid grid-cols-1 md:grid-cols-12 min-h-[560px]">
    <!-- Side panel (mirrors login.vue — forest hero with tri-pattern) -->
    <aside class="col-span-1 md:col-span-5 bg-forest text-cream p-12 flex flex-col justify-center relative overflow-hidden tri-pattern">
      <div class="relative">
        <p class="text-xs font-semibold tracking-widest uppercase text-ochre-light mb-4">
          Account access
        </p>
        <h2 class="font-serif text-4xl text-cream leading-tight mb-4">
          Forgot your password?
        </h2>
        <p class="text-sm text-cream/80 leading-relaxed">
          Enter the email tied to your Lumi account and we'll send you a link
          to choose a new one. The link expires in one hour.
        </p>
      </div>
    </aside>

    <!-- Form panel -->
    <div class="col-span-1 md:col-span-7 p-12 flex flex-col justify-center">
      <div class="max-w-md mx-auto w-full">
        <!-- ── Success panel (replaces the form after submit) ─────────────── -->
        <div v-if="submitted" class="text-center">
          <svg class="w-14 h-14 mx-auto mb-5 text-forest" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <circle cx="12" cy="12" r="11" stroke-width="1.5" class="text-forest/30" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M7 12.5l3.5 3.5L17 9" />
          </svg>
          <h1 class="font-serif text-3xl text-forest-dark mb-2">Check your email</h1>
          <p class="text-sm text-stone mb-1">
            If an account exists for
            <span class="font-semibold text-ink">{{ submittedEmail || 'that email' }}</span>,
            we've sent a reset link.
          </p>
          <p class="text-xs text-stone-light mb-8">The link expires in 1 hour.</p>
          <NuxtLink to="/login" class="focus-ring btn btn-secondary btn-md">
            Back to login
          </NuxtLink>
        </div>

        <!-- ── Request form ───────────────────────────────────────────────── -->
        <div v-else>
          <h1 class="font-serif text-3xl text-forest-dark mb-1">Reset your password</h1>
          <p class="text-sm text-stone mb-6">
            Enter your email and we'll send you a link to reset your password.
          </p>

          <!-- Inline error (rate limit / invalid email format) -->
          <div
            v-if="error"
            class="bg-terracotta/10 border border-terracotta/30 rounded-lg p-3 mb-4 text-sm text-terracotta-dark"
            role="alert"
          >
            {{ error }}
          </div>

          <form class="space-y-4" @submit.prevent="onSubmit">
            <div>
              <label class="field-label" for="forgot-email">Email</label>
              <input
                id="forgot-email"
                v-model="email"
                type="email"
                autocomplete="email"
                required
                class="field"
                :class="error ? 'field-error' : ''"
                placeholder="you@example.com"
                :disabled="submitting || rateLimited"
              />
            </div>

            <button
              type="submit"
              :disabled="submitting || rateLimited"
              class="focus-ring btn btn-primary btn-lg w-full"
            >
              <svg v-if="submitting" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24" aria-hidden="true">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              {{ submitting ? 'Sending…' : (rateLimited ? 'Too many requests' : 'Send reset link') }}
            </button>
          </form>

          <p class="text-xs text-stone text-center mt-6">
            Remember your password?
            <NuxtLink to="/login" class="focus-ring font-semibold text-forest hover:underline">
              Back to login
            </NuxtLink>
          </p>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref, computed, onUnmounted } from 'vue'

definePageMeta({
  ssr: false, // SPA mode — auth-flow pattern
  middleware: 'guest', // redirect to / if already logged in
})

const toast = useToast()

const email = ref('')
const submitting = ref(false)
const submitted = ref(false)
const submittedEmail = ref('')
const error = ref('')

// ── Rate-limit cooldown ───────────────────────────────────────────────────
// On 429 we disable the button for 60s and show a countdown-free "Too many
// requests" label. The backend enforces the real limit; this is just UX.
const rateLimited = ref(false)
let rateTimer: ReturnType<typeof setTimeout> | null = null

function startRateLimitCooldown() {
  rateLimited.value = true
  if (rateTimer) clearTimeout(rateTimer)
  rateTimer = setTimeout(() => {
    rateLimited.value = false
    error.value = ''
  }, 60_000)
}

onUnmounted(() => {
  if (rateTimer) clearTimeout(rateTimer)
})

// Track whether the email field looks valid (client-side pre-check so we
// can give instant feedback without a round-trip).
const emailValid = computed(() => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value.trim()))

async function onSubmit() {
  error.value = ''

  if (!emailValid.value) {
    error.value = 'Please enter a valid email address.'
    return
  }

  submitting.value = true
  try {
    await requestPasswordReset(email.value.trim())
    // Always show the success panel — the backend returns the same response
    // whether or not the email exists, to prevent enumeration.
    submittedEmail.value = email.value.trim()
    submitted.value = true
  } catch (err: unknown) {
    const e = err as { response?: { status?: number; _data?: { detail?: string } }; message?: string }
    const status = e.response?.status
    if (status === 429) {
      error.value = 'Too many requests. Please try again later.'
      startRateLimitCooldown()
    } else if (status === 422) {
      // Backend email-format validation rejected it
      error.value = 'Please enter a valid email address.'
    } else {
      // Network error, 5xx, etc. — fall back to a generic message but still
      // surface something actionable. We do NOT auto-flip to the success
      // panel here because the request genuinely failed.
      error.value = (e.response?._data?.detail as string) || 'Could not send the reset email. Please try again.'
      toast.error('Could not send reset email')
    }
  } finally {
    submitting.value = false
  }
}
</script>

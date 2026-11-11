<template>
  <section class="grid grid-cols-1 md:grid-cols-12 min-h-[560px]">
    <!-- Side panel (mirrors login.vue) -->
    <aside class="col-span-1 md:col-span-5 bg-forest text-cream p-12 flex flex-col justify-center relative overflow-hidden tri-pattern">
      <div class="relative">
        <p class="text-xs font-semibold tracking-widest uppercase text-ochre-light mb-4">
          Account access
        </p>
        <h2 class="font-serif text-4xl text-cream leading-tight mb-4">
          Set a new password.
        </h2>
        <p class="text-sm text-cream/80 leading-relaxed">
          Choose a strong password — at least 8 characters. After resetting
          you'll be redirected to log in with your new password.
        </p>
      </div>
    </aside>

    <!-- Form panel -->
    <div class="col-span-1 md:col-span-7 p-12 flex flex-col justify-center">
      <div class="max-w-md mx-auto w-full">
        <!-- ── No-token / invalid-link error state ────────────────────────── -->
        <div v-if="!token" class="text-center">
          <svg class="w-14 h-14 mx-auto mb-5 text-terracotta" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 9v3.75m0 3.75h.008v.008H12v-.008zM21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <h1 class="font-serif text-3xl text-forest-dark mb-2">Invalid reset link</h1>
          <p class="text-sm text-stone mb-8">
            This reset link is missing its token. Please request a new password reset.
          </p>
          <NuxtLink to="/forgot-password" class="focus-ring btn btn-primary btn-md">
            Request a new reset link
          </NuxtLink>
        </div>

        <!-- ── Invalid / expired token error state (returned 400) ─────────── -->
        <div v-else-if="linkInvalid" class="text-center">
          <svg class="w-14 h-14 mx-auto mb-5 text-terracotta" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 9v3.75m0 3.75h.008v.008H12v-.008zM21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <h1 class="font-serif text-3xl text-forest-dark mb-2">Link expired or invalid</h1>
          <p class="text-sm text-stone mb-8">
            This reset link is invalid or has expired. Reset links are valid
            for one hour.
          </p>
          <NuxtLink to="/forgot-password" class="focus-ring btn btn-primary btn-md">
            Request a new reset link
          </NuxtLink>
        </div>

        <!-- ── Success state ──────────────────────────────────────────────── -->
        <div v-else-if="succeeded" class="text-center">
          <svg class="w-14 h-14 mx-auto mb-5 text-forest" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <circle cx="12" cy="12" r="11" stroke-width="1.5" class="text-forest/30" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M7 12.5l3.5 3.5L17 9" />
          </svg>
          <h1 class="font-serif text-3xl text-forest-dark mb-2">Password reset!</h1>
          <p class="text-sm text-stone mb-8">
            Your password has been changed. Redirecting to login<span v-if="countdown > 0"> in {{ countdown }}s</span>…
          </p>
          <NuxtLink to="/login" class="focus-ring btn btn-primary btn-md">
            Go to login now
          </NuxtLink>
        </div>

        <!-- ── Reset form ─────────────────────────────────────────────────── -->
        <div v-else>
          <h1 class="font-serif text-3xl text-forest-dark mb-1">Set a new password</h1>
          <p class="text-sm text-stone mb-6">
            Enter your new password below.
          </p>

          <form class="space-y-4" @submit.prevent="onSubmit">
            <div>
              <label class="field-label" for="reset-new">New password</label>
              <div class="relative">
                <input
                  id="reset-new"
                  v-model="password"
                  :type="showPassword ? 'text' : 'password'"
                  autocomplete="new-password"
                  required
                  minlength="8"
                  class="field pr-10"
                  :class="passwordError ? 'field-error' : ''"
                  placeholder="At least 8 characters"
                  :disabled="submitting"
                />
                <button
                  type="button"
                  class="focus-ring absolute inset-y-0 right-0 px-3 flex items-center text-stone hover:text-forest"
                  :aria-label="showPassword ? 'Hide password' : 'Show password'"
                  :title="showPassword ? 'Hide password' : 'Show password'"
                  @click="showPassword = !showPassword"
                >
                  <!-- Eye icon (show) / eye-off icon (hide) -->
                  <svg v-if="!showPassword" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                  </svg>
                  <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.542-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.542 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                  </svg>
                </button>
              </div>
              <p v-if="passwordError" class="text-xs text-terracotta mt-1.5">{{ passwordError }}</p>
            </div>

            <div>
              <label class="field-label" for="reset-confirm">Confirm password</label>
              <input
                id="reset-confirm"
                v-model="confirmPassword"
                :type="showPassword ? 'text' : 'password'"
                autocomplete="new-password"
                required
                minlength="8"
                class="field"
                :class="confirmError ? 'field-error' : ''"
                placeholder="Re-enter your new password"
                :disabled="submitting"
              />
              <p v-if="confirmError" class="text-xs text-terracotta mt-1.5">{{ confirmError }}</p>
            </div>

            <button
              type="submit"
              :disabled="submitting"
              class="focus-ring btn btn-primary btn-lg w-full"
            >
              <svg v-if="submitting" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24" aria-hidden="true">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              {{ submitting ? 'Resetting…' : 'Reset password' }}
            </button>
          </form>

          <p class="text-xs text-stone text-center mt-6">
            Link expired?
            <NuxtLink to="/forgot-password" class="focus-ring font-semibold text-forest hover:underline">
              Request a new one
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

// ── SEO ───────────────────────────────────────────────────────────────────
useSiteSeo({ noindex: true })

const route = useRoute()
const toast = useToast()

// Token comes from the email link's query string: /reset-password?token=xxx
const token = computed(() => (route.query.token as string | undefined)?.trim() || '')

// ── Form state ────────────────────────────────────────────────────────────
const password = ref('')
const confirmPassword = ref('')
const showPassword = ref(false)
const submitting = ref(false)
const passwordError = ref('')
const confirmError = ref('')

// ── Outcome state (mutually exclusive with the form) ──────────────────────
const linkInvalid = ref(false) // backend rejected the token (400)
const succeeded = ref(false)   // backend accepted the new password

// ── Auto-redirect countdown ───────────────────────────────────────────────
const REDIRECT_MS = 3000
const countdown = ref(3)
let countdownTimer: ReturnType<typeof setInterval> | null = null
let redirectTimer: ReturnType<typeof setTimeout> | null = null

function startRedirect() {
  countdown.value = Math.ceil(REDIRECT_MS / 1000)
  countdownTimer = setInterval(() => {
    countdown.value = Math.max(0, countdown.value - 1)
  }, 1000)
  redirectTimer = setTimeout(() => {
    navigateTo('/login')
  }, REDIRECT_MS)
}

onUnmounted(() => {
  if (countdownTimer) clearInterval(countdownTimer)
  if (redirectTimer) clearTimeout(redirectTimer)
})

function clearFieldErrors() {
  passwordError.value = ''
  confirmError.value = ''
}

function validate(): boolean {
  clearFieldErrors()
  let ok = true
  if (password.value.length < 8) {
    passwordError.value = 'Password must be at least 8 characters.'
    ok = false
  }
  if (confirmPassword.value !== password.value) {
    confirmError.value = 'Passwords do not match.'
    ok = false
  } else if (confirmPassword.value.length === 0) {
    confirmError.value = 'Please confirm your new password.'
    ok = false
  }
  return ok
}

async function onSubmit() {
  // Defensive: the form is only rendered when token is present and no
  // terminal state has been reached, but guard anyway.
  if (!token.value || linkInvalid.value || succeeded.value) return

  if (!validate()) return

  submitting.value = true
  try {
    await confirmPasswordReset(token.value, password.value)
    succeeded.value = true
    toast.success('Password reset')
    startRedirect()
  } catch (err: unknown) {
    const e = err as { response?: { status?: number; _data?: { detail?: string } }; message?: string }
    const status = e.response?.status
    if (status === 400) {
      // Invalid or expired token — flip to the invalid-link state.
      linkInvalid.value = true
    } else if (status === 422) {
      // Password failed backend validation (e.g. too short). Mirror that as
      // an inline error on the password field.
      passwordError.value = (e.response?._data?.detail as string) || 'Password is not valid.'
    } else {
      toast.error((e.response?._data?.detail as string) || 'Could not reset password. Please try again.')
    }
  } finally {
    submitting.value = false
  }
}
</script>

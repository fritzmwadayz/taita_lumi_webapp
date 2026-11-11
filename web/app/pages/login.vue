<template>
  <section class="grid grid-cols-1 md:grid-cols-12 min-h-[560px]">
    <!-- Side panel -->
    <aside class="col-span-1 md:col-span-5 bg-forest text-cream p-12 flex flex-col justify-center relative overflow-hidden tri-pattern">
      <div class="relative">
        <p class="text-xs font-semibold tracking-widest uppercase text-ochre-light mb-4">
          Join the dictionary
        </p>
        <h2 class="font-serif text-4xl text-cream leading-tight mb-4">
          A community effort to digitize the Taita language.
        </h2>
        <p class="text-sm text-cream/80 leading-relaxed mb-6">
          Sign up to add words, vote on suggestions, and help shape the dictionary.
        </p>
        <ul class="space-y-2 text-sm text-cream/90">
          <li class="flex items-start gap-2">
            <svg class="w-4 h-4 mt-1 text-ochre-light" fill="currentColor" viewBox="0 0 20 20">
              <path d="M16.7 5.3a1 1 0 010 1.4l-8 8a1 1 0 01-1.4 0l-4-4a1 1 0 011.4-1.4L8 12.6l7.3-7.3a1 1 0 011.4 0z" />
            </svg>
            Add new words directly
          </li>
          <li class="flex items-start gap-2">
            <svg class="w-4 h-4 mt-1 text-ochre-light" fill="currentColor" viewBox="0 0 20 20">
              <path d="M16.7 5.3a1 1 0 010 1.4l-8 8a1 1 0 01-1.4 0l-4-4a1 1 0 011.4-1.4L8 12.6l7.3-7.3a1 1 0 011.4 0z" />
            </svg>
            Vote on community suggestions
          </li>
          <li class="flex items-start gap-2">
            <svg class="w-4 h-4 mt-1 text-ochre-light" fill="currentColor" viewBox="0 0 20 20">
              <path d="M16.7 5.3a1 1 0 010 1.4l-8 8a1 1 0 01-1.4 0l-4-4a1 1 0 011.4-1.4L8 12.6l7.3-7.3a1 1 0 011.4 0z" />
            </svg>
            Track your contributions
          </li>
        </ul>
      </div>
    </aside>

    <!-- Form panel -->
    <div class="col-span-1 md:col-span-7 p-12 flex flex-col justify-center">
      <div class="max-w-md mx-auto w-full">
        <h1 class="font-serif text-3xl text-forest-dark mb-1">
          {{ activeTab === 'login' ? 'Welcome back' : 'Create account' }}
        </h1>
        <p class="text-sm text-stone mb-6">
          {{ activeTab === 'login' ? 'Log in to contribute.' : 'Sign up to start contributing.' }}
        </p>

        <!-- Tabs (underline style) -->
        <div class="border-b border-cream-200 mb-6">
          <div class="flex items-center gap-1">
            <button :class="['tab-underline', activeTab === 'login' && 'tab-underline-active']" @click="activeTab = 'login'">
              Log in
            </button>
            <button :class="['tab-underline', activeTab === 'signup' && 'tab-underline-active']" @click="activeTab = 'signup'">
              Sign up
            </button>
          </div>
        </div>

        <!-- Error message -->
        <div v-if="error" class="bg-terracotta/10 border border-terracotta/30 rounded-lg p-3 mb-4 text-sm text-terracotta-dark">
          {{ error }}
        </div>

        <!-- Google OAuth -->
        <button
          :disabled="loading"
          class="focus-ring w-full flex items-center justify-center gap-2 border border-cream-300 rounded-md px-4 py-2.5 text-sm font-medium text-ink-soft bg-white hover:bg-cream-50 transition mb-3"
          @click="handleGoogleLogin"
        >
          <svg class="w-4 h-4" viewBox="0 0 24 24">
            <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
            <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
            <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
            <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
          </svg>
          {{ activeTab === 'login' ? 'Continue with Google' : 'Sign up with Google' }}
        </button>

        <!-- OAuth error from callback -->
        <div v-if="oauthError" class="text-[10px] text-stone-light text-center mb-3 italic">
          {{ oauthError }}
        </div>

        <div class="flex items-center gap-3 mb-6">
          <div class="flex-1 h-px bg-cream-200"></div>
          <span class="text-[10px] uppercase tracking-wider text-stone-light">or</span>
          <div class="flex-1 h-px bg-cream-200"></div>
        </div>

        <!-- Email/password form -->
        <form class="space-y-4" @submit.prevent="onSubmit">
          <div>
            <label class="field-label">Email</label>
            <input
              v-model="email"
              type="email"
              required
              class="field"
              placeholder="you@example.com"
              :disabled="loading"
            />
          </div>
          <div>
            <label class="field-label">Password</label>
            <input
              v-model="password"
              type="password"
              required
              :minlength="activeTab === 'signup' ? 8 : undefined"
              class="field"
              :placeholder="activeTab === 'signup' ? 'At least 8 characters' : 'Your password'"
              :disabled="loading"
            />
          </div>

          <!-- Forgot password link — login tab only.
               Signup creates a new account so the link is irrelevant there. -->
          <div v-if="activeTab === 'login'" class="flex items-center justify-end -mt-1">
            <NuxtLink
              to="/forgot-password"
              class="focus-ring text-xs text-forest hover:underline rounded"
            >
              Forgot password?
            </NuxtLink>
          </div>

          <div v-if="activeTab === 'signup'">
            <label class="field-label">
              Display name <span class="text-stone-light font-normal">(optional)</span>
            </label>
            <input
              v-model="displayName"
              type="text"
              class="field"
              placeholder="@yourname"
              :disabled="loading"
            />
          </div>

          <button
            type="submit"
            :disabled="loading"
            class="focus-ring btn btn-primary btn-lg w-full"
          >
            <svg v-if="loading" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
            {{ loading
              ? (activeTab === 'login' ? 'Logging in…' : 'Creating account…')
              : (activeTab === 'login' ? 'Log in' : 'Create account') }}
          </button>
        </form>

        <p class="text-xs text-stone text-center mt-6">
          <template v-if="activeTab === 'login'">
            No account?
            <button class="focus-ring font-semibold text-forest hover:underline" @click="activeTab = 'signup'">Sign up</button>
          </template>
          <template v-else>
            Already have an account?
            <button class="focus-ring font-semibold text-forest hover:underline" @click="activeTab = 'login'">Log in</button>
          </template>
        </p>
      </div>
    </div>

    <!-- Success overlay — shown after successful login/register.
         Teleported to <body>, full-screen, covers the form during the
         gap between "login succeeded" and "destination page is ready".
         Stays visible during the page transition (we don't reset
         showSuccess before navigating — the component unmount handles it). -->
    <SuccessOverlay
      :show="showSuccess"
      :title="successTitle"
      :subtitle="successSubtitle"
      @close="finishSuccess"
    />
  </section>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

definePageMeta({
  ssr: false, // SPA mode — no SSR for authed pages
  middleware: 'guest', // redirect to / if already logged in
})

// ── SEO ───────────────────────────────────────────────────────────────────
useSiteSeo({ noindex: true })

const route = useRoute()
const { login, register, loginWithGoogle } = useAuth()

const activeTab = ref<'login' | 'signup'>('login')
const email = ref('')
const password = ref('')
const displayName = ref('')
const error = ref('')
const loading = ref(false)

// ── Success overlay state ──────────────────────────────────────────────
const showSuccess = ref(false)
const userEmail = ref('')
const SUCCESS_MS = 1400

const successTitle = computed(() =>
  activeTab.value === 'login' ? 'Karibu tena!' : 'Karibu!',
)
const successSubtitle = computed(() =>
  activeTab.value === 'login'
    ? `Signed in as ${userEmail.value}`
    : `Welcome, ${userEmail.value}`,
)

function finishSuccess() {
  if (!showSuccess.value) return // guard double-navigation
  // Navigate WITHOUT resetting showSuccess — the overlay stays visible
  // during the page transition (out-in fade) and disappears when the
  // login page unmounts. This fills the gap between "login succeeded"
  // and "destination page rendered".
  const next = route.query.next as string | undefined
  navigateTo(next || '/')
}

// Check for OAuth error in query params (set by the callback handler)
const oauthError = computed(() => {
  const err = route.query.error as string | undefined
  if (!err) return null
  const messages: Record<string, string> = {
    google_no_id_token: 'Google sign-in not configured properly.',
    profile_fetch_failed: 'Could not fetch your profile after Google sign-in.',
    oauth_failed: 'Google sign-in failed. Please try again.',
  }
  return messages[err] || decodeURIComponent(err)
})

// ── Email/password submit ──────────────────────────────────────────────
async function onSubmit() {
  error.value = ''
  loading.value = true
  try {
    if (activeTab.value === 'login') {
      await login(email.value, password.value)
    } else {
      await register(email.value, password.value, displayName.value || null)
    }
    // Success — show the overlay, then navigate after SUCCESS_MS.
    // The overlay covers the form so the user doesn't see the static
    // login content during the route transition.
    userEmail.value = email.value
    showSuccess.value = true
    setTimeout(finishSuccess, SUCCESS_MS)
  } catch (err: unknown) {
    const e = err as { response?: { _data?: { detail?: string } }; message?: string }
    error.value = (e.response?._data?.detail as string) || 'Something went wrong.'
  } finally {
    loading.value = false
  }
}

function handleGoogleLogin() {
  // Store the redirect target in a cookie so the OAuth callback can redirect there
  const next = (route.query.next as string) || '/'
  if (next !== '/') {
    const redirectCookie = useCookie('lumi_oauth_redirect')
    redirectCookie.value = next
  }
  loginWithGoogle()
}
</script>

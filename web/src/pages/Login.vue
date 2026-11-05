<template>
  <section class="grid grid-cols-12 min-h-[560px]">
    <!-- Side panel -->
    <aside class="col-span-5 bg-forest text-cream p-12 flex flex-col justify-center relative overflow-hidden">
      <div class="absolute top-0 right-0 w-64 h-64 opacity-10">
        <svg viewBox="0 0 100 100" fill="none" stroke="currentColor" stroke-width="0.5">
          <pattern id="tri6" patternUnits="userSpaceOnUse" width="20" height="20">
            <path d="M10 0L20 20L0 20Z" fill="none" stroke="currentColor" />
          </pattern>
          <rect width="100" height="100" fill="url(#tri6)" />
        </svg>
      </div>
      <div class="relative">
        <p class="text-xs font-semibold tracking-widest uppercase text-ochre-light mb-4">
          Join the dictionary
        </p>
        <h2 class="font-serif text-4xl text-cream leading-tight mb-4">
          A community effort to keep Taita alive.
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
    <div class="col-span-7 p-12 flex flex-col justify-center">
      <div class="max-w-md mx-auto w-full">
        <h1 class="font-serif text-3xl text-forest-dark mb-1">
          {{ activeTab === "login" ? "Welcome back" : "Create account" }}
        </h1>
        <p class="text-sm text-stone mb-6">
          {{ activeTab === "login" ? "Log in to contribute." : "Sign up to start contributing." }}
        </p>

        <!-- Tabs -->
        <div class="flex bg-cream-100 rounded-lg p-1 mb-6">
          <button
            @click="activeTab = 'login'"
            :class="['flex-1 tab-pill', activeTab === 'login' && 'active']"
          >
            Log in
          </button>
          <button
            @click="activeTab = 'signup'"
            :class="['flex-1 tab-pill', activeTab === 'signup' && 'active']"
          >
            Sign up
          </button>
        </div>

        <!-- Error message -->
        <div
          v-if="error"
          class="bg-terracotta/10 border border-terracotta/30 rounded-lg p-3 mb-4 text-sm text-terracotta-dark"
        >
          {{ error }}
        </div>

        <!-- Loading overlay (shown during Google OAuth verification) -->
        <div
          v-if="googleLoading"
          class="bg-forest/5 border border-forest/20 rounded-lg p-4 mb-4 flex items-center gap-3"
        >
          <svg
            class="w-5 h-5 text-forest animate-spin flex-shrink-0"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              class="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              stroke-width="4"
            ></circle>
            <path
              class="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            ></path>
          </svg>
          <div>
            <p class="text-sm font-medium text-forest-dark">Signing you in…</p>
            <p class="text-xs text-stone">Verifying with Google</p>
          </div>
        </div>

        <!-- OAuth -->
        <div
          v-if="googleClientId && !googleLoading"
          id="google-button-container"
          class="mb-3 flex justify-center"
        ></div>
        <div
          v-else-if="googleLoading"
          class="mb-3 flex justify-center"
        >
          <div
            class="flex items-center gap-2 px-4 py-2.5 border border-cream-300 rounded-lg text-sm font-medium text-stone-light bg-cream-50"
          >
            <svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Google sign-in…
          </div>
        </div>
        <p v-if="!googleClientId" class="text-[10px] text-stone-light text-center mb-3 italic">
          Google sign-in not configured (set VITE_GOOGLE_CLIENT_ID)
        </p>

        <div class="flex items-center gap-3 mb-6">
          <div class="flex-1 h-px bg-cream-200"></div>
          <span class="text-[10px] uppercase tracking-wider text-stone-light">or</span>
          <div class="flex-1 h-px bg-cream-200"></div>
        </div>

        <!-- Form -->
        <form @submit.prevent="onSubmit" class="space-y-4">
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
            class="w-full bg-forest hover:bg-forest-dark text-cream font-semibold text-sm py-3 rounded-lg transition disabled:opacity-50 flex items-center justify-center gap-2"
          >
            <svg
              v-if="loading"
              class="w-4 h-4 animate-spin"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            {{ loading
              ? (activeTab === "login" ? "Logging in…" : "Creating account…")
              : (activeTab === "login" ? "Log in" : "Create account") }}
          </button>
        </form>

        <p class="text-xs text-stone text-center mt-6">
          <template v-if="activeTab === 'login'">
            No account?
            <button @click="activeTab = 'signup'" class="font-semibold text-forest hover:underline">
              Sign up
            </button>
          </template>
          <template v-else>
            Already have an account?
            <button @click="activeTab = 'login'" class="font-semibold text-forest hover:underline">
              Log in
            </button>
          </template>
        </p>
      </div>
    </div>
  </section>
</template>

<script setup>
import { ref, onMounted, nextTick, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth";

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();

const activeTab = ref("login");
const email = ref("");
const password = ref("");
const displayName = ref("");
const error = ref("");
const loading = ref(false);
const googleLoading = ref(false);

const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID || "";

// ── Google Identity Services ──────────────────────────────────
function renderGoogleButton() {
  if (!googleClientId || !window.google?.accounts?.id) return;

  window.google.accounts.id.initialize({
    client_id: googleClientId,
    callback: handleGoogleCallback,
  });

  window.google.accounts.id.renderButton(
    document.getElementById("google-button-container"),
    {
      theme: "outline",
      size: "large",
      width: 320,
      text: activeTab.value === "login" ? "continue_with" : "signup_with",
    },
  );
}

async function handleGoogleCallback(response) {
  // response.credential is the Google ID token
  error.value = "";
  googleLoading.value = true;
  try {
    await authStore.loginWithGoogle(response.credential);
    redirectToNext();
  } catch (err) {
    error.value = err.response?.data?.detail || "Google sign-in failed.";
  } finally {
    googleLoading.value = false;
  }
}

// ── Email/password submit ────────────────────────────────────
async function onSubmit() {
  error.value = "";
  loading.value = true;
  try {
    if (activeTab.value === "login") {
      await authStore.login(email.value, password.value);
    } else {
      await authStore.register(
        email.value,
        password.value,
        displayName.value || null,
      );
    }
    redirectToNext();
  } catch (err) {
    error.value = err.response?.data?.detail || "Something went wrong.";
  } finally {
    loading.value = false;
  }
}

function redirectToNext() {
  // Redirect to the page the user was trying to reach, or home
  const next = route.query.next;
  router.push(next || "/");
}

// ── Init ──────────────────────────────────────────────────────
// If already logged in, redirect away
onMounted(async () => {
  if (authStore.isAuthenticated) {
    router.push("/");
    return;
  }

  // Wait for the Google script to load, then render the button
  await nextTick();
  // Give the external script a moment to load
  setTimeout(renderGoogleButton, 100);
});

// Re-render Google button when tab changes (text changes)
watch(activeTab, () => {
  nextTick(() => renderGoogleButton());
});
</script>

<style scoped>
.tab-pill {
  padding: 8px 14px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.15s;
}
.tab-pill.active {
  background: #1f2937;
  color: #fbf7f0;
}

.field {
  width: 100%;
  padding: 10px 14px;
  border: 1px solid #e8dfc8;
  border-radius: 8px;
  background: #fdfbf6;
  font-size: 14px;
  color: #1f2937;
  font-family: "Inter", sans-serif;
}
.field:focus {
  outline: none;
  border-color: #2d5a3d;
  box-shadow: 0 0 0 3px rgba(45, 90, 61, 0.1);
}
.field:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.field-label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: #374151;
  margin-bottom: 6px;
  letter-spacing: 0.02em;
}
</style>

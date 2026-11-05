<template>
  <div class="max-w-2xl mx-auto px-8 py-16">
    <!-- Loading -->
    <div v-if="authStore.loading" class="text-center py-24">
      <div class="animate-pulse">
        <div class="h-16 bg-cream-200 rounded w-1/3 mx-auto mb-4"></div>
        <div class="h-4 bg-cream-100 rounded w-1/2 mx-auto"></div>
      </div>
    </div>

    <!-- Not logged in -->
    <div v-else-if="!authStore.isAuthenticated" class="text-center py-12">
      <p class="font-serif text-3xl text-forest-dark mb-4">You're not logged in.</p>
      <p class="text-sm text-stone mb-8">Log in to see your profile and contributions.</p>
      <RouterLink
        :to="{ path: '/login', query: { next: '/me' } }"
        class="inline-block bg-forest hover:bg-forest-dark text-cream font-semibold text-sm px-5 py-2.5 rounded-lg transition"
      >
        Go to login
      </RouterLink>
    </div>

    <!-- Profile -->
    <div v-else>
      <header class="mb-8">
        <p class="text-xs font-semibold tracking-widest uppercase text-ochre mb-2">Profile</p>

        <!-- Display name (editable) -->
        <div v-if="!editingName" class="flex items-center gap-3 mb-2">
          <h1 class="font-serif text-4xl text-forest-dark">{{ authStore.displayName }}</h1>
          <button
            @click="startEditName"
            class="text-stone-light hover:text-forest p-1"
            title="Edit display name"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
            </svg>
          </button>
        </div>
        <div v-else class="mb-4">
          <input
            v-model="nameEdit"
            type="text"
            class="field text-2xl font-serif"
            placeholder="Display name"
            @keyup.enter="saveName"
            @keyup.escape="cancelEditName"
          />
          <div class="flex gap-2 mt-2">
            <button
              @click="saveName"
              :disabled="savingName"
              class="bg-forest hover:bg-forest-dark text-cream text-sm font-semibold px-4 py-1.5 rounded-lg transition"
            >
              {{ savingName ? "Saving..." : "Save" }}
            </button>
            <button
              @click="cancelEditName"
              class="text-sm text-stone hover:text-ink px-4 py-1.5"
            >
              Cancel
            </button>
          </div>
        </div>

        <p class="text-sm text-stone">{{ authStore.user.email }}</p>
        <div class="flex items-center gap-2 mt-3">
          <span
            class="text-[10px] font-semibold uppercase tracking-wider px-2 py-1 rounded"
            :class="authStore.isAdmin ? 'bg-terracotta/15 text-terracotta-dark' : 'bg-cream-200 text-stone'"
          >
            {{ authStore.isAdmin ? "Admin" : authStore.user.role === "reviewer" ? "Reviewer" : "User" }}
          </span>
          <span class="text-xs text-stone-light">
            Joined {{ formatDate(authStore.user.created_at) }}
          </span>
        </div>
      </header>

      <!-- Stats -->
      <section class="grid grid-cols-2 md:grid-cols-3 gap-4 mb-8">
        <div class="bg-cream-50 border border-cream-200 rounded-xl p-5 text-center">
          <p class="font-serif text-3xl text-forest-dark font-semibold">
            {{ stats?.words_added ?? 0 }}
          </p>
          <p class="text-[10px] uppercase tracking-wider text-stone">Words added</p>
        </div>
        <div class="bg-cream-50 border border-cream-200 rounded-xl p-5 text-center">
          <p class="font-serif text-3xl text-forest-dark font-semibold">
            {{ stats?.suggestions_submitted ?? 0 }}
          </p>
          <p class="text-[10px] uppercase tracking-wider text-stone">Suggestions</p>
        </div>
        <div class="bg-cream-50 border border-cream-200 rounded-xl p-5 text-center">
          <p class="font-serif text-3xl text-forest-dark font-semibold">
            {{ stats?.votes_cast ?? 0 }}
          </p>
          <p class="text-[10px] uppercase tracking-wider text-stone">Votes cast</p>
        </div>
      </section>

      <!-- Suggestion breakdown -->
      <section v-if="stats && stats.suggestions_submitted > 0" class="mb-8">
        <h2 class="text-xs font-semibold uppercase tracking-widest text-stone mb-3">
          Your suggestions
        </h2>
        <div class="grid grid-cols-2 md:grid-cols-3 gap-3 text-center">
          <div class="bg-terracotta/5 border border-terracotta/20 rounded-lg p-3">
            <p class="font-serif text-xl text-terracotta font-semibold">{{ stats.suggestions_open }}</p>
            <p class="text-[10px] uppercase tracking-wider text-stone">Open</p>
          </div>
          <div class="bg-forest/5 border border-forest/20 rounded-lg p-3">
            <p class="font-serif text-xl text-forest font-semibold">{{ stats.suggestions_accepted }}</p>
            <p class="text-[10px] uppercase tracking-wider text-stone">Accepted</p>
          </div>
          <div class="bg-stone/5 border border-stone/20 rounded-lg p-3">
            <p class="font-serif text-xl text-stone font-semibold">{{ stats.suggestions_rejected }}</p>
            <p class="text-[10px] uppercase tracking-wider text-stone">Rejected</p>
          </div>
        </div>
      </section>

      <!-- Admin link -->
      <section v-if="authStore.isAdmin" class="mb-8">
        <RouterLink
          to="/admin"
          class="block bg-cream-100 hover:bg-cream-200 border border-cream-200 rounded-xl p-4 transition"
        >
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm font-semibold text-ink">Admin dashboard</p>
              <p class="text-xs text-stone">Manage users, words, and suggestions.</p>
            </div>
            <svg class="w-5 h-5 text-forest" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
            </svg>
          </div>
        </RouterLink>
      </section>

      <!-- Change password -->
      <section class="mb-8">
        <h2 class="text-xs font-semibold uppercase tracking-widest text-stone mb-3">
          Change password
        </h2>
        <div v-if="!authStore.user?.oauth_provider" class="bg-cream-50 border border-cream-200 rounded-xl p-5">
          <div v-if="!pwFormOpen">
            <button
              @click="openPwForm"
              class="text-sm font-semibold text-forest hover:underline"
            >
              Change password →
            </button>
          </div>
          <div v-else class="space-y-3">
            <div>
              <label class="field-label">Current password</label>
              <input v-model="pwForm.current" type="password" class="field" :disabled="pwSaving" />
            </div>
            <div>
              <label class="field-label">New password</label>
              <input v-model="pwForm.new" type="password" class="field" placeholder="At least 8 characters" :disabled="pwSaving" />
            </div>
            <div v-if="pwError" class="text-xs text-terracotta">{{ pwError }}</div>
            <div v-if="pwSuccess" class="text-xs text-forest">Password changed successfully.</div>
            <div class="flex gap-2">
              <button
                @click="savePassword"
                :disabled="pwSaving"
                class="bg-forest hover:bg-forest-dark text-cream text-sm font-semibold px-4 py-2 rounded-lg transition disabled:opacity-50"
              >
                {{ pwSaving ? "Saving..." : "Save" }}
              </button>
              <button @click="closePwForm" class="text-sm text-stone hover:text-ink px-4 py-2">
                Cancel
              </button>
            </div>
          </div>
        </div>
        <div v-else class="text-xs text-stone-light italic">
          You're signed in with Google — no password to change.
        </div>
      </section>

      <!-- Actions -->
      <section class="border-t border-cream-200 pt-6">
        <button
          @click="handleLogout"
          :disabled="loggingOut"
          class="text-sm font-semibold text-terracotta hover:text-terracotta-dark"
        >
          {{ loggingOut ? "Logging out..." : "Log out" }}
        </button>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from "vue";
import { useRouter, RouterLink } from "vue-router";
import { useAuthStore } from "../stores/auth";
import { fetchMyStats, updateMe, changePassword } from "../api/auth";

const router = useRouter();
const authStore = useAuthStore();
const loggingOut = ref(false);

const stats = ref(null);
const editingName = ref(false);
const nameEdit = ref("");
const savingName = ref(false);

// Password form state
const pwFormOpen = ref(false);
const pwForm = reactive({ current: "", new: "" });
const pwSaving = ref(false);
const pwError = ref("");
const pwSuccess = ref(false);

function openPwForm() {
  pwForm.current = "";
  pwForm.new = "";
  pwError.value = "";
  pwSuccess.value = false;
  pwFormOpen.value = true;
}

function closePwForm() {
  pwFormOpen.value = false;
  pwError.value = "";
  pwSuccess.value = false;
}

async function savePassword() {
  if (!pwForm.current || !pwForm.new) {
    pwError.value = "Please fill in both fields.";
    return;
  }
  if (pwForm.new.length < 8) {
    pwError.value = "New password must be at least 8 characters.";
    return;
  }

  pwSaving.value = true;
  pwError.value = "";
  pwSuccess.value = false;

  try {
    await changePassword(pwForm.current, pwForm.new);
    pwSuccess.value = true;
    pwForm.current = "";
    pwForm.new = "";
  } catch (err) {
    pwError.value = err.response?.data?.detail || "Failed to change password.";
  } finally {
    pwSaving.value = false;
  }
}

function formatDate(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function startEditName() {
  nameEdit.value = authStore.user?.display_name || "";
  editingName.value = true;
}

function cancelEditName() {
  editingName.value = false;
  nameEdit.value = "";
}

async function saveName() {
  savingName.value = true;
  try {
    const updated = await updateMe(nameEdit.value.trim() || null);
    authStore.user = updated;
    editingName.value = false;
  } catch (err) {
    console.error("Failed to update name:", err);
  } finally {
    savingName.value = false;
  }
}

async function handleLogout() {
  loggingOut.value = true;
  await authStore.logout();
  loggingOut.value = false;
  router.push("/");
}

onMounted(async () => {
  if (authStore.isAuthenticated) {
    if (!authStore.user) {
      await authStore.fetchMe();
    }
    try {
      stats.value = await fetchMyStats();
    } catch (err) {
      console.error("Failed to load stats:", err);
    }
  }
});
</script>

<style scoped>
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
</style>

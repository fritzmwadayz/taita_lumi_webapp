<template>
  <div class="max-w-2xl mx-auto px-8 py-16">
    <!-- Loading (session still fetching) -->
    <div v-if="sessionPending" class="text-center py-24">
      <div class="animate-pulse">
        <div class="h-16 bg-cream-200 rounded w-1/3 mx-auto mb-4"></div>
        <div class="h-4 bg-cream-100 rounded w-1/2 mx-auto"></div>
      </div>
    </div>

    <!-- Logged in -->
    <div v-else-if="user">
      <header class="mb-8">
        <p class="text-xs font-semibold tracking-widest uppercase text-ochre mb-2">Profile</p>

        <!-- Display name (editable) -->
        <div v-if="!editingName" class="flex items-center gap-3 mb-2">
          <h1 class="font-serif text-4xl text-forest-dark">{{ displayName }}</h1>
          <button
            class="focus-ring text-stone-light hover:text-forest p-1 rounded"
            title="Edit display name"
            @click="startEditName"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
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
            <button :disabled="savingName" class="focus-ring btn btn-primary btn-sm" @click="saveName">
              {{ savingName ? 'Saving...' : 'Save' }}
            </button>
            <button class="focus-ring btn btn-ghost btn-sm" @click="cancelEditName">Cancel</button>
          </div>
        </div>

        <p class="text-sm text-stone">{{ user.email }}</p>
        <div class="flex items-center gap-2 mt-3">
          <span
            class="status-badge"
            :class="isAdmin ? 'bg-terracotta/15 text-terracotta-dark' : isReviewer ? 'bg-forest-tint text-forest-dark' : 'bg-cream-200 text-stone-dark'"
          >
            {{ isAdmin ? 'Admin' : isReviewer ? 'Reviewer' : 'User' }}
          </span>
          <span class="text-xs text-stone-light">Joined {{ formatDate(user.created_at) }}</span>
        </div>
      </header>

      <!-- Stats -->
      <section class="grid grid-cols-2 md:grid-cols-3 gap-4 mb-8">
        <div class="bg-cream-50 border border-cream-200 rounded-xl p-5 text-center">
          <p class="font-serif text-3xl text-forest-dark font-semibold">{{ stats?.words_added ?? 0 }}</p>
          <p class="text-[10px] uppercase tracking-wider text-stone">Words added</p>
        </div>
        <div class="bg-cream-50 border border-cream-200 rounded-xl p-5 text-center">
          <p class="font-serif text-3xl text-forest-dark font-semibold">{{ stats?.suggestions_submitted ?? 0 }}</p>
          <p class="text-[10px] uppercase tracking-wider text-stone">Suggestions</p>
        </div>
        <div class="bg-cream-50 border border-cream-200 rounded-xl p-5 text-center">
          <p class="font-serif text-3xl text-forest-dark font-semibold">{{ stats?.votes_cast ?? 0 }}</p>
          <p class="text-[10px] uppercase tracking-wider text-stone">Votes cast</p>
        </div>
      </section>

      <!-- Suggestion breakdown -->
      <section v-if="stats && stats.suggestions_submitted > 0" class="mb-8">
        <h2 class="text-xs font-semibold uppercase tracking-widest text-stone mb-3">Your suggestions</h2>
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
      <section v-if="isAdmin" class="mb-8">
        <NuxtLink
          to="/admin"
          class="focus-ring block bg-cream-100 hover:bg-cream-200 border border-cream-200 rounded-xl p-4 transition"
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
        </NuxtLink>
      </section>

      <!-- Reviewer link -->
      <section v-if="isReviewer" class="mb-8">
        <NuxtLink
          to="/review"
          class="focus-ring block bg-forest-tint hover:bg-forest/15 border border-forest/20 rounded-xl p-4 transition"
        >
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm font-semibold text-forest-dark">Review queue</p>
              <p class="text-xs text-stone">Review community suggestions and add words directly.</p>
            </div>
            <svg class="w-5 h-5 text-forest" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
            </svg>
          </div>
        </NuxtLink>
      </section>

      <!-- Change password -->
      <section class="mb-8">
        <h2 class="text-xs font-semibold uppercase tracking-widest text-stone mb-3">Change password</h2>
        <div v-if="!user.oauth_provider" class="bg-cream-50 border border-cream-200 rounded-xl p-5">
          <div v-if="!pwFormOpen">
            <button class="focus-ring text-sm font-semibold text-forest hover:underline" @click="openPwForm">
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
              <button :disabled="pwSaving" class="focus-ring btn btn-primary btn-sm" @click="savePassword">
                {{ pwSaving ? 'Saving...' : 'Save' }}
              </button>
              <button class="focus-ring btn btn-ghost btn-sm" @click="closePwForm">Cancel</button>
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
          :disabled="loggingOut"
          class="focus-ring text-sm font-semibold text-terracotta hover:text-terracotta-dark"
          @click="handleLogout"
        >
          {{ loggingOut ? 'Logging out...' : 'Log out' }}
        </button>
      </section>
    </div>

    <!-- Not logged in (fallback — middleware should redirect) -->
    <div v-else class="text-center py-12">
      <p class="font-serif text-3xl text-forest-dark mb-4">You're not logged in.</p>
      <p class="text-sm text-stone mb-8">Log in to see your profile and contributions.</p>
      <NuxtLink :to="{ path: '/login', query: { next: '/me' } }" class="focus-ring btn btn-primary btn-md">
        Go to login
      </NuxtLink>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import type { UserStats } from '~/types'

definePageMeta({
  middleware: 'auth', // redirect to /login?next=/me if not authenticated
})

const { user, displayName, isAdmin, isReviewer, logout } = useAuth()
const session = useUserSession()
const toast = useToast()
const sessionPending = computed(() => !session.ready.value)

// ── Stats ───────────────────────────────────────────────────────────────────
const stats = ref<UserStats | null>(null)

onMounted(async () => {
  if (user.value) {
    try {
      stats.value = await fetchMyStats()
    } catch (err) {
      console.error('Failed to load stats:', err)
    }
  }
})

// ── Edit name ───────────────────────────────────────────────────────────────
const editingName = ref(false)
const nameEdit = ref('')
const savingName = ref(false)

function startEditName() {
  nameEdit.value = user.value?.display_name || ''
  editingName.value = true
}

function cancelEditName() {
  editingName.value = false
  nameEdit.value = ''
}

async function saveName() {
  savingName.value = true
  try {
    await updateMe(nameEdit.value.trim() || null)
    // Refresh the session to get the updated user
    await session.fetch()
    toast.success('Profile updated')
  } catch (err) {
    console.error('Failed to update name:', err)
    toast.error('Could not update profile')
  } finally {
    savingName.value = false
    editingName.value = false
  }
}

// ── Change password ─────────────────────────────────────────────────────────
const pwFormOpen = ref(false)
const pwForm = reactive({ current: '', new: '' })
const pwSaving = ref(false)
const pwError = ref('')
const pwSuccess = ref(false)

function openPwForm() {
  pwForm.current = ''
  pwForm.new = ''
  pwError.value = ''
  pwSuccess.value = false
  pwFormOpen.value = true
}

function closePwForm() {
  pwFormOpen.value = false
  pwError.value = ''
  pwSuccess.value = false
}

async function savePassword() {
  if (!pwForm.current || !pwForm.new) {
    pwError.value = 'Please fill in both fields.'
    return
  }
  if (pwForm.new.length < 8) {
    pwError.value = 'New password must be at least 8 characters.'
    return
  }
  pwSaving.value = true
  pwError.value = ''
  pwSuccess.value = false
  try {
    await changePassword(pwForm.current, pwForm.new)
    pwSuccess.value = true
    pwForm.current = ''
    pwForm.new = ''
    toast.success('Password changed')
  } catch (err: unknown) {
    const e = err as { response?: { _data?: { detail?: string } } }
    pwError.value = (e.response?._data?.detail as string) || 'Failed to change password.'
  } finally {
    pwSaving.value = false
  }
}

// ── Logout ──────────────────────────────────────────────────────────────────
const loggingOut = ref(false)

async function handleLogout() {
  loggingOut.value = true
  await logout()
  loggingOut.value = false
}

function formatDate(iso: string): string {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}
</script>

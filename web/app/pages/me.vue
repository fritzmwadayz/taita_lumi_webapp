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
      <!-- ═══════════════════════════════════════════════════════════════════ -->
      <!-- Section: Profile                                                       -->
      <!-- ═══════════════════════════════════════════════════════════════════ -->
      <section class="mb-10">
        <h2 class="text-xs font-semibold uppercase tracking-widest text-stone mb-5">Profile</h2>

        <!-- Display name (editable) -->
        <div v-if="!editingName" class="flex items-center gap-3 mb-3">
          <h1 class="font-serif text-4xl text-forest-dark">{{ displayName }}</h1>
          <button
            class="focus-ring text-stone-light hover:text-forest p-1 rounded"
            title="Edit display name"
            @click="startEditName"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
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

        <!-- Email row + change -->
        <div class="mb-4">
          <!-- OAuth-only: email is managed by Google -->
          <div v-if="isOAuthOnly" class="flex items-center justify-between gap-3">
            <div>
              <p class="text-xs text-stone-light uppercase tracking-wider mb-0.5">Email</p>
              <p class="text-sm text-ink">{{ user.email }}</p>
              <p class="text-xs text-stone-light italic mt-1">Your email is managed by Google.</p>
            </div>
          </div>

          <!-- Password-account: show email + Change button or inline form -->
          <div v-else>
            <div v-if="!emailFormOpen" class="flex items-center justify-between gap-3">
              <div>
                <p class="text-xs text-stone-light uppercase tracking-wider mb-0.5">Email</p>
                <p class="text-sm text-ink">{{ user.email }}</p>
              </div>
              <button class="focus-ring text-sm font-semibold text-forest hover:underline" @click="openEmailForm">
                Change
              </button>
            </div>

            <!-- Inline email-change form -->
            <div v-else class="bg-cream-50 border border-cream-200 rounded-xl p-5 mt-2 space-y-3">
              <div>
                <label class="field-label" for="email-new">New email</label>
                <input
                  id="email-new"
                  v-model="emailForm.newEmail"
                  type="email"
                  required
                  class="field"
                  :class="emailError ? 'field-error' : ''"
                  placeholder="alice.new@example.com"
                  :disabled="emailSaving"
                />
              </div>
              <div>
                <label class="field-label" for="email-pw">Current password</label>
                <input
                  id="email-pw"
                  v-model="emailForm.currentPassword"
                  type="password"
                  required
                  class="field"
                  :class="emailError ? 'field-error' : ''"
                  placeholder="Re-enter your password to confirm"
                  :disabled="emailSaving"
                />
              </div>
              <p v-if="emailError" class="text-xs text-terracotta">{{ emailError }}</p>
              <div class="flex gap-2">
                <button :disabled="emailSaving" class="focus-ring btn btn-primary btn-sm" @click="saveEmail">
                  {{ emailSaving ? 'Saving...' : 'Save' }}
                </button>
                <button class="focus-ring btn btn-ghost btn-sm" @click="closeEmailForm">Cancel</button>
              </div>
            </div>
          </div>
        </div>

        <!-- Role + join date -->
        <div class="flex items-center gap-2 mb-4">
          <span
            class="status-badge"
            :class="isAdmin ? 'bg-terracotta/15 text-terracotta-dark' : isReviewer ? 'bg-forest-tint text-forest-dark' : 'bg-cream-200 text-stone-dark'"
          >
            {{ isAdmin ? 'Admin' : isReviewer ? 'Reviewer' : 'User' }}
          </span>
          <span class="text-xs text-stone-light">Joined {{ formatDate(user.created_at) }}</span>
        </div>

        <!-- Connected accounts -->
        <div>
          <p class="text-xs text-stone-light uppercase tracking-wider mb-2">Connected accounts</p>
          <div v-if="connectedPending" class="flex gap-2">
            <div class="h-7 w-24 bg-cream-100 rounded animate-pulse"></div>
            <div class="h-7 w-24 bg-cream-100 rounded animate-pulse"></div>
          </div>
          <div v-else class="flex flex-wrap gap-2">
            <span
              v-if="connected?.google"
              class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold uppercase tracking-wider bg-forest-tint text-forest-dark"
            >
              <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
                <path d="M16.7 5.3a1 1 0 010 1.4l-8 8a1 1 0 01-1.4 0l-4-4a1 1 0 011.4-1.4L8 12.6l7.3-7.3a1 1 0 011.4 0z" />
              </svg>
              Google
            </span>
            <span
              v-if="connected?.has_password"
              class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold uppercase tracking-wider bg-forest-tint text-forest-dark"
            >
              <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
                <path d="M16.7 5.3a1 1 0 010 1.4l-8 8a1 1 0 01-1.4 0l-4-4a1 1 0 011.4-1.4L8 12.6l7.3-7.3a1 1 0 011.4 0z" />
              </svg>
              Password
            </span>
            <span v-if="!connected?.google && !connected?.has_password" class="text-xs text-stone-light italic">
              No connected accounts.
            </span>
          </div>
        </div>
      </section>

      <!-- ═══════════════════════════════════════════════════════════════════ -->
      <!-- Section: My contributions                                             -->
      <!-- ═══════════════════════════════════════════════════════════════════ -->
      <section class="border-t border-cream-200 pt-8 mb-10">
        <h2 class="text-xs font-semibold uppercase tracking-widest text-stone mb-5">My contributions</h2>

        <!-- Stats -->
        <div class="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6">
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
        </div>

        <!-- Suggestion breakdown -->
        <div v-if="stats && stats.suggestions_submitted > 0" class="mb-6">
          <p class="text-xs text-stone-light uppercase tracking-wider mb-3">Your suggestions</p>
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
        </div>

        <!-- Admin link -->
        <NuxtLink
          v-if="isAdmin"
          to="/admin"
          class="focus-ring block bg-cream-100 hover:bg-cream-200 border border-cream-200 rounded-xl p-4 transition mb-3"
        >
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm font-semibold text-ink">Admin dashboard</p>
              <p class="text-xs text-stone">Manage users, words, and suggestions.</p>
            </div>
            <svg class="w-5 h-5 text-forest" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
            </svg>
          </div>
        </NuxtLink>

        <!-- Reviewer link -->
        <NuxtLink
          v-if="isReviewer"
          to="/review"
          class="focus-ring block bg-forest-tint hover:bg-forest/15 border border-forest/20 rounded-xl p-4 transition"
        >
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm font-semibold text-forest-dark">Review queue</p>
              <p class="text-xs text-stone">Review community suggestions and add words directly.</p>
            </div>
            <svg class="w-5 h-5 text-forest" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
            </svg>
          </div>
        </NuxtLink>
      </section>

      <!-- ═══════════════════════════════════════════════════════════════════ -->
      <!-- Section: Security                                                      -->
      <!-- ═══════════════════════════════════════════════════════════════════ -->
      <section class="border-t border-cream-200 pt-8 mb-10">
        <h2 class="text-xs font-semibold uppercase tracking-widest text-stone mb-5">Security</h2>

        <!-- Change password -->
        <div v-if="!isOAuthOnly" class="bg-cream-50 border border-cream-200 rounded-xl p-5">
          <div v-if="!pwFormOpen">
            <button class="focus-ring text-sm font-semibold text-forest hover:underline" @click="openPwForm">
              Change password →
            </button>
          </div>
          <div v-else class="space-y-3">
            <div>
              <label class="field-label" for="pw-current">Current password</label>
              <input id="pw-current" v-model="pwForm.current" type="password" class="field" :disabled="pwSaving" />
            </div>
            <div>
              <label class="field-label" for="pw-new">New password</label>
              <input id="pw-new" v-model="pwForm.new" type="password" class="field" placeholder="At least 8 characters" :disabled="pwSaving" />
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

      <!-- ═══════════════════════════════════════════════════════════════════ -->
      <!-- Section: Danger zone                                                  -->
      <!-- ═══════════════════════════════════════════════════════════════════ -->
      <section class="border-t border-terracotta/30 pt-8 mb-8">
        <h2 class="text-xs font-semibold uppercase tracking-widest text-terracotta mb-5">Danger zone</h2>

        <div class="bg-terracotta-wash/40 border border-terracotta/20 rounded-xl p-5">
          <p class="text-sm font-semibold text-terracotta-dark mb-1">Delete account</p>
          <p class="text-xs text-stone-dark leading-relaxed mb-4">
            This will permanently remove your email, password, and OAuth connections.
            Your contributions (suggestions, words) will remain in the dictionary as
            "deleted user". This cannot be undone.
          </p>

          <!-- OAuth-only: deletion not available -->
          <div v-if="isOAuthOnly">
            <p class="text-xs text-stone-light italic">
              Account deletion is not available for Google sign-in accounts.
            </p>
          </div>

          <!-- Password-account: delete button → confirmation form -->
          <div v-else>
            <div v-if="!deleteFormOpen">
              <button
                class="focus-ring btn btn-danger btn-sm"
                @click="openDeleteForm"
              >
                Delete my account
              </button>
            </div>
            <div v-else class="space-y-3">
              <p class="text-sm font-semibold text-terracotta-dark">Are you sure?</p>
              <div>
                <label class="field-label" for="del-pw">Password</label>
                <input
                  id="del-pw"
                  v-model="deleteForm.password"
                  type="password"
                  required
                  class="field"
                  :class="deleteError ? 'field-error' : ''"
                  placeholder="Enter your password to confirm"
                  :disabled="deleteSaving"
                />
              </div>
              <p v-if="deleteError" class="text-xs text-terracotta">{{ deleteError }}</p>
              <div class="flex gap-2">
                <button :disabled="deleteSaving" class="focus-ring btn btn-danger btn-sm" @click="confirmDelete">
                  {{ deleteSaving ? 'Deleting...' : 'Yes, delete my account' }}
                </button>
                <button class="focus-ring btn btn-ghost btn-sm" @click="closeDeleteForm">Cancel</button>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- Log out -->
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
import { reactive, ref, computed } from 'vue'
import type { UserStats } from '~/types'

definePageMeta({
  middleware: 'auth', // redirect to /login?next=/me if not authenticated
})

const { user, displayName, isAdmin, isReviewer, logout } = useAuth()
const session = useUserSession()
const toast = useToast()
const sessionPending = computed(() => !session.ready.value)

// ── OAuth-only check ──────────────────────────────────────────────────────
// An OAuth-only account has google linked and no password set. We use the
// connected-accounts endpoint as the source of truth once it loads; before
// that we fall back to user.oauth_provider so the UI doesn't flash the
// password form for Google users during the initial load.
const connected = ref<{ google: boolean; has_password: boolean } | null>(null)
const connectedPending = ref(true)

const isOAuthOnly = computed(() => {
  if (connected.value) {
    return connected.value.google && !connected.value.has_password
  }
  // Fallback while loading: a Google user with no password hint
  return user.value?.oauth_provider === 'google'
})

// ── Stats + connected accounts (fetched on mount) ─────────────────────────
const stats = ref<UserStats | null>(null)

onMounted(async () => {
  if (!user.value) return

  // Fire both requests in parallel — they're independent.
  const tasks: Promise<unknown>[] = []

  tasks.push(
    fetchMyStats()
      .then((s) => { stats.value = s })
      .catch((err) => console.error('Failed to load stats:', err)),
  )

  tasks.push(
    getConnectedAccounts()
      .then((c) => { connected.value = c })
      .catch((err) => {
        // Non-fatal — the page still works without the connected-accounts
        // panel. Fall back to the oauth_provider hint.
        console.error('Failed to load connected accounts:', err)
      })
      .finally(() => { connectedPending.value = false }),
  )

  await Promise.allSettled(tasks)
})

// ── Edit name ─────────────────────────────────────────────────────────────
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

// ── Change email ──────────────────────────────────────────────────────────
const emailFormOpen = ref(false)
const emailForm = reactive({ newEmail: '', currentPassword: '' })
const emailSaving = ref(false)
const emailError = ref('')

function openEmailForm() {
  emailForm.newEmail = ''
  emailForm.currentPassword = ''
  emailError.value = ''
  emailFormOpen.value = true
}

function closeEmailForm() {
  emailFormOpen.value = false
  emailForm.newEmail = ''
  emailForm.currentPassword = ''
  emailError.value = ''
}

async function saveEmail() {
  emailError.value = ''

  if (!emailForm.newEmail.trim()) {
    emailError.value = 'Please enter a new email.'
    return
  }
  // Light client-side check; the backend will do the authoritative validation.
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(emailForm.newEmail.trim())) {
    emailError.value = 'Please enter a valid email address.'
    return
  }
  if (!emailForm.currentPassword) {
    emailError.value = 'Please enter your current password.'
    return
  }
  // No-op if the email is unchanged.
  if (emailForm.newEmail.trim().toLowerCase() === (user.value?.email || '').toLowerCase()) {
    emailError.value = 'That is already your email.'
    return
  }

  emailSaving.value = true
  try {
    await changeEmail(emailForm.newEmail.trim(), emailForm.currentPassword)
    // Refresh the session so the cached user reflects the new email.
    await session.fetch()
    toast.success('Email updated')
    closeEmailForm()
  } catch (err: unknown) {
    const e = err as { response?: { status?: number; _data?: { detail?: string } }; message?: string }
    const status = e.response?.status
    if (status === 401) {
      emailError.value = 'Current password is incorrect.'
    } else if (status === 409) {
      emailError.value = 'An account with this email already exists.'
    } else if (status === 400) {
      // OAuth-only — shouldn't happen here because we hide the form, but
      // handle it gracefully.
      emailError.value = 'Your email is managed by Google and cannot be changed here.'
    } else {
      emailError.value = (e.response?._data?.detail as string) || 'Could not change email.'
    }
  } finally {
    emailSaving.value = false
  }
}

// ── Change password ───────────────────────────────────────────────────────
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

// ── Delete account ────────────────────────────────────────────────────────
const deleteFormOpen = ref(false)
const deleteForm = reactive({ password: '' })
const deleteSaving = ref(false)
const deleteError = ref('')

function openDeleteForm() {
  deleteForm.password = ''
  deleteError.value = ''
  deleteFormOpen.value = true
}

function closeDeleteForm() {
  deleteFormOpen.value = false
  deleteForm.password = ''
  deleteError.value = ''
}

async function confirmDelete() {
  deleteError.value = ''
  if (!deleteForm.password) {
    deleteError.value = 'Please enter your password to confirm.'
    return
  }

  deleteSaving.value = true
  try {
    await deleteAccount(deleteForm.password)
    // 204 — success. Clear the session and bounce to the home page.
    await session.clear()
    toast.success('Account deleted.')
    navigateTo('/')
  } catch (err: unknown) {
    const e = err as { response?: { status?: number; _data?: { detail?: string } }; message?: string }
    const status = e.response?.status
    if (status === 401) {
      deleteError.value = 'Password is incorrect.'
    } else if (status === 400) {
      // OAuth-only — form is hidden, but guard anyway.
      deleteError.value = 'Account deletion is not available for Google sign-in accounts.'
    } else {
      deleteError.value = (e.response?._data?.detail as string) || 'Could not delete account.'
    }
  } finally {
    deleteSaving.value = false
  }
}

// ── Logout ────────────────────────────────────────────────────────────────
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

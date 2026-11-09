<template>
  <nav
    class="border-b border-cream-200 bg-cream/95 backdrop-blur px-4 md:px-6 py-3 flex items-center justify-between sticky top-0 z-20"
  >
    <!-- LEFT: brand + desktop nav -->
    <div class="flex items-center gap-4 md:gap-6">
      <NuxtLink to="/" class="flex items-center gap-2 focus-ring rounded-md">
        <div class="w-8 h-8 rounded-lg bg-forest flex items-center justify-center">
          <span class="font-serif text-cream text-base font-bold">L</span>
        </div>
        <span class="font-serif text-lg text-forest-dark font-semibold tracking-tight hidden sm:inline">Lumi</span>
      </NuxtLink>

      <div class="hidden md:flex items-center gap-0.5">
        <NuxtLink to="/" class="focus-ring px-3 py-1.5 rounded-md text-[13px] font-medium text-ink-soft hover:text-ink hover:bg-cream-100 transition">Home</NuxtLink>
        <NuxtLink to="/search" class="focus-ring px-3 py-1.5 rounded-md text-[13px] font-medium text-ink-soft hover:text-ink hover:bg-cream-100 transition">Browse</NuxtLink>
        <NuxtLink to="/contribute" class="focus-ring px-3 py-1.5 rounded-md text-[13px] font-medium text-ink-soft hover:text-ink hover:bg-cream-100 transition">Contribute</NuxtLink>
        <NuxtLink to="/guide" class="focus-ring px-3 py-1.5 rounded-md text-[13px] font-medium text-ink-soft hover:text-ink hover:bg-cream-100 transition">Guide</NuxtLink>
        <template v-if="!isReviewer">
          <NuxtLink to="/support" class="focus-ring px-3 py-1.5 rounded-md text-[13px] font-medium text-ink-soft hover:text-ink hover:bg-cream-100 transition">Support</NuxtLink>
          <NuxtLink to="/contact" class="focus-ring px-3 py-1.5 rounded-md text-[13px] font-medium text-ink-soft hover:text-ink hover:bg-cream-100 transition">Contact</NuxtLink>
        </template>
      </div>
    </div>

    <!-- RIGHT: auth + hamburger -->
    <div class="flex items-center gap-2 relative">
      <!-- Authenticated: profile dropdown (desktop) -->
      <div v-if="isAuthenticated" class="relative" ref="profileDropdownRef">
        <button
          class="focus-ring flex items-center gap-2 px-2 md:px-3 py-1.5 rounded-md hover:bg-cream-100 transition"
          @click="profileDropdownOpen = !profileDropdownOpen"
          :aria-expanded="profileDropdownOpen"
          aria-label="User menu"
        >
          <div class="w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold text-cream" :class="isAdmin ? 'bg-terracotta' : 'bg-forest'">{{ initial }}</div>
          <span class="text-sm font-medium text-ink hidden sm:inline">{{ displayName }}</span>
          <span v-if="isAdmin" class="text-[10px] uppercase tracking-wider text-cream bg-terracotta px-1.5 py-0.5 rounded font-semibold hidden md:inline">admin</span>
          <span v-else-if="isReviewer" class="text-[10px] uppercase tracking-wider text-ochre-dark bg-ochre-tint px-1.5 py-0.5 rounded font-semibold hidden md:inline">reviewer</span>
          <svg class="w-4 h-4 text-stone transition-transform hidden md:block" :class="{ 'rotate-180': profileDropdownOpen }" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
          </svg>
        </button>
        <!-- Profile dropdown (desktop) -->
        <div v-if="profileDropdownOpen" class="absolute right-0 top-full mt-2 w-56 bg-white border border-cream-200 rounded-xl shadow-lift py-1.5 z-30 hidden md:block">
          <div class="px-4 py-2 border-b border-cream-200">
            <p class="text-sm font-semibold text-ink">{{ displayName }}</p>
            <p class="text-xs text-stone-light truncate">{{ user?.email }}</p>
          </div>
          <NuxtLink to="/me" class="focus-ring flex items-center gap-2 px-4 py-2 text-sm text-ink-soft hover:bg-cream-50 hover:text-ink transition" @click="profileDropdownOpen = false">
            <svg class="w-4 h-4 text-stone" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" /></svg>
            Profile
          </NuxtLink>
          <a v-if="isReviewer" :href="bugReportUrl" class="focus-ring flex items-center gap-2 px-4 py-2 text-sm text-ink-soft hover:bg-cream-50 hover:text-ink transition" @click="profileDropdownOpen = false">
            <svg class="w-4 h-4 text-stone" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
            Report bug
          </a>
          <div class="border-t border-cream-200 my-1.5"></div>
          <button class="focus-ring w-full flex items-center gap-2 px-4 py-2 text-sm text-terracotta hover:bg-terracotta-wash transition text-left" @click="handleLogout">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" /></svg>
            Log out
          </button>
        </div>
      </div>

      <!-- Not authenticated: Sign in (desktop) -->
      <button v-else class="focus-ring hidden md:inline-flex btn btn-secondary btn-sm" @click="goToLogin">Sign in</button>

      <!-- Mobile: hamburger (opens drawer) -->
      <button
        class="md:hidden p-1.5 rounded-md text-stone hover:bg-cream-100 focus-ring"
        @click="drawerOpen = true"
        aria-label="Open menu"
      >
        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
        </svg>
      </button>
    </div>

    <!-- Mobile drawer (teleported to body by the component) -->
    <MobileDrawer :open="drawerOpen" @close="drawerOpen = false" />
  </nav>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'

const { isAuthenticated, isAdmin, isReviewer, displayName, initial, user, logout } = useAuth()
const route = useRoute()

const profileDropdownOpen = ref(false)
const drawerOpen = ref(false)
const profileDropdownRef = ref<HTMLElement | null>(null)

const bugReportUrl = computed(() =>
  'mailto:mwadayz@yandex.com?subject=' + encodeURIComponent('Bug report — Lumi'),
)

function goToLogin() { navigateTo({ path: '/login', query: { next: route.fullPath } }) }
async function handleLogout() {
  profileDropdownOpen.value = false
  await logout()
}

watch(() => route.fullPath, () => {
  profileDropdownOpen.value = false
  drawerOpen.value = false
})

function handleClickOutside(e: MouseEvent) {
  if (profileDropdownRef.value && !profileDropdownRef.value.contains(e.target as Node)) {
    profileDropdownOpen.value = false
  }
}
function handleEscape(e: KeyboardEvent) {
  if (e.key !== 'Escape') return
  if (profileDropdownOpen.value) profileDropdownOpen.value = false
  else if (drawerOpen.value) drawerOpen.value = false
}
onMounted(() => {
  document.addEventListener('click', handleClickOutside)
  document.addEventListener('keydown', handleEscape)
})
onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
  document.removeEventListener('keydown', handleEscape)
})
</script>

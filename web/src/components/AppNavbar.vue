<template>
  <nav
    class="border-b border-cream-200 bg-cream/95 backdrop-blur px-4 md:px-8 py-3 flex items-center justify-between sticky top-0 z-20"
  >
    <div class="flex items-center gap-4 md:gap-8">
      <RouterLink to="/" class="flex items-center gap-2 flex-shrink-0">
        <div class="w-8 h-8 rounded-lg bg-forest flex items-center justify-center">
          <span class="font-serif text-cream text-base font-bold">T</span>
        </div>
        <span class="font-serif text-xl text-forest-dark font-semibold tracking-tight hidden sm:inline">
          TaitaLumi
        </span>
      </RouterLink>

      <!-- Desktop nav links -->
      <div class="hidden md:flex items-center gap-1">
        <RouterLink
          v-for="link in navLinks"
          :key="link.to"
          :to="link.to"
          class="nav-link"
          active-class="nav-link-active"
        >
          {{ link.label }}
        </RouterLink>
      </div>
    </div>

    <div class="flex items-center gap-2 md:gap-3 relative">
      <!-- Authenticated: name + dropdown -->
      <div v-if="authStore.isAuthenticated && !authStore.loading" class="relative" ref="dropdownRef">
        <button
          @click="dropdownOpen = !dropdownOpen"
          class="flex items-center gap-2 px-2 md:px-3 py-1.5 rounded-lg hover:bg-cream-100 transition"
        >
          <div class="w-7 h-7 rounded-full bg-forest text-cream flex items-center justify-center text-xs font-semibold">
            {{ initial }}
          </div>
          <span class="text-sm font-medium text-ink hidden sm:inline">{{ authStore.displayName }}</span>
          <svg class="w-4 h-4 text-stone" :class="{ 'rotate-180': dropdownOpen }" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
          </svg>
        </button>

        <div
          v-if="dropdownOpen"
          class="absolute right-0 mt-2 w-48 bg-white border border-cream-200 rounded-lg shadow-lg py-1 z-30"
        >
          <RouterLink to="/me" @click="dropdownOpen = false" class="block px-4 py-2 text-sm text-ink-soft hover:bg-cream-50">
            Profile
          </RouterLink>
          <RouterLink v-if="authStore.isAdmin" to="/admin" @click="dropdownOpen = false" class="block px-4 py-2 text-sm text-ink-soft hover:bg-cream-50">
            Admin
          </RouterLink>
          <button @click="handleLogout" class="block w-full text-left px-4 py-2 text-sm text-terracotta hover:bg-cream-50">
            Log out
          </button>
        </div>
      </div>

      <!-- Not authenticated: show Sign in button (desktop only) -->
      <button
        v-else-if="!authStore.loading"
        @click="goToLogin"
        class="hidden md:block text-xs font-semibold text-forest border border-forest rounded-lg px-4 py-1.5 hover:bg-forest hover:text-cream transition"
      >
        Sign in
      </button>

      <!-- Mobile menu button -->
      <button
        @click="mobileMenuOpen = !mobileMenuOpen"
        class="md:hidden p-1.5 rounded-lg text-stone hover:bg-cream-100"
      >
        <svg v-if="!mobileMenuOpen" class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
        </svg>
        <svg v-else class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    <!-- Mobile menu -->
    <div
      v-if="mobileMenuOpen"
      class="absolute top-full left-0 right-0 bg-cream border-b border-cream-200 md:hidden z-20"
    >
      <div class="px-4 py-3 space-y-1">
        <RouterLink
          v-for="link in navLinks"
          :key="link.to"
          :to="link.to"
          @click="mobileMenuOpen = false"
          class="block px-3 py-2 text-sm font-medium text-ink-soft rounded-lg hover:bg-cream-100"
          active-class="text-forest bg-cream-100"
        >
          {{ link.label }}
        </RouterLink>
        <button
          v-if="!authStore.isAuthenticated && !authStore.loading"
          @click="goToLogin(); mobileMenuOpen = false"
          class="block w-full text-left px-3 py-2 text-sm font-semibold text-forest"
        >
          Sign in
        </button>
      </div>
    </div>
  </nav>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from "vue";
import { RouterLink, useRouter, useRoute } from "vue-router";
import { useAuthStore } from "../stores/auth";

const router = useRouter();
const route = useRoute();
const authStore = useAuthStore();

const dropdownOpen = ref(false);
const dropdownRef = ref(null);
const mobileMenuOpen = ref(false);

const navLinks = [
  { to: "/", label: "Home" },
  { to: "/search", label: "Browse" },
  { to: "/contribute", label: "Contribute" },
  { to: "/guide", label: "Guide" },
  { to: "/support", label: "Support" },
  { to: "/contact", label: "Contact" },
];

const initial = computed(() => {
  const name = authStore.displayName;
  return name ? name[0].toUpperCase() : "?";
});

function goToLogin() {
  router.push({ path: "/login", query: { next: route.fullPath } });
}

async function handleLogout() {
  dropdownOpen.value = false;
  mobileMenuOpen.value = false;
  await authStore.logout();
  router.push("/");
}

function handleClickOutside(e) {
  if (dropdownRef.value && !dropdownRef.value.contains(e.target)) {
    dropdownOpen.value = false;
  }
}

onMounted(() => {
  document.addEventListener("click", handleClickOutside);
});

onUnmounted(() => {
  document.removeEventListener("click", handleClickOutside);
});
</script>

<style scoped>
.nav-link {
  font-size: 13px;
  font-weight: 500;
  color: #374151;
  padding: 6px 12px;
  border-radius: 6px;
  cursor: pointer;
}
.nav-link:hover {
  background: #f5efe3;
  color: #1f2937;
}
.nav-link-active {
  color: #2d5a3d;
  font-weight: 600;
}
</style>

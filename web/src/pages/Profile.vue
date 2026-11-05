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
        <h1 class="font-serif text-4xl text-forest-dark mb-2">
          {{ authStore.displayName }}
        </h1>
        <p class="text-sm text-stone">{{ authStore.user.email }}</p>
        <div class="flex items-center gap-2 mt-3">
          <span
            class="text-[10px] font-semibold uppercase tracking-wider px-2 py-1 rounded"
            :class="authStore.isAdmin ? 'bg-terracotta/15 text-terracotta-dark' : 'bg-cream-200 text-stone'"
          >
            {{ authStore.isAdmin ? "Admin" : "Contributor" }}
          </span>
          <span class="text-xs text-stone-light">
            Joined {{ formatDate(authStore.user.created_at) }}
          </span>
        </div>
      </header>

      <!-- Stats placeholder (Phase 3+ will show real contribution counts) -->
      <section class="grid grid-cols-3 gap-4 mb-8">
        <div class="bg-cream-50 border border-cream-200 rounded-xl p-5 text-center">
          <p class="font-serif text-3xl text-forest-dark font-semibold">0</p>
          <p class="text-[10px] uppercase tracking-wider text-stone">Words added</p>
        </div>
        <div class="bg-cream-50 border border-cream-200 rounded-xl p-5 text-center">
          <p class="font-serif text-3xl text-forest-dark font-semibold">0</p>
          <p class="text-[10px] uppercase tracking-wider text-stone">Suggestions</p>
        </div>
        <div class="bg-cream-50 border border-cream-200 rounded-xl p-5 text-center">
          <p class="font-serif text-3xl text-forest-dark font-semibold">0</p>
          <p class="text-[10px] uppercase tracking-wider text-stone">Votes cast</p>
        </div>
      </section>

      <p class="text-xs text-stone-light italic mb-8">
        Contribution stats will appear here once you start adding words and voting.
      </p>

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
import { ref, onMounted } from "vue";
import { useRouter, RouterLink } from "vue-router";
import { useAuthStore } from "../stores/auth";

const router = useRouter();
const authStore = useAuthStore();
const loggingOut = ref(false);

function formatDate(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

async function handleLogout() {
  loggingOut.value = true;
  await authStore.logout();
  loggingOut.value = false;
  router.push("/");
}

onMounted(() => {
  if (authStore.isAuthenticated && !authStore.user) {
    authStore.fetchMe();
  }
});
</script>

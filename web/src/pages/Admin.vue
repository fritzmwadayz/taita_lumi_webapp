<template>
  <div class="px-12 py-12">
    <!-- Loading -->
    <div v-if="loading" class="animate-pulse">
      <div class="h-10 bg-cream-200 rounded w-1/4 mb-6"></div>
      <div class="grid grid-cols-4 gap-4 mb-8">
        <div v-for="i in 4" :key="i" class="h-24 bg-cream-100 rounded-xl"></div>
      </div>
    </div>

    <!-- Error -->
    <div
      v-else-if="error"
      class="bg-terracotta/10 border border-terracotta/30 rounded-xl p-6 text-sm text-terracotta-dark"
    >
      <p class="font-medium mb-1">Couldn't load admin data</p>
      <p class="text-xs">{{ error }}</p>
    </div>

    <!-- Dashboard -->
    <div v-else-if="stats">
      <header class="mb-8">
        <p class="text-xs font-semibold tracking-widest uppercase text-ochre mb-2">
          Admin
        </p>
        <h1 class="font-serif text-4xl text-forest-dark">Dashboard</h1>
      </header>

      <!-- Stats cards -->
      <section class="grid grid-cols-4 gap-4 mb-10">
        <div class="bg-white border border-cream-200 rounded-xl p-5">
          <p class="font-serif text-3xl text-forest-dark font-semibold">
            {{ stats.total_words.toLocaleString() }}
          </p>
          <p class="text-[10px] uppercase tracking-wider text-stone mt-1">Words</p>
        </div>
        <div class="bg-white border border-cream-200 rounded-xl p-5">
          <p class="font-serif text-3xl text-forest-dark font-semibold">
            {{ stats.total_users }}
          </p>
          <p class="text-[10px] uppercase tracking-wider text-stone mt-1">Users</p>
        </div>
        <div class="bg-white border border-cream-200 rounded-xl p-5">
          <p class="font-serif text-3xl text-terracotta font-semibold">
            {{ stats.open_suggestions }}
          </p>
          <p class="text-[10px] uppercase tracking-wider text-stone mt-1">Open suggestions</p>
        </div>
        <div class="bg-white border border-cream-200 rounded-xl p-5">
          <p class="font-serif text-3xl text-forest font-semibold">
            {{ stats.total_votes }}
          </p>
          <p class="text-[10px] uppercase tracking-wider text-stone mt-1">Votes cast</p>
        </div>
      </section>

      <!-- Two columns: recent words + recent suggestions -->
      <section class="grid grid-cols-2 gap-6 mb-10">
        <!-- Recent words -->
        <div>
          <h2 class="font-serif text-xl text-forest-dark mb-4">Recently added words</h2>
          <div class="space-y-2">
            <div
              v-for="w in stats.recent_words"
              :key="w.id"
              class="bg-white border border-cream-200 rounded-lg p-3 flex items-center justify-between"
            >
              <div>
                <RouterLink
                  :to="`/words/${w.id}`"
                  class="font-serif text-base text-ink font-medium hover:underline"
                >
                  {{ w.headword }}
                </RouterLink>
                <p v-if="w.swahili_gloss" class="text-xs text-stone">{{ w.swahili_gloss }}</p>
              </div>
              <span class="text-[10px] text-stone-light">{{ timeAgo(w.created_at) }}</span>
            </div>
            <div
              v-if="stats.recent_words.length === 0"
              class="text-sm text-stone-light italic text-center py-4"
            >
              No words yet.
            </div>
          </div>
        </div>

        <!-- Recent suggestions -->
        <div>
          <h2 class="font-serif text-xl text-forest-dark mb-4">Recent suggestions</h2>
          <div class="space-y-2">
            <div
              v-for="s in stats.recent_suggestions"
              :key="s.id"
              class="bg-white border border-cream-200 rounded-lg p-3 flex items-center justify-between"
            >
              <div>
                <RouterLink
                  :to="`/suggestions/${s.id}`"
                  class="font-serif text-base text-ink font-medium hover:underline"
                >
                  {{ s.headword || s.target_type }}
                </RouterLink>
                <p class="text-xs text-stone">{{ s.target_type }}</p>
              </div>
              <div class="flex items-center gap-2">
                <span
                  :class="[
                    'text-[10px] font-medium px-2 py-0.5 rounded',
                    s.status === 'open' ? 'bg-cream-100 text-stone' :
                    s.status === 'accepted' ? 'bg-forest/10 text-forest' :
                    'bg-terracotta/10 text-terracotta'
                  ]"
                >
                  {{ s.status }}
                </span>
                <span class="text-[10px] text-stone-light">{{ timeAgo(s.created_at) }}</span>
              </div>
            </div>
            <div
              v-if="stats.recent_suggestions.length === 0"
              class="text-sm text-stone-light italic text-center py-4"
            >
              No suggestions yet.
            </div>
          </div>
        </div>
      </section>

      <!-- Suggestion breakdown -->
      <section class="bg-cream-50 border border-cream-200 rounded-xl p-6 mb-10">
        <h2 class="font-serif text-xl text-forest-dark mb-4">Suggestion breakdown</h2>
        <div class="grid grid-cols-3 gap-4 text-center">
          <div>
            <p class="font-serif text-2xl text-terracotta font-semibold">{{ stats.open_suggestions }}</p>
            <p class="text-[10px] uppercase tracking-wider text-stone">Open</p>
          </div>
          <div>
            <p class="font-serif text-2xl text-forest font-semibold">{{ stats.accepted_suggestions }}</p>
            <p class="text-[10px] uppercase tracking-wider text-stone">Accepted</p>
          </div>
          <div>
            <p class="font-serif text-2xl text-stone font-semibold">{{ stats.rejected_suggestions }}</p>
            <p class="text-[10px] uppercase tracking-wider text-stone">Rejected</p>
          </div>
        </div>
      </section>

      <!-- Admin tools (placeholder links — full pages come in future iterations) -->
      <section>
        <h2 class="font-serif text-xl text-forest-dark mb-4">Admin tools</h2>
        <div class="grid grid-cols-3 gap-4">
          <div class="bg-white border border-cream-200 rounded-xl p-5">
            <p class="font-medium text-ink mb-1">User management</p>
            <p class="text-xs text-stone mb-3">View, block, or promote users.</p>
            <p class="text-xs text-stone-light italic">
              {{ stats.total_users }} users · use API directly for now
            </p>
          </div>
          <div class="bg-white border border-cream-200 rounded-xl p-5">
            <p class="font-medium text-ink mb-1">Word editing</p>
            <p class="text-xs text-stone mb-3">Edit, hide, or merge words.</p>
            <p class="text-xs text-stone-light italic">
              Go to any word's detail page · use API for merge
            </p>
          </div>
          <div class="bg-white border border-cream-200 rounded-xl p-5">
            <p class="font-medium text-ink mb-1">Audit log</p>
            <p class="text-xs text-stone mb-3">Every change, tracked.</p>
            <p class="text-xs text-stone-light italic">
              Use API: GET /api/admin/audit-log
            </p>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { RouterLink } from "vue-router";
import { getStats } from "../api/admin";

const stats = ref(null);
const loading = ref(true);
const error = ref("");

function timeAgo(iso) {
  if (!iso) return "";
  const date = new Date(iso);
  const now = new Date();
  const seconds = Math.floor((now - date) / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

onMounted(async () => {
  try {
    stats.value = await getStats();
  } catch (err) {
    if (err.response?.status === 403) {
      error.value = "You need admin access to view this page.";
    } else {
      error.value = err.message || "Failed to load admin data.";
    }
  } finally {
    loading.value = false;
  }
});
</script>

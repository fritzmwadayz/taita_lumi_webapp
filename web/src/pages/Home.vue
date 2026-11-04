<template>
  <div class="px-12 py-16 grid grid-cols-12 gap-12 items-center">
    <div class="col-span-7">
      <p
        class="text-xs font-semibold tracking-widest uppercase text-ochre mb-3"
      >
        Kamusi ya Kidawida
      </p>
      <h1
        class="font-serif text-5xl text-forest-dark leading-tight mb-4"
      >
        A living dictionary of the Taita language.
      </h1>
      <p class="text-base text-stone leading-relaxed mb-8 max-w-lg">
        Built by and for speakers of Dawida, Sagala, and Kasighau. Browse,
        search, and contribute — Taita to Swahili and English.
      </p>

      <div
        class="search-bar flex items-center gap-3 bg-cream-50 border border-cream-300 rounded-xl px-5 py-4 transition max-w-xl"
      >
        <svg
          class="w-5 h-5 text-stone"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M21 21l-4.35-4.35M11 18a7 7 0 100-14 7 7 0 000 14z"
          />
        </svg>
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Tafuta neno... / Search a word..."
          class="flex-1 bg-transparent text-base text-ink placeholder-stone-light outline-none"
          @keyup.enter="goToSearch"
        />
        <kbd
          class="text-[10px] font-mono text-stone-light bg-cream-100 px-1.5 py-0.5 rounded border border-cream-200"
          >↵</kbd
        >
      </div>

      <div class="flex flex-wrap gap-2 mt-4">
        <button
          v-for="filter in quickFilters"
          :key="filter"
          class="text-xs px-3 py-1.5 bg-cream-100 hover:bg-cream-200 text-ink-soft rounded-full border border-cream-200 transition"
        >
          {{ filter }}
        </button>
      </div>
    </div>

    <div class="col-span-5">
      <div class="flex items-baseline justify-between mb-3">
        <h3 class="font-serif text-base text-forest-dark">Word of the day</h3>
        <span class="text-[10px] text-stone-light uppercase tracking-wider"
          >Coming soon</span
        >
      </div>
      <div
        class="bg-forest text-cream rounded-2xl p-6 relative overflow-hidden"
      >
        <div class="relative">
          <div class="flex items-baseline gap-3 mb-3">
            <h4 class="font-serif text-4xl text-cream font-semibold">
              mlima
            </h4>
            <span
              class="text-[11px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full"
              style="background: rgba(212, 162, 76, 0.25); color: #e8c886"
              >placeholder</span
            >
          </div>
          <p class="text-base text-cream/90 font-medium mb-1">mlima, kilima</p>
          <p class="text-sm text-cream/70 mb-4">mountain, hill</p>
          <p
            class="text-xs text-cream/70 leading-relaxed border-l-2 border-ochre pl-3 mb-4 italic"
          >
            "Mlima ule unawaka kwa moto wa kale."
          </p>
          <a
            href="#"
            class="inline-flex items-center gap-1 text-xs font-semibold text-ochre-light hover:text-cream transition"
          >
            View full entry
            <svg
              class="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M9 5l7 7-7 7"
              />
            </svg>
          </a>
        </div>
      </div>
    </div>

    <!-- API health check — Phase 0b proof that frontend talks to backend -->
    <div class="col-span-12 mt-8">
      <div
        class="bg-cream-50 border border-cream-200 rounded-xl p-4 flex items-center gap-3"
      >
        <div
          :class="[
            'w-2.5 h-2.5 rounded-full',
            healthStatus === 'ok'
              ? 'bg-forest'
              : healthStatus === 'loading'
                ? 'bg-ochre animate-pulse'
                : 'bg-terracotta',
          ]"
        ></div>
        <div class="text-sm">
          <span class="text-stone">API:</span>
          <span v-if="healthStatus === 'loading'" class="text-stone"
            >checking...</span
          >
          <span v-else-if="healthStatus === 'ok'" class="text-forest font-medium"
            >connected · {{ healthResponse }}</span
          >
          <span v-else class="text-terracotta font-medium">{{ healthError }}</span>
        </div>
        <span class="ml-auto text-[10px] text-stone-light uppercase tracking-wider"
          >Phase 0b health check</span
        >
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import api from "../api/client";

const router = useRouter();
const searchQuery = ref("");
const quickFilters = ["All", "Nouns", "Verbs", "Phrases"];

const healthStatus = ref("loading");
const healthResponse = ref("");
const healthError = ref("");

function goToSearch() {
  router.push({ path: "/search", query: { q: searchQuery.value } });
}

onMounted(async () => {
  try {
    const res = await api.get("/api/health");
    healthStatus.value = "ok";
    healthResponse.value = res.data.status;
  } catch (err) {
    healthStatus.value = "error";
    healthError.value = err.message || "Cannot reach API";
  }
});
</script>

<template>
  <nav
    class="border-b border-cream-200 bg-cream/95 backdrop-blur px-8 py-3 flex items-center justify-between sticky top-0 z-10"
  >
    <div class="flex items-center gap-8">
      <RouterLink to="/" class="flex items-center gap-2">
        <div
          class="w-8 h-8 rounded-lg bg-forest flex items-center justify-center"
        >
          <span class="font-serif text-cream text-base font-bold">T</span>
        </div>
        <span
          class="font-serif text-xl text-forest-dark font-semibold tracking-tight"
          >TaitaLumi</span
        >
      </RouterLink>
      <div class="flex items-center gap-1">
        <RouterLink
          v-for="link in navLinks"
          :key="link.to"
          :to="link.to"
          class="nav-link"
          active-class="nav-link-active"
          >{{ link.label }}</RouterLink
        >
      </div>
    </div>
    <div class="flex items-center gap-3">
      <button
        class="text-xs font-semibold text-forest border border-forest rounded-lg px-4 py-1.5 hover:bg-forest hover:text-cream transition"
      >
        Sign in
      </button>
    </div>
  </nav>
</template>

<script setup>
import { RouterLink } from "vue-router";

const navLinks = [
  { to: "/", label: "Home" },
  { to: "/search", label: "Browse" },
  { to: "/suggest", label: "Suggest" },
  { to: "/suggestions", label: "Suggestions" },
  { to: "/guide", label: "Reading Guide" },
  { to: "/donate", label: "Donate" },
];
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

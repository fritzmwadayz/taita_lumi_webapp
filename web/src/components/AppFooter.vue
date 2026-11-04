<template>
  <footer
    class="px-8 py-6 border-t border-cream-200 bg-cream-50 text-center text-xs text-stone"
  >
    <div class="flex items-center justify-center gap-6 mb-2">
      <RouterLink to="/" class="hover:text-forest">About</RouterLink>
      <RouterLink to="/guide" class="hover:text-forest">Reading Guide</RouterLink>
      <RouterLink to="/donate" class="hover:text-forest">Donate</RouterLink>
      <a
        href="https://github.com/fritzmwadayz"
        target="_blank"
        rel="noopener"
        class="hover:text-forest"
        >Source on GitHub</a
      >
    </div>
    <p class="text-stone-light">© 2026 TaitaLumi · MIT License</p>
  </footer>
</template>

<script setup>
import { RouterLink } from "vue-router";
</script>

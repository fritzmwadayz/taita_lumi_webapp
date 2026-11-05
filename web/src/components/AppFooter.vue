<template>
  <footer
    class="px-4 md:px-8 py-6 border-t border-cream-200 bg-cream-50 text-center text-xs text-stone"
  >
    <div class="flex flex-wrap items-center justify-center gap-4 md:gap-6 mb-2">
      <RouterLink to="/guide" class="hover:text-forest">Guide</RouterLink>
      <RouterLink to="/contribute" class="hover:text-forest">Contribute</RouterLink>
      <RouterLink to="/support" class="hover:text-forest">Support</RouterLink>
      <RouterLink to="/contact" class="hover:text-forest">Contact</RouterLink>
      <a href="https://github.com/fritzmwadayz" target="_blank" rel="noopener" class="hover:text-forest">Source on GitHub</a>
    </div>
    <p class="text-stone-light">© 2026 TaitaLumi · MIT License</p>
  </footer>
</template>

<script setup>
import { RouterLink } from "vue-router";
</script>

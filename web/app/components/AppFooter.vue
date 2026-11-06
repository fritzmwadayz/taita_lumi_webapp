<template>
  <footer
    class="px-4 md:px-8 py-6 border-t border-cream-200 bg-cream-50 text-center text-xs text-stone"
  >
    <div class="flex flex-wrap items-center justify-center gap-4 md:gap-6 mb-2">
      <NuxtLink to="/guide" class="hover:text-forest focus-ring rounded">Guide</NuxtLink>
      <NuxtLink to="/contribute" class="hover:text-forest focus-ring rounded">Contribute</NuxtLink>
      <NuxtLink to="/support" class="hover:text-forest focus-ring rounded">Support</NuxtLink>
      <NuxtLink to="/contact" class="hover:text-forest focus-ring rounded">Contact</NuxtLink>
      <a
        href="https://github.com/fritzmwadayz"
        target="_blank"
        rel="noopener"
        class="hover:text-forest focus-ring rounded"
      >
        Source on GitHub
      </a>
    </div>
    <p class="text-stone-light">© 2026 Lumi · MIT License</p>
  </footer>
</template>

<script setup>
// Footer is ported as-is from the Vue source (AppFooter.vue).
// Support + Contact remain here as the fallback for superusers who have them
// hidden from the main navbar (Phase 5).
</script>

<template>
  <div class="px-12 py-24 text-center">
    <p class="text-xs font-semibold tracking-widest uppercase text-ochre mb-3">
      404
    </p>
    <h1 class="font-serif text-5xl text-forest-dark mb-4">
      This page doesn't exist.
    </h1>
    <p class="text-base text-stone mb-8">
      Maybe the URL is wrong, or this page hasn't been built yet.
    </p>
    <RouterLink
      to="/"
      class="inline-block bg-forest hover:bg-forest-dark text-cream font-semibold text-sm px-5 py-2.5 rounded-lg transition"
    >
      Back to home
    </RouterLink>
  </div>
</template>

<script setup>
import { RouterLink } from "vue-router";
</script>

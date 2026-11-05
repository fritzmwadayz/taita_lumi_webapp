<template>
  <!-- App shell: Navbar + RouterView + Footer.
       The Navbar is shown on all pages; individual pages control their own
       internal layout via <template> blocks. -->
  <div class="min-h-screen flex flex-col">
    <AppNavbar />
    <main class="flex-1">
      <RouterView />
    </main>
    <AppFooter />
  </div>
</template>

<script setup>
import { RouterView } from "vue-router";
import AppNavbar from "./components/AppNavbar.vue";
import AppFooter from "./components/AppFooter.vue";
</script>

<template>
  <div class="min-h-screen flex flex-col">
    <AppNavbar />
    <div class="flex-1 flex">
      <!-- Sidebar: persistent for reviewer+admin on ALL pages -->
      <AdminSidebar v-if="showSidebar" />
      <main class="flex-1" :class="showSidebar ? 'overflow-x-auto' : ''">
        <slot />
      </main>
    </div>
    <AppFooter />
  </div>
</template>

<script setup>
// The sidebar is the default view for power users (reviewer + admin).
// It shows on every page — Home, Search, WordDetail, /review, /admin/* —
// providing persistent navigation context.
// Anon and regular users see no sidebar (full-width content).
const { isReviewer } = useAuth()
const showSidebar = computed(() => isReviewer.value)
</script>

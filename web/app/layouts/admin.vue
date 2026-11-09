<template>
  <div class="min-h-screen flex flex-col">
    <AppNavbar />
    <div class="flex-1 flex">
      <AdminSidebar />
      <main class="flex-1 bg-white overflow-x-auto">
        <slot />
      </main>
    </div>
    <AppFooter />
  </div>
</template>

<script setup>
// Admin layout: navbar + sidebar + content + footer.
// Used by all /admin/* pages via definePageMeta({ layout: 'admin' }).
</script>

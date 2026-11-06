<template>
  <aside class="w-52 bg-cream-50 border-r border-cream-200 p-4 hidden md:block flex-shrink-0">
    <!-- Admin-only section -->
    <template v-if="isAdmin">
      <p class="text-[10px] uppercase tracking-widest text-stone-light font-semibold mb-3 px-2">Admin</p>
      <nav class="space-y-0.5 mb-4">
        <NuxtLink
          v-for="item in adminItems"
          :key="item.to"
          :to="item.to"
          class="flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium transition"
          :class="isActive(item.to) ? 'text-forest-dark bg-forest-tint font-semibold' : 'text-ink-soft hover:bg-cream-100'"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" :d="item.icon" />
          </svg>
          {{ item.label }}
        </NuxtLink>
      </nav>
      <div class="border-t border-cream-200 my-4"></div>
      <p class="text-[10px] uppercase tracking-widest text-stone-light font-semibold mb-3 px-2">Review</p>
    </template>

    <!-- Reviewer section (always visible for reviewer+) -->
    <template v-else>
      <p class="text-[10px] uppercase tracking-widest text-stone-light font-semibold mb-3 px-2">Review</p>
    </template>

    <nav class="space-y-0.5 mb-4">
      <NuxtLink
        to="/review"
        class="flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium transition"
        :class="isActive('/review') ? 'text-forest-dark bg-forest-tint font-semibold' : 'text-ink-soft hover:bg-cream-100'"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        Review queue
        <span
          v-if="openCount > 0"
          class="ml-auto inline-flex items-center justify-center text-[10px] font-bold text-cream bg-terracotta rounded-full px-1.5 min-w-[18px] h-[16px]"
        >{{ openCount }}</span>
      </NuxtLink>
    </nav>

    <div class="border-t border-cream-200 my-4"></div>
    <p class="text-[10px] uppercase tracking-widest text-stone-light font-semibold mb-3 px-2">Dictionary</p>

    <nav class="space-y-0.5">
      <NuxtLink
        to="/search"
        class="flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium transition"
        :class="route.path === '/search' ? 'text-forest-dark bg-forest-tint font-semibold' : 'text-ink-soft hover:bg-cream-100'"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-4.35-4.35M11 18a7 7 0 100-14 7 7 0 000 14z" />
        </svg>
        Browse
      </NuxtLink>
      <NuxtLink
        to="/contribute"
        class="flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium transition"
        :class="route.path === '/contribute' ? 'text-forest-dark bg-forest-tint font-semibold' : 'text-ink-soft hover:bg-cream-100'"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
        </svg>
        Contribute
      </NuxtLink>
      <NuxtLink
        to="/guide"
        class="flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium transition"
        :class="route.path === '/guide' ? 'text-forest-dark bg-forest-tint font-semibold' : 'text-ink-soft hover:bg-cream-100'"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253" />
        </svg>
        Reading guide
      </NuxtLink>
    </nav>

    <div class="border-t border-cream-200 my-4"></div>
    <NuxtLink
      to="/"
      class="flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium text-ink-soft hover:bg-cream-100 transition"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
      </svg>
      View site
    </NuxtLink>
  </aside>
</template>

<script setup>
const route = useRoute()
const { isAdmin } = useAuth()

// Fetch open suggestion count for the badge
const { data: openCountData, execute: fetchOpenCount } = useFetch('/api/suggestions', {
  params: { status: 'open', size: 1 },
  immediate: false,
  server: false,
})
const openCount = computed(() => openCountData.value?.total || 0)

// Fetch when component mounts (sidebar is always visible for power users)
onMounted(() => { fetchOpenCount() })

const adminItems = [
  { to: '/admin', label: 'Dashboard', icon: 'M4 6a2 2 0 012-2h12a2 2 0 012 2v12a2 2 0 01-2 2H6a2 2 0 01-2-2V6z' },
  { to: '/admin/users', label: 'Users', icon: 'M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z' },
  { to: '/admin/words', label: 'Words', icon: 'M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13' },
  { to: '/admin/audit-log', label: 'Audit log', icon: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2' },
]

function isActive(to) {
  if (to === '/admin') return route.path === '/admin'
  if (to === '/review') return route.path === '/review'
  return route.path.startsWith(to)
}
</script>

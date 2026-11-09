<template>
  <Teleport to="body">
    <Transition name="drawer">
      <div v-if="open" class="fixed inset-0 z-50 md:hidden">
        <!-- Overlay (tap to close) -->
        <div class="absolute inset-0 bg-ink/40" @click="$emit('close')" />
        <!-- Drawer panel -->
        <div class="absolute top-0 left-0 bottom-0 w-72 bg-cream overflow-y-auto shadow-lift">
          <!-- User header -->
          <div v-if="isAuthenticated" class="bg-forest text-cream p-4 tri-pattern relative">
            <button
              class="absolute top-3 right-3 text-cream/70 hover:text-cream"
              aria-label="Close menu"
              @click="$emit('close')"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
            <div class="flex items-center gap-3">
              <div
                class="w-10 h-10 rounded-full flex items-center justify-center text-sm font-semibold text-cream"
                :class="isAdmin ? 'bg-terracotta' : 'bg-cream/20'"
              >{{ initial }}</div>
              <div>
                <p class="text-sm font-semibold">{{ displayName }}</p>
                <span
                  v-if="isAdmin"
                  class="text-[10px] uppercase tracking-wider text-cream bg-terracotta px-1.5 py-0.5 rounded font-semibold"
                >admin</span>
                <span
                  v-else-if="isReviewer"
                  class="text-[10px] uppercase tracking-wider text-ochre-light bg-ochre/30 px-1.5 py-0.5 rounded font-semibold"
                >reviewer</span>
              </div>
            </div>
          </div>

          <!-- Nav items -->
          <div class="p-3">
            <!-- Admin section -->
            <template v-if="isAdmin">
              <p class="text-[10px] uppercase tracking-widest text-stone-light font-semibold mb-2 px-2">Admin</p>
              <NuxtLink
                v-for="item in adminItems"
                :key="item.to"
                :to="item.to"
                class="flex items-center gap-2 px-3 py-2.5 rounded-md text-sm font-medium transition mb-0.5"
                :class="isActive(item.to) ? 'text-forest-dark bg-forest-tint font-semibold' : 'text-ink-soft hover:bg-cream-100'"
                @click="$emit('close')"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" :d="item.icon" />
                </svg>
                {{ item.label }}
              </NuxtLink>
              <div class="border-t border-cream-200 my-3"></div>
            </template>

            <!-- Review queue (reviewer+) -->
            <NuxtLink
              v-if="isReviewer"
              to="/review"
              class="flex items-center gap-2 px-3 py-2.5 rounded-md text-sm font-medium transition mb-0.5"
              :class="isActive('/review') ? 'text-forest-dark bg-forest-tint font-semibold' : 'text-ink-soft hover:bg-cream-100'"
              @click="$emit('close')"
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

            <div v-if="isReviewer" class="border-t border-cream-200 my-3"></div>

            <!-- Dictionary links -->
            <p class="text-[10px] uppercase tracking-widest text-stone-light font-semibold mb-2 px-2">Dictionary</p>
            <NuxtLink to="/" class="block px-3 py-2.5 rounded-md text-sm font-medium text-ink-soft hover:bg-cream-100 mb-0.5" @click="$emit('close')">Home</NuxtLink>
            <NuxtLink to="/search" class="block px-3 py-2.5 rounded-md text-sm font-medium text-ink-soft hover:bg-cream-100 mb-0.5" @click="$emit('close')">Browse</NuxtLink>
            <NuxtLink to="/contribute" class="block px-3 py-2.5 rounded-md text-sm font-medium text-ink-soft hover:bg-cream-100 mb-0.5" @click="$emit('close')">Contribute</NuxtLink>
            <NuxtLink to="/guide" class="block px-3 py-2.5 rounded-md text-sm font-medium text-ink-soft hover:bg-cream-100 mb-0.5" @click="$emit('close')">Reading guide</NuxtLink>

            <!-- Support + Contact (hidden for reviewer+admin) -->
            <template v-if="!isReviewer">
              <NuxtLink to="/support" class="block px-3 py-2.5 rounded-md text-sm font-medium text-ink-soft hover:bg-cream-100 mb-0.5" @click="$emit('close')">Support</NuxtLink>
              <NuxtLink to="/contact" class="block px-3 py-2.5 rounded-md text-sm font-medium text-ink-soft hover:bg-cream-100 mb-0.5" @click="$emit('close')">Contact</NuxtLink>
            </template>

            <div class="border-t border-cream-200 my-3"></div>

            <!-- Profile / auth -->
            <NuxtLink v-if="isAuthenticated" to="/me" class="block px-3 py-2.5 rounded-md text-sm font-medium text-ink-soft hover:bg-cream-100 mb-0.5" @click="$emit('close')">Profile</NuxtLink>
            <a v-if="isAuthenticated && isReviewer" :href="bugReportUrl" class="block px-3 py-2.5 rounded-md text-sm font-medium text-ink-soft hover:bg-cream-100 mb-0.5" @click="$emit('close')">Report bug</a>
            <button v-if="isAuthenticated" class="block w-full text-left px-3 py-2.5 rounded-md text-sm font-medium text-terracotta hover:bg-terracotta-wash" @click="handleLogout">Log out</button>
            <NuxtLink v-else :to="{ path: '/login', query: { next: route.fullPath } }" class="block px-3 py-2.5 rounded-md text-sm font-semibold text-forest" @click="$emit('close')">Sign in</NuxtLink>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
const props = defineProps<{ open: boolean }>()
const emit = defineEmits<{ close: [] }>()

const { isAuthenticated, isAdmin, isReviewer, displayName, initial, logout } = useAuth()
const route = useRoute()

const { data: openCountData, execute: fetchOpenCount } = useFetch('/api/suggestions', {
  params: { status: 'open', size: 1 },
  immediate: false,
  server: false,
})
const openCount = computed(() => openCountData.value?.total || 0)
watch(() => props.open, (v) => { if (v && isReviewer.value) fetchOpenCount() })

const bugReportUrl = computed(() =>
  'mailto:mwadayz@yandex.com?subject=' + encodeURIComponent('Bug report — Lumi'),
)

const adminItems = [
  { to: '/admin', label: 'Dashboard', icon: 'M4 6a2 2 0 012-2h12a2 2 0 012 2v12a2 2 0 01-2 2H6a2 2 0 01-2-2V6z' },
  { to: '/admin/users', label: 'Users', icon: 'M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z' },
  { to: '/admin/words', label: 'Words', icon: 'M12 6.253v13' },
  { to: '/admin/audit-log', label: 'Audit log', icon: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2' },
]

function isActive(to: string) {
  if (to === '/admin') return route.path === '/admin'
  if (to === '/review') return route.path === '/review'
  return route.path.startsWith(to)
}

async function handleLogout() {
  emit('close')
  await logout()
}

// Close drawer on route change
watch(() => route.fullPath, () => emit('close'))
</script>

<style scoped>
.drawer-enter-active,
.drawer-leave-active {
  transition: opacity 0.2s ease;
}
.drawer-enter-active > div:last-child,
.drawer-leave-active > div:last-child {
  transition: transform 0.2s ease;
}
.drawer-enter-from,
.drawer-leave-to {
  opacity: 0;
}
.drawer-enter-from > div:last-child,
.drawer-leave-to > div:last-child {
  transform: translateX(-100%);
}
</style>

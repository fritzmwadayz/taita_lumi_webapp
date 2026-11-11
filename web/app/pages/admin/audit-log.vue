<template>
  <div class="p-6 md:p-8">
    <header class="mb-6">
      <p class="text-xs font-semibold tracking-widest uppercase text-ochre mb-2">Admin · Audit log</p>
      <h1 class="font-serif text-2xl text-forest-dark">Audit log</h1>
      <p class="text-sm text-stone mt-1">Every change, tracked. {{ total }} entries.</p>
    </header>

    <!-- Filter bar -->
    <div class="flex items-center gap-3 mb-4">
      <span class="text-[10px] uppercase tracking-widest text-stone-light font-semibold">Filter:</span>
      <select v-model="actionFilter" class="focus-ring px-3 py-1.5 rounded-md border border-cream-200 bg-cream-50 text-xs text-ink">
        <option value="">All actions</option>
        <option v-for="action in actionTypes" :key="action" :value="action">{{ action }}</option>
      </select>
    </div>

    <!-- Table -->
    <div v-if="pending" class="space-y-2">
      <div v-for="i in 5" :key="i" class="h-10 bg-cream-100 rounded-lg animate-pulse"></div>
    </div>

    <!-- Not pending: show table (desktop) or cards (mobile) -->
    <div v-else>
      <!-- Desktop table -->
      <div class="hidden md:block bg-cream-50 border border-cream-200 rounded-xl overflow-hidden">
      <table class="w-full text-sm">
        <thead class="bg-cream-100 text-[10px] uppercase tracking-wider text-stone-light">
          <tr>
            <th class="text-left px-4 py-2 font-semibold">When</th>
            <th class="text-left px-4 py-2 font-semibold">Actor</th>
            <th class="text-left px-4 py-2 font-semibold">Action</th>
            <th class="text-left px-4 py-2 font-semibold hidden md:table-cell">Target</th>
            <th class="text-left px-4 py-2 font-semibold hidden lg:table-cell">Details</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-cream-200 bg-white">
          <tr v-for="entry in entries" :key="entry.id" class="hover:bg-cream-50 transition">
            <td class="px-4 py-2 text-xs text-stone-light whitespace-nowrap">{{ timeAgo(entry.created_at) }}</td>
            <td class="px-4 py-2 text-xs">
              <span class="font-medium text-ink">{{ entry.actor_email || 'system' }}</span>
              <span
                v-if="entry.actor_role"
                class="ml-1 text-[10px] px-1.5 py-0.5 rounded font-semibold"
                :class="entry.actor_role === 'admin' ? 'bg-terracotta-tint text-terracotta-dark' : 'bg-forest-tint text-forest-dark'"
              >{{ entry.actor_role }}</span>
            </td>
            <td class="px-4 py-2 text-xs text-ink-soft font-mono">{{ entry.action }}</td>
            <td class="px-4 py-2 text-xs text-stone hidden md:table-cell">
              {{ entry.target_type }}:<span class="font-mono">{{ (entry.target_id || '').slice(0, 8) }}</span>
            </td>
            <td class="px-4 py-2 text-xs text-stone-light hidden lg:table-cell">
              <code class="font-mono text-[10px] bg-cream-100 px-1 py-0.5 rounded">{{ formatDetails(entry.details) }}</code>
            </td>
          </tr>
        </tbody>
      </table>
      </div>

      <!-- Mobile cards -->
      <div class="md:hidden space-y-2">
      <div v-for="entry in entries" :key="entry.id" class="bg-white border border-cream-200 rounded-lg p-2.5">
        <div class="flex items-center justify-between mb-0.5">
          <span class="text-[10px] font-medium text-ink">{{ entry.actor_email || 'system' }}</span>
          <span v-if="entry.actor_role" class="text-[8px] px-1 py-0.5 rounded font-semibold" :class="entry.actor_role === 'admin' ? 'text-cream bg-terracotta' : 'text-cream bg-forest'">{{ entry.actor_role }}</span>
        </div>
        <p class="text-[10px] text-stone-dark font-mono">{{ entry.action }}</p>
        <p class="text-[9px] text-stone-light mt-0.5">{{ timeAgo(entry.created_at) }} · {{ entry.target_type }}:{{ (entry.target_id || '').slice(0, 8) }}</p>
      </div>
      </div>
    </div>

    <!-- Pagination -->
    <div v-if="total > pageSize" class="mt-4 flex items-center justify-between text-xs">
      <p class="text-stone-light">Page {{ page }} of {{ Math.ceil(total / pageSize) }}</p>
      <div class="flex gap-2">
        <button :disabled="page <= 1" class="focus-ring btn btn-ghost btn-sm" @click="page--; refresh()">← Prev</button>
        <button :disabled="page * pageSize >= total" class="focus-ring btn btn-ghost btn-sm" @click="page++; refresh()">Next →</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { AuditLogEntry } from '~/types'

definePageMeta({
  ssr: false,
  middleware: 'admin',
})

// ── SEO ───────────────────────────────────────────────────────────────────
useSiteSeo({ noindex: true })

const page = ref(1)
const pageSize = 20
const actionFilter = ref('')

const actionTypes = [
  'word.create',
  'word.update',
  'word.hide',
  'word.merge',
  'word.import',
  'translation.create',
  'example.create',
  'sense.create',
  'sense.update',
  'variation.create',
  'relationship.create',
  'suggestion.accept',
  'suggestion.reject',
  'user.role.change',
  'user.block',
  'user.unblock',
]

const { data, pending, refresh: _refresh } = await useFetch<{ items: AuditLogEntry[]; total: number }>('/api/admin/audit-log', {
  params: { page, size: pageSize },
})

const entries = computed(() => {
  let items = data.value?.items || []
  if (actionFilter.value) {
    items = items.filter(e => e.action === actionFilter.value)
  }
  return items
})

const total = computed(() => data.value?.total || 0)

// Re-fetch when page changes
watch(page, () => _refresh())

function timeAgo(iso: string): string {
  const date = new Date(iso)
  const seconds = Math.floor((Date.now() - date.getTime()) / 1000)
  if (seconds < 60) return 'just now'
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  if (days < 7) return `${days}d ago`
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

function formatDetails(details: Record<string, unknown> | null): string {
  if (!details) return '—'
  return JSON.stringify(details).slice(0, 60)
}
</script>

<template>
  <div class="p-6 md:p-8">
    <header class="mb-8">
      <p class="text-xs font-semibold tracking-widest uppercase text-ochre mb-2">Admin · Overview</p>
      <h1 class="font-serif text-3xl text-forest-dark">Site health</h1>
    </header>

    <div v-if="pending" class="animate-pulse space-y-4">
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div v-for="i in 4" :key="i" class="h-24 bg-cream-100 rounded-xl"></div>
      </div>
    </div>

    <div v-else-if="stats">
      <!-- Stat cards -->
      <section class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8">
        <div class="bg-cream-50 border border-cream-200 rounded-xl p-4">
          <p class="text-[10px] uppercase tracking-wider text-stone-light mb-1">Words</p>
          <p class="font-serif text-3xl text-forest-dark font-semibold">{{ stats.total_words.toLocaleString() }}</p>
          <p class="text-[10px] text-forest mt-1">↑ 24 this week</p>
        </div>
        <div class="bg-cream-50 border border-cream-200 rounded-xl p-4">
          <p class="text-[10px] uppercase tracking-wider text-stone-light mb-1">Users</p>
          <p class="font-serif text-3xl text-forest-dark font-semibold">{{ stats.total_users }}</p>
          <p class="text-[10px] text-forest mt-1">↑ 8 this week</p>
        </div>
        <div class="bg-cream-50 border border-cream-200 rounded-xl p-4">
          <p class="text-[10px] uppercase tracking-wider text-stone-light mb-1">Open suggestions</p>
          <p class="font-serif text-3xl text-terracotta font-semibold">{{ stats.open_suggestions }}</p>
          <p class="text-[10px] text-stone-light mt-1">↓ 3 from last week</p>
        </div>
        <div class="bg-cream-50 border border-cream-200 rounded-xl p-4">
          <p class="text-[10px] uppercase tracking-wider text-stone-light mb-1">Votes cast</p>
          <p class="font-serif text-3xl text-forest font-semibold">{{ stats.total_votes.toLocaleString() }}</p>
          <p class="text-[10px] text-forest mt-1">↑ 142 this week</p>
        </div>
      </section>

      <!-- Recent activity -->
      <section class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        <div>
          <h2 class="font-serif text-lg text-forest-dark font-semibold mb-3">Recently added words</h2>
          <div class="space-y-1.5">
            <NuxtLink
              v-for="w in stats.recent_words"
              :key="w.id"
              :to="`/words/${w.id}`"
              class="focus-ring flex items-center justify-between bg-cream-50 hover:bg-cream-100 border border-cream-200 rounded-lg p-3 transition"
            >
              <div>
                <p class="font-serif text-base text-ink font-medium">{{ w.headword }}</p>
                <p class="text-xs text-stone">{{ w.swahili_gloss }}</p>
              </div>
              <span class="text-[10px] text-stone-light">{{ timeAgo(w.created_at) }}</span>
            </NuxtLink>
          </div>
        </div>
        <div>
          <h2 class="font-serif text-lg text-forest-dark font-semibold mb-3">Recent suggestions</h2>
          <div class="space-y-1.5">
            <NuxtLink
              v-for="s in stats.recent_suggestions"
              :key="s.id"
              :to="`/suggestions/${s.id}`"
              class="focus-ring flex items-center justify-between bg-cream-50 hover:bg-cream-100 border border-cream-200 rounded-lg p-3 transition"
            >
              <div>
                <p class="font-serif text-base text-ink font-medium">{{ s.headword || s.target_type }}</p>
                <p class="text-xs text-stone">{{ s.target_type }}</p>
              </div>
              <div class="flex items-center gap-2">
                <span class="status-badge" :class="statusClass(s.status)">{{ s.status }}</span>
                <span class="text-[10px] text-stone-light">{{ timeAgo(s.created_at) }}</span>
              </div>
            </NuxtLink>
          </div>
        </div>
      </section>

      <!-- Suggestion breakdown -->
      <section class="bg-cream-50 border border-cream-200 rounded-xl p-5 mb-8">
        <h2 class="font-serif text-lg text-forest-dark font-semibold mb-4">Suggestion breakdown</h2>
        <div class="grid grid-cols-3 gap-4 text-center mb-4">
          <div><p class="font-serif text-2xl text-terracotta font-semibold">{{ stats.open_suggestions }}</p><p class="text-[10px] uppercase tracking-wider text-stone-light mt-1">Open</p></div>
          <div><p class="font-serif text-2xl text-forest font-semibold">{{ stats.accepted_suggestions }}</p><p class="text-[10px] uppercase tracking-wider text-stone-light mt-1">Accepted</p></div>
          <div><p class="font-serif text-2xl text-stone font-semibold">{{ stats.rejected_suggestions }}</p><p class="text-[10px] uppercase tracking-wider text-stone-light mt-1">Rejected</p></div>
        </div>
        <div class="flex h-2 rounded-full overflow-hidden bg-cream-200">
          <div class="bg-terracotta" :style="{ width: pct(stats.open_suggestions) }"></div>
          <div class="bg-forest" :style="{ width: pct(stats.accepted_suggestions) }"></div>
          <div class="bg-stone" :style="{ width: pct(stats.rejected_suggestions) }"></div>
        </div>
        <p class="text-[10px] text-stone-light mt-2">Lifetime: {{ stats.open_suggestions + stats.accepted_suggestions + stats.rejected_suggestions }} total · {{ Math.round(stats.accepted_suggestions / (stats.open_suggestions + stats.accepted_suggestions + stats.rejected_suggestions) * 100) }}% accepted</p>
      </section>

      <!-- Audit log preview -->
      <section>
        <div class="flex items-baseline justify-between mb-3">
          <h2 class="font-serif text-lg text-forest-dark font-semibold">Recent audit log</h2>
          <NuxtLink to="/admin/audit-log" class="text-xs font-semibold text-forest hover:underline">Full log →</NuxtLink>
        </div>
        <div class="bg-cream-50 border border-cream-200 rounded-xl overflow-hidden">
          <table class="w-full text-sm">
            <thead class="bg-cream-100 text-[10px] uppercase tracking-wider text-stone-light">
              <tr>
                <th class="text-left px-4 py-2 font-semibold">When</th>
                <th class="text-left px-4 py-2 font-semibold">Actor</th>
                <th class="text-left px-4 py-2 font-semibold">Action</th>
                <th class="text-left px-4 py-2 font-semibold hidden md:table-cell">Target</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-cream-200 bg-white">
              <tr v-for="entry in auditPreview" :key="entry.id" class="hover:bg-cream-50 transition">
                <td class="px-4 py-2 text-xs text-stone-light">{{ timeAgo(entry.created_at) }}</td>
                <td class="px-4 py-2 text-xs">
                  <span class="font-medium text-ink">{{ entry.actor_email || 'system' }}</span>
                  <span v-if="entry.actor_role" class="ml-1 text-[10px] px-1.5 py-0.5 rounded font-semibold" :class="entry.actor_role === 'admin' ? 'bg-terracotta-tint text-terracotta-dark' : 'bg-forest-tint text-forest-dark'">{{ entry.actor_role }}</span>
                </td>
                <td class="px-4 py-2 text-xs text-ink-soft">{{ entry.action }}</td>
                <td class="px-4 py-2 text-xs text-stone hidden md:table-cell">{{ entry.target_type }}:{{ (entry.target_id || '').slice(0, 8) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { AdminStats, AuditLogEntry } from '~/types'

definePageMeta({
  ssr: false,
  middleware: 'admin',
})

const { data: stats, pending } = await useFetch<AdminStats>('/api/admin/stats')
const { data: auditData } = await useFetch<{ items: AuditLogEntry[] }>('/api/admin/audit-log', {
  params: { size: 5 },
})

const auditPreview = computed(() => auditData.value?.items || [])

function statusClass(status: string) {
  if (status === 'accepted') return 'status-accepted'
  if (status === 'rejected') return 'status-rejected'
  return 'status-open'
}

function pct(n: number) {
  const total = (stats.value?.open_suggestions || 0) + (stats.value?.accepted_suggestions || 0) + (stats.value?.rejected_suggestions || 0)
  return total > 0 ? `${(n / total * 100)}%` : '0%'
}

function timeAgo(iso: string): string {
  if (!iso) return ''
  const date = new Date(iso)
  const now = new Date()
  const seconds = Math.floor((now.getTime() - date.getTime()) / 1000)
  if (seconds < 60) return 'just now'
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  if (days < 7) return `${days}d ago`
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}
</script>

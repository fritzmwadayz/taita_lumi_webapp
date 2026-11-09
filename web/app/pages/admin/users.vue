<template>
  <div class="p-6 md:p-8">
    <header class="mb-6">
      <p class="text-xs font-semibold tracking-widest uppercase text-ochre mb-2">Admin · Users</p>
      <h1 class="font-serif text-2xl text-forest-dark">User management</h1>
      <p class="text-sm text-stone mt-1">{{ total }} users total</p>
    </header>

    <div v-if="pending" class="animate-pulse">
      <div v-for="i in 5" :key="i" class="h-12 bg-cream-100 rounded-lg mb-2"></div>
    </div>

    <!-- Not pending: show table (desktop) or cards (mobile) -->
    <div v-else>
      <!-- Desktop table -->
      <div class="hidden md:block bg-cream-50 border border-cream-200 rounded-xl overflow-hidden">
      <table class="w-full text-sm">
        <thead class="bg-cream-100 text-[10px] uppercase tracking-wider text-stone-light">
          <tr>
            <th class="text-left px-4 py-3 font-semibold">User</th>
            <th class="text-left px-4 py-3 font-semibold">Role</th>
            <th class="text-left px-4 py-3 font-semibold hidden md:table-cell">Joined</th>
            <th class="text-left px-4 py-3 font-semibold hidden md:table-cell">Last seen</th>
            <th class="text-right px-4 py-3 font-semibold">Actions</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-cream-200 bg-white">
          <tr v-for="user in users" :key="user.id" class="hover:bg-cream-50 transition" :class="{ 'opacity-50': user.is_blocked }">
            <td class="px-4 py-3">
              <p class="text-sm font-medium text-ink">{{ user.display_name || '(no name)' }}</p>
              <p class="text-xs text-stone-light">{{ user.email }}</p>
            </td>
            <td class="px-4 py-3">
              <span class="status-badge" :class="roleClass(user.role)">{{ user.role }}</span>
              <span v-if="user.is_blocked" class="ml-1 text-[10px] text-terracotta-dark bg-terracotta-wash px-1.5 py-0.5 rounded font-semibold">blocked</span>
            </td>
            <td class="px-4 py-3 text-xs text-stone hidden md:table-cell">{{ formatDate(user.created_at) }}</td>
            <td class="px-4 py-3 text-xs text-stone-light hidden md:table-cell">{{ user.last_seen_at ? timeAgo(user.last_seen_at) : 'never' }}</td>
            <td class="px-4 py-3 text-right">
              <div v-if="user.id !== currentUserId" class="flex items-center justify-end gap-1.5">
                <button
                  v-if="user.role !== 'admin'"
                  class="focus-ring text-[10px] font-medium text-forest-dark bg-forest-tint hover:bg-forest/20 px-2 py-1 rounded transition"
                  :disabled="actingId === user.id"
                  @click="changeRole(user.id, 'admin')"
                >Make admin</button>
                <button
                  v-if="user.role === 'admin'"
                  class="focus-ring text-[10px] font-medium text-stone-dark bg-cream-200 hover:bg-cream-300 px-2 py-1 rounded transition"
                  :disabled="actingId === user.id"
                  @click="changeRole(user.id, 'user')"
                >Demote</button>
                <button
                  v-if="user.role !== 'reviewer' && user.role !== 'admin'"
                  class="focus-ring text-[10px] font-medium text-ochre-dark bg-ochre-tint hover:bg-ochre/20 px-2 py-1 rounded transition"
                  :disabled="actingId === user.id"
                  @click="changeRole(user.id, 'reviewer')"
                >Make reviewer</button>
                <button
                  v-if="!user.is_blocked"
                  class="focus-ring text-[10px] font-medium text-terracotta-dark bg-terracotta-tint hover:bg-terracotta/20 px-2 py-1 rounded transition"
                  :disabled="actingId === user.id"
                  @click="toggleBlock(user.id, true)"
                >Block</button>
                <button
                  v-else
                  class="focus-ring text-[10px] font-medium text-forest-dark bg-forest-tint hover:bg-forest/20 px-2 py-1 rounded transition"
                  :disabled="actingId === user.id"
                  @click="toggleBlock(user.id, false)"
                >Unblock</button>
              </div>
              <span v-else class="text-[10px] text-stone-light italic">You</span>
            </td>
          </tr>
        </tbody>
      </table>
      </div>

      <!-- Mobile cards -->
      <div class="md:hidden space-y-2">
      <div
        v-for="user in users"
        :key="user.id"
        class="bg-cream-50 border border-cream-200 rounded-lg p-3"
        :class="{ 'opacity-50': user.is_blocked }"
      >
        <div class="flex items-center justify-between mb-1">
          <p class="text-sm font-medium text-ink">{{ user.display_name || '(no name)' }}</p>
          <span class="status-badge" :class="roleClass(user.role)">{{ user.role }}</span>
        </div>
        <p class="text-xs text-stone-light mb-1">{{ user.email }}</p>
        <p class="text-[10px] text-stone-light mb-2">Joined {{ formatDate(user.created_at) }} · {{ user.last_seen_at ? timeAgo(user.last_seen_at) : 'never' }}</p>
        <div v-if="user.is_blocked" class="inline-block text-[10px] text-terracotta-dark bg-terracotta-wash px-1.5 py-0.5 rounded font-semibold mb-2">blocked</div>
        <div v-if="user.id !== currentUserId" class="flex flex-wrap gap-1.5">
          <button v-if="user.role !== 'admin'" class="text-[10px] font-medium text-forest-dark bg-forest-tint px-2 py-1 rounded" :disabled="actingId === user.id" @click="changeRole(user.id, 'admin')">Make admin</button>
          <button v-if="user.role === 'admin'" class="text-[10px] font-medium text-stone-dark bg-cream-200 px-2 py-1 rounded" :disabled="actingId === user.id" @click="changeRole(user.id, 'user')">Demote</button>
          <button v-if="user.role !== 'reviewer' && user.role !== 'admin'" class="text-[10px] font-medium text-ochre-dark bg-ochre-tint px-2 py-1 rounded" :disabled="actingId === user.id" @click="changeRole(user.id, 'reviewer')">Make reviewer</button>
          <button v-if="!user.is_blocked" class="text-[10px] font-medium text-terracotta-dark bg-terracotta-tint px-2 py-1 rounded" :disabled="actingId === user.id" @click="toggleBlock(user.id, true)">Block</button>
          <button v-else class="text-[10px] font-medium text-forest-dark bg-forest-tint px-2 py-1 rounded" :disabled="actingId === user.id" @click="toggleBlock(user.id, false)">Unblock</button>
        </div>
        <p v-else class="text-[10px] text-stone-light italic">You</p>
      </div>
    </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { AdminUser } from '~/types'

definePageMeta({
  ssr: false,
  middleware: 'admin',
})

const { data, pending, refresh } = await useFetch<{ items: AdminUser[]; total: number }>('/api/admin/users')
const users = computed(() => data.value?.items || [])
const total = computed(() => data.value?.total || 0)
const actingId = ref<string | null>(null)
const { user: currentUser } = useAuth()
const currentUserId = computed(() => currentUser.value?.id)

async function changeRole(userId: string, role: string) {
  actingId.value = userId
  try {
    await updateAdminUser(userId, { role })
    await refresh()
  } catch (err) {
    console.error('Failed to change role:', err)
  } finally {
    actingId.value = null
  }
}

async function toggleBlock(userId: string, isBlocked: boolean) {
  actingId.value = userId
  try {
    await updateAdminUser(userId, { is_blocked: isBlocked })
    await refresh()
  } catch (err) {
    console.error('Failed to toggle block:', err)
  } finally {
    actingId.value = null
  }
}

function roleClass(role: string) {
  if (role === 'admin') return 'bg-terracotta-tint text-terracotta-dark'
  if (role === 'reviewer') return 'bg-forest-tint text-forest-dark'
  return 'bg-cream-200 text-stone-dark'
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

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
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}
</script>

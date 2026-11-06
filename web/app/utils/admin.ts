// ── Lumi — admin API wrappers (auto-imported) ──────────────────────────────
import type { AdminStats, AdminUserListResponse, AuditLogResponse } from '~/types'

export async function getAdminStats(): Promise<AdminStats> {
  return await $fetch<AdminStats>('/api/admin/stats')
}

export async function listAdminUsers(
  params: { page?: number; size?: number } = {},
): Promise<AdminUserListResponse> {
  return await $fetch<AdminUserListResponse>('/api/admin/users', { params })
}

export async function updateAdminUser(
  userId: string,
  data: { role?: string; is_blocked?: boolean },
): Promise<Record<string, unknown>> {
  return await $fetch(`/api/admin/users/${userId}`, { method: 'PATCH', body: data })
}

export async function adminHideWord(wordId: string): Promise<Record<string, unknown>> {
  return await $fetch(`/api/admin/words/${wordId}/hide`, { method: 'POST' })
}

export async function adminMergeWords(
  sourceId: string,
  targetId: string,
): Promise<Record<string, unknown>> {
  return await $fetch('/api/admin/words/merge', {
    method: 'POST',
    body: { source_id: sourceId, target_id: targetId },
  })
}

export async function getAuditLog(
  params: { page?: number; size?: number; action?: string } = {},
): Promise<AuditLogResponse> {
  return await $fetch<AuditLogResponse>('/api/admin/audit-log', { params })
}

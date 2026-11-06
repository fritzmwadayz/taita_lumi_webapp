// ── Lumi — suggestions API wrappers ───────────────────────────────────────
// Auto-imported by Nuxt.

import type {
  SuggestionListResponse,
  VoteResponse,
  DecideResponse,
} from '~/types'

export interface ListSuggestionsParams {
  status?: string
  target_type?: string
  page?: number
  size?: number
}

/** Create a new suggestion. */
export async function createSuggestion(data: {
  target_type: string
  target_id?: string | null
  field_path?: string | null
  proposed_value: Record<string, unknown>
  rationale?: string | null
}): Promise<Record<string, unknown>> {
  return await $fetch('/api/suggestions', { method: 'POST', body: data })
}

/** List suggestions with optional filters. */
export async function listSuggestions(
  params: ListSuggestionsParams = {},
): Promise<SuggestionListResponse> {
  return await $fetch<SuggestionListResponse>('/api/suggestions', { params })
}

/** Get a single suggestion by ID. */
export async function getSuggestion<T = Record<string, unknown>>(id: string): Promise<T> {
  return await $fetch<T>(`/api/suggestions/${id}`)
}

/** Cast or change a vote on a suggestion. Requires auth. */
export async function castVote(
  id: string,
  vote: 'up' | 'down',
): Promise<VoteResponse> {
  return await $fetch<VoteResponse>(`/api/suggestions/${id}/vote`, {
    method: 'POST',
    body: { vote },
  })
}

/** Remove the current user's vote. */
export async function removeVote(id: string): Promise<Record<string, unknown>> {
  return await $fetch(`/api/suggestions/${id}/vote`, { method: 'DELETE' })
}

/** Reviewer/admin accepts or rejects a suggestion. */
export async function decideSuggestion(
  id: string,
  decision: 'accept' | 'reject',
): Promise<DecideResponse> {
  return await $fetch<DecideResponse>(`/api/suggestions/${id}/decide`, {
    method: 'POST',
    body: { decision },
  })
}

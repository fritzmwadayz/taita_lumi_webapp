// ── Lumi — words API wrappers ─────────────────────────────────────────────
// All calls go through the Nitro catch-all proxy (server/api/[...].ts) which
// forwards to FastAPI with auth + anon cookie attached.
//
// Auto-imported by Nuxt.

import type { WordListResponse, WordDetail, SearchResponse } from '~/types'

export interface ListWordsParams {
  q?: string
  pos?: string
  dialect?: string
  page?: number
  size?: number
}

/** List words with optional filters and pagination. */
export async function listWords(params: ListWordsParams = {}): Promise<WordListResponse> {
  return await $fetch<WordListResponse>('/api/words', { params })
}

/** Get full detail for a single word. */
export async function getWord(id: string): Promise<WordDetail> {
  return await $fetch<WordDetail>(`/api/words/${id}`)
}

/** Fuzzy search across Taita headwords. */
export async function searchWords(q: string, limit = 20): Promise<SearchResponse> {
  return await $fetch<SearchResponse>('/api/search', { params: { q, limit } })
}

/** Create a new word (goes live immediately). Requires reviewer/admin. */
export async function createWord(data: {
  headword: string
  part_of_speech?: string | null
  noun_class?: string | null
  dialect?: string | null
  literal_translation?: string | null
  morphology_notes?: string | null
  swahili_translation?: string | null
  english_translation?: string | null
}): Promise<WordDetail> {
  return await $fetch<WordDetail>('/api/words', { method: 'POST', body: data })
}

/** Edit an existing word's fields. Requires reviewer/admin. */
export async function editWord(
  id: string,
  data: Record<string, unknown>,
): Promise<WordDetail> {
  return await $fetch<WordDetail>(`/api/words/${id}`, { method: 'PATCH', body: data })
}

/** Soft-delete (hide) a word. Admin only. */
export async function deleteWord(id: string): Promise<{ id: string; status: string }> {
  return await $fetch(`/api/admin/words/${id}/hide`, { method: 'POST' })
}

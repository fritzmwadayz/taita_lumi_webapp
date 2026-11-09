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

// ── Example input shape (shared by createWord body and new_word suggestion) ──
// Matches the backend's ExampleInput (§7.2.4). On POST /api/words, examples are
// scoped to the auto-created default sense (sense_id is not accepted here —
// use addExample() if you need to scope to a specific sense).
export interface ExampleInput {
  taita_text: string                       // 1..2000 chars, required
  swahili_text?: string | null
  english_text?: string | null
  source_ref?: string | null               // max 500 chars
}

/** Create a new word (goes live immediately). Requires reviewer/admin.
 *  `examples` (if provided) are scoped to the auto-created default sense. */
export async function createWord(data: {
  headword: string
  part_of_speech?: string | null
  noun_class?: string | null
  dialect?: string | null
  literal_translation?: string | null
  morphology_notes?: string | null
  swahili_translation?: string | null
  english_translation?: string | null
  examples?: ExampleInput[] | null
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

// ── Sense + Example endpoints (reviewer+ direct shortcuts) ────────────────
// These bypass the suggestion queue and write directly to the word graph.
// All three return the parent word's full WordDetail so the page can refresh
// the whole view after a successful write.

export interface CreateExampleRequest {
  taita_text: string                       // 1..2000 chars, required
  swahili_text?: string | null
  english_text?: string | null
  source_ref?: string | null               // max 500 chars
  sense_id?: string | null                 // optional — scopes to a specific sense
}

export interface CreateSenseRequest {
  part_of_speech?: string | null
  definition?: string | null               // max 500 chars
  notes?: string | null                    // max 2000 chars
}

export interface EditSenseRequest {
  order_index?: number | null              // >= 1 — backend does NOT reshuffle
  part_of_speech?: string | null
  definition?: string | null
  notes?: string | null
}

/** Reviewer+ appends a single example to a word. Returns the updated word. */
export async function addExample(
  wordId: string,
  body: CreateExampleRequest,
): Promise<WordDetail> {
  return await $fetch<WordDetail>(`/api/words/${wordId}/examples`, {
    method: 'POST',
    body,
  })
}

/** Reviewer+ adds a new sense to a word. Returns the updated word. */
export async function addSense(
  wordId: string,
  body: CreateSenseRequest,
): Promise<WordDetail> {
  return await $fetch<WordDetail>(`/api/words/${wordId}/senses`, {
    method: 'POST',
    body,
  })
}

/** Reviewer+ edits a sense (order_index, definition, notes, POS). Returns the
 * parent word's full detail — refresh the whole word view. */
export async function editSense(
  senseId: string,
  body: EditSenseRequest,
): Promise<WordDetail> {
  return await $fetch<WordDetail>(`/api/senses/${senseId}`, {
    method: 'PATCH',
    body,
  })
}

// ── Lumi — suggestions API wrappers ───────────────────────────────────────
// Auto-imported by Nuxt.

import type {
  SuggestionListResponse,
  SuggestionListItem,
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

// ── Display helpers (shared by review pages + SuggestionChange) ───────────

// Legacy v1.3 aliases → the fields they actually mean.
const FIELD_LABELS: Record<string, string> = {
  headword: 'Headword',
  part_of_speech: 'Part of speech',
  noun_class: 'Noun class',
  dialect: 'Dialect',
  literal_translation: 'Literal translation',
  morphology_notes: 'Morphology notes',
  swahili_translation: 'Swahili translation',
  english_translation: 'English translation',
  swahili_gloss: 'Swahili translation',
  english_gloss: 'English translation',
  gloss: 'Translation',
  definition: 'Definition',
  notes: 'Notes',
}

/** Humanize a suggestion field_path (normalizes legacy gloss aliases). */
export function suggestionFieldLabel(path: string | null | undefined): string {
  if (!path) return ''
  return FIELD_LABELS[path.toLowerCase()] || path
}

// Types that map to a Variation row (vs. a Relationship row on the backend).
const VARIANT_TYPES = new Set(['variant', 'plural', 'singular', 'conjugation', 'diminutive', 'augmentative'])

/**
 * H1 heading for a suggestion detail page, per target type.
 * `targetHeadword` (from enrichment, may be null) is included when known.
 */
export function suggestionHeading(
  s: Pick<SuggestionListItem, 'target_type' | 'field_path' | 'proposed_value'>,
  targetHeadword?: string | null,
): string {
  const hw = targetHeadword ? ` on “${targetHeadword}”` : ''
  switch (s.target_type) {
    case 'new_word':
      return (s.proposed_value as Record<string, unknown>)?.headword as string || 'New word'
    case 'translation':
    case 'gloss':
      return `Translation update${hw}`
    case 'word':
      return `Correction: ${suggestionFieldLabel(s.field_path)}${hw}`
    case 'example':
    case 'new_example':
      return targetHeadword ? `New example for “${targetHeadword}”` : 'New example'
    case 'relation':
    case 'variation':
    case 'relationship': {
      const rt = (s.proposed_value as Record<string, unknown>)?.relation_type
      const label = typeof rt === 'string' && rt ? rt.replace(/_/g, ' ').toLowerCase() : 'variant'
      if (VARIANT_TYPES.has(label)) {
        return targetHeadword ? `New ${label} of “${targetHeadword}”` : `New ${label}`
      }
      return targetHeadword ? `New relation for “${targetHeadword}”` : 'New relation'
    }
    default:
      return s.field_path ? `Update: ${suggestionFieldLabel(s.field_path)}` : 'Suggestion'
  }
}

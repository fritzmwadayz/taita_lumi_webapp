// ── Lumi — API types ──────────────────────────────────────────────────────

export type UserRole = 'user' | 'reviewer' | 'admin'

export interface User {
  id: string
  email: string
  display_name: string | null
  role: UserRole
  created_at: string
  last_seen_at: string | null
  oauth_provider?: string | null
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

export interface UserStats {
  words_added: number
  suggestions_submitted: number
  suggestions_accepted: number
  suggestions_open: number
  suggestions_rejected: number
  votes_cast: number
}

export interface WordListItem {
  id: string
  slug: string
  headword: string
  part_of_speech: string | null
  noun_class: string | null
  dialect: string | null
  swahili_translation: string | null  // v1.3 — was swahili_gloss
  english_translation: string | null  // v1.3 — was english_gloss
  has_relations: boolean
}

export interface WordListResponse {
  items: WordListItem[]
  total: number
  page: number
  size: number
  has_next: boolean
}

// ── v1.3: Gloss → Translation ──────────────────────────────────────────
export interface Translation {
  language: string  // 'sw' or 'en'
  text: string
}

// ── v1.2/v1.3: Variations & Relationships (replace the legacy Relation) ──
// These are populated on WordDetail by the backend. The UI doesn't use them
// yet — wiring them into words/[id].vue is a target for the next phase.
export interface Variation {
  other_word_id: string
  other_headword: string
  other_slug: string
  variation_type: 'variant' | 'plural' | 'singular' | 'conjugation' | 'diminutive' | 'augmentative'
}

export interface Relationship {
  other_word_id: string
  other_headword: string
  other_slug: string
  relationship_type: 'antonym' | 'synonym' | 'see_also' | 'derived' | 'etymological'
  direction: 'bidirectional' | 'forward' | 'reverse'
  note: string | null
}

export interface Sense {
  id: string
  order_index: number  // 1-based
  part_of_speech: string | null
  definition: string | null
  notes: string | null
  translations: Translation[]
  examples: Example[]
}

export interface Example {
  id: string
  sense_id: string | null
  taita_text: string
  swahili_text: string | null
  english_text: string | null
  source_ref: string | null
}

// DEPRECATED — use Variation + Relationship instead. Still populated by the
// backend for backward compat with v1.1 frontend code.
export interface Relation {
  other_word_id: string
  other_headword: string
  other_slug: string | null
  relation_type: string
  direction: 'outgoing' | 'incoming'
}

export interface WordDetail {
  id: string
  slug: string
  headword: string
  part_of_speech: string | null
  noun_class: string | null
  dialect: string | null
  literal_translation: string | null
  morphology_notes: string | null
  status: string
  created_at: string

  // v1.3: glosses → translations
  translations: Translation[]  // v1.3 — was glosses
  examples: Example[]

  // v1.2/v1.3: structured word graph (UI wiring = next phase target)
  variations: Variation[]
  relationships: Relationship[]
  senses: Sense[]

  // DEPRECATED — still populated for backward compat. Use variations +
  // relationships instead. The UI currently reads this field; migrating to
  // the structured fields is a target for the next phase.
  relations: Relation[]
}

export interface SearchResponse {
  query: string
  items: SearchResultItem[]
  total: number
}

// v1.4 — search results extend WordListItem with a similarity score (0..1, 3 decimals).
// Backend returns this from GET /api/search; null when Postgres similarity() returns NULL.
export interface SearchResultItem extends WordListItem {
  similarity: number | null
}

// v1.3: 'gloss' → 'translation'. 'gloss' kept as legacy alias for in-flight suggestions.
// v1.2 added: 'new_example', 'variation', 'relationship'.
export type SuggestionTargetType =
  | 'new_word' | 'word' | 'translation' | 'gloss' | 'example'
  | 'new_example' | 'relation' | 'variation' | 'relationship'
export type SuggestionStatus = 'open' | 'accepted' | 'rejected'

export interface SuggestionListItem {
  id: string
  target_type: SuggestionTargetType
  target_id: string | null
  field_path: string | null
  proposed_value: Record<string, unknown>
  rationale: string | null
  status: SuggestionStatus
  created_at: string
  author_display: string | null
  created_by_user_id?: string | null
  upvotes: number
  downvotes: number
  user_vote?: 'up' | 'down' | null
}

export interface SuggestionListResponse {
  items: SuggestionListItem[]
  total: number
  page: number
  size: number
  has_next: boolean
}

export interface VoteResponse {
  suggestion_id: string
  upvotes: number
  downvotes: number
  user_vote: 'up' | 'down' | null
  promoted: boolean
}

export interface DecideResponse {
  id: string
  status: SuggestionStatus
  decided_at: string
  decided_by: string
}

export interface SessionData {
  user?: User
  tokens?: { access_token: string; refresh_token: string }
}

// ── Admin ─────────────────────────────────────────────────────────────────
export interface AdminStats {
  total_words: number
  total_users: number
  open_suggestions: number
  accepted_suggestions: number
  rejected_suggestions: number
  total_votes: number
  recent_words: WordListItem[]
  recent_suggestions: Array<{
    id: string
    headword: string | null
    target_type: SuggestionTargetType
    status: SuggestionStatus
    created_at: string
  }>
}

export interface AdminUser {
  id: string
  email: string
  display_name: string | null
  role: UserRole
  is_blocked: boolean
  created_at: string
  last_seen_at: string | null
}

export interface AdminUserListResponse {
  items: AdminUser[]
  total: number
  page: number
  size: number
}

export interface AuditLogEntry {
  id: string
  created_at: string
  actor_id: string | null
  actor_email: string | null
  actor_role: string | null
  action: string
  target_type: string | null
  target_id: string | null
  details: Record<string, unknown> | null
}

export interface AuditLogResponse {
  items: AuditLogEntry[]
  total: number
  page: number
  size: number
}

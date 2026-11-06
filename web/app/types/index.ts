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
  headword: string
  part_of_speech: string | null
  noun_class: string | null
  dialect: string | null
  swahili_gloss: string | null
  english_gloss: string | null
  has_relations: boolean
}

export interface WordListResponse {
  items: WordListItem[]
  total: number
  page: number
  size: number
  has_next: boolean
}

export interface Gloss { language: string; text: string }
export interface Relation {
  other_word_id: string
  other_headword: string
  relation_type: string
  direction: string
}

export interface WordDetail {
  id: string
  headword: string
  part_of_speech: string | null
  noun_class: string | null
  dialect: string | null
  literal_translation: string | null
  morphology_notes: string | null
  status: string
  created_at: string
  glosses: Gloss[]
  examples: unknown[]
  relations: Relation[]
}

export interface SearchResponse {
  query: string
  items: WordListItem[]
  total: number
}

export type SuggestionTargetType = 'new_word' | 'word' | 'gloss' | 'example' | 'relation'
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

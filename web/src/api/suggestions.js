// Suggestion API service.

import api from "./client";

/**
 * @typedef {Object} SuggestionListItem
 * @property {string} id
 * @property {string} target_type
 * @property {string|null} target_id
 * @property {string|null} field_path
 * @property {Object} proposed_value
 * @property {string|null} rationale
 * @property {string} status
 * @property {string} created_at
 * @property {string|null} author_display
 * @property {number} upvotes
 * @property {number} downvotes
 */

/**
 * @typedef {Object} SuggestionListResponse
 * @property {SuggestionListItem[]} items
 * @property {number} total
 * @property {number} page
 * @property {number} size
 * @property {boolean} has_next
 */

/**
 * Create a new suggestion.
 * @param {Object} data - { target_type, target_id?, field_path?, proposed_value, rationale? }
 * @returns {Promise<Object>} SuggestionResponse
 */
export async function createSuggestion(data) {
  const res = await api.post("/api/suggestions", data);
  return res.data;
}

/**
 * List suggestions with optional filters.
 * @param {Object} params
 * @param {string} [params.status] - Filter by status (default: 'open')
 * @param {string} [params.target_type] - Filter by target type
 * @param {number} [params.page=1]
 * @param {number} [params.size=20]
 * @returns {Promise<SuggestionListResponse>}
 */
export async function listSuggestions(params = {}) {
  const res = await api.get("/api/suggestions", { params });
  return res.data;
}

/**
 * Get a single suggestion by ID.
 * @param {string} id
 * @returns {Promise<Object>} SuggestionResponse
 */
export async function getSuggestion(id) {
  const res = await api.get(`/api/suggestions/${id}`);
  return res.data;
}

/**
 * Cast or change a vote on a suggestion.
 * Requires authentication — anon users will get 401.
 *
 * Repeating the same vote toggles it off (returns user_vote: null).
 *
 * @param {string} id - Suggestion ID
 * @param {string} vote - 'up' or 'down'
 * @returns {Promise<{suggestion_id: string, upvotes: number, downvotes: number, user_vote: string|null, promoted: boolean}>}
 */
export async function castVote(id, vote) {
  const res = await api.post(`/api/suggestions/${id}/vote`, { vote });
  return res.data;
}

/**
 * Remove the current user's vote on a suggestion.
 * @param {string} id - Suggestion ID
 * @returns {Promise<Object>} VoteResponse
 */
export async function removeVote(id) {
  const res = await api.delete(`/api/suggestions/${id}/vote`);
  return res.data;
}

/**
 * Reviewer/admin accepts or rejects a suggestion.
 * Accepting applies it to the word graph immediately.
 * @param {string} id - Suggestion ID
 * @param {string} decision - 'accept' or 'reject'
 * @returns {Promise<Object>} { id, status, decided_at, decided_by }
 */
export async function decideSuggestion(id, decision) {
  const res = await api.post(`/api/suggestions/${id}/decide`, { decision });
  return res.data;
}

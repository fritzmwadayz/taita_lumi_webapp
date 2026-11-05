// API service for word endpoints.
// All functions return promises; callers should .catch() errors.

import api from "./client";

// ── Types (JSDoc — for editor autocomplete) ───────────────────

/**
 * @typedef {Object} WordListItem
 * @property {string} id
 * @property {string} headword
 * @property {string|null} part_of_speech
 * @property {string|null} noun_class
 * @property {string|null} dialect
 * @property {string|null} swahili_gloss
 * @property {string|null} english_gloss
 * @property {boolean} has_relations
 */

/**
 * @typedef {Object} WordListResponse
 * @property {WordListItem[]} items
 * @property {number} total
 * @property {number} page
 * @property {number} size
 * @property {boolean} has_next
 */

/**
 * @typedef {Object} Gloss
 * @property {string} language
 * @property {string} text
 */

/**
 * @typedef {Object} Relation
 * @property {string} other_word_id
 * @property {string} other_headword
 * @property {string} relation_type
 * @property {string} direction
 */

/**
 * @typedef {Object} WordDetail
 * @property {string} id
 * @property {string} headword
 * @property {string|null} part_of_speech
 * @property {string|null} noun_class
 * @property {string|null} dialect
 * @property {string|null} literal_translation
 * @property {string|null} morphology_notes
 * @property {string} status
 * @property {string} created_at
 * @property {Gloss[]} glosses
 * @property {Array} examples
 * @property {Relation[]} relations
 */

// ── API functions ────────────────────────────────────────────

/**
 * List words with optional filters and pagination.
 * @param {Object} params
 * @param {string} [params.q] - Fuzzy search query
 * @param {string} [params.pos] - Filter by part of speech
 * @param {string} [params.dialect] - Filter by dialect
 * @param {number} [params.page=1] - Page number (1-indexed)
 * @param {number} [params.size=20] - Page size (max 100)
 * @returns {Promise<WordListResponse>}
 */
export async function listWords(params = {}) {
  const res = await api.get("/api/words", { params });
  return res.data;
}

/**
 * Get full detail for a single word.
 * @param {string} id - Word UUID
 * @returns {Promise<WordDetail>}
 */
export async function getWord(id) {
  const res = await api.get(`/api/words/${id}`);
  return res.data;
}

/**
 * Fuzzy search across Taita headwords.
 * @param {string} q - Search query
 * @param {number} [limit=20] - Max results
 * @returns {Promise<{query: string, items: WordListItem[], total: number}>}
 */
export async function searchWords(q, limit = 20) {
  const res = await api.get("/api/search", { params: { q, limit } });
  return res.data;
}

/**
 * Create a new word that goes live immediately.
 * Requires authentication (contributor or admin).
 *
 * @param {Object} data - { headword, part_of_speech?, noun_class?, dialect?, literal_translation?, morphology_notes?, swahili_gloss?, english_gloss? }
 * @returns {Promise<WordDetail>} The created word with glosses
 */
export async function createWord(data) {
  const res = await api.post("/api/words", data);
  return res.data;
}

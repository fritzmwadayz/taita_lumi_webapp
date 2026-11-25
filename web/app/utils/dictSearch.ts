// ── Lumi — client-side trigram search (pg_trgm parity) ────────────────────
// app/utils/dictSearch.ts
//
// Replaces GET /api/search for the static-first frontend. Mirrors the
// backend's ranking exactly (app/routes/words.py:search_words):
//
//   1. normalized_form % query  → pg_trgm trigram similarity > 0.3
//   2. headword ILIKE 'q%'     → prefix match on the display form
//   3. slug ILIKE 'q%'          → prefix match on the slug
//
// …ranked by similarity DESC, then headword ASC, capped at `limit`.
// The similarity value is the pg_trgm formula: shared trigrams over the
// union of the two deduplicated trigram sets (Jaccard), where each word in
// a string is padded with two spaces before and one after, and non-word
// characters act as separators (KEEPONLYALNUM — see Postgres docs, pg_trgm).
//
// Used with the static dictionary index loaded from
// /dictionary/words.json — zero backend calls per keystroke.

import type { SearchResultItem, WordListItem } from '~/types'

/** pg_trgm default for the % operator — strictly greater than, per docs. */
const SIMILARITY_THRESHOLD = 0.3

// ── Trigram extraction (pg_trgm parity) ───────────────────────────────────
// show_trgm('cat') → [' c', ' ca', 'cat', 'at ']:
//   lowercase → split on non-alphanumeric → each word padded as '  word '
//   → slide a 3-char window → dedupe (a set, not a bag).
const WORD_SPLIT = /[^a-z0-9]+/

/** Sorted, deduplicated trigram set of a string (pg_trgm show_trgm parity). */
export function trigrams(text: string): string[] {
  const words = text.toLowerCase().split(WORD_SPLIT).filter(Boolean)
  const set = new Set<string>()
  for (const word of words) {
    const padded = `  ${word} `
    for (let i = 0; i + 3 <= padded.length; i++) {
      set.add(padded.slice(i, i + 3))
    }
  }
  return [...set]
}

/** pg_trgm similarity(a, b) — shared trigrams over the union (Jaccard). */
export function similarity(a: string, b: string): number {
  const ta = trigrams(a)
  const tb = trigrams(b)
  if (ta.length === 0 || tb.length === 0) return 0
  const sa = new Set(ta)
  let shared = 0
  for (const t of tb) if (sa.has(t)) shared++
  const union = ta.length + tb.length - shared
  return union === 0 ? 0 : shared / union
}

/** Backend _normalize_form: lowercase, non-[a-z'] → space, collapse. */
export function normalizeForm(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^a-z']+/g, ' ')
    .trim()
}

// ── Index shape ───────────────────────────────────────────────────────────
/** Precomputed search row: one per live word, from words.json items. */
export interface DictSearchRow {
  /** The WordListItem — returned as-is in results. */
  item: WordListItem
  /** normalizeForm(headword) — mirrors Word.normalized_form in the DB. */
  norm: string
  /** Deduped trigram set of norm, for pg_trgm parity. */
  trigramSet: Set<string>
}

/**
 * Build the search index once from the static words.json items.
 * Computing trigram sets up front makes each search O(rows) with no
 * re-tokenisation, which keeps keystroke-to-paint instant for thousands
 * of words on a phone.
 */
export function buildDictSearchRows(items: WordListItem[]): DictSearchRow[] {
  return items.map((item) => {
    const norm = normalizeForm(item.headword)
    return { item, norm, trigramSet: new Set(trigrams(norm)) }
  })
}

// ── The search itself ──────────────────────────────────────────────────────
export interface DictSearchResult {
  items: SearchResultItem[]
  total: number
}

/**
 * Client-side mirror of GET /api/search.
 *
 * Rows are collected from three passes (similarity %, headword prefix,
 * slug prefix — same three OR branches as the backend), then ranked by
 * similarity DESC, headword ASC. Prefix-only matches (similarity ≤
 * threshold) still rank by their real similarity value, exactly like the
 * backend's `similarity(...) DESC` ORDER BY.
 */
export function dictSearch(
  rows: DictSearchRow[],
  query: string,
  limit = 20,
): DictSearchResult {
  const q = query.toLowerCase().trim()
  if (!q) return { items: [], total: 0 }

  const qt = new Set(trigrams(q))
  const qtList = [...qt]

  // Collect the best row per word (dedupe across the three branches).
  const seen = new Map<DictSearchRow, { sim: number; prefix: boolean }>()

  for (const row of rows) {
    // ── Branch 1: trigram similarity % q ─────────────────────────────
    // (Union/Jaccard over the two deduped trigram sets — see similarity().)
    let sim = 0
    if (qtList.length > 0 && row.trigramSet.size > 0) {
      let shared = 0
      for (const t of qtList) if (row.trigramSet.has(t)) shared++
      const union = row.trigramSet.size + qtList.length - shared
      sim = union > 0 ? shared / union : 0
    }

    // ── Branches 2+3: headword/slug prefix (ILIKE 'q%') ──────────────
    const prefix = row.norm.startsWith(q) || itemSlug(row).startsWith(q)

    if (sim > SIMILARITY_THRESHOLD || prefix) {
      seen.set(row, { sim })
    }
  }

  const ranked = [...seen.entries()].map(([row, { sim }]) => ({ row, sim }))

  // Backend ORDER BY: similarity DESC, headword ASC.
  ranked.sort((a, b) => b.sim - a.sim || a.row.item.headword.localeCompare(b.row.item.headword))

  const items: SearchResultItem[] = ranked.slice(0, limit).map(({ row, sim }) => ({
    ...row.item,
    similarity: round3(sim),
  }))

  // total = ALL matches (before the limit slice), mirroring the backend's
  // "items are capped at 50, total says how many matched" behavior.
  return { items, total: ranked.length }
}

function itemSlug(row: DictSearchRow): string {
  return row.item.slug || ''
}

function round3(n: number): number {
  return Math.round(n * 1000) / 1000
}

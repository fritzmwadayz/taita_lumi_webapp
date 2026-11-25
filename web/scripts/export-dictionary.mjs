#!/usr/bin/env node
// ── Lumi — dictionary static snapshot script ──────────────────────────────
// scripts/export-dictionary.mjs
//
// Fetches the bulk export from FastAPI (GET /api/export/dictionary) and
// writes a static snapshot into public/dictionary/:
//
//   public/dictionary/manifest.json    — { exported_at, total, slugs }
//   public/dictionary/words.json       — compact list index (the fields
//                                         WordCard/SearchBar need)
//   public/dictionary/words/<slug>.json — full WordDetail per word
//   public/dictionary/sitemap-words.xml — static <url> fragment listing
//                                         every word page
//
// The snapshot is committed or generated in CI before `nuxt build`, so the
// deploy never needs the backend up (the old prerender plugin did) and the
// built site serves dictionary reads from static files.
//
// Usage:
//   node scripts/export-dictionary.mjs [apiBase]
//
//   apiBase defaults to $LUMI_API_BASE_URL, then http://localhost:8000.
//   Add ?fail-if-missing to CI when you want a missing backend to fail the
//   build (default behaviour is to warn and keep the existing snapshot).

import { mkdir, readFile, writeFile, rm } from 'node:fs/promises'
import { existsSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join, resolve } from 'node:path'

const __dirname = dirname(fileURLToPath(import.meta.url))
const FRONTEND_ROOT = resolve(__dirname, '..')
const OUT_DIR = join(FRONTEND_ROOT, 'public', 'dictionary')
const WORDS_DIR = join(OUT_DIR, 'words')

// URL for fetching; env var wins, then arg, then localhost.
const API_BASE = (
  process.env.LUMI_API_BASE_URL ||
  process.argv[2] ||
  'http://localhost:8000'
).replace(/\/+$/, '')

const failIfMissing = process.argv.includes('--fail-if-missing')

// ── 1. Fetch the bulk export ─────────────────────────────────────────────
async function fetchDictionary() {
  const url = `${API_BASE}/api/export/dictionary`
  console.log(`[export] Fetching ${url} …`)

  const response = await fetch(url, {
    headers: { Accept: 'application/json' },
    signal: AbortSignal.timeout(120_000),
  })
  if (!response.ok) {
    throw new Error(`backend responded ${response.status} ${response.statusText}`)
  }
  return response.json()
}

// ── 2. Write files ───────────────────────────────────────────────────────
async function writeJson(path, data) {
  await writeFile(path, JSON.stringify(data), 'utf8')
}

async function main() {
  let dump
  try {
    dump = await fetchDictionary()
  } catch (err) {
    if (existsSync(WORDS_DIR)) {
      console.warn(
        `[export] Could not reach backend (${err.message}). ` +
        'Keeping the existing snapshot in public/dictionary/.',
      )
      if (failIfMissing) process.exit(1)
      return
    }
    console.error(
      `[export] Backend unreachable and no existing snapshot. ` +
      (failIfMissing
        ? 'Failing (CI mode).'
        : 'Continuing with an EMPTY dictionary — the frontend will fall back ' +
          'to the live API for every word until the next export.'),
    )
    if (failIfMissing) process.exit(1)
    dump = { exported_at: new Date().toISOString(), total: 0, words: [], list: [] }
  }

  const words = Array.isArray(dump.words) ? dump.words : []
  // Prefer the backend's compact list index; derive one from words[] if absent.
  const list = Array.isArray(dump.list) && dump.list.length === words.length
    ? dump.list
    : words.map(toListItem)

  console.log(`[export] Backend returned ${words.length} words.`)

  // Fresh output dir — stale files from removed words must not linger.
  await rm(WORDS_DIR, { recursive: true, force: true })
  await mkdir(WORDS_DIR, { recursive: true })

  // words.json — the compact list index consumed by home + search pages.
  // list items only; keeps the payload small (≈100 bytes per word).
  await writeJson(join(OUT_DIR, 'words.json'), {
    exported_at: dump.exported_at,
    total: words.length,
    items: list,
  })

  // Per-word detail files: public/dictionary/words/<slug>.json
  let written = 0
  const slugs = []
  for (const word of words) {
    if (!word.slug) continue
    await writeJson(join(WORDS_DIR, `${word.slug}.json`), word)
    slugs.push(word.slug)
    written++
  }

  // manifest.json — counts + the slug set (prerender plugin + debugging)
  await writeJson(join(OUT_DIR, 'manifest.json'), {
    exported_at: dump.exported_at,
    total: written,
    slugs,
  })

  // sitemap-words.xml — static fragment, appended to the static pages in
  // server/routes/sitemap.xml.ts (which no longer calls the backend).
  const urlEntries = slugs
    .map((slug) => `  <url>\n    <loc>__BASE__/words/${slug}</loc>\n    <changefreq>weekly</changefreq>\n    <priority>0.7</priority>\n  </url>`)
    .join('\n')
  await writeFile(
    join(OUT_DIR, 'sitemap-words.xml'),
    urlEntries ? `__BASE__PLACEHOLDER__\n${urlEntries}` : '',
    'utf8',
  )

  console.log(
    `[export] Snapshot written: ${written} word files → public/dictionary/ ` +
    `(exported_at=${dump.exported_at}).`,
  )

  // Sanity guard: the live-API fallback path assumes the detail files match
  // the list index 1:1.
  if (written !== list.length) {
    console.warn(
      `[export] WARNING: ${written} detail files but ${list.length} list items — ` +
      'slug mismatch between words[] and list[] in the export.',
    )
  }
}

function toListItem(word) {
  return {
    id: word.id,
    slug: word.slug,
    headword: word.headword,
    part_of_speech: word.part_of_speech ?? null,
    noun_class: word.noun_class ?? null,
    dialect: word.dialect ?? null,
    swahili_translation: word.swahili_translation ?? null,
    english_translation: word.english_translation ?? null,
    has_relations: word.has_relations ?? false,
  }
}

main().catch((err) => {
  console.error('[export] Failed:', err)
  process.exit(1)
})

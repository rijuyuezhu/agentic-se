import { readdir, readFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { pathToFileURL } from 'node:url'
import MiniSearch from 'minisearch'
import { searchOptions, tokenize } from '../search.mjs'

const siteDir = resolve(import.meta.dirname, '..')
const chunksDir = resolve(siteDir, '.vitepress/dist/assets/chunks')
const base = (() => {
  const raw = process.env.COURSE_SITE_BASE
  if (!raw || raw === '/') return '/'
  return `/${raw.replace(/^\/+|\/+$/g, '')}/`
})()
const routeWithBase = (route) => `${base}${route.replace(/^\//, '')}`
const chunks = (await readdir(chunksDir)).filter((name) => name.startsWith('@localSearchIndex') && name.endsWith('.js'))
if (chunks.length !== 1) {
  throw new Error(`expected exactly one local-search index chunk, got ${chunks.length}: ${chunks.join(', ')}`)
}

const indexModule = await import(pathToFileURL(resolve(chunksDir, chunks[0])).href)
const search = MiniSearch.loadJSON(indexModule.default, {
  fields: ['title', 'titles', 'text'],
  storeFields: ['title', 'titles'],
  searchOptions,
  tokenize,
})

const probes = [
  ['控制不了', '/modules/06-working-with-legacy-code'],
  ['无法凭空得到', '/modules/07-concurrency-lifecycle-failure'],
  ['delegation contract', '/modules/12-agentic-software-engineering'],
  ['authority localization', '/modules/10-code-review-change-engineering'],
  ['Source Audit M07', '/reading-notes/m07-source-audit'],
]

for (const [query, expectedPrefix] of probes) {
  const results = search.search(query, searchOptions)
  const expected = routeWithBase(expectedPrefix)
  if (!results.some((item) => String(item.id).startsWith(expected))) {
    throw new Error(
      `search probe ${JSON.stringify(query)} did not find ${expected}; got ${results.slice(0, 8).map((item) => item.id).join(', ')}`
    )
  }
}

const model = JSON.parse(await readFile(resolve(siteDir, '.generated/site-model.json'), 'utf8'))
const indexText = await readFile(resolve(chunksDir, chunks[0]), 'utf8')
for (const page of model.excluded_canonical) {
  const route = routeWithBase(page.route)
  if (indexText.includes(route)) {
    throw new Error(`excluded canonical route leaked into search index: ${route}`)
  }
}

console.log(`search verification: PASS (${probes.length} bilingual/type probes)`)

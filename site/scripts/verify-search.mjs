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

const model = JSON.parse(await readFile(resolve(siteDir, '.generated/site-model.json'), 'utf8'))
const byId = new Map(model.pages.map((page) => [page.id, page]))
const routeFor = (id) => {
  const page = byId.get(id)
  if (!page) throw new Error(`search verification requires visible page ${id}`)
  return page.route
}

const probes = [
  ['控制不了', routeFor('M06')],
  ['无法凭空得到', routeFor('M07')],
  ['delegation contract', routeFor('M12')],
  ['authority localization', routeFor('M10')],
  ['Source Audit M07', routeFor('source-M07')],
  ['Extension M07', routeFor('ext-models-notation')],
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

const multiModuleResults = search.search('Extension M07', searchOptions)
const multiModule = multiModuleResults.find((item) =>
  String(item.id).startsWith(routeWithBase(routeFor('ext-models-notation')))
)
if (!multiModule || !String(multiModule.title).includes('【Extension · M02 / M07 / M09】')) {
  throw new Error(
    `multi-module Extension search label lost canonical relations: ${JSON.stringify(multiModule ?? null)}`
  )
}

const indexText = await readFile(resolve(chunksDir, chunks[0]), 'utf8')
for (const page of model.excluded_canonical) {
  const route = routeWithBase(page.route)
  if (indexText.includes(route)) {
    throw new Error(`excluded canonical route leaked into search index: ${route}`)
  }
}

console.log(`search verification: PASS (${probes.length} bilingual/type/relation probes)`)

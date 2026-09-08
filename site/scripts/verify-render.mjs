import { readFile } from 'node:fs/promises'
import { resolve } from 'node:path'

const siteDir = resolve(import.meta.dirname, '..')
const dist = resolve(siteDir, '.vitepress/dist')
const base = (() => {
  const raw = process.env.COURSE_SITE_BASE
  if (!raw || raw === '/') return '/'
  return `/${raw.replace(/^\/+|\/+$/g, '')}/`
})()
const href = (route) => `${base}${route.replace(/^\//, '')}`
const sourceRepo = (
  process.env.COURSE_SOURCE_REPO ??
  'https://github.com/rijuyuezhu/software-engineering-for-agentic-development'
).replace(/\/+$/, '')
const sourceRef = process.env.COURSE_SOURCE_REF ?? 'main'
const source = (kind, path) =>
  `${sourceRepo}/${kind}/${encodeURIComponent(sourceRef)}/${path.split('/').map(encodeURIComponent).join('/')}`
const model = JSON.parse(await readFile(resolve(siteDir, '.generated/site-model.json'), 'utf8'))
const byId = new Map(model.pages.map((page) => [page.id, page]))

async function html(path) {
  return readFile(resolve(dist, path), 'utf8')
}

function requireText(body, needle, context) {
  if (!body.includes(needle)) throw new Error(`${context}: missing ${JSON.stringify(needle)}`)
}

function forbidText(body, needle, context) {
  if (body.includes(needle)) throw new Error(`${context}: unexpectedly contains ${JSON.stringify(needle)}`)
}

const m07 = await html('modules/07-concurrency-lifecycle-failure.html')
requireText(m07, '<aside class="course-context"', 'M07 course context')
requireText(m07, 'Main Path · 8 / 15', 'M07 progress')
requireText(m07, `href="${href('/labs/07-concurrency-lifecycle-failure')}"`, 'M07 related Lab')
requireText(m07, `href="${href('/reading-notes/m07-source-audit')}"`, 'M07 related source audit')
requireText(m07, `href="${href('/extensions/models-notation-and-uml')}"`, 'M07 related extension')
const m07Case = byId.get('case-M07')
if (m07Case) {
  requireText(m07, `href="${href(m07Case.route)}"`, 'M07 related Case Study')
} else {
  forbidText(m07, '/case-studies/m07/', 'student M07 hidden Case Study relation')
}
requireText(
  m07,
  `pager-link prev" href="${href('/modules/06-working-with-legacy-code')}"`,
  'M07 previous page'
)
requireText(
  m07,
  `pager-link next" href="${href('/modules/08-dependency-compatibility-migration')}"`,
  'M07 next page'
)

const extension = await html('extensions/security-engineering.html')
forbidText(extension, 'pager-link prev', 'Extension pagination')
forbidText(extension, 'pager-link next', 'Extension pagination')

const m13 = await html('modules/13-capstone-change-engineering.html')
requireText(
  m13,
  source('tree', 'labs/taskforge/capstone-starter'),
  'repo-only directory link'
)
requireText(
  m13,
  source('blob', 'labs/taskforge/capstone-starter/ISSUE.md'),
  'repo-only file link'
)
const m13Source = byId.get('source-M13')
if (m13Source) {
  requireText(m13, `href="${href(m13Source.route)}"`, 'M13 instructor source audit relation')
} else {
  forbidText(m13, '/reading-notes/m13-source-audit', 'student M13 hidden source audit relation')
}

const home = await html('index.html')
forbidText(home, '<aside class="course-context"', 'course overview')

console.log('render verification: PASS (relations, Main Path pagination, repo artifacts)')

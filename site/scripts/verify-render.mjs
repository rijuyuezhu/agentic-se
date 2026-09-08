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
  'https://github.com/rijuyuezhu/agentic-se'
).replace(/\/+$/, '')
const sourceRef = process.env.COURSE_SOURCE_REF ?? 'main'
const source = (kind, path) =>
  `${sourceRepo}/${kind}/${encodeURIComponent(sourceRef)}/${path.split('/').map(encodeURIComponent).join('/')}`
const model = JSON.parse(await readFile(resolve(siteDir, '.generated/site-model.json'), 'utf8'))
const byId = new Map(model.pages.map((page) => [page.id, page]))
const routeFor = (id) => {
  const page = byId.get(id)
  if (!page) throw new Error(`render verification requires visible page ${id}`)
  return page.route
}

async function html(path) {
  return readFile(resolve(dist, path), 'utf8')
}

function requireText(body, needle, context) {
  if (!body.includes(needle)) throw new Error(`${context}: missing ${JSON.stringify(needle)}`)
}

function forbidText(body, needle, context) {
  if (body.includes(needle)) throw new Error(`${context}: unexpectedly contains ${JSON.stringify(needle)}`)
}

function requireMatch(body, pattern, context) {
  const match = body.match(pattern)
  if (!match) throw new Error(`${context}: missing ${pattern}`)
  return match[0]
}

const checkSourceNavigation = model.visibility === 'all' ? requireText : forbidText
const m07 = await html('modules/07-concurrency-lifecycle-failure.html')
const m07Context = requireMatch(
  m07, /<aside\b[^>]*class="course-context"[^>]*>[\s\S]*?<\/aside>/, 'M07 course context'
)
requireText(m07Context, 'Main Path · 8 / 15', 'M07 progress')
requireText(m07Context, `href="${href(routeFor('lab-M07'))}"`, 'M07 related Lab')
checkSourceNavigation(m07Context, `href="${href(routeFor('source-M07'))}"`, 'M07 related source audit')
requireText(m07Context, `href="${href(routeFor('ext-models-notation'))}"`, 'M07 related extension')
const m07Case = byId.get('case-M07')
if (m07Case) {
  requireText(m07Context, `href="${href(m07Case.route)}"`, 'M07 related Case Study')
} else {
  forbidText(m07Context, '/case-studies/m07/', 'student M07 hidden Case Study relation')
}
requireText(
  m07,
  `pager-link prev" href="${href(routeFor('M06'))}"`,
  'M07 previous page'
)
requireText(
  m07,
  `pager-link next" href="${href(routeFor('M08'))}"`,
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
const m13Context = requireMatch(
  m13, /<aside\b[^>]*class="course-context"[^>]*>[\s\S]*?<\/aside>/, 'M13 course context'
)
if (model.visibility === 'all') {
  requireText(m13Context, `href="${href(routeFor('source-M13'))}"`, 'M13 all source audit relation')
} else {
  forbidText(m13Context, '/reading-notes/m13-source-audit', 'M13 hidden source audit relation')
}
checkSourceNavigation(m07Context, '<strong>Source Audit</strong>', 'M07 source audit cards')
checkSourceNavigation(m13Context, '<strong>Source Audit</strong>', 'M13 source audit cards')

for (const [name, context] of [['M07', m07Context], ['M13', m13Context]]) {
  const details = requireMatch(
    context, /<details\b[^>]*class="course-context__related"[^>]*>/, `${name} related disclosure`
  )
  if (/\sopen(?:\s|=|>)/.test(details)) throw new Error(`${name}: related materials must start closed`)
  const meta = context.slice(0, context.indexOf(details))
  requireText(meta, 'class="course-context__meta"', `${name} metadata outside disclosure`)
  requireText(meta, 'class="course-context__progress-text"', `${name} progress text outside disclosure`)
  requireText(meta, 'class="course-context__progress"', `${name} progress outside disclosure`)
}

const nav = requireMatch(
  m07, /<nav\b[^>]*class="VPNavBarMenu\b[^"]*"[^>]*>[\s\S]*?<\/nav>/, 'top navigation'
)
const sidebar = requireMatch(
  m07, /<nav\b[^>]*id="VPSidebarNav"[^>]*>[\s\S]*?<\/nav>/, 'sidebar navigation'
)
checkSourceNavigation(nav, '>Sources</span>', `${model.visibility} Sources top navigation`)
checkSourceNavigation(sidebar, '>Source Audits</span>', `${model.visibility} Source Audits sidebar`)
for (const page of model.pages.filter((page) => page.type === 'source_audit')) {
  const link = `href="${href(page.route)}"`
  checkSourceNavigation(sidebar, link, `${model.visibility} sidebar ${page.id}`)
  if (model.visibility !== 'all') forbidText(nav, link, `${model.visibility} top navigation ${page.id}`)
}
const audienceLabels = { student: '学生版', instructor: '教师版', all: '完整版' }
requireText(
  sidebar, `class="course-sidebar__audience">${audienceLabels[model.visibility]}</span>`, 'sidebar audience'
)
const groups = sidebar.match(/<details\b[^>]*class="course-sidebar__group[^"]*"[^>]*>[\s\S]*?<\/details>/g) ?? []
if (!groups.length || groups.length !== (sidebar.match(/class="course-sidebar__summary"/g) ?? []).length) {
  throw new Error('sidebar: named groups must use native details')
}
for (const group of groups) {
  if (/^<details\b[^>]*\sopen(?:\s|=|>)/.test(group)) throw new Error('sidebar groups must start closed')
  const count = (group.match(/<a\b/g) ?? []).length
  requireText(group, `class="course-sidebar__count" aria-label="${count} 篇"`, 'sidebar group count')
}
const activeLink = `href="${href(routeFor('M07'))}"`
const activeGroup = groups.find((group) => group.includes(activeLink)) ?? ''
requireText(activeGroup, 'course-sidebar__group has-active-link', 'M07 active sidebar group')
requireText(activeGroup, `${activeLink} aria-current="page"`, 'M07 current sidebar link')

const layout = requireMatch(m07, /<div\b[^>]*class="Layout\b[^"]*"[^>]*>/, 'course layout')
requireText(layout, 'course-sidebar-collapsed', 'desktop sidebar default')
const toggle = requireMatch(m07, /<button\b[^>]*class="course-sidebar-toggle"[^>]*>/, 'sidebar toggle')
for (const attribute of [
  'type="button"', 'aria-expanded="false"', 'aria-controls="VPSidebarNav"',
  'aria-label="展开课程导航"', 'title="展开课程导航"',
]) {
  requireText(toggle, attribute, 'collapsed sidebar toggle')
}

const home = await html('index.html')
forbidText(home, '<aside class="course-context"', 'course overview')

console.log('render verification: PASS (audience navigation, closed disclosures/sidebar, relations, Main Path pagination, repo artifacts)')

import { existsSync, readFileSync, statSync } from 'node:fs'
import { dirname, relative, resolve, sep } from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vitepress'
import { searchLabel, searchOptions, tokenize } from '../search.mjs'

const configDir = dirname(fileURLToPath(import.meta.url))
const siteDir = resolve(configDir, '..')
const repoRoot = resolve(siteDir, '..')
const model = JSON.parse(
  readFileSync(resolve(siteDir, '.generated/site-model.json'), 'utf8')
)

const pages = model.pages
const byId = new Map(pages.map((page: any) => [page.id, page]))
const byPath = new Map(pages.map((page: any) => [page.path, page]))
const allCanonicalPaths = new Set([
  ...pages.map((page: any) => page.path),
  ...model.excluded_canonical.map((page: any) => page.path),
])
const mainPath = model.main_path
const mainIndex = new Map(mainPath.map((page: any, index: number) => [page.id, index]))
const inverseRewrites = new Map(
  Object.entries(model.rewrites).map(([source, destination]) => [destination, source])
)
const directoryRouteByLinkPath = new Map(
  pages
    .filter((page: any) => page.route.endsWith('/'))
    .flatMap((page: any) => [
      [page.path, page.route],
      [page.path.replace(/\.md$/i, '.html'), page.route],
    ])
)

function normalizeBase(value: string | undefined) {
  if (!value || value === '/') return '/'
  const trimmed = value.replace(/^\/+|\/+$/g, '')
  return `/${trimmed}/`
}

const siteBase = normalizeBase(process.env.COURSE_SITE_BASE)

function relativeRoute(sourceRoute: string, targetRoute: string) {
  if (typeof sourceRoute !== 'string' || typeof targetRoute !== 'string') {
    throw new Error(
      `site routes must be strings: source=${JSON.stringify(sourceRoute)} target=${JSON.stringify(targetRoute)}`
    )
  }
  const sourceDir = sourceRoute.endsWith('/') ? sourceRoute : `${dirname(sourceRoute)}/`
  let value = relative(sourceDir, targetRoute).replaceAll(sep, '/')
  if (!value || value === '.') value = './'
  else if (!value.startsWith('.')) value = `./${value}`
  if (targetRoute.endsWith('/') && !value.endsWith('/')) value += '/'
  return value
}

function routeItem(page: any) {
  return { text: page.title, link: page.route }
}

function relatedModuleOrder(page: any) {
  const ids = [...new Set([...(page.related ?? []), ...(page.related_by ?? [])])]
  const orders = ids
    .map((id) => byId.get(id))
    .filter((item: any) => item?.type === 'module')
    .map((item: any) => item.order ?? 999)
  return orders.length ? Math.min(...orders) : 999
}

function pagesOfType(type: string) {
  return pages
    .filter((page: any) => page.type === type)
    .sort((a: any, b: any) => {
      const aOrder = relatedModuleOrder(a)
      const bOrder = relatedModuleOrder(b)
      if (aOrder !== bOrder) return aOrder - bOrder
      if (a.id === 'extensions') return -1
      if (b.id === 'extensions') return 1
      return a.title.localeCompare(b.title, 'zh-CN')
    })
}

const home = byId.get('course-overview')
if (!home) throw new Error('site model must contain canonical course-overview')
const labs = pagesOfType('lab')
const cases = pagesOfType('case_study')
const extensions = pagesOfType('extension')
const sources = model.visibility === 'all' ? pagesOfType('source_audit') : []
const practicums = pagesOfType('practicum')
const references = pagesOfType('reference').filter((page: any) => page.id !== 'course-overview')

const sidebar: any[] = []
if (home) sidebar.push({ text: '课程概览', link: home.route })
sidebar.push({ text: 'Main Path', collapsed: true, items: mainPath.map(routeItem) })
if (labs.length) sidebar.push({ text: 'Labs', collapsed: true, items: labs.map(routeItem) })
if (cases.length) sidebar.push({ text: 'Case Studies', collapsed: true, items: cases.map(routeItem) })
if (extensions.length)
  sidebar.push({ text: 'Extensions', collapsed: true, items: extensions.map(routeItem) })
if (sources.length)
  sidebar.push({ text: 'Source Audits', collapsed: true, items: sources.map(routeItem) })
if (practicums.length)
  sidebar.push({ text: 'Final Practicum', collapsed: true, items: practicums.map(routeItem) })
if (references.length)
  sidebar.push({ text: 'References', collapsed: true, items: references.map(routeItem) })

const nav: any[] = []
if (home) nav.push({ text: '首页', link: home.route })
if (mainPath.length) nav.push({ text: 'Main Path', link: mainPath[0].route })
const practiceNav: any[] = []
if (labs.length) practiceNav.push({ text: 'Labs', link: labs[0].route })
if (cases.length) practiceNav.push({ text: 'Case Studies', link: cases[0].route })
const finalPracticum = byId.get('final-practicum')
if (finalPracticum) practiceNav.push({ text: 'Final Practicum', link: finalPracticum.route })
if (practiceNav.length) nav.push({ text: '实践', items: practiceNav })
const extensionIndex = byId.get('extensions') ?? extensions[0]
if (extensionIndex) nav.push({ text: 'Extensions', link: extensionIndex.route })
if (sources.length) nav.push({ text: 'Sources', link: sources[0].route })

function sourcePageFromBuildSource(source: string | undefined) {
  if (!source) return undefined
  let value = source.replaceAll('\\', '/')
  if (value.startsWith(repoRoot.replaceAll('\\', '/'))) {
    value = relative(repoRoot, value).replaceAll(sep, '/')
  }
  value = value.replace(/^\/+/, '')
  value = inverseRewrites.get(value) ?? value
  return byPath.get(value)
}

function canonicalDirectoryLink(link: string, sourcePage: any) {
  if (!sourcePage || !link || link.startsWith('#') || link.startsWith('//')) return null
  if (/^[A-Za-z][A-Za-z0-9+.-]*:/.test(link)) return null

  const hashIndex = link.indexOf('#')
  const queryIndex = link.indexOf('?')
  const cut = [hashIndex, queryIndex].filter((index) => index >= 0)
  const end = cut.length ? Math.min(...cut) : link.length
  const rawPath = link.slice(0, end)
  if (!rawPath) return null

  let decodedPath: string
  try {
    decodedPath = decodeURIComponent(rawPath)
  } catch {
    return null
  }

  const rel = decodedPath.startsWith('/')
    ? decodedPath.replace(/^\/+/, '')
    : relative(repoRoot, resolve(repoRoot, dirname(sourcePage.path), decodedPath)).replaceAll(sep, '/')
  const route = directoryRouteByLinkPath.get(rel)
  return route ? `${relativeRoute(sourcePage.route, route)}${link.slice(end)}` : null
}

function localArtifact(link: string, sourcePage: any) {
  if (!sourcePage || !link || link.startsWith('#') || link.startsWith('/') || link.startsWith('//'))
    return null
  if (/^[A-Za-z][A-Za-z0-9+.-]*:/.test(link)) return null

  const hashIndex = link.indexOf('#')
  const queryIndex = link.indexOf('?')
  const cut = [hashIndex, queryIndex].filter((index) => index >= 0)
  const end = cut.length ? Math.min(...cut) : link.length
  const rawPath = link.slice(0, end)
  if (!rawPath) return null

  let decodedPath: string
  try {
    decodedPath = decodeURIComponent(rawPath)
  } catch {
    return null
  }

  const absolute = resolve(repoRoot, dirname(sourcePage.path), decodedPath)
  const rel = relative(repoRoot, absolute).replaceAll(sep, '/')
  if (!rel || rel === '..' || rel.startsWith('../') || !existsSync(absolute)) return null
  if (allCanonicalPaths.has(rel)) return null

  return { absolute, rel, suffix: link.slice(end) }
}

const sourceRepo = (
  process.env.COURSE_SOURCE_REPO ??
  'https://github.com/rijuyuezhu/agentic-se'
).replace(/\/+$/, '')
const sourceRef = process.env.COURSE_SOURCE_REF ?? 'main'

function sourceUrl(artifact: any) {
  const kind = statSync(artifact.absolute).isDirectory() ? 'tree' : 'blob'
  const encoded = artifact.rel.split('/').map(encodeURIComponent).join('/')
  return `${sourceRepo}/${kind}/${encodeURIComponent(sourceRef)}/${encoded}${artifact.suffix}`
}

function escapeHtml(text: string) {
  return text
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
}

export default defineConfig({
  lang: 'zh-CN',
  title: home.title,
  description: '面向 Agent 时代的软件工程自学课程',
  base: siteBase,
  srcDir: '..',
  srcExclude: model.src_exclude,
  rewrites: model.rewrites,
  // Keep hrefs aligned with emitted .html files so the artifact works on a
  // generic static server without extensionless -> .html rewrite support.
  cleanUrls: false,
  vite: {
    resolve: {
      alias: [
        {
          // Keep the default mobile drawer, but let readers control group expansion.
          find: /^.*\/VPSidebarGroup\.vue$/,
          replacement: resolve(configDir, 'theme/CourseSidebar.vue'),
        },
        {
          find: /^vue$/,
          replacement: resolve(siteDir, 'node_modules/vue/dist/vue.runtime.esm-bundler.js'),
        },
        {
          find: /^vue\/server-renderer$/,
          replacement: resolve(siteDir, 'node_modules/vue/server-renderer/index.js'),
        },
      ],
    },
  },
  ignoreDeadLinks: [
    (link, source) => {
      const sourcePage = sourcePageFromBuildSource(source)
      return localArtifact(link, sourcePage) !== null
    },
  ],
  markdown: {
    config(md) {
      const defaultLinkOpen =
        md.renderer.rules.link_open ??
        ((tokens, idx, options, _env, self) => self.renderToken(tokens, idx, options))
      md.renderer.rules.link_open = (tokens, idx, options, env, self) => {
        const token = tokens[idx]
        const hrefIndex = token.attrIndex('href')
        const sourcePage = byId.get(env.frontmatter?.id)
        if (hrefIndex >= 0 && sourcePage) {
          const href = token.attrs![hrefIndex][1]
          const canonical = canonicalDirectoryLink(href, sourcePage)
          if (canonical) {
            token.attrs![hrefIndex][1] = canonical
          } else {
            const artifact = localArtifact(href, sourcePage)
            if (artifact) token.attrs![hrefIndex][1] = sourceUrl(artifact)
          }
        }
        return defaultLinkOpen(tokens, idx, options, env, self)
      }
    },
  },
  transformPageData(pageData) {
    const page = byId.get(pageData.frontmatter?.id)
    if (!page) return
    const index = mainIndex.get(page.id)
    if (index === undefined) {
      pageData.frontmatter.prev = false
      pageData.frontmatter.next = false
      return
    }
    const prev = index > 0 ? mainPath[index - 1] : null
    const next = index + 1 < mainPath.length ? mainPath[index + 1] : null
    pageData.frontmatter.prev = prev ? routeItem(prev) : false
    pageData.frontmatter.next = next ? routeItem(next) : false
  },
  themeConfig: {
    siteTitle: '软件工程 · Agent',
    nav,
    sidebar,
    outline: { level: [2, 4], label: '本页目录' },
    docFooter: { prev: '上一篇', next: '下一篇' },
    returnToTopLabel: '回到顶部',
    sidebarMenuLabel: '课程导航',
    darkModeSwitchLabel: '主题',
    search: {
      provider: 'local',
      options: {
        miniSearch: { options: { tokenize }, searchOptions },
        _render(src, env, md) {
          const html = md.render(src, env)
          const page = byId.get(env.frontmatter?.id)
          if (!page) return ''
          const label = escapeHtml(searchLabel(page, byId))
          return html.replace(/(<h1\b[^>]*>)/i, `$1【${label}】 `)
        },
        translations: {
          button: { buttonText: '搜索', buttonAriaLabel: '搜索课程' },
          modal: {
            noResultsText: '没有找到相关内容',
            resetButtonTitle: '清除查询',
            footer: {
              selectText: '选择',
              navigateText: '切换',
              closeText: '关闭',
            },
          },
        },
      },
    },
  },
})

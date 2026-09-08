import { cp, mkdir, rm, writeFile } from 'node:fs/promises'
import { spawnSync } from 'node:child_process'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const scriptDir = dirname(fileURLToPath(import.meta.url))
const siteDir = resolve(scriptDir, '..')
const distDir = resolve(siteDir, '.vitepress/dist')
const outputDir = resolve(siteDir, '.pages-dist')
const dispatchIndex = resolve(siteDir, 'dispatch/index.html')

function normalizeBase(value) {
  if (!value || value === '/') return '/'
  return `/${value.replace(/^\/+|\/+$/g, '')}/`
}

const repository = process.env.GITHUB_REPOSITORY ?? 'rijuyuezhu/agentic-se'
const repositoryName = repository.split('/').at(-1)
const pagesBase = normalizeBase(process.env.COURSE_PAGES_BASE ?? `/${repositoryName}/`)
const sourceRepo = process.env.COURSE_SOURCE_REPO ?? `https://github.com/${repository}`
const sourceRef = process.env.COURSE_SOURCE_REF ?? process.env.GITHUB_SHA ?? 'main'

const variants = [
  ['student', 'student'],
  ['instructor', 'teacher'],
  ['all', 'all'],
]

await rm(outputDir, { recursive: true, force: true })
await mkdir(outputDir, { recursive: true })

for (const [mode, publicPath] of variants) {
  const base = `${pagesBase}${publicPath}/`
  const result = spawnSync('npm', ['run', `build:${mode}`], {
    cwd: siteDir,
    stdio: 'inherit',
    env: {
      ...process.env,
      COURSE_SITE_BASE: base,
      COURSE_SOURCE_REPO: sourceRepo,
      COURSE_SOURCE_REF: sourceRef,
    },
  })

  if (result.error) throw result.error
  if (result.status !== 0) process.exit(result.status ?? 1)

  await cp(distDir, resolve(outputDir, publicPath), { recursive: true })
}

await cp(dispatchIndex, resolve(outputDir, 'index.html'))
await writeFile(resolve(outputDir, '.nojekyll'), '')

console.log(`Pages bundle: ${outputDir}`)
console.log(`Dispatch base: ${pagesBase}`)
console.log('Variants: student/, teacher/, all/')

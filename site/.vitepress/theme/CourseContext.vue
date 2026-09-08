<script setup lang="ts">
import { computed } from 'vue'
import { useData, withBase } from 'vitepress'
import model from '../../.generated/site-model.json'

type CoursePage = {
  id: string
  type: string
  title: string
  route: string
  order: number | null
  related: string[]
  related_by: string[]
}

const TYPE_LABELS: Record<string, string> = {
  module: '正文',
  lab: 'Lab',
  case_study: 'Case Study',
  source_audit: 'Source Audit',
  extension: 'Extension',
  practicum: 'Final Practicum',
  reference: 'Reference',
}

const GROUP_LABELS: Record<string, string> = {
  lab: 'Lab',
  case_study: 'Case Study',
  source_audit: 'Source Audit',
  extension: '相关 Extension',
  module: '关联章节',
  practicum: '相关 Practicum',
  reference: '相关 Reference',
}

const pages = model.pages as CoursePage[]
const mainPath = model.main_path as CoursePage[]
const byId = new Map(pages.map((page) => [page.id, page]))
const { frontmatter } = useData()

const current = computed(() => byId.get(frontmatter.value.id as string))
const mainPosition = computed(() => {
  if (!current.value || current.value.order === null) return null
  const index = mainPath.findIndex((page) => page.id === current.value?.id)
  return index < 0 ? null : { current: index + 1, total: mainPath.length }
})

const relatedGroups = computed(() => {
  const page = current.value
  if (!page) return []
  const ids = [...new Set([...(page.related ?? []), ...(page.related_by ?? [])])]
  const related = ids
    .map((id) => byId.get(id))
    .filter((item): item is CoursePage => Boolean(item) && item!.id !== page.id)

  const wanted =
    page.type === 'module'
      ? ['lab', 'case_study', 'source_audit', 'extension']
      : ['module', 'lab', 'case_study', 'source_audit', 'extension', 'practicum', 'reference']

  return wanted
    .filter((type) => type !== 'source_audit' || model.visibility === 'all')
    .map((type) => ({
      type,
      label: GROUP_LABELS[type] ?? type,
      pages: related
        .filter((item) => item.type === type)
        .sort((a, b) => (a.order ?? 999) - (b.order ?? 999) || a.title.localeCompare(b.title, 'zh-CN')),
    }))
    .filter((group) => group.pages.length > 0)
})

const relatedCount = computed(() =>
  relatedGroups.value.reduce((count, group) => count + group.pages.length, 0)
)
const show = computed(() => current.value && current.value.id !== 'course-overview')
</script>

<template>
  <aside v-if="show" class="course-context" aria-label="课程上下文">
    <div class="course-context__meta">
      <span class="course-context__type">{{ TYPE_LABELS[current!.type] ?? current!.type }}</span>
      <span v-if="mainPosition" class="course-context__progress-text">
        Main Path · {{ mainPosition.current }} / {{ mainPosition.total }}
      </span>
    </div>

    <progress
      v-if="mainPosition"
      class="course-context__progress"
      :value="mainPosition.current"
      :max="mainPosition.total"
      :aria-label="`Main Path ${mainPosition.current} / ${mainPosition.total}`"
    />

    <details v-if="relatedGroups.length" class="course-context__related">
      <summary class="course-context__summary">
        <span>配套材料</span>
        <span class="course-context__count">{{ relatedCount }} 项</span>
        <span class="vpi-chevron-right course-context__chevron" aria-hidden="true" />
      </summary>
      <div class="course-context__grid">
        <div v-for="group in relatedGroups" :key="group.type" class="course-context__group">
          <strong>{{ group.label }}</strong>
          <ul>
            <li v-for="page in group.pages" :key="page.id">
              <a :href="withBase(page.route)">{{ page.title }}</a>
            </li>
          </ul>
        </div>
      </div>
    </details>
  </aside>
</template>

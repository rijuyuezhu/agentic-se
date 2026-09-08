<script setup lang="ts">
import { computed } from 'vue'
import { useData, withBase } from 'vitepress'
import model from '../../.generated/site-model.json'

defineProps<{
  items: { text?: string; items: { text: string; link: string }[] }[]
}>()

const audienceLabels: Record<string, string> = {
  student: '学生版',
  instructor: '教师版',
  all: '完整版',
}
const { frontmatter } = useData()
const byId = new Map(model.pages.map((page) => [page.id, page]))
const currentRoute = computed(() => byId.get(frontmatter.value.id)?.route)
</script>

<template>
  <div class="course-sidebar">
    <div class="course-sidebar__heading">
      <span>课程导航</span>
      <span class="course-sidebar__audience">{{ audienceLabels[model.visibility] }}</span>
    </div>

    <!-- Native disclosures stay closed until clicked, including on the active route. -->
    <component
      :is="group.text ? 'details' : 'div'"
      v-for="(group, index) in items"
      :key="group.text ?? index"
      class="course-sidebar__group"
      :class="{ 'has-active-link': group.items.some((item) => item.link === currentRoute) }"
    >
      <summary v-if="group.text" class="course-sidebar__summary">
        <span class="course-sidebar__label">{{ group.text }}</span>
        <span class="course-sidebar__count" :aria-label="`${group.items.length} 篇`">
          {{ group.items.length }}
        </span>
        <span class="vpi-chevron-right course-sidebar__chevron" aria-hidden="true" />
      </summary>
      <ul class="course-sidebar__links">
        <li v-for="item in group.items" :key="item.link">
          <a
            :href="withBase(item.link)"
            :aria-current="item.link === currentRoute ? 'page' : undefined"
          >
            {{ item.text }}
          </a>
        </li>
      </ul>
    </component>
  </div>
</template>

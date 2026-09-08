<script setup lang="ts">
import { computed, ref } from 'vue'
import { useData } from 'vitepress'
import DefaultTheme from 'vitepress/theme'
import CourseContext from './CourseContext.vue'

const { Layout } = DefaultTheme
const { frontmatter, theme } = useData()
const sidebarExpanded = ref(false)
const hasSidebar = computed(() =>
  Boolean(theme.value.sidebar) &&
  frontmatter.value.sidebar !== false &&
  frontmatter.value.layout !== 'home' &&
  frontmatter.value.layout !== false
)
const toggleLabel = computed(() => sidebarExpanded.value ? '收起课程导航' : '展开课程导航')
</script>

<template>
  <Layout :class="{ 'course-sidebar-collapsed': !sidebarExpanded }">
    <template #layout-top>
      <div v-if="hasSidebar" class="course-sidebar-control">
        <button
          type="button"
          class="course-sidebar-toggle"
          :aria-expanded="sidebarExpanded"
          aria-controls="VPSidebarNav"
          :aria-label="toggleLabel"
          :title="toggleLabel"
          @click="sidebarExpanded = !sidebarExpanded"
        >
          <span class="vpi-align-left" aria-hidden="true" />
          <span>{{ sidebarExpanded ? '收起' : '导航' }}</span>
        </button>
      </div>
    </template>
    <template #doc-before>
      <CourseContext />
    </template>
  </Layout>
</template>

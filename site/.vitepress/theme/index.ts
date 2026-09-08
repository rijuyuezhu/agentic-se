import { h } from 'vue'
import DefaultTheme from 'vitepress/theme'
import CourseContext from './CourseContext.vue'
import './custom.css'

export default {
  extends: DefaultTheme,
  Layout() {
    return h(DefaultTheme.Layout, null, {
      'doc-before': () => h(CourseContext),
    })
  },
}

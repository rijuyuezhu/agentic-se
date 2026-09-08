import DefaultTheme from 'vitepress/theme'
import CourseLayout from './CourseLayout.vue'
import './custom.css'

export default {
  extends: DefaultTheme,
  Layout: CourseLayout,
}

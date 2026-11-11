import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ContextMenu from '@imengyu/vue3-context-menu'
import '@imengyu/vue3-context-menu/lib/vue3-context-menu.css'

import App from './App.vue'
import router from './router/index.ts'
import './main.css'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(ContextMenu)

app.mount('#app')

// Add scrollbar fade effect
let scrollTimeout: number
document.addEventListener('scroll', (e) => {
  const target = e.target as HTMLElement
  if (target.classList.contains('custom-scrollbar')) {
    target.classList.add('scrolling')
    clearTimeout(scrollTimeout)
    scrollTimeout = window.setTimeout(() => {
      target.classList.remove('scrolling')
    }, 1000)
  }
}, true)

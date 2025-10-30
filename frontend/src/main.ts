import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'
import { applySavedTheme } from './utils/theme'
import App from './App.vue'
import router from './router'

const app = createApp(App)
applySavedTheme()
app.use(createPinia())
app.use(router)
app.use(ElementPlus)
app.mount('#app')



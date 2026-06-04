import { createApp } from 'vue'
import './style.css'
import { loadRuntimeConfig } from './config'

async function bootstrap() {
  await loadRuntimeConfig()
  const { default: App } = await import('./App.vue')
  createApp(App).mount('#app')
}

bootstrap()

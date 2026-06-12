<script setup>
import { KeepAlive, computed } from 'vue'
import ConversationPanel from './conversation/GUI.vue'
import { getFrontendConfig } from './config'
import SettingsPanel from './settings/GUI.vue'
import { appState, setActiveMode } from './state/appState'
import UploadPanel from './upload/GUI.vue'

const frontendConfig = getFrontendConfig()
const protocolLabel = frontendConfig.api?.protocol_label || 'HTTP Upload · WS Stream · Config Driven'

const activeMode = computed({
  get: () => appState.activeMode,
  set: (value) => setActiveMode(value),
})

const modes = [
  {
    key: 'conversation',
    label: '流式对话',
    description: '标准 LLM 一问一答，支持历史记录与重连',
  },
  {
    key: 'upload',
    label: '文档预处理',
    description: '上传文件或文件夹，构建文档索引',
  },
  {
    key: 'settings',
    label: '对话设置',
    description: '配置温度、输出长度、思考模式与 RAG',
  },
]

const activeModeInfo = computed(() => modes.find((mode) => mode.key === activeMode.value))
const activeComponent = computed(() => {
  if (activeMode.value === 'conversation') return ConversationPanel
  if (activeMode.value === 'settings') return SettingsPanel
  return UploadPanel
})
</script>

<template>
  <main class="app-shell" :class="`mode-${activeMode}`">
    <aside class="sidebar glass-card">
      <div class="brand-block">
        <div class="brand-mark">R</div>
        <div>
          <p class="eyebrow">Qwen RAG Console</p>
          <h1>文档问答系统</h1>
        </div>
      </div>

      <p class="side-description">
        面向文档 RAG 的双模式前端：文档上传预处理与 LLM WebSocket 流式对话彼此独立、模块化调用。
      </p>

      <nav class="mode-switcher">
        <button
          v-for="mode in modes"
          :key="mode.key"
          class="mode-button"
          :class="{ active: activeMode === mode.key }"
          @click="activeMode = mode.key"
        >
          <span>{{ mode.label }}</span>
          <small>{{ mode.description }}</small>
        </button>
      </nav>
    </aside>

    <section class="workspace" :class="`mode-${activeMode}`">
      <Transition name="mode-header-switch" mode="out-in">
        <header class="workspace-header glass-card" :key="activeMode">
          <div>
            <p class="eyebrow">Current Mode</p>
            <h2>{{ activeModeInfo.label }}</h2>
          </div>
          <div class="protocol-pill">{{ protocolLabel }}</div>
        </header>
      </Transition>

      <div class="workspace-content-shell">
        <Transition name="mode-panel-switch" mode="out-in" appear>
          <KeepAlive>
            <component :is="activeComponent" :key="activeMode" class="workspace-panel" />
          </KeepAlive>
        </Transition>
      </div>
    </section>
  </main>
</template>

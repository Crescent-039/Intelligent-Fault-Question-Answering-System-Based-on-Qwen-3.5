<script setup>
import { computed, ref } from 'vue'
import ConversationPanel from './conversation/GUI.vue'
import UploadPanel from './upload/GUI.vue'

const activeMode = ref('upload')

const modes = [
  {
    key: 'upload',
    label: '文档预处理',
    description: '上传文件或文件夹，构建文档索引',
  },
  {
    key: 'conversation',
    label: '流式对话',
    description: '标准 LLM 一问一答，支持中断生成',
  },
]

const activeModeInfo = computed(() => modes.find((mode) => mode.key === activeMode.value))
</script>

<template>
  <main class="app-shell">
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

    <section class="workspace">
      <header class="workspace-header glass-card">
        <div>
          <p class="eyebrow">Current Mode</p>
          <h2>{{ activeModeInfo.label }}</h2>
        </div>
        <div class="protocol-pill">HTTP Upload · WS Stream · Localhost</div>
      </header>

      <UploadPanel v-if="activeMode === 'upload'" />
      <ConversationPanel v-else />
    </section>
  </main>
</template>

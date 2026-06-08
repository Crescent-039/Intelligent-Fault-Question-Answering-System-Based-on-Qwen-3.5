<script setup>
import { computed } from 'vue'
import { appState, updateChatSettings } from '../state/appState'

const settings = computed(() => appState.chatSettings)

function updateField(key, value) {
  updateChatSettings({ [key]: value })
}
</script>

<template>
  <section class="module-panel settings-panel">
    <div class="panel-header">
      <div>
        <p class="eyebrow">Model Settings</p>
        <h2>对话参数设置</h2>
      </div>
    </div>

    <div class="settings-grid">
      <label class="form-field wide">
        <span>System Prompt</span>
        <textarea
          :value="settings.systemPrompt"
          rows="4"
          placeholder="你是一个文档分析助手"
          @input="updateField('systemPrompt', $event.target.value)"
        ></textarea>
      </label>

      <label class="form-field">
        <span>temperature</span>
        <input
          type="number"
          min="0"
          max="2"
          step="0.1"
          :value="settings.temperature"
          @input="updateField('temperature', Number($event.target.value))"
        />
      </label>

      <label class="form-field">
        <span>max_tokens</span>
        <input
          type="number"
          min="1"
          step="1"
          :value="settings.maxTokens"
          @input="updateField('maxTokens', Number($event.target.value))"
        />
      </label>

      <label class="form-field checkbox-field">
        <input
          type="checkbox"
          :checked="settings.ragEnabled"
          @change="updateField('ragEnabled', $event.target.checked)"
        />
        <span>启用 RAG</span>
      </label>

      <label class="form-field">
        <span>top_k</span>
        <input
          type="number"
          min="1"
          step="1"
          :value="settings.topK"
          @input="updateField('topK', Number($event.target.value))"
        />
      </label>
    </div>
  </section>
</template>
<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import {
  DEFAULT_CLEARED_MESSAGE,
  ChatStreamClient,
  DEFAULT_MODEL_CONFIG,
  DEFAULT_RAG_CONFIG,
  DEFAULT_WELCOME_MESSAGE,
  buildChatMessages,
  createDefaultWsUrl,
} from './backend'

const messages = ref([
  { role: 'assistant', content: DEFAULT_WELCOME_MESSAGE },
])
const input = ref('')
const connectionStatus = ref('disconnected')
const generating = ref(false)
const activeRequestId = ref(null)
const errorText = ref('')
const scrollArea = ref(null)

let client

function scrollToBottom() {
  nextTick(() => {
    if (scrollArea.value) scrollArea.value.scrollTop = scrollArea.value.scrollHeight
  })
}

function ensureAssistantMessage() {
  const last = messages.value[messages.value.length - 1]
  if (last?.role === 'assistant' && last.streaming) return last

  const assistant = { role: 'assistant', content: '', streaming: true }
  messages.value.push(assistant)
  return assistant
}

function initClient() {
  client = new ChatStreamClient({
    url: createDefaultWsUrl(),
    handlers: {
      onOpen: () => { connectionStatus.value = 'connected' },
      onClose: () => { connectionStatus.value = 'disconnected' },
      onStreamStart: () => { generating.value = true },
      onChunk: ({ delta }) => {
        const assistant = ensureAssistantMessage()
        assistant.content += delta
        scrollToBottom()
      },
      onStreamEnd: ({ payload }) => {
        generating.value = false
        activeRequestId.value = null
        const last = messages.value[messages.value.length - 1]
        if (last?.role === 'assistant') {
          last.streaming = false
          last.finishReason = payload.finish_reason
        }
      },
      onError: (error) => {
        errorText.value = error.message || '对话请求失败'
        generating.value = false
        activeRequestId.value = null
      },
    },
  })
  connectionStatus.value = 'connecting'
  client.connect()
}

function sendMessage() {
  const content = input.value.trim()
  if (!content || generating.value) return

  errorText.value = ''
  messages.value.push({ role: 'user', content })
  input.value = ''
  messages.value.push({ role: 'assistant', content: '', streaming: true })
  scrollToBottom()

  try {
    activeRequestId.value = client.sendChat({
      messages: buildChatMessages(messages.value.filter((message) => !message.streaming)),
      fileIds: [],
      rag: DEFAULT_RAG_CONFIG,
      modelConfig: DEFAULT_MODEL_CONFIG,
    })
    generating.value = true
  } catch (error) {
    errorText.value = error.message
    const last = messages.value[messages.value.length - 1]
    if (last?.role === 'assistant' && !last.content) messages.value.pop()
  }
}

function stopGeneration() {
  client?.cancel(activeRequestId.value)
  generating.value = false
  const last = messages.value[messages.value.length - 1]
  if (last?.role === 'assistant') {
    last.streaming = false
    last.finishReason = 'cancelled'
  }
}

function handleKeydown(event) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    sendMessage()
  }
}

function clearChat() {
  if (generating.value) stopGeneration()
  messages.value = [{ role: 'assistant', content: DEFAULT_CLEARED_MESSAGE }]
}

onMounted(initClient)
onBeforeUnmount(() => client?.close())
</script>

<template>
  <section class="module-panel chat-panel">
    <div class="panel-header">
      <div>
        <p class="eyebrow">Streaming Chat</p>
        <h2>LLM 流式对话</h2>
      </div>
      <div class="chat-toolbar">
        <span class="connection-dot" :class="connectionStatus"></span>
        <span class="muted">{{ connectionStatus }}</span>
        <button class="ghost-btn small" @click="clearChat">清空</button>
      </div>
    </div>

    <div ref="scrollArea" class="message-list">
      <article v-for="(message, index) in messages" :key="index" class="message" :class="message.role">
        <div class="message-role">{{ message.role === 'user' ? '你' : '助手' }}</div>
        <div class="message-bubble">
          <span v-if="message.content">{{ message.content }}</span>
          <span v-else class="typing">正在思考...</span>
          <span v-if="message.streaming" class="cursor"></span>
        </div>
      </article>
    </div>

    <p v-if="errorText" class="notice error chat-error">{{ errorText }}</p>

    <div class="composer chat-composer">
      <textarea
        v-model="input"
        rows="3"
        placeholder="输入问题，Enter 发送，Shift + Enter 换行"
        :disabled="generating"
        @keydown="handleKeydown"
      ></textarea>
      <button v-if="!generating" class="composer-send" :disabled="!input.trim()" @click="sendMessage">发送</button>
      <button v-else class="composer-send stop" @click="stopGeneration">停止</button>
    </div>
  </section>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import {
  DEFAULT_CLEARED_MESSAGE,
  ChatStreamClient,
  buildChatMessages,
  createDefaultWsUrl,
} from './backend'
import {
  appState,
  clearSessionMessages,
  createChatSession,
  deleteChatSession,
  getActiveChatSession,
  pushSessionMessage,
  removeLastSessionMessage,
  setActiveChatSession,
  updateChatSettings,
  updateLastSessionMessage,
} from '../state/appState'

const input = ref('')
const connectionStatus = ref('disconnected')
const generating = ref(false)
const activeRequestId = ref(null)
const errorText = ref('')
const scrollArea = ref(null)
const streamingSessionId = ref(null)

const sessions = computed(() => appState.chatSessions)
const currentSession = computed(() => getActiveChatSession())
const messages = computed(() => currentSession.value?.messages || [])
const chatSettings = computed(() => appState.chatSettings)

let client

function scrollToBottom() {
  nextTick(() => {
    if (scrollArea.value) scrollArea.value.scrollTop = scrollArea.value.scrollHeight
  })
}

function ensureAssistantMessage() {
  const sessionId = streamingSessionId.value || currentSession.value?.id
  const session = sessionId ? appState.chatSessions.find((item) => item.id === sessionId) : null
  const last = session?.messages?.[session.messages.length - 1]
  if (last?.role === 'assistant' && last.streaming) return last

  const assistant = { role: 'assistant', content: '', streaming: true }
  if (sessionId) pushSessionMessage(sessionId, assistant)
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
        if (streamingSessionId.value) updateLastSessionMessage(streamingSessionId.value, { content: assistant.content })
        scrollToBottom()
      },
      onStreamEnd: ({ payload }) => {
        generating.value = false
        activeRequestId.value = null
        const session = streamingSessionId.value ? appState.chatSessions.find((item) => item.id === streamingSessionId.value) : null
        const last = session?.messages?.[session.messages.length - 1]
        if (last?.role === 'assistant') {
          updateLastSessionMessage(streamingSessionId.value, {
            streaming: false,
            finishReason: payload.finish_reason,
          })
        }
        streamingSessionId.value = null
      },
      onError: (error) => {
        connectionStatus.value = 'error'
        errorText.value = error.message || '对话请求失败'
        generating.value = false
        activeRequestId.value = null
        if (streamingSessionId.value) updateLastSessionMessage(streamingSessionId.value, { streaming: false })
        streamingSessionId.value = null
      },
    },
  })
  connectionStatus.value = 'connecting'
  client.connect()
}

function sendMessage() {
  const content = input.value.trim()
  if (!content || generating.value || !currentSession.value) return

  errorText.value = ''
  const sessionId = currentSession.value.id
  pushSessionMessage(sessionId, { role: 'user', content })
  input.value = ''
  pushSessionMessage(sessionId, { role: 'assistant', content: '', streaming: true })
  streamingSessionId.value = sessionId
  scrollToBottom()

  try {
    activeRequestId.value = client.sendChat({
      messages: buildChatMessages(messages.value.filter((message) => !message.streaming), chatSettings.value.systemPrompt),
      fileIds: currentSession.value.fileIds || [],
      rag: {
        enabled: chatSettings.value.ragEnabled,
        top_k: Number(chatSettings.value.topK),
      },
      modelConfig: {
        temperature: Number(chatSettings.value.temperature),
        max_tokens: Number(chatSettings.value.maxTokens),
        enable_thinking: Boolean(chatSettings.value.enableThinking),
      },
    })
    generating.value = true
  } catch (error) {
    errorText.value = error.message
    removeLastSessionMessage(sessionId)
    streamingSessionId.value = null
  }
}

function stopGeneration() {
  client?.cancel(activeRequestId.value)
  generating.value = false
  if (streamingSessionId.value) {
    updateLastSessionMessage(streamingSessionId.value, {
      streaming: false,
      finishReason: 'cancelled',
    })
  }
  streamingSessionId.value = null
}

function handleKeydown(event) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    sendMessage()
  }
}

function clearChat() {
  if (generating.value) stopGeneration()
  if (!currentSession.value) return
  clearSessionMessages(currentSession.value.id, DEFAULT_CLEARED_MESSAGE)
}

function retryConnection() {
  errorText.value = ''
  connectionStatus.value = 'connecting'
  client?.reconnect()
}

function toggleThinking() {
  updateChatSettings({ enableThinking: !chatSettings.value.enableThinking })
}

function startNewChat() {
  createChatSession()
  errorText.value = ''
  scrollToBottom()
}

function selectSession(sessionId) {
  setActiveChatSession(sessionId)
  errorText.value = ''
  scrollToBottom()
}

function removeSession(sessionId) {
  if (streamingSessionId.value === sessionId) stopGeneration()
  deleteChatSession(sessionId)
  errorText.value = ''
}

onMounted(initClient)
onBeforeUnmount(() => client?.close())
</script>

<template>
  <section class="module-panel chat-panel">
    <div class="chat-layout">
      <aside class="chat-sessions">
        <div class="panel-header compact">
          <div>
            <p class="eyebrow">Chat History</p>
            <h3>历史对话</h3>
          </div>
          <button class="primary-btn small" @click="startNewChat">新建</button>
        </div>

        <div class="session-list">
          <button
            v-for="session in sessions"
            :key="session.id"
            class="session-item"
            :class="{ active: currentSession?.id === session.id }"
            @click="selectSession(session.id)"
          >
            <div class="session-item-main">
              <strong>{{ session.title }}</strong>
              <span class="muted session-time">{{ new Date(session.updatedAt).toLocaleString() }}</span>
            </div>
            <button class="ghost-btn small" @click.stop="removeSession(session.id)">删除</button>
          </button>
        </div>
      </aside>

      <div class="chat-main">
        <div class="panel-header">
          <div>
            <p class="eyebrow">Streaming Chat</p>
            <h2>LLM 流式对话</h2>
          </div>
          <div class="chat-toolbar">
            <button
              class="thinking-toggle"
              :class="{ active: chatSettings.enableThinking }"
              @click="toggleThinking"
            >
              <span class="thinking-toggle-dot"></span>
              <span>{{ chatSettings.enableThinking ? '思考模式已开启' : '思考模式已关闭' }}</span>
            </button>
            <span class="connection-dot" :class="connectionStatus"></span>
            <span class="muted">{{ connectionStatus }}</span>
            <button v-if="connectionStatus !== 'connected'" class="ghost-btn small" @click="retryConnection">重试连接</button>
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
      </div>
    </div>
  </section>
</template>

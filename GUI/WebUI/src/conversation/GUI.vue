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
const citationDialogVisible = ref(false)
const citationLoading = ref(false)
const citationError = ref('')
const citationDetail = ref(null)
const pendingCitationRequestId = ref(null)

const sessions = computed(() => appState.chatSessions)
const currentSession = computed(() => getActiveChatSession())
const messages = computed(() => currentSession.value?.messages || [])
const chatSettings = computed(() => appState.chatSettings)
const renderMessages = computed(() => messages.value.map((message) => ({
  ...message,
  parsed: parseMessageContent(message),
})))

let client

function parseAnswerSegments(answerContent) {
  const content = answerContent || ''
  const regex = /\[r(\d+)\]/g
  const segments = []
  let lastIndex = 0
  let match

  while ((match = regex.exec(content)) !== null) {
    const [token, chunkUidText] = match
    const matchIndex = match.index

    if (matchIndex > lastIndex) {
      segments.push({
        type: 'text',
        text: content.slice(lastIndex, matchIndex),
      })
    }

    segments.push({
      type: 'citation',
      token,
      chunkUid: Number(chunkUidText),
    })

    lastIndex = matchIndex + token.length
  }

  if (lastIndex < content.length) {
    segments.push({
      type: 'text',
      text: content.slice(lastIndex),
    })
  }

  if (!segments.length) {
    segments.push({
      type: 'text',
      text: content,
    })
  }

  return segments
}

function parseMessageContent(message) {
  if (message.role !== 'assistant') {
    return {
      thinkingContent: '',
      answerContent: message.content || '',
      answerSegments: parseAnswerSegments(message.content || ''),
    }
  }

  const rawContent = message.content || ''
  const thinkingStartToken = 'Thinking Process:'
  const thinkingEndToken = '</think>'
  const thinkingStartIndex = rawContent.indexOf(thinkingStartToken)

  if (thinkingStartIndex === -1) {
    const answerContent = rawContent
    return {
      thinkingContent: '',
      answerContent,
      answerSegments: parseAnswerSegments(answerContent),
    }
  }

  const thinkingEndIndex = rawContent.indexOf(thinkingEndToken, thinkingStartIndex + thinkingStartToken.length)
  const answerBeforeThinking = rawContent.slice(0, thinkingStartIndex)

  if (thinkingEndIndex === -1) {
    const answerContent = answerBeforeThinking.trimEnd()
    return {
      thinkingContent: rawContent.slice(thinkingStartIndex + thinkingStartToken.length).trimStart(),
      answerContent,
      answerSegments: parseAnswerSegments(answerContent),
    }
  }

  const answerContent = `${answerBeforeThinking}${rawContent.slice(thinkingEndToken.length + thinkingEndIndex)}`.trim()

  return {
    thinkingContent: rawContent.slice(thinkingStartIndex + thinkingStartToken.length, thinkingEndIndex).trim(),
    answerContent,
    answerSegments: parseAnswerSegments(answerContent),
  }
}

function closeCitationDialog() {
  citationDialogVisible.value = false
  citationLoading.value = false
  citationError.value = ''
  citationDetail.value = null
  pendingCitationRequestId.value = null
}

function openCitationDetail(chunkUid) {
  citationDialogVisible.value = true
  citationLoading.value = true
  citationError.value = ''
  citationDetail.value = null

  try {
    pendingCitationRequestId.value = client.requestCitationDetail(chunkUid)
  } catch (error) {
    citationLoading.value = false
    citationError.value = error.message || '引用详情加载失败'
    pendingCitationRequestId.value = null
  }
}

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
      onCitationDetail: ({ requestId, payload }) => {
        if (requestId !== pendingCitationRequestId.value) return
        citationLoading.value = false
        citationError.value = ''
        citationDetail.value = payload
        pendingCitationRequestId.value = null
      },
      onError: (error) => {
        if (error.requestId && error.requestId === pendingCitationRequestId.value) {
          citationLoading.value = false
          citationError.value = error.message || '引用详情加载失败'
          pendingCitationRequestId.value = null
          return
        }
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
          <article v-for="(message, index) in renderMessages" :key="index" class="message" :class="message.role">
            <div class="message-role">{{ message.role === 'user' ? '你' : '助手' }}</div>
            <div class="message-bubble">
              <div class="message-content-stack">
                <details v-if="message.parsed.thinkingContent" class="thinking-block" :open="message.streaming">
                  <summary>
                    <span class="thinking-title">Thinking Process</span>
                    <span class="thinking-hint">点击展开/收起</span>
                  </summary>
                  <div class="thinking-body">{{ message.parsed.thinkingContent }}</div>
                </details>

                <div v-if="message.parsed.answerContent" class="answer-content">
                  <template v-for="(segment, segmentIndex) in message.parsed.answerSegments" :key="`${index}-${segmentIndex}`">
                    <span v-if="segment.type === 'text'">{{ segment.text }}</span>
                    <button
                      v-else
                      class="citation-chip"
                      :disabled="message.streaming"
                      @click="openCitationDetail(segment.chunkUid)"
                    >
                      {{ segment.token }}
                    </button>
                  </template>
                  <span v-if="message.streaming" class="cursor"></span>
                </div>

                <div v-else-if="message.streaming" class="typing">正在思考...</div>
              </div>
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

        <div v-if="citationDialogVisible" class="citation-dialog-backdrop" @click.self="closeCitationDialog">
          <div class="citation-dialog">
            <div class="panel-header compact citation-dialog-header">
              <div>
                <p class="eyebrow">Citation Detail</p>
                <h3>引用详情</h3>
              </div>
              <button class="ghost-btn small" @click="closeCitationDialog">关闭</button>
            </div>

            <div v-if="citationLoading" class="typing">正在加载引用内容...</div>
            <p v-else-if="citationError" class="notice error">{{ citationError }}</p>
            <div v-else-if="citationDetail" class="citation-detail-body">
              <p class="muted">chunk_uid：{{ citationDetail.chunk_uid }}</p>
              <p class="muted" v-if="citationDetail.source">来源：{{ citationDetail.source }}</p>
              <p class="muted" v-if="citationDetail.doc_id">doc_id：{{ citationDetail.doc_id }}</p>
              <div class="citation-detail-text">{{ citationDetail.text }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.citation-chip {
  margin: 0 0.2rem;
  padding: 0.08rem 0.45rem;
  border: 1px solid rgba(59, 130, 246, 0.35);
  border-radius: 999px;
  background: rgba(59, 130, 246, 0.12);
  color: #2563eb;
  cursor: pointer;
  font: inherit;
}

.citation-chip:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.citation-dialog-backdrop {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(15, 23, 42, 0.35);
  z-index: 1000;
}

.citation-dialog {
  width: min(640px, calc(100vw - 32px));
  max-height: min(70vh, 720px);
  overflow: auto;
  border-radius: 16px;
  background: #fff;
  box-shadow: 0 20px 60px rgba(15, 23, 42, 0.22);
  padding: 1rem;
}

.citation-dialog-header {
  margin-bottom: 0.75rem;
}

.citation-detail-body {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.citation-detail-text {
  white-space: pre-wrap;
  line-height: 1.7;
  padding: 0.9rem 1rem;
  border-radius: 12px;
  background: #f8fafc;
}
</style>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import DOMPurify from 'dompurify'
import { marked } from 'marked'
import {
  DEFAULT_CLEARED_MESSAGE,
  DEFAULT_WELCOME_MESSAGE,
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
  renameChatSession,
  toggleChatSessionPinned,
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

const CITATION_FADE_EDGE = 10

const activeSessionMenuId = ref(null)
const editingSessionId = ref(null)
const editingTitle = ref('')
const editingTitleInput = ref(null)
const sessionMenuStyle = ref({})

const pinnedSessions = computed(() => appState.chatSessions.filter((session) => session.pinned))
const regularSessions = computed(() => appState.chatSessions.filter((session) => !session.pinned))
const activeMenuSession = computed(() => appState.chatSessions.find((session) => session.id === activeSessionMenuId.value) || null)
const currentSession = computed(() => getActiveChatSession())
const messages = computed(() => currentSession.value?.messages || [])
const chatSettings = computed(() => appState.chatSettings)
const renderMessages = computed(() => messages.value.map((message) => ({
  ...message,
  parsed: parseMessageContent(message),
})))

let client

marked.setOptions({
  breaks: true,
  gfm: true,
})

function renderMarkdownWithCitations(answerContent = '') {
  const citationMap = new Map()
  const placeholderContent = answerContent.replace(/\[r(\d+)\]/g, (_, chunkUidText) => {
    const chunkUid = Number(chunkUidText)
    const key = `TRAE_CITATION_${citationMap.size}_${chunkUid}`
    citationMap.set(key, { chunkUid, token: `[r${chunkUid}]` })
    return key
  })

  let html = marked.parse(placeholderContent)
  html = html.replace(/TRAE_CITATION_(\d+)_(\d+)/g, (_, indexText, chunkUidText) => {
    const key = `TRAE_CITATION_${indexText}_${chunkUidText}`
    const citation = citationMap.get(key)
    if (!citation) return ''
    return `<button type="button" class="citation-chip" data-citation-chunk-uid="${citation.chunkUid}">${citation.token}</button>`
  })

  return DOMPurify.sanitize(html, {
    ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'code', 'pre', 'blockquote', 'ul', 'ol', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr', 'a', 'button'],
    ALLOWED_ATTR: ['href', 'target', 'rel', 'class', 'type', 'data-citation-chunk-uid'],
  })
}

function parseMessageContent(message) {
  if (message.role !== 'assistant') {
    return {
      thinkingContent: '',
      answerContent: message.content || '',
      answerHtml: renderMarkdownWithCitations(message.content || ''),
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
      answerHtml: renderMarkdownWithCitations(answerContent),
    }
  }

  const thinkingEndIndex = rawContent.indexOf(thinkingEndToken, thinkingStartIndex + thinkingStartToken.length)
  const answerBeforeThinking = rawContent.slice(0, thinkingStartIndex)

  if (thinkingEndIndex === -1) {
    const answerContent = answerBeforeThinking.trimEnd()
    return {
      thinkingContent: rawContent.slice(thinkingStartIndex + thinkingStartToken.length).trimStart(),
      answerContent,
      answerHtml: renderMarkdownWithCitations(answerContent),
    }
  }

  const answerContent = `${answerBeforeThinking}${rawContent.slice(thinkingEndToken.length + thinkingEndIndex)}`.trim()

  return {
    thinkingContent: rawContent.slice(thinkingStartIndex + thinkingStartToken.length, thinkingEndIndex).trim(),
    answerContent,
    answerHtml: renderMarkdownWithCitations(answerContent),
  }
}

function buildCitationFadeChars(text) {
  const chars = Array.from(text || '')
  const length = chars.length

  if (!length) return []

  const edge = Math.min(CITATION_FADE_EDGE, Math.ceil(length / 2))
  const denominator = Math.max(edge - 1, 1)

  return chars.map((char, index) => {
    let opacity = 1

    if (index < edge) {
      opacity = index / denominator
    }

    if (index >= length - edge) {
      const tailDistance = length - index
      const tailOpacity = (tailDistance - 1) / denominator
      opacity = Math.min(opacity, tailOpacity)
    }

    return {
      char,
      opacity: Number(opacity.toFixed(3)),
    }
  })
}

function closeCitationDialog() {
  citationDialogVisible.value = false
  citationLoading.value = false
  citationError.value = ''
  citationDetail.value = null
  pendingCitationRequestId.value = null
}

async function openCitationDetail(chunkUid) {
  citationDialogVisible.value = true
  citationLoading.value = true
  citationError.value = ''
  citationDetail.value = null

  try {
    pendingCitationRequestId.value = await client.requestCitationDetail(chunkUid)
  } catch (error) {
    citationLoading.value = false
    citationError.value = error.message || '引用详情加载失败'
    pendingCitationRequestId.value = null
  }
}

function handleAnswerContentClick(event) {
  const button = event.target.closest?.('[data-citation-chunk-uid]')
  if (!button) return
  const chunkUid = Number(button.dataset.citationChunkUid)
  if (!Number.isFinite(chunkUid)) return
  openCitationDetail(chunkUid)
}

function scrollToBottom() {
  nextTick(() => {
    if (scrollArea.value) scrollArea.value.scrollTop = scrollArea.value.scrollHeight
  })
}

function getLatestRound() {
  const sessionMessages = currentSession.value?.messages || []
  const assistantIndex = sessionMessages.length - 1
  const userIndex = assistantIndex - 1

  if (assistantIndex < 1) return null

  const assistantMessage = sessionMessages[assistantIndex]
  const userMessage = sessionMessages[userIndex]

  if (assistantMessage?.role !== 'assistant' || userMessage?.role !== 'user') return null
  if (assistantMessage.content === DEFAULT_WELCOME_MESSAGE) return null

  return {
    assistantIndex,
    assistantMessage,
    userMessage,
  }
}

function shouldShowMessageActions(message, index) {
  if (generating.value || message.role !== 'assistant' || message.streaming) return false
  if (message.content === DEFAULT_WELCOME_MESSAGE) return false
  if (index !== renderMessages.value.length - 1) return false
  return renderMessages.value[index - 1]?.role === 'user'
}

async function copyAnswerContent(message) {
  const text = message.parsed.answerContent?.trim()
  if (!text) return

  try {
    await navigator.clipboard.writeText(text)
    errorText.value = ''
  } catch (error) {
    errorText.value = error.message || '复制失败'
  }
}

function retryLastRound() {
  if (generating.value || !currentSession.value) return

  const latestRound = getLatestRound()
  if (!latestRound) return

  errorText.value = ''
  const sessionId = currentSession.value.id
  const requestMessages = currentSession.value.messages.filter((message, index) => index !== latestRound.assistantIndex && !message.streaming)

  removeLastSessionMessage(sessionId)
  pushSessionMessage(sessionId, { role: 'assistant', content: '', streaming: true })
  streamingSessionId.value = sessionId
  scrollToBottom()

  try {
    activeRequestId.value = client.sendChat({
      messages: buildChatMessages(requestMessages, chatSettings.value.systemPrompt),
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

function deleteLastRound() {
  if (generating.value || !currentSession.value) return

  const latestRound = getLatestRound()
  if (!latestRound) return

  const sessionId = currentSession.value.id
  removeLastSessionMessage(sessionId)
  removeLastSessionMessage(sessionId)
  errorText.value = ''
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

function toggleRagEnabled() {
  updateChatSettings({ ragEnabled: !chatSettings.value.ragEnabled })
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
  activeSessionMenuId.value = null
  errorText.value = ''
  scrollToBottom()
}

function toggleSessionMenu(event, sessionId) {
  if (activeSessionMenuId.value === sessionId) {
    activeSessionMenuId.value = null
    return
  }

  const rect = event.currentTarget.getBoundingClientRect()
  sessionMenuStyle.value = {
    position: 'fixed',
    top: `${rect.bottom + 8}px`,
    left: `${Math.max(12, Math.min(rect.right - 160, window.innerWidth - 172))}px`,
  }
  activeSessionMenuId.value = sessionId
}

function setEditingTitleInput(element) {
  if (element) editingTitleInput.value = element
}

function startRenameSession(session) {
  editingSessionId.value = session.id
  editingTitle.value = session.title || ''
  activeSessionMenuId.value = null
}

function submitRenameSession(sessionId) {
  renameChatSession(sessionId, editingTitle.value)
  editingSessionId.value = null
  editingTitle.value = ''
  errorText.value = ''
}

function cancelRenameSession() {
  editingSessionId.value = null
  editingTitle.value = ''
}

function togglePinnedSession(sessionId) {
  toggleChatSessionPinned(sessionId)
  activeSessionMenuId.value = null
}

function handleWindowClick() {
  activeSessionMenuId.value = null
}

function removeSession(sessionId) {
  if (streamingSessionId.value === sessionId) stopGeneration()
  deleteChatSession(sessionId)
  if (activeSessionMenuId.value === sessionId) activeSessionMenuId.value = null
  if (editingSessionId.value === sessionId) cancelRenameSession()
  errorText.value = ''
}

watch(editingSessionId, async (value) => {
  if (!value) return
  await nextTick()
  editingTitleInput.value?.focus()
  editingTitleInput.value?.select?.()
})

onMounted(() => {
  initClient()
  window.addEventListener('click', handleWindowClick)
})

onBeforeUnmount(() => {
  client?.close()
  window.removeEventListener('click', handleWindowClick)
})
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
          <p v-if="pinnedSessions.length" class="session-group-label">已置顶</p>
          <div
            v-for="session in pinnedSessions"
            :key="session.id"
            class="session-item"
            :class="{ active: currentSession?.id === session.id, editing: editingSessionId === session.id }"
          >
            <button class="session-select" @click="selectSession(session.id)">
              <div class="session-item-main">
                <div v-if="editingSessionId === session.id" class="session-title-editor" @click.stop>
                  <input
                    :ref="setEditingTitleInput"
                    v-model="editingTitle"
                    class="session-title-input"
                    maxlength="40"
                    @click.stop
                    @keydown.enter.prevent="submitRenameSession(session.id)"
                    @keydown.esc.prevent="cancelRenameSession"
                    @blur="submitRenameSession(session.id)"
                  />
                </div>
                <strong v-else>
                  <span class="session-pin-mark">置顶</span>{{ session.title }}
                </strong>
                <span class="muted session-time">{{ new Date(session.updatedAt).toLocaleString() }}</span>
              </div>
            </button>
            <div class="session-item-actions">
              <button class="session-menu-trigger" @click.stop="toggleSessionMenu($event, session.id)">•••</button>
            </div>
          </div>

          <p v-if="regularSessions.length" class="session-group-label">最近对话</p>
          <div
            v-for="session in regularSessions"
            :key="session.id"
            class="session-item"
            :class="{ active: currentSession?.id === session.id, editing: editingSessionId === session.id }"
          >
            <button class="session-select" @click="selectSession(session.id)">
              <div class="session-item-main">
                <div v-if="editingSessionId === session.id" class="session-title-editor" @click.stop>
                  <input
                    :ref="setEditingTitleInput"
                    v-model="editingTitle"
                    class="session-title-input"
                    maxlength="40"
                    @click.stop
                    @keydown.enter.prevent="submitRenameSession(session.id)"
                    @keydown.esc.prevent="cancelRenameSession"
                    @blur="submitRenameSession(session.id)"
                  />
                </div>
                <strong v-else>{{ session.title }}</strong>
                <span class="muted session-time">{{ new Date(session.updatedAt).toLocaleString() }}</span>
              </div>
            </button>
            <div class="session-item-actions">
              <button class="session-menu-trigger" @click.stop="toggleSessionMenu($event, session.id)">•••</button>
            </div>
          </div>
        </div>

        <Teleport to="body">
          <Transition name="session-menu-fade">
            <div v-if="activeMenuSession" class="session-menu teleported-session-menu" :style="sessionMenuStyle" @click.stop>
              <button class="session-menu-item" @click="startRenameSession(activeMenuSession)">重命名</button>
              <button class="session-menu-item" @click="togglePinnedSession(activeMenuSession.id)">{{ activeMenuSession.pinned ? '取消置顶' : '置顶' }}</button>
              <button class="session-menu-item danger" @click="removeSession(activeMenuSession.id)">删除</button>
            </div>
          </Transition>
        </Teleport>
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
              :class="{ active: chatSettings.ragEnabled }"
              @click="toggleRagEnabled"
            >
              <span class="thinking-toggle-dot"></span>
              <span>{{ chatSettings.ragEnabled ? 'RAG 搜索已开启' : 'RAG 搜索已关闭' }}</span>
            </button>
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
          <TransitionGroup name="chat-bubble-fade" tag="div" class="message-list-inner">
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

                  <div v-if="message.parsed.answerContent" class="answer-content markdown-body" @click="handleAnswerContentClick">
                    <div v-html="message.parsed.answerHtml"></div>
                    <span v-if="message.streaming" class="cursor"></span>
                  </div>

                  <div v-else-if="message.streaming" class="typing">正在思考...</div>
                </div>
              </div>

              <div v-if="shouldShowMessageActions(message, index)" class="message-actions">
                <button class="ghost-btn small" @click="copyAnswerContent(message)">复制</button>
                <button class="ghost-btn small" @click="retryLastRound">重试</button>
                <button class="danger-btn small" @click="deleteLastRound">删除</button>
              </div>
            </article>
          </TransitionGroup>
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
              <div class="citation-detail-text">
                <span
                  v-for="(char, charIndex) in buildCitationFadeChars(citationDetail.text)"
                  :key="`${citationDetail.chunk_uid}-${charIndex}`"
                  class="citation-detail-char"
                  :style="{ opacity: char.opacity }"
                >{{ char.char }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.answer-content :deep(p),
.answer-content :deep(ul),
.answer-content :deep(ol),
.answer-content :deep(blockquote),
.answer-content :deep(pre),
.answer-content :deep(h1),
.answer-content :deep(h2),
.answer-content :deep(h3),
.answer-content :deep(h4) {
  margin: 0 0 0.75rem;
}

.answer-content :deep(p:last-child),
.answer-content :deep(ul:last-child),
.answer-content :deep(ol:last-child),
.answer-content :deep(blockquote:last-child),
.answer-content :deep(pre:last-child) {
  margin-bottom: 0;
}

.answer-content :deep(pre) {
  overflow-x: auto;
  padding: 0.85rem 1rem;
  border-radius: 12px;
  background: rgba(15, 23, 42, 0.72);
}

.answer-content :deep(code) {
  font-family: Consolas, Monaco, monospace;
}

.answer-content :deep(:not(pre) > code) {
  padding: 0.12rem 0.35rem;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.08);
}

.answer-content :deep(blockquote) {
  margin-left: 0;
  padding-left: 0.9rem;
  border-left: 3px solid rgba(86, 134, 254, 0.45);
  color: var(--muted);
}

.answer-content :deep(ul),
.answer-content :deep(ol) {
  padding-left: 1.25rem;
}

.answer-content :deep(a) {
  color: #7cb6ff;
}

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
  border: 1px solid var(--border);
  border-radius: 16px;
  color: var(--text);
  background: linear-gradient(145deg, rgba(16, 22, 34, 0.96), rgba(10, 15, 25, 0.92));
  box-shadow: var(--shadow);
  backdrop-filter: blur(18px);
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

.message-actions {
  display: flex;
  gap: 8px;
}

.citation-detail-text {
  white-space: pre-wrap;
  line-height: 1.7;
  padding: 0.9rem 1rem;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.06);
  background: rgba(255, 255, 255, 0.055);
}

.citation-detail-char {
  transition: opacity 0.28s ease;
}

.session-group-label {
  margin: 0.75rem 0 0.35rem;
  font-size: 0.75rem;
  color: rgba(148, 163, 184, 0.9);
}

.teleported-session-menu {
  position: fixed;
  z-index: 1200;
  min-width: 160px;
}
</style>

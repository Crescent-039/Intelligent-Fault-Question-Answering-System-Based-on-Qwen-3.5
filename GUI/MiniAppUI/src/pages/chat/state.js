import {
  DEFAULT_CLEARED_MESSAGE,
  DEFAULT_MODEL_CONFIG,
  DEFAULT_RAG_CONFIG,
  DEFAULT_SYSTEM_PROMPT,
  DEFAULT_WELCOME_MESSAGE,
} from './backend'

const CHAT_STATE_STORAGE_KEY = 'miniapp_chat_state_v2'
const SETTINGS_STORAGE_KEY = 'miniapp_chat_settings'

function deepClone(value) {
  return JSON.parse(JSON.stringify(value))
}

function createMessage(role, content, extra = {}) {
  return {
    id: `msg-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`,
    role,
    content,
    streaming: false,
    createdAt: Date.now(),
    ...extra,
  }
}

function createSessionTitle(messages = []) {
  const firstUserMessage = messages.find((message) => message.role === 'user' && message.content?.trim())
  if (!firstUserMessage) return '新对话'
  return firstUserMessage.content.trim().slice(0, 18) || '新对话'
}

function createSession(messages = null) {
  const now = Date.now()
  const sessionMessages = messages || [createMessage('assistant', DEFAULT_WELCOME_MESSAGE)]
  return {
    id: `session-${now}-${Math.random().toString(16).slice(2, 8)}`,
    title: createSessionTitle(sessionMessages),
    createdAt: now,
    updatedAt: now,
    messages: sessionMessages,
    fileIds: [],
  }
}

function buildDefaultChatSettings() {
  const saved = uni.getStorageSync(SETTINGS_STORAGE_KEY)
  return {
    systemPrompt: saved?.systemPrompt || DEFAULT_SYSTEM_PROMPT,
    temperature: saved?.temperature || String(DEFAULT_MODEL_CONFIG.temperature),
    maxTokens: saved?.maxTokens || String(DEFAULT_MODEL_CONFIG.max_tokens),
    topK: saved?.topK || String(DEFAULT_RAG_CONFIG.top_k),
    enableThinking: Boolean(DEFAULT_MODEL_CONFIG.enable_thinking),
    ragEnabled: Boolean(DEFAULT_RAG_CONFIG.enabled),
  }
}

function buildDefaultState() {
  const session = createSession()
  return {
    activeSessionId: session.id,
    chatSessions: [session],
    chatSettings: buildDefaultChatSettings(),
  }
}

function normalizeMessage(message) {
  return {
    id: message.id || `msg-restored-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`,
    role: message.role || 'assistant',
    content: message.content || '',
    streaming: Boolean(message.streaming),
    finishReason: message.finishReason || '',
    createdAt: Number(message.createdAt) || Date.now(),
  }
}

function normalizeSession(session) {
  const messages = Array.isArray(session?.messages) && session.messages.length
    ? session.messages.map(normalizeMessage)
    : [createMessage('assistant', DEFAULT_WELCOME_MESSAGE)]

  return {
    id: session.id || `session-restored-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`,
    title: session.title || createSessionTitle(messages),
    createdAt: Number(session.createdAt) || Date.now(),
    updatedAt: Number(session.updatedAt) || Date.now(),
    messages,
    fileIds: Array.isArray(session.fileIds) ? session.fileIds : [],
  }
}

function loadState() {
  const fallback = buildDefaultState()
  const saved = uni.getStorageSync(CHAT_STATE_STORAGE_KEY)

  if (!saved || typeof saved !== 'object') {
    return fallback
  }

  const chatSessions = Array.isArray(saved.chatSessions) && saved.chatSessions.length
    ? saved.chatSessions.map(normalizeSession)
    : fallback.chatSessions

  const activeSessionId = chatSessions.some((session) => session.id === saved.activeSessionId)
    ? saved.activeSessionId
    : chatSessions[0].id

  return {
    activeSessionId,
    chatSessions,
    chatSettings: {
      systemPrompt: buildDefaultChatSettings().systemPrompt,
      temperature: buildDefaultChatSettings().temperature,
      maxTokens: buildDefaultChatSettings().maxTokens,
      topK: buildDefaultChatSettings().topK,
      enableThinking: saved.chatSettings?.enableThinking ?? fallback.chatSettings.enableThinking,
      ragEnabled: saved.chatSettings?.ragEnabled ?? fallback.chatSettings.ragEnabled,
    },
  }
}

const appState = loadState()

export function snapshotAppState() {
  return deepClone(appState)
}

export function persistAppState() {
  uni.setStorageSync(CHAT_STATE_STORAGE_KEY, snapshotAppState())
}

export function syncChatSettingsFromStorage() {
  const storedSettings = buildDefaultChatSettings()
  Object.assign(appState.chatSettings, {
    ...appState.chatSettings,
    systemPrompt: storedSettings.systemPrompt,
    temperature: storedSettings.temperature,
    maxTokens: storedSettings.maxTokens,
    topK: storedSettings.topK,
  })
  persistAppState()
}

export function getChatSessionById(sessionId) {
  return appState.chatSessions.find((session) => session.id === sessionId) || null
}

export function getActiveChatSession() {
  return getChatSessionById(appState.activeSessionId) || appState.chatSessions[0] || null
}

export function setActiveChatSession(sessionId) {
  if (!getChatSessionById(sessionId)) return
  appState.activeSessionId = sessionId
  persistAppState()
}

export function createChatSession() {
  const session = createSession()
  appState.chatSessions.unshift(session)
  appState.activeSessionId = session.id
  persistAppState()
  return session
}

export function deleteChatSession(sessionId) {
  appState.chatSessions = appState.chatSessions.filter((session) => session.id !== sessionId)

  if (!appState.chatSessions.length) {
    const session = createSession()
    appState.chatSessions = [session]
    appState.activeSessionId = session.id
  } else if (appState.activeSessionId === sessionId) {
    appState.activeSessionId = appState.chatSessions[0].id
  }

  persistAppState()
}

export function pushSessionMessage(sessionId, message) {
  const session = getChatSessionById(sessionId)
  if (!session) return null

  const nextMessage = normalizeMessage(message)
  session.messages.push(nextMessage)
  session.updatedAt = Date.now()
  session.title = createSessionTitle(session.messages)
  persistAppState()
  return nextMessage
}

export function updateLastSessionMessage(sessionId, patch) {
  const session = getChatSessionById(sessionId)
  if (!session?.messages.length) return null

  Object.assign(session.messages[session.messages.length - 1], patch)
  session.updatedAt = Date.now()
  session.title = createSessionTitle(session.messages)
  persistAppState()
  return session.messages[session.messages.length - 1]
}

export function removeLastSessionMessage(sessionId) {
  const session = getChatSessionById(sessionId)
  if (!session?.messages.length) return null

  const removed = session.messages.pop()
  session.updatedAt = Date.now()
  session.title = createSessionTitle(session.messages)
  persistAppState()
  return removed
}

export function clearSessionMessages(sessionId) {
  const session = getChatSessionById(sessionId)
  if (!session) return

  session.messages = [createMessage('assistant', DEFAULT_CLEARED_MESSAGE)]
  session.updatedAt = Date.now()
  session.title = '新对话'
  persistAppState()
}

export function updateChatSettings(patch) {
  Object.assign(appState.chatSettings, patch)
  persistAppState()
}

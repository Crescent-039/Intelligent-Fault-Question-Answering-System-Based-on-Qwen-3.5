import { reactive } from 'vue'
import { getFrontendConfig } from '../config'

const STORAGE_KEY = 'qwen-rag-console-state-v1'

const frontendConfig = getFrontendConfig()
const chatConfig = frontendConfig.chat || {}

const DEFAULT_SETTINGS = {
  systemPrompt: chatConfig.system_prompt || '你是一个文档分析助手',
  temperature: chatConfig.model_config?.temperature ?? 0.7,
  maxTokens: chatConfig.model_config?.max_tokens ?? 2048,
  enableThinking: chatConfig.model_config?.enable_thinking ?? false,
  ragEnabled: chatConfig.rag?.enabled ?? true,
  topK: chatConfig.rag?.top_k ?? 5,
}

const DEFAULT_WELCOME_MESSAGE = chatConfig.welcome_message || '你好，我是文档分析助手。上传并完成索引后，你可以在这里进行基础 RAG 对话。'
const DEFAULT_USER_ID = frontendConfig.user?.default_user_id || 'default_user'

function createSessionTitle(messages = []) {
  const firstUserMessage = messages.find((message) => message.role === 'user' && message.content?.trim())
  if (!firstUserMessage) return '新对话'
  return firstUserMessage.content.trim().slice(0, 18) || '新对话'
}

function createSession(messages = null) {
  const now = Date.now()
  const sessionMessages = messages || [{ role: 'assistant', content: DEFAULT_WELCOME_MESSAGE }]
  return {
    id: globalThis.crypto?.randomUUID?.() || `session-${now}`,
    title: createSessionTitle(sessionMessages),
    createdAt: now,
    updatedAt: now,
    messages: sessionMessages,
    fileIds: [],
  }
}

function buildDefaultState() {
  const session = createSession()
  return {
    activeMode: 'conversation',
    activeSessionId: session.id,
    chatSessions: [session],
    chatSettings: { ...DEFAULT_SETTINGS },
    upload: {
      userId: DEFAULT_USER_ID,
    },
  }
}

function loadState() {
  const fallback = buildDefaultState()
  const raw = localStorage.getItem(STORAGE_KEY)
  if (!raw) return fallback

  const parsed = JSON.parse(raw)
  const chatSessions = Array.isArray(parsed?.chatSessions) && parsed.chatSessions.length
    ? parsed.chatSessions.map((session) => ({
        ...session,
        title: session.title || createSessionTitle(session.messages),
        messages: Array.isArray(session.messages) ? session.messages : [],
        fileIds: Array.isArray(session.fileIds) ? session.fileIds : [],
      }))
    : fallback.chatSessions

  return {
    activeMode: parsed?.activeMode || fallback.activeMode,
    activeSessionId: parsed?.activeSessionId || chatSessions[0].id,
    chatSessions,
    chatSettings: {
      ...DEFAULT_SETTINGS,
      ...(parsed?.chatSettings || {}),
    },
    upload: {
      userId: parsed?.upload?.userId || fallback.upload.userId,
    },
  }
}

export const appState = reactive(loadState())

export function persistAppState() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify({
    activeMode: appState.activeMode,
    activeSessionId: appState.activeSessionId,
    chatSessions: appState.chatSessions,
    chatSettings: appState.chatSettings,
    upload: appState.upload,
  }))
}

export function setActiveMode(mode) {
  appState.activeMode = mode
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

export function updateSessionTitle(sessionId) {
  const session = getChatSessionById(sessionId)
  if (!session) return
  session.title = createSessionTitle(session.messages)
  session.updatedAt = Date.now()
  persistAppState()
}

export function pushSessionMessage(sessionId, message) {
  const session = getChatSessionById(sessionId)
  if (!session) return
  session.messages.push(message)
  session.updatedAt = Date.now()
  session.title = createSessionTitle(session.messages)
  persistAppState()
}

export function updateLastSessionMessage(sessionId, patch) {
  const session = getChatSessionById(sessionId)
  if (!session?.messages.length) return
  Object.assign(session.messages[session.messages.length - 1], patch)
  session.updatedAt = Date.now()
  session.title = createSessionTitle(session.messages)
  persistAppState()
}

export function removeLastSessionMessage(sessionId) {
  const session = getChatSessionById(sessionId)
  if (!session?.messages.length) return
  session.messages.pop()
  session.updatedAt = Date.now()
  session.title = createSessionTitle(session.messages)
  persistAppState()
}

export function clearSessionMessages(sessionId, clearedMessage) {
  const session = getChatSessionById(sessionId)
  if (!session) return
  session.messages = [{ role: 'assistant', content: clearedMessage }]
  session.updatedAt = Date.now()
  session.title = '新对话'
  persistAppState()
}

export function updateChatSettings(patch) {
  Object.assign(appState.chatSettings, patch)
  persistAppState()
}

export function setUploadUserId(userId) {
  appState.upload.userId = userId
  persistAppState()
}
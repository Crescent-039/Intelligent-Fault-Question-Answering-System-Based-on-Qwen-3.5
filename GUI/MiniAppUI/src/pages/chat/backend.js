export const DEFAULT_HTTP_BASE_URL = 'http://10.214.170.32:11451'
const DEFAULT_WS_PATH = '/ws/chat'
const DEFAULT_HEARTBEAT_INTERVAL_MS = 30_000

export const DEFAULT_SYSTEM_PROMPT = '你是一个文档分析助手'
export const DEFAULT_WELCOME_MESSAGE = '你好，我是文档分析助手。上传并完成索引后，你可以在这里进行基础 RAG 对话。'
export const DEFAULT_CLEARED_MESSAGE = '对话已清空。你可以开始新的问题。'

export const DEFAULT_MODEL_CONFIG = {
  temperature: 0.7,
  max_tokens: 2048,
  enable_thinking: false,
}

export const DEFAULT_RAG_CONFIG = {
  enabled: true,
  top_k: 5,
}

function createRequestId() {
  return `req-${Date.now()}-${Math.random().toString(16).slice(2, 10)}`
}

function parseBaseUrl(baseUrl = DEFAULT_HTTP_BASE_URL) {
  const matched = String(baseUrl).match(/^(https?):\/\/([^/]+)(\/.*)?$/i)
  if (!matched) {
    return {
      protocol: 'http:',
      host: '127.0.0.1:11451',
    }
  }

  return {
    protocol: `${matched[1].toLowerCase()}:`,
    host: matched[2],
  }
}

export function createDefaultWsUrl(wsPath = DEFAULT_WS_PATH, httpBaseUrl = DEFAULT_HTTP_BASE_URL) {
  const normalizedPath = wsPath.startsWith('/') ? wsPath : `/${wsPath}`
  const { protocol, host } = parseBaseUrl(httpBaseUrl)
  const wsProtocol = protocol === 'https:' ? 'wss:' : 'ws:'
  return `${wsProtocol}//${host}${normalizedPath}`
}

export function buildChatMessages(visibleMessages, systemPrompt = DEFAULT_SYSTEM_PROMPT) {
  return [
    { role: 'system', content: systemPrompt },
    ...(visibleMessages || [])
      .filter((message) => ['user', 'assistant'].includes(message.role) && message.content?.trim())
      .map((message) => ({
        role: message.role,
        content: message.content,
      })),
  ]
}

export class ChatStreamClient {
  constructor(options = {}) {
    this.url = options.url || createDefaultWsUrl()
    this.handlers = options.handlers || {}
    this.socketTask = null
    this.heartbeatTimer = null
    this.activeRequestId = null
    this.connected = false
    this.connectPromise = null
    this.bound = false
  }

  isOpen() {
    return this.connected
  }

  connect() {
    if (this.isOpen()) return Promise.resolve()
    if (this.connectPromise) return this.connectPromise

    this.connectPromise = new Promise((resolve, reject) => {
      const socketTask = uni.connectSocket({
        url: this.url,
        complete: () => {},
      })

      this.socketTask = socketTask
      this.bindSocketEvents(socketTask, resolve, reject)
    })

    return this.connectPromise
  }

  bindSocketEvents(socketTask, resolve, reject) {
    if (!socketTask) return

    socketTask.onOpen(() => {
      this.connected = true
      this.startHeartbeat()
      this.handlers.onOpen?.()
      this.connectPromise = null
      resolve?.()
    })

    socketTask.onMessage((event) => {
      this.handleMessage(event.data)
    })

    socketTask.onError((error) => {
      this.connected = false
      this.stopHeartbeat()
      this.handlers.onError?.({ code: 'WS_ERROR', message: 'WebSocket 连接异常', raw: error })
      this.connectPromise = null
      reject?.(new Error('WebSocket 连接异常'))
    })

    socketTask.onClose(() => {
      this.connected = false
      this.stopHeartbeat()
      this.handlers.onClose?.()
      this.connectPromise = null
    })
  }

  sendRaw(data) {
    if (!this.socketTask || !this.isOpen()) {
      throw new Error('WebSocket 尚未连接，请稍后重试')
    }

    this.socketTask.send({
      data: JSON.stringify(data),
    })
  }

  sendChat({ messages, fileIds = [], rag = DEFAULT_RAG_CONFIG, modelConfig = DEFAULT_MODEL_CONFIG }) {
    if (!this.isOpen()) {
      this.connect()
      throw new Error('WebSocket 尚未连接，请稍后重试')
    }

    const requestId = createRequestId()
    this.activeRequestId = requestId
    this.sendRaw({
      request_id: requestId,
      type: 'chat',
      payload: {
        messages,
        file_ids: fileIds,
        rag,
        model_config: modelConfig,
      },
    })
    return requestId
  }

  cancel(requestId = this.activeRequestId) {
    if (!requestId || !this.isOpen()) return
    this.sendRaw({
      request_id: requestId,
      type: 'cancel',
    })
  }

  requestCitationDetail(chunkUid) {
    if (!this.isOpen()) {
      throw new Error('WebSocket 尚未连接，请稍后重试')
    }

    const requestId = createRequestId()
    this.sendRaw({
      request_id: requestId,
      type: 'citation_detail',
      payload: {
        chunk_uid: Number(chunkUid),
      },
    })
    return requestId
  }

  ping() {
    if (!this.isOpen()) return
    this.sendRaw({
      request_id: `ping-${Date.now()}`,
      type: 'ping',
      payload: {},
    })
  }

  startHeartbeat() {
    this.stopHeartbeat()
    this.heartbeatTimer = setInterval(() => this.ping(), DEFAULT_HEARTBEAT_INTERVAL_MS)
  }

  stopHeartbeat() {
    if (!this.heartbeatTimer) return
    clearInterval(this.heartbeatTimer)
    this.heartbeatTimer = null
  }

  reconnect() {
    this.close()
    return this.connect()
  }

  close() {
    this.stopHeartbeat()
    if (this.socketTask) {
      try {
        this.socketTask.close({})
      } catch (error) {
        console.warn('[chat] socket close failed', error)
      }
    }
    this.socketTask = null
    this.connected = false
    this.connectPromise = null
  }

  handleMessage(rawMessage) {
    let message
    try {
      message = typeof rawMessage === 'string' ? JSON.parse(rawMessage) : rawMessage
    } catch (error) {
      this.handlers.onError?.({ code: 'INVALID_JSON', message: '收到非 JSON 消息', raw: rawMessage, error })
      return
    }

    this.handlers.onMessage?.(message)
    const { request_id: requestId, type, payload = {} } = message

    if (type === 'stream_start') this.handlers.onStreamStart?.({ requestId, payload })
    if (type === 'stream_chunk') this.handlers.onChunk?.({ requestId, delta: payload.delta || '', payload })
    if (type === 'stream_end') {
      if (requestId === this.activeRequestId) this.activeRequestId = null
      this.handlers.onStreamEnd?.({ requestId, payload })
    }
    if (type === 'error') {
      if (requestId === this.activeRequestId) this.activeRequestId = null
      this.handlers.onError?.({ requestId, ...payload })
    }
    if (type === 'citation_detail_result') this.handlers.onCitationDetail?.({ requestId, payload })
    if (type === 'pong') this.handlers.onPong?.({ requestId, payload })
  }
}

export const DEFAULT_SYSTEM_PROMPT = '你是一个文档分析助手'

export const DEFAULT_MODEL_CONFIG = {
  temperature: 0.7,
  max_tokens: 2048,
}

export const DEFAULT_RAG_CONFIG = {
  enabled: true,
  top_k: 5,
}

export function createDefaultWsUrl() {
  return 'ws://127.0.0.1:5173/ws/chat'
}

function createRequestId() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID()
  return `req-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

export class ChatStreamClient {
  constructor(options = {}) {
    this.url = options.url || createDefaultWsUrl()
    this.handlers = options.handlers || {}
    this.socket = null
    this.activeRequestId = null
    this.heartbeatTimer = null
  }

  connect() {
    if (this.socket && [WebSocket.OPEN, WebSocket.CONNECTING].includes(this.socket.readyState)) return

    this.socket = new WebSocket(this.url)

    this.socket.addEventListener('open', () => {
      this.handlers.onOpen?.()
      this.startHeartbeat()
    })

    this.socket.addEventListener('message', (event) => this.handleMessage(event.data))

    this.socket.addEventListener('error', (event) => {
      this.handlers.onError?.({ code: 'WS_ERROR', message: 'WebSocket 连接异常', raw: event })
    })

    this.socket.addEventListener('close', () => {
      this.stopHeartbeat()
      this.handlers.onClose?.()
    })
  }

  isOpen() {
    return this.socket?.readyState === WebSocket.OPEN
  }

  sendChat({ messages, fileIds = [], rag = DEFAULT_RAG_CONFIG, modelConfig = DEFAULT_MODEL_CONFIG }) {
    if (!this.isOpen()) {
      this.connect()
      throw new Error('WebSocket 尚未连接，请稍后重试')
    }

    const requestId = createRequestId()
    this.activeRequestId = requestId

    this.socket.send(JSON.stringify({
      request_id: requestId,
      type: 'chat',
      payload: {
        messages,
        file_ids: fileIds,
        rag,
        model_config: modelConfig,
      },
    }))

    return requestId
  }

  cancel(requestId = this.activeRequestId) {
    if (!requestId || !this.isOpen()) return
    this.socket.send(JSON.stringify({ request_id: requestId, type: 'cancel' }))
  }

  ping() {
    if (!this.isOpen()) return
    this.socket.send(JSON.stringify({
      request_id: `ping-${Date.now()}`,
      type: 'ping',
      payload: {},
    }))
  }

  startHeartbeat() {
    this.stopHeartbeat()
    this.heartbeatTimer = window.setInterval(() => this.ping(), 30_000)
  }

  stopHeartbeat() {
    if (!this.heartbeatTimer) return
    window.clearInterval(this.heartbeatTimer)
    this.heartbeatTimer = null
  }

  close() {
    this.stopHeartbeat()
    this.socket?.close()
    this.socket = null
  }

  handleMessage(rawMessage) {
    let message
    try {
      message = JSON.parse(rawMessage)
    } catch {
      this.handlers.onError?.({ code: 'INVALID_JSON', message: '收到非 JSON 消息', raw: rawMessage })
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
    if (type === 'pong') this.handlers.onPong?.({ requestId, payload })
  }
}

export function buildChatMessages(visibleMessages, systemPrompt = DEFAULT_SYSTEM_PROMPT) {
  return [
    { role: 'system', content: systemPrompt },
    ...visibleMessages
      .filter((message) => ['user', 'assistant'].includes(message.role) && message.content?.trim())
      .map((message) => ({ role: message.role, content: message.content })),
  ]
}

const DEFAULT_RUNTIME_CONFIG = {
  protocol: {
    version: '1.0',
  },
  frontend: {
    api: {
      http_base_url: 'http://127.0.0.1:11451',
      config_endpoint: '/api/config/frontend',
      ws_path: '/ws/chat',
      protocol_label: 'HTTP Upload · WS Stream · Config Driven',
    },
    user: {
      default_user_id: 'default_user',
    },
    ws: {
      heartbeat_interval_ms: 30_000,
    },
    upload: {
      supported_extensions: ['pdf', 'png', 'jpg', 'jpeg'],
      max_file_size_mb: 100,
      max_batch_count: 200,
      concurrent_uploads: 3,
      poll_interval_ms: 2_000,
    },
    chat: {
      system_prompt: '你是一个文档分析助手',
      welcome_message: '你好，我是文档分析助手。上传并完成索引后，你可以在这里进行基础 RAG 对话。',
      cleared_message: '对话已清空。你可以开始新的问题。',
      rag: {
        enabled: true,
        top_k: 5,
      },
      model_config: {
        temperature: 0.7,
        max_tokens: 2048,
        enable_thinking: false,
      },
    },
  },
}

let runtimeConfig = deepClone(DEFAULT_RUNTIME_CONFIG)

function deepClone(value) {
  return JSON.parse(JSON.stringify(value))
}

function isPlainObject(value) {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}

function deepMerge(base, override) {
  const result = deepClone(base)

  if (!isPlainObject(override)) return result

  Object.entries(override).forEach(([key, value]) => {
    if (isPlainObject(value) && isPlainObject(result[key])) {
      result[key] = deepMerge(result[key], value)
      return
    }

    result[key] = value
  })

  return result
}

export async function loadRuntimeConfig() {
  const apiConfig = DEFAULT_RUNTIME_CONFIG.frontend.api
  const endpoint = apiConfig.config_endpoint?.startsWith('http')
    ? apiConfig.config_endpoint
    : `${apiConfig.http_base_url || ''}${apiConfig.config_endpoint || ''}`

  try {
    const response = await fetch(endpoint)
    if (!response.ok) throw new Error(`配置加载失败：${response.status}`)

    const data = await response.json()
    runtimeConfig = deepMerge(DEFAULT_RUNTIME_CONFIG, data)
    return runtimeConfig
  } catch (error) {
    console.warn('[config] 使用默认前端配置：', error)
    runtimeConfig = deepClone(DEFAULT_RUNTIME_CONFIG)
    return runtimeConfig
  }
}

export function getRuntimeConfig() {
  return runtimeConfig
}

export function getFrontendConfig() {
  return runtimeConfig.frontend || {}
}

export function buildWebSocketUrl(wsPath = '/ws/chat') {
  const normalizedPath = wsPath.startsWith('/') ? wsPath : `/${wsPath}`
  const configuredBaseUrl = runtimeConfig.frontend?.api?.http_base_url

  if (configuredBaseUrl) {
    const parsed = new URL(configuredBaseUrl, window.location.origin)
    const protocol = parsed.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${protocol}//${parsed.host}${normalizedPath}`
  }

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}${normalizedPath}`
}
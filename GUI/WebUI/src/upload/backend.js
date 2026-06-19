import { getFrontendConfig } from '../config'

const frontendConfig = getFrontendConfig()
const API_BASE = frontendConfig.api?.http_base_url || ''

export const DEFAULT_USER_ID = frontendConfig.user?.default_user_id || 'default_user'
export const SUPPORTED_EXTENSIONS = frontendConfig.upload?.supported_extensions || ['txt', 'md', 'pdf', 'docx', 'csv', 'xlsx', 'xls', 'html', 'htm', 'pptx', 'ppt']
export const ACCEPT_ATTRIBUTE = SUPPORTED_EXTENSIONS.map((extension) => `.${extension}`).join(',')

export function isSupportedFile(file) {
  if (!file?.name) return false
  const extension = file.name.split('.').pop()?.toLowerCase()
  return SUPPORTED_EXTENSIONS.includes(extension)
}

async function parseResponse(response) {
  const data = await response.json().catch(() => null)

  if (!response.ok || data?.status === 'error') {
    const error = new Error(data?.message || `请求失败：${response.status}`)
    error.code = data?.code || response.status
    error.payload = data
    throw error
  }

  return data
}

export async function uploadFile(file, userId = DEFAULT_USER_ID) {
  if (!isSupportedFile(file)) {
    const error = new Error(`仅支持 ${SUPPORTED_EXTENSIONS.join(' / ')} 格式`)
    error.code = 'UNSUPPORTED_FILE_TYPE'
    throw error
  }

  const formData = new FormData()
  formData.append('file', file)
  formData.append('user_id', userId)

  const response = await fetch(`${API_BASE}/api/upload`, {
    method: 'POST',
    body: formData,
  })

  return parseResponse(response)
}

export async function fetchFiles(userId = DEFAULT_USER_ID) {
  const response = await fetch(`${API_BASE}/api/files?user_id=${encodeURIComponent(userId)}`)
  const data = await parseResponse(response)
  return Array.isArray(data?.files) ? data.files : []
}

export async function fetchFileStatus(fileId) {
  const response = await fetch(`${API_BASE}/api/file/${encodeURIComponent(fileId)}/status`)
  return parseResponse(response)
}

export async function deleteFile(fileId) {
  const response = await fetch(`${API_BASE}/api/file/${encodeURIComponent(fileId)}`, {
    method: 'DELETE',
  })

  return parseResponse(response)
}

export function normalizeUploadError(error) {
  return {
    code: error?.code || 'UPLOAD_ERROR',
    message: error?.message || '上传失败，请稍后重试',
  }
}

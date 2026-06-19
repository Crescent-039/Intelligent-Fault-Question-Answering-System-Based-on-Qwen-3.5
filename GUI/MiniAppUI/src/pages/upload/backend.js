import { DEFAULT_HTTP_BASE_URL } from '../chat/backend'

export const API_BASE = DEFAULT_HTTP_BASE_URL
export const DEFAULT_USER_ID = 'default_user'
export const SUPPORTED_EXTENSIONS = ['txt', 'md', 'pdf', 'docx', 'csv', 'xlsx', 'xls', 'html', 'htm', 'pptx', 'ppt']
export const FILE_LIST_CACHE_KEY = 'miniapp_upload_files_cache'

export function isSupportedFile(file) {
  if (!file?.name) return false
  const extension = file.name.split('.').pop()?.toLowerCase()
  return SUPPORTED_EXTENSIONS.includes(extension)
}

function parsePayload(rawData) {
  if (!rawData) return null
  if (typeof rawData === 'string') {
    try {
      return JSON.parse(rawData)
    } catch (error) {
      return null
    }
  }
  return rawData
}

function normalizeError(payload, fallbackMessage) {
  const error = new Error(payload?.message || fallbackMessage)
  error.code = payload?.code || 'REQUEST_ERROR'
  error.payload = payload
  return error
}

function request({ url, method = 'GET', data }) {
  return new Promise((resolve, reject) => {
    uni.request({
      url,
      method,
      data,
      success: (response) => {
        const payload = parsePayload(response.data)
        if (response.statusCode < 200 || response.statusCode >= 300 || payload?.status === 'error') {
          reject(normalizeError(payload, `请求失败：${response.statusCode}`))
          return
        }
        resolve(payload)
      },
      fail: (error) => {
        reject(normalizeError(null, error?.errMsg || '网络请求失败'))
      },
    })
  })
}

export function uploadFile(file, userId = DEFAULT_USER_ID) {
  if (!isSupportedFile(file)) {
    throw normalizeError({ code: 'UNSUPPORTED_FILE_TYPE', message: `仅支持 ${SUPPORTED_EXTENSIONS.join(' / ')} 格式` }, '文件类型不支持')
  }

  return new Promise((resolve, reject) => {
    uni.uploadFile({
      url: `${API_BASE}/api/upload`,
      filePath: file.path,
      name: 'file',
      formData: {
        user_id: userId,
      },
      success: (response) => {
        const payload = parsePayload(response.data)
        if (response.statusCode < 200 || response.statusCode >= 300 || payload?.status === 'error') {
          reject(normalizeError(payload, `上传失败：${response.statusCode}`))
          return
        }
        resolve(payload)
      },
      fail: (error) => {
        reject(normalizeError(null, error?.errMsg || '上传失败'))
      },
    })
  })
}

export function fetchFiles(userId = DEFAULT_USER_ID) {
  return request({
    url: `${API_BASE}/api/files?user_id=${encodeURIComponent(userId)}`,
  }).then((payload) => (Array.isArray(payload?.files) ? payload.files : []))
}

export function readCachedFiles() {
  const cached = uni.getStorageSync(FILE_LIST_CACHE_KEY)
  return Array.isArray(cached) ? cached : []
}

export function cacheFiles(files) {
  if (!Array.isArray(files)) return
  uni.setStorageSync(FILE_LIST_CACHE_KEY, files)
}

export function warmFileCache(userId = DEFAULT_USER_ID) {
  return fetchFiles(userId).then((files) => {
    cacheFiles(files)
    return files
  })
}

export function fetchFileStatus(fileId) {
  return request({
    url: `${API_BASE}/api/file/${encodeURIComponent(fileId)}/status`,
  })
}

export function deleteFile(fileId) {
  return request({
    url: `${API_BASE}/api/file/${encodeURIComponent(fileId)}`,
    method: 'DELETE',
  })
}

export function normalizeUploadError(error) {
  return {
    code: error?.code || 'UPLOAD_ERROR',
    message: error?.message || '上传失败，请稍后重试',
  }
}

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import {
  ACCEPT_ATTRIBUTE,
  SUPPORTED_EXTENSIONS,
  deleteFile,
  fetchFileStatus,
  fetchFiles,
  isSupportedFile,
  normalizeUploadError,
  uploadFile,
} from './backend'
import { appState, setUploadUserId } from '../state/appState'

const userId = computed({
  get: () => appState.upload.userId,
  set: (value) => setUploadUserId(value),
})
const fileInput = ref(null)
const folderInput = ref(null)
const selectedFiles = ref([])
const uploadedFiles = ref([])
const loading = ref(false)
const uploading = ref(false)
const notice = ref('')
const acceptAttribute = ACCEPT_ATTRIBUTE
const supportedFormatText = SUPPORTED_EXTENSIONS.join(' / ')
const previousStatusMap = new Map()
const progressStartMap = new Map()
const progressNow = ref(Date.now())

let pollingTimer = null
let progressTimer = null

const supportedFiles = computed(() => selectedFiles.value.filter((item) => item.supported))

const statusText = {
  pending: '等待处理',
  downloading: '正在下载',
  downloaded: '下载完成',
  preprocessing: '正在预处理',
  indexing: '正在索引',
  done: '可用于对话',
  failed: '处理失败',
}

const activeStatuses = ['pending', 'downloading', 'downloaded', 'preprocessing', 'indexing']
const progressStatuses = [...activeStatuses, 'done', 'failed']

function openFileDialog() {
  fileInput.value?.click()
}

function openFolderDialog() {
  folderInput.value?.click()
}

function collectFiles(event) {
  const files = Array.from(event.target.files || [])
  selectedFiles.value = files.map((file) => ({
    file,
    name: file.webkitRelativePath || file.name,
    supported: isSupportedFile(file),
    status: 'ready',
    message: isSupportedFile(file) ? '待上传' : '格式不支持',
  }))
  event.target.value = ''
}

async function loadFiles() {
  loading.value = true
  try {
    const files = await fetchFiles(userId.value)
    handleStatusTransitions(files)
    uploadedFiles.value = files
    syncPollingState(files)
  } catch (error) {
    notice.value = error.message || '文件列表获取失败'
  } finally {
    loading.value = false
  }
}

function handleStatusTransitions(files) {
  for (const file of files) {
    const previousStatus = previousStatusMap.get(file.file_id)
    const currentStatus = file.index_status

    if (previousStatus !== currentStatus) {
      if (previousStatus !== 'downloaded' && currentStatus === 'downloaded') {
        notice.value = `${file.filename} 下载完成`
      }

      if (previousStatus !== 'done' && currentStatus === 'done') {
        notice.value = `${file.filename} 预处理完成`
      }

      if (previousStatus !== 'failed' && currentStatus === 'failed' && file.message) {
        notice.value = `${file.filename} 处理失败：${file.message}`
      }
    }

    previousStatusMap.set(file.file_id, currentStatus)
  }
}

function getFakeProgress(file) {
  if (file.index_status === 'done') return 100
  if (file.index_status === 'failed') return 100
  if (!activeStatuses.includes(file.index_status)) return 0

  const startedAt = progressStartMap.get(file.file_id) || progressNow.value
  const elapsedRatio = Math.min((progressNow.value - startedAt) / 20000, 1)
  const easedRatio = 1 - Math.pow(1 - elapsedRatio, 3)
  return Math.min(Math.round(8 + easedRatio * 91), 99)
}

function shouldShowProgress(file) {
  return progressStatuses.includes(file.index_status)
}

function hasActiveFiles(files) {
  return files.some((file) => activeStatuses.includes(file.index_status))
}

function stopPolling() {
  if (!pollingTimer) return
  window.clearTimeout(pollingTimer)
  pollingTimer = null
}

function stopProgressTimer() {
  if (!progressTimer) return
  window.clearInterval(progressTimer)
  progressTimer = null
}

function syncProgressTimer(files = uploadedFiles.value) {
  for (const file of files) {
    if (activeStatuses.includes(file.index_status) && !progressStartMap.has(file.file_id)) {
      progressStartMap.set(file.file_id, Date.now())
    }
  }

  if (hasActiveFiles(files)) {
    if (!progressTimer) {
      progressTimer = window.setInterval(() => {
        progressNow.value = Date.now()
      }, 500)
    }
    return
  }

  stopProgressTimer()
}

function schedulePolling() {
  stopPolling()
  pollingTimer = window.setTimeout(async () => {
    await loadFiles()
  }, 2000)
}

function syncPollingState(files = uploadedFiles.value) {
  syncProgressTimer(files)

  if (hasActiveFiles(files)) {
    schedulePolling()
    return
  }

  stopPolling()
}

async function uploadSelectedFiles() {
  if (!supportedFiles.value.length || uploading.value) return

  const existingNames = new Set(uploadedFiles.value.map((file) => file.filename))
  const duplicatedFiles = supportedFiles.value.filter((item) => existingNames.has(item.file.name))

  if (duplicatedFiles.length) {
    window.alert(`以下文件已存在，将从待上传列表移除：\n${duplicatedFiles.map((item) => item.file.name).join('\n')}`)
    selectedFiles.value = selectedFiles.value.filter((item) => !duplicatedFiles.includes(item))
  }

  const queuedFiles = selectedFiles.value.filter((item) => item.supported)
  if (!queuedFiles.length) return

  uploading.value = true
  notice.value = ''
  selectedFiles.value = []

  for (const item of queuedFiles) {
    if (!item.supported) continue

    item.status = 'uploading'
    item.message = '上传中...'

    try {
      await uploadFile(item.file, userId.value)
      item.status = 'success'
      item.message = '上传成功，等待索引'
    } catch (error) {
      const normalized = normalizeUploadError(error)
      item.status = 'failed'
      item.message = normalized.message
    }
  }

  uploading.value = false
  await loadFiles()
}

async function refreshStatus(file) {
  file.refreshing = true
  try {
    const result = await fetchFileStatus(file.file_id)
    file.index_status = result.index_status
    file.message = result.message
  } catch (error) {
    file.message = error.message || '状态刷新失败'
  } finally {
    file.refreshing = false
  }
}

async function removeFile(file) {
  if (file.deleting) return
  if (!window.confirm(`确认删除 ${file.filename}？`)) return

  file.deleting = true
  try {
    const result = await deleteFile(file.file_id)
    window.alert(result?.message || '删除成功')
    await loadFiles()
  } catch (error) {
    window.alert(error?.message || '删除失败')
  } finally {
    file.deleting = false
  }
}

onMounted(loadFiles)
onBeforeUnmount(() => {
  stopPolling()
  stopProgressTimer()
})
</script>

<template>
  <section class="module-panel upload-panel">
    <div class="panel-header">
      <div>
        <p class="eyebrow">Document Pipeline</p>
        <h2>文档上传与预处理</h2>
      </div>
      <button class="ghost-btn" :disabled="loading" @click="loadFiles">
        {{ loading ? '刷新中' : '刷新列表' }}
      </button>
    </div>

    <div class="upload-top-grid">
      <div class="upload-dropzone">
        <input ref="fileInput" hidden type="file" multiple :accept="acceptAttribute" @change="collectFiles" />
        <input ref="folderInput" hidden type="file" multiple webkitdirectory directory @change="collectFiles" />

        <div class="dropzone-glow"></div>
        <p class="dropzone-title">选择文件或文件夹</p>
        <p class="muted">支持 {{ supportedFormatText }}</p>
        <div class="action-row">
          <button class="primary-btn" @click="openFileDialog">选择文件</button>
          <button class="secondary-btn" @click="openFolderDialog">选择文件夹</button>
        </div>
      </div>

      <div class="sub-panel upload-queue-panel">
        <div class="panel-header compact">
          <h3>待上传队列</h3>
          <button class="primary-btn small" :disabled="uploading || !supportedFiles.length" @click="uploadSelectedFiles">
            {{ uploading ? '上传中...' : `上传 ${supportedFiles.length} 个文件` }}
          </button>
        </div>

        <div v-if="!selectedFiles.length" class="empty-state queue-empty">暂无待上传文件。</div>

        <div v-else class="queue-list">
          <div v-for="item in selectedFiles" :key="item.name" class="file-row">
            <div>
              <strong>{{ item.name }}</strong>
              <p>{{ item.message }}</p>
            </div>
            <span class="badge" :class="item.status">{{ item.status }}</span>
          </div>
        </div>
      </div>
    </div>

    <div class="sub-panel file-library">
      <div class="panel-header compact">
        <h3>文档库</h3>
        <span class="muted">user_id: {{ userId }}</span>
      </div>

      <div v-if="!uploadedFiles.length" class="empty-state">暂无文档，请先上传。</div>

      <div v-else class="file-list">
        <div v-for="file in uploadedFiles" :key="file.file_id" class="file-card">
          <div class="file-meta">
            <strong>{{ file.filename }}</strong>
            <p>{{ file.file_type }} · {{ file.uploaded_at || '刚刚上传' }}</p>
            <p v-if="file.message" class="file-message">{{ file.message }}</p>
            <div v-if="shouldShowProgress(file)" class="file-progress">
              <div class="progress-track">
                <div class="progress-fill" :class="file.index_status" :style="{ width: `${getFakeProgress(file)}%` }"></div>
              </div>
              <span>{{ getFakeProgress(file) }}%</span>
            </div>
          </div>
          <div class="file-actions">
            <span class="badge" :class="file.index_status">{{ statusText[file.index_status] || file.index_status }}</span>
            <button class="ghost-btn small" :disabled="file.refreshing" @click="refreshStatus(file)">
              {{ file.refreshing ? '查询中' : '状态' }}
            </button>
            <button class="danger-btn small" :disabled="file.deleting" @click="removeFile(file)">
              {{ file.deleting ? '删除中...' : '删除' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

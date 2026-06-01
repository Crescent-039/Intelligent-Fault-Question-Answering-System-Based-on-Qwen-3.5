<script setup>
import { computed, onMounted, ref } from 'vue'
import {
  DEFAULT_USER_ID,
  deleteFile,
  fetchFileStatus,
  fetchFiles,
  isSupportedFile,
  normalizeUploadError,
  uploadFile,
} from './backend'

const userId = ref(DEFAULT_USER_ID)
const fileInput = ref(null)
const folderInput = ref(null)
const selectedFiles = ref([])
const uploadedFiles = ref([])
const loading = ref(false)
const uploading = ref(false)
const notice = ref('')

const supportedFiles = computed(() => selectedFiles.value.filter((item) => item.supported))

const statusText = {
  pending: '等待处理',
  indexing: '正在索引',
  done: '可用于对话',
  failed: '处理失败',
}

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
  notice.value = ''
  try {
    uploadedFiles.value = await fetchFiles(userId.value)
  } catch (error) {
    notice.value = error.message || '文件列表获取失败'
  } finally {
    loading.value = false
  }
}

async function uploadSelectedFiles() {
  if (!supportedFiles.value.length || uploading.value) return

  uploading.value = true
  notice.value = ''

  for (const item of selectedFiles.value) {
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
  if (!window.confirm(`确认删除 ${file.filename}？`)) return
  await deleteFile(file.file_id)
  await loadFiles()
}

onMounted(loadFiles)
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

    <div class="upload-dropzone">
      <input ref="fileInput" hidden type="file" multiple accept=".pdf,.png,.jpg,.jpeg" @change="collectFiles" />
      <input ref="folderInput" hidden type="file" multiple webkitdirectory directory @change="collectFiles" />

      <div class="dropzone-glow"></div>
      <p class="dropzone-title">选择文件或文件夹</p>
      <p class="muted">支持 pdf / png / jpg，文件夹会自动拆分为多个文件上传。</p>
      <div class="action-row">
        <button class="primary-btn" @click="openFileDialog">选择文件</button>
        <button class="secondary-btn" @click="openFolderDialog">选择文件夹</button>
      </div>
    </div>

    <div v-if="selectedFiles.length" class="sub-panel">
      <div class="panel-header compact">
        <h3>待上传队列</h3>
        <button class="primary-btn small" :disabled="uploading || !supportedFiles.length" @click="uploadSelectedFiles">
          {{ uploading ? '上传中...' : `上传 ${supportedFiles.length} 个文件` }}
        </button>
      </div>

      <div class="queue-list">
        <div v-for="item in selectedFiles" :key="item.name" class="file-row">
          <div>
            <strong>{{ item.name }}</strong>
            <p>{{ item.message }}</p>
          </div>
          <span class="badge" :class="item.status">{{ item.status }}</span>
        </div>
      </div>
    </div>

    <p v-if="notice" class="notice">{{ notice }}</p>

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
          </div>
          <div class="file-actions">
            <span class="badge" :class="file.index_status">{{ statusText[file.index_status] || file.index_status }}</span>
            <button class="ghost-btn small" :disabled="file.refreshing" @click="refreshStatus(file)">
              {{ file.refreshing ? '查询中' : '状态' }}
            </button>
            <button class="danger-btn small" @click="removeFile(file)">删除</button>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

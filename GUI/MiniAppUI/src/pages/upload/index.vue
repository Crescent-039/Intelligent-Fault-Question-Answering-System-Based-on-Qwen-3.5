<template>
  <view class="page-shell">
    <view class="ambient ambient-left"></view>
    <view class="ambient ambient-right"></view>

    <view class="top-bar">
      <view class="menu-button" @tap="toggleSidebar">
        <view class="menu-line"></view>
        <view class="menu-line"></view>
        <view class="menu-line short"></view>
      </view>
      <view class="page-title-wrap">
        <text class="page-caption">DOCUMENT PIPELINE</text>
        <text class="page-title">文档上传与预处理</text>
      </view>
    </view>

    <view class="sidebar-mask" :class="{ show: sidebarOpen }" @tap="closeSidebar"></view>
    <view class="sidebar" :class="{ open: sidebarOpen }">
      <view class="sidebar-header">
        <text class="sidebar-title">文档库</text>
        <text class="sidebar-subtitle">user_id: {{ userId }}</text>
      </view>

      <scroll-view class="sidebar-scroll" scroll-y="true" enhanced="true" show-scrollbar="true">
        <text v-if="!uploadedFiles.length" class="sidebar-empty">暂无文档，请先上传。</text>

        <view
          v-for="item in uploadedFiles"
          :key="`${item.file_id}-${getStatusClass(item)}`"
          class="library-card"
        >
          <text class="library-name">{{ item.filename }}</text>
          <text class="library-meta">{{ item.file_type }} · {{ item.uploaded_at || '刚刚上传' }}</text>
          <text v-if="item.message" class="library-message">{{ item.message }}</text>

          <view v-if="shouldShowProgress(item)" class="library-progress">
            <view class="progress-track">
              <view
                class="progress-fill"
                :class="getStatusClass(item)"
                :style="{ width: `${getFakeProgress(item)}%` }"
              ></view>
            </view>
            <text class="progress-text">{{ getFakeProgress(item) }}%</text>
          </view>

          <view class="library-actions">
            <view class="status-pill" :class="getStatusClass(item)">
              <text class="status-pill-text">{{ getStatusText(item) }}</text>
            </view>
            <view class="library-action-button" @tap="refreshStatus(item)">
              <text class="library-action-text">{{ item.refreshing ? '查询中' : '状态' }}</text>
            </view>
            <view class="library-action-button danger" @tap="removeFile(item)">
              <text class="library-action-text">{{ item.deleting ? '删除中' : '删除' }}</text>
            </view>
          </view>
        </view>
      </scroll-view>
    </view>

    <view class="page-body">
      <view class="upload-grid">
        <view class="panel-card panel-card-compact">
          <view class="panel-head panel-head-compact">
            <text class="panel-title">选择文件或文件夹</text>
            <view class="refresh-button" @tap="loadFiles">
              <text class="refresh-text">{{ loading ? '刷新中' : '刷新列表' }}</text>
            </view>
          </view>
          <text class="panel-description">支持 {{ supportedFormatText }}</text>
          <text v-if="notice" class="panel-notice">{{ notice }}</text>
          <view class="panel-actions">
            <view class="action-button primary" @tap="chooseFiles">
              <text class="action-text">选择文件</text>
            </view>
            <view class="action-button" @tap="chooseFolder">
              <text class="action-text">选择文件夹</text>
            </view>
          </view>
        </view>

        <view class="panel-card queue-panel">
          <view class="panel-head">
            <text class="panel-title">待上传队列</text>
            <view
              class="badge badge-action"
              :class="{ disabled: uploading || !supportedFilesCount }"
              @tap="uploadSelectedFiles"
            >
              <text class="badge-text">{{ uploading ? '上传中...' : `上传 ${supportedFilesCount} 个文件` }}</text>
            </view>
          </view>
          <scroll-view class="queue-box" scroll-y="true" enhanced="true" show-scrollbar="true">
            <text v-if="!uploadQueue.length" class="queue-placeholder">暂无待上传文件。</text>
            <view
              v-for="item in uploadQueue"
              :key="item.id"
              class="queue-item"
            >
              <text class="queue-name">{{ item.name }}</text>
              <text class="queue-meta">{{ item.meta }}</text>
              <view class="queue-foot">
                <text class="queue-message">{{ item.message }}</text>
                <view class="status-pill small" :class="item.status">
                  <text class="status-pill-text">{{ queueStatusText[item.status] || item.status }}</text>
                </view>
              </view>
            </view>
          </scroll-view>
        </view>
      </view>
    </view>
    <view class="page-switcher">
      <view class="page-tab" @tap="goPage('chat')">
        <text class="page-tab-text">流式对话</text>
      </view>
      <view class="page-tab active" @tap="goPage('upload')">
        <text class="page-tab-text">文档上传</text>
      </view>
      <view class="page-tab" @tap="goPage('settings')">
        <text class="page-tab-text">对话设置</text>
      </view>
    </view>
  </view>
</template>

<script>
import {
  cacheFiles,
  DEFAULT_USER_ID,
  SUPPORTED_EXTENSIONS,
  deleteFile,
  fetchFileStatus,
  fetchFiles,
  isSupportedFile,
  normalizeUploadError,
  readCachedFiles,
  uploadFile,
} from './backend'

const ACTIVE_STATUSES = ['pending', 'downloading', 'downloaded', 'preprocessing', 'indexing']
const PROGRESS_STATUSES = [...ACTIVE_STATUSES, 'done', 'failed']
const FILE_NAME_CACHE_KEY = 'miniapp_upload_file_name_map'

export default {
  data() {
    return {
      sidebarOpen: false,
      hasLoadedOnce: false,
      userId: DEFAULT_USER_ID,
      supportedFormatText: SUPPORTED_EXTENSIONS.join(' / '),
      loading: false,
      uploading: false,
      notice: '',
      uploadQueue: [],
      uploadedFiles: [],
      progressNow: Date.now(),
      pollingTimer: null,
      progressTimer: null,
      localFileNameMap: {},
      previousStatusMap: Object.create(null),
      progressStartMap: Object.create(null),
      queueStatusText: {
        ready: '待上传',
        uploading: '上传中',
        indexing: '处理中',
        success: '已完成',
        failed: '失败',
      },
      statusText: {
        pending: '等待处理',
        downloading: '正在下载',
        downloaded: '下载完成',
        preprocessing: '正在预处理',
        indexing: '正在索引',
        done: '可用于对话',
        failed: '处理失败',
      },
    }
  },
  computed: {
    supportedFilesCount() {
      return this.uploadQueue.filter((item) => item.supported).length
    },
  },
  onLoad() {
    this.hydrateLocalFileNames()
    this.hydrateCachedFiles()
  },
  onReady() {
    setTimeout(() => {
      this.loadFiles()
      this.hasLoadedOnce = true
    }, 80)
  },
  onShow() {
    if (this.hasLoadedOnce) {
      this.loadFiles()
    }
  },
  onUnload() {
    this.stopPolling()
    this.stopProgressTimer()
  },
  methods: {
    toggleSidebar() {
      this.sidebarOpen = !this.sidebarOpen
    },
    closeSidebar() {
      this.sidebarOpen = false
    },
    chooseFiles() {
      uni.chooseMessageFile({
        count: 20,
        type: 'file',
        extension: SUPPORTED_EXTENSIONS,
        success: ({ tempFiles = [] }) => {
          this.collectFiles(tempFiles)
        },
        fail: (error) => {
          if (error?.errMsg?.includes('cancel')) {
            return
          }
          this.notice = '文件选择失败'
        },
      })
    },
    chooseFolder() {
      this.notice = '微信小程序暂不支持直接选择文件夹，请改用批量选文件'
    },
    collectFiles(files) {
      const supportedItems = []
      const unsupportedNames = []

      files.forEach((file) => {
        if (!isSupportedFile(file)) {
          unsupportedNames.push(file.name)
          return
        }

        supportedItems.push({
          id: `${Date.now()}-${Math.random().toString(16).slice(2, 8)}`,
          name: file.name,
          meta: this.formatSize(file.size || 0),
          message: '待上传',
          status: 'ready',
          supported: true,
          path: file.path,
          size: file.size || 0,
        })
      })

      if (supportedItems.length) {
        this.uploadQueue = [...this.uploadQueue, ...supportedItems]
      }

      if (unsupportedNames.length) {
        const preview = unsupportedNames.slice(0, 3).join('、')
        this.notice = `已跳过 ${unsupportedNames.length} 个不支持的文件${preview ? `：${preview}` : ''}`
      }
    },
    hydrateLocalFileNames() {
      const cachedMap = uni.getStorageSync(FILE_NAME_CACHE_KEY)
      this.localFileNameMap = cachedMap && typeof cachedMap === 'object' && !Array.isArray(cachedMap) ? cachedMap : {}
    },
    rememberLocalFileName(fileId, filename) {
      if (!fileId || !filename || this.localFileNameMap[fileId] === filename) {
        return
      }
      this.localFileNameMap = { ...this.localFileNameMap, [fileId]: filename }
      uni.setStorageSync(FILE_NAME_CACHE_KEY, this.localFileNameMap)
    },
    removeLocalFileName(fileId) {
      if (!fileId || !this.localFileNameMap[fileId]) {
        return
      }
      const nextMap = { ...this.localFileNameMap }
      delete nextMap[fileId]
      this.localFileNameMap = nextMap
      uni.setStorageSync(FILE_NAME_CACHE_KEY, nextMap)
    },
    applyLocalFileName(file) {
      const filename = this.localFileNameMap[file?.file_id]
      return filename ? { ...file, filename } : file
    },
    getNormalizedStatus(status) {
      return typeof status === 'string' ? status.trim().toLowerCase() : ''
    },
    getStatusClass(file) {
      return this.getNormalizedStatus(file?.index_status)
    },
    getStatusText(file) {
      const status = this.getStatusClass(file)
      return this.statusText[status] || file?.index_status || ''
    },
    patchUploadedFile(fileId, patch) {
      this.uploadedFiles = this.uploadedFiles.map((item) => (
        item.file_id === fileId
          ? { ...item, ...patch, index_status: this.getNormalizedStatus(patch.index_status ?? item.index_status) }
          : item
      ))
    },
    hydrateCachedFiles() {
      const cachedFiles = readCachedFiles()
      if (!cachedFiles.length) {
        return
      }
      this.uploadedFiles = cachedFiles.map((file) => ({
        ...this.applyLocalFileName(file),
        refreshing: false,
        deleting: false,
      }))
      this.syncPollingState(this.uploadedFiles)
    },
    async loadFiles() {
      if (this.loading) {
        return
      }

      this.loading = true
      try {
        const files = await fetchFiles(this.userId)
        const displayFiles = files.map((file) => this.applyLocalFileName(file))
        cacheFiles(displayFiles)
        this.handleStatusTransitions(displayFiles)
        this.uploadedFiles = displayFiles.map((file) => ({
          ...file,
          refreshing: false,
          deleting: false,
        }))
        this.syncPollingState(this.uploadedFiles)
      } catch (error) {
        this.notice = error.message || '文件列表获取失败'
      } finally {
        this.loading = false
      }
    },
    handleStatusTransitions(files) {
      files.forEach((file) => {
        const previousStatus = this.getNormalizedStatus(this.previousStatusMap[file.file_id])
        const currentStatus = this.getNormalizedStatus(file.index_status)

        if (previousStatus !== currentStatus) {
          if (previousStatus !== 'downloaded' && currentStatus === 'downloaded') {
            this.notice = `${file.filename} 下载完成`
          }
          if (previousStatus !== 'done' && currentStatus === 'done') {
            this.notice = `${file.filename} 预处理完成`
          }
          if (previousStatus !== 'failed' && currentStatus === 'failed' && file.message) {
            this.notice = `${file.filename} 处理失败：${file.message}`
          }
        }

        this.previousStatusMap[file.file_id] = currentStatus
      })
    },
    shouldShowProgress(file) {
      return PROGRESS_STATUSES.includes(this.getStatusClass(file))
    },
    getFakeProgress(file) {
      const status = this.getStatusClass(file)
      if (status === 'done' || status === 'failed') {
        return 100
      }
      if (!ACTIVE_STATUSES.includes(status)) {
        return 0
      }

      const startedAt = this.progressStartMap[file.file_id] || this.progressNow
      const elapsedRatio = Math.min((this.progressNow - startedAt) / 20000, 1)
      const easedRatio = 1 - Math.pow(1 - elapsedRatio, 3)
      return Math.min(Math.round(8 + easedRatio * 91), 99)
    },
    hasActiveFiles(files) {
      return files.some((file) => ACTIVE_STATUSES.includes(this.getStatusClass(file)))
    },
    syncProgressTimer(files = this.uploadedFiles) {
      files.forEach((file) => {
        if (ACTIVE_STATUSES.includes(this.getStatusClass(file)) && !this.progressStartMap[file.file_id]) {
          this.progressStartMap[file.file_id] = Date.now()
        }
      })

      if (this.hasActiveFiles(files)) {
        if (!this.progressTimer) {
          this.progressTimer = setInterval(() => {
            this.progressNow = Date.now()
          }, 500)
        }
        return
      }

      this.stopProgressTimer()
    },
    syncPollingState(files = this.uploadedFiles) {
      this.syncProgressTimer(files)
      if (this.hasActiveFiles(files)) {
        this.schedulePolling()
        return
      }
      this.stopPolling()
    },
    schedulePolling() {
      this.stopPolling()
      this.pollingTimer = setTimeout(() => {
        this.loadFiles()
      }, 2000)
    },
    stopPolling() {
      if (!this.pollingTimer) {
        return
      }
      clearTimeout(this.pollingTimer)
      this.pollingTimer = null
    },
    stopProgressTimer() {
      if (!this.progressTimer) {
        return
      }
      clearInterval(this.progressTimer)
      this.progressTimer = null
    },
    async uploadSelectedFiles() {
      if (!this.supportedFilesCount || this.uploading) {
        return
      }

      const existingNames = new Set(this.uploadedFiles.map((file) => file.filename))
      const duplicatedFiles = this.uploadQueue.filter((item) => item.supported && existingNames.has(item.name))

      if (duplicatedFiles.length) {
        this.notice = `已移除 ${duplicatedFiles.length} 个同名文件`
        this.uploadQueue = this.uploadQueue.filter((item) => !duplicatedFiles.includes(item))
      }

      if (!this.supportedFilesCount) {
        return
      }

      this.uploading = true
      this.notice = ''

      try {
        while (this.uploadQueue.some((item) => item.supported)) {
          const item = this.uploadQueue.find((queuedItem) => queuedItem.supported)
          await this.processQueuedFile(item)
          this.uploadQueue = this.uploadQueue.filter((queuedItem) => queuedItem !== item)
        }
      } finally {
        this.uploading = false
        await this.loadFiles()
      }
    },
    async processQueuedFile(item) {
      item.status = 'uploading'
      item.message = '上传中...'

      try {
        const uploadResult = await uploadFile(item, this.userId)
        const fileId = uploadResult.file_id || item.name
        this.rememberLocalFileName(fileId, item.name)

        item.status = 'indexing'
        item.message = uploadResult.message || '上传成功，等待预处理'
        await this.loadFiles()

        const finalResult = await this.waitForFileCompletion(fileId)
        if (finalResult.index_status === 'done') {
          item.status = 'success'
          item.message = finalResult.message || '预处理完成'
        } else {
          item.status = 'failed'
          item.message = finalResult.message || '处理失败'
        }

        await this.loadFiles()
      } catch (error) {
        const normalized = normalizeUploadError(error)
        item.status = 'failed'
        item.message = normalized.message
      }
    },
    async waitForFileCompletion(fileId) {
      while (true) {
        const result = await fetchFileStatus(fileId)
        if (result.index_status === 'done' || result.index_status === 'failed') {
          return result
        }
        await this.sleep(2000)
      }
    },
    sleep(ms) {
      return new Promise((resolve) => {
        setTimeout(resolve, ms)
      })
    },
    async refreshStatus(file) {
      if (file.refreshing) {
        return
      }

      this.patchUploadedFile(file.file_id, { refreshing: true })
      try {
        const result = await fetchFileStatus(file.file_id)
        this.patchUploadedFile(file.file_id, {
          index_status: result.index_status,
          message: result.message,
          refreshing: false,
        })
        this.syncPollingState(this.uploadedFiles)
      } catch (error) {
        this.patchUploadedFile(file.file_id, {
          message: error.message || '状态刷新失败',
          refreshing: false,
        })
      }
    },
    async removeFile(file) {
      if (file.deleting) {
        return
      }

      const confirmed = await new Promise((resolve) => {
        uni.showModal({
          title: '确认删除',
          content: `确认删除 ${file.filename}？`,
          success: ({ confirm }) => resolve(confirm),
          fail: () => resolve(false),
        })
      })

      if (!confirmed) {
        return
      }

      file.deleting = true
      try {
        const result = await deleteFile(file.file_id)
        this.removeLocalFileName(file.file_id)
        this.notice = result?.message || '删除成功'
        await this.loadFiles()
      } catch (error) {
        this.notice = error?.message || '删除失败'
      } finally {
        file.deleting = false
      }
    },
    formatSize(size) {
      if (!size) {
        return '0 B'
      }
      const units = ['B', 'KB', 'MB', 'GB']
      let value = size
      let unitIndex = 0
      while (value >= 1024 && unitIndex < units.length - 1) {
        value /= 1024
        unitIndex += 1
      }
      return `${value >= 10 || unitIndex === 0 ? Math.round(value) : value.toFixed(1)} ${units[unitIndex]}`
    },
    goPage(page) {
      const pageMap = {
        chat: '/pages/chat/index',
        upload: '/pages/upload/index',
        settings: '/pages/settings/index',
      }
      const url = pageMap[page]
      if (!url || url === '/pages/upload/index') {
        return
      }
      this.closeSidebar()
      uni.switchTab({ url })
    },
  },
}
</script>

<style>
.page-shell {
  position: relative;
  min-height: 100vh;
  min-height: -webkit-fill-available;
  height: 100vh;
  display: flex;
  flex-direction: column;
  padding: 88rpx 32rpx 28rpx;
  padding-top: calc(88rpx + constant(safe-area-inset-top));
  padding-top: calc(88rpx + env(safe-area-inset-top));
  padding-bottom: calc(128rpx + constant(safe-area-inset-bottom));
  padding-bottom: calc(128rpx + env(safe-area-inset-bottom));
  box-sizing: border-box;
  overflow: hidden;
  background:
    radial-gradient(circle at top left, rgba(56, 106, 255, 0.18), transparent 34%),
    radial-gradient(circle at top right, rgba(17, 83, 214, 0.16), transparent 26%),
    linear-gradient(180deg, #050b16 0%, #071225 46%, #040914 100%);
}


.ambient {
  position: absolute;
  border-radius: 50%;
  filter: blur(42rpx);
  opacity: 0.46;
  pointer-events: none;
}

.ambient-left {
  top: 140rpx;
  left: -80rpx;
  width: 280rpx;
  height: 280rpx;
  background: rgba(71, 118, 255, 0.22);
}

.ambient-right {
  right: -120rpx;
  bottom: 240rpx;
  width: 360rpx;
  height: 360rpx;
  background: rgba(23, 95, 255, 0.14);
}

.top-bar {
  position: relative;
  z-index: 5;
  display: flex;
  align-items: center;
  gap: 18rpx;
}

.menu-button {
  width: 72rpx;
  height: 72rpx;
  padding: 18rpx 16rpx;
  border: 1rpx solid rgba(90, 129, 255, 0.28);
  border-radius: 24rpx;
  box-sizing: border-box;
  background: rgba(10, 20, 39, 0.9);
  box-shadow: 0 12rpx 30rpx rgba(0, 0, 0, 0.22);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  flex-shrink: 0;
}

.menu-line {
  width: 100%;
  height: 4rpx;
  border-radius: 999rpx;
  background: #d7e3ff;
}

.menu-line.short {
  width: 60%;
}

.page-title-wrap {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8rpx;
}

.page-caption {
  font-size: 18rpx;
  letter-spacing: 6rpx;
  color: rgba(122, 154, 255, 0.84);
}

.page-title {
  font-size: 46rpx;
  font-weight: 600;
  color: #f4f7ff;
}

.refresh-button {
  height: 58rpx;
  padding: 0 22rpx;
  border-radius: 999rpx;
  border: 1rpx solid rgba(130, 157, 239, 0.28);
  background: rgba(12, 21, 39, 0.88);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.refresh-text {
  font-size: 22rpx;
  color: rgba(231, 238, 255, 0.9);
}

.sidebar-mask {
  position: fixed;
  inset: 0;
  z-index: 9;
  background: rgba(2, 5, 12, 0.52);
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.28s ease;
}

.sidebar-mask.show {
  opacity: 1;
  pointer-events: auto;
}

.sidebar {
  position: fixed;
  top: 0;
  left: 0;
  z-index: 10;
  width: 520rpx;
  height: 100vh;
  padding: 124rpx 24rpx 32rpx;
  box-sizing: border-box;
  background: linear-gradient(180deg, rgba(6, 14, 29, 0.98), rgba(4, 9, 20, 0.98));
  border-right: 1rpx solid rgba(87, 129, 255, 0.2);
  box-shadow: 24rpx 0 60rpx rgba(0, 0, 0, 0.3);
  transform: translateX(-100%);
  transition: transform 0.28s ease;
  display: flex;
  flex-direction: column;
}

.sidebar.open {
  transform: translateX(0);
}

.sidebar-header {
  margin-bottom: 28rpx;
}

.sidebar-title {
  display: block;
  font-size: 36rpx;
  font-weight: 600;
  color: #f4f7ff;
}

.sidebar-subtitle {
  display: block;
  margin-top: 10rpx;
  font-size: 22rpx;
  color: rgba(188, 204, 241, 0.68);
}

.sidebar-scroll {
  flex: 1;
  min-height: 0;
}

.library-card {
  margin-bottom: 18rpx;
  padding: 24rpx;
  border: 1rpx solid rgba(82, 120, 255, 0.16);
  border-radius: 24rpx;
  background: rgba(15, 25, 46, 0.72);
}

.library-name {
  display: block;
  font-size: 28rpx;
  color: #eef3ff;
}

.library-meta {
  display: block;
  margin-top: 10rpx;
  font-size: 22rpx;
  color: rgba(165, 182, 224, 0.66);
}

.library-message {
  display: block;
  margin-top: 12rpx;
  font-size: 20rpx;
  line-height: 1.6;
  color: rgba(222, 232, 255, 0.82);
}

.library-progress {
  margin-top: 16rpx;
  display: flex;
  align-items: center;
  gap: 14rpx;
}

.progress-track {
  flex: 1;
  height: 12rpx;
  border-radius: 999rpx;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.08);
}

.progress-fill {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #6890ff 0%, #4f78ff 100%);
}

.progress-fill.done {
  background: linear-gradient(90deg, #5fd4b0 0%, #3db78f 100%);
}

.progress-fill.failed {
  background: linear-gradient(90deg, #ff7b90 0%, #ff5b73 100%);
}

.progress-text {
  font-size: 20rpx;
  color: rgba(219, 229, 255, 0.88);
}

.library-actions {
  margin-top: 18rpx;
  display: flex;
  align-items: center;
  gap: 12rpx;
  flex-wrap: wrap;
}

.library-action-button {
  min-width: 94rpx;
  height: 48rpx;
  padding: 0 18rpx;
  border-radius: 999rpx;
  border: 1rpx solid rgba(122, 151, 223, 0.2);
  background: rgba(14, 24, 45, 0.84);
  display: flex;
  align-items: center;
  justify-content: center;
}

.library-action-button.danger {
  border-color: rgba(255, 116, 132, 0.3);
  background: rgba(68, 18, 29, 0.7);
}

.library-action-text {
  font-size: 20rpx;
  color: #eef4ff;
}

.sidebar-empty {
  display: block;
  font-size: 24rpx;
  color: rgba(180, 198, 236, 0.68);
}

.page-body {
  position: relative;
  z-index: 1;
  flex: 1;
  min-height: 0;
  padding-top: 22rpx;
  display: flex;
  flex-direction: column;
}

.upload-grid {
  display: flex;
  flex-direction: column;
  gap: 20rpx;
  flex: 1;
  min-height: 0;
}

.panel-card {
  min-height: 220rpx;
  padding: 28rpx;
  border: 1rpx solid rgba(87, 125, 255, 0.2);
  border-radius: 32rpx;
  background:
    linear-gradient(180deg, rgba(9, 19, 37, 0.92), rgba(7, 14, 28, 0.9));
  box-shadow:
    0 18rpx 44rpx rgba(0, 0, 0, 0.18),
    inset 0 1rpx 0 rgba(255, 255, 255, 0.03);
  box-sizing: border-box;
}

.panel-card-compact {
  min-height: 194rpx;
}

.queue-panel {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.panel-title {
  display: block;
  font-size: 36rpx;
  font-weight: 600;
  color: #f3f7ff;
}

.panel-description {
  display: block;
  margin-top: 12rpx;
  font-size: 24rpx;
  color: rgba(184, 201, 238, 0.72);
}

.panel-notice {
  display: block;
  margin-top: 10rpx;
  font-size: 22rpx;
  line-height: 1.6;
  color: rgba(138, 178, 255, 0.92);
}

.panel-actions {
  margin-top: 28rpx;
  display: flex;
  align-items: center;
  gap: 16rpx;
  flex-wrap: wrap;
}

.action-button {
  min-width: 162rpx;
  height: 58rpx;
  padding: 0 24rpx;
  border: 1rpx solid rgba(122, 151, 223, 0.2);
  border-radius: 999rpx;
  background: rgba(14, 24, 45, 0.84);
  display: flex;
  align-items: center;
  justify-content: center;
}

.action-button.primary {
  background: linear-gradient(180deg, #6389ff 0%, #4c72ff 100%);
  box-shadow: 0 12rpx 26rpx rgba(72, 105, 255, 0.26);
}

.action-text {
  font-size: 22rpx;
  font-weight: 600;
  color: #eef4ff;
}

.panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16rpx;
}

.panel-head-compact {
  align-items: center;
}

.badge {
  height: 56rpx;
  padding: 0 22rpx;
  border-radius: 999rpx;
  background: rgba(87, 125, 255, 0.24);
  display: flex;
  align-items: center;
  justify-content: center;
}

.badge-action.disabled {
  opacity: 0.46;
}

.badge-text {
  font-size: 22rpx;
  color: rgba(225, 234, 255, 0.9);
}

.queue-box {
  margin-top: 20rpx;
  flex: 1;
  min-height: 0;
  padding: 24rpx;
  border-radius: 24rpx;
  background: rgba(255, 255, 255, 0.04);
  box-sizing: border-box;
}

.queue-item + .queue-item {
  margin-top: 16rpx;
}

.queue-item {
  padding: 22rpx 20rpx;
  border-radius: 20rpx;
  background: rgba(17, 26, 46, 0.86);
  border: 1rpx solid rgba(94, 121, 191, 0.14);
}

.queue-foot {
  margin-top: 14rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12rpx;
}

.queue-name {
  display: block;
  font-size: 24rpx;
  color: #eef4ff;
}

.queue-meta {
  display: block;
  margin-top: 10rpx;
  font-size: 20rpx;
  color: rgba(180, 198, 236, 0.64);
}

.queue-message {
  flex: 1;
  min-width: 0;
  font-size: 20rpx;
  color: rgba(222, 232, 255, 0.78);
}

.queue-placeholder {
  display: block;
  font-size: 26rpx;
  color: rgba(180, 198, 236, 0.68);
}

.status-pill {
  height: 44rpx;
  padding: 0 18rpx;
  border-radius: 999rpx;
  background: rgba(87, 125, 255, 0.18);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.status-pill.small {
  height: 40rpx;
  padding: 0 14rpx;
}

.status-pill.ready,
.status-pill.pending,
.status-pill.downloaded {
  background: rgba(87, 125, 255, 0.18);
}

.status-pill.uploading,
.status-pill.preprocessing,
.status-pill.indexing,
.status-pill.downloading {
  background: rgba(98, 140, 255, 0.24);
}

.status-pill.success,
.status-pill.done {
  background: rgba(73, 184, 143, 0.2);
}

.status-pill.failed {
  background: rgba(255, 96, 118, 0.18);
}

.status-pill-text {
  font-size: 20rpx;
  color: rgba(236, 241, 255, 0.92);
}

.page-switcher {
  position: fixed;
  left: 24rpx;
  right: 24rpx;
  bottom: calc(24rpx + constant(safe-area-inset-bottom));
  bottom: calc(24rpx + env(safe-area-inset-bottom));
  z-index: 30;
  padding: 12rpx;
  border: 1rpx solid rgba(87, 125, 255, 0.16);
  border-radius: 999rpx;
  background: rgba(7, 15, 30, 0.86);
  box-shadow: 0 18rpx 40rpx rgba(0, 0, 0, 0.24);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12rpx;
}

.page-tab {
  min-width: 156rpx;
  height: 56rpx;
  padding: 0 22rpx;
  border-radius: 999rpx;
  background: rgba(255, 255, 255, 0.04);
  display: flex;
  align-items: center;
  justify-content: center;
}

.page-tab.active {
  background: linear-gradient(180deg, rgba(84, 122, 255, 0.24), rgba(64, 96, 204, 0.16));
  box-shadow: inset 0 0 0 1rpx rgba(106, 149, 255, 0.18);
}

.page-tab-text {
  font-size: 22rpx;
  color: rgba(219, 230, 255, 0.9);
}
</style>

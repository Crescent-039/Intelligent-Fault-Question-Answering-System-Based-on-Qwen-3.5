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
        <text class="sidebar-subtitle">仅做展示，暂未接入真实数据</text>
      </view>

      <view
        v-for="item in libraryList"
        :key="item.id"
        class="library-card"
      >
        <text class="library-name">{{ item.name }}</text>
        <text class="library-meta">{{ item.meta }}</text>
      </view>
    </view>

    <view class="page-body">
      <view class="upload-grid">
        <view class="panel-card panel-card-compact">
          <view class="panel-head panel-head-compact">
            <text class="panel-title">选择文件或文件夹</text>
            <view class="refresh-button">
              <text class="refresh-text">刷新列表</text>
            </view>
          </view>
          <text class="panel-description">支持 pdf / png / jpg / jpeg</text>
          <view class="panel-actions">
            <view class="action-button primary">
              <text class="action-text">选择文件</text>
            </view>
            <view class="action-button">
              <text class="action-text">选择文件夹</text>
            </view>
          </view>
        </view>

        <view class="panel-card queue-panel">
          <view class="panel-head">
            <text class="panel-title">待上传队列</text>
            <view class="badge">
              <text class="badge-text">上传 {{ uploadQueue.length }} 个文件</text>
            </view>
          </view>
          <scroll-view class="queue-box" scroll-y="true" enhanced="true" show-scrollbar="true">
            <view
              v-for="item in uploadQueue"
              :key="item.id"
              class="queue-item"
            >
              <text class="queue-name">{{ item.name }}</text>
              <text class="queue-meta">{{ item.meta }}</text>
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
export default {
  data() {
    return {
      sidebarOpen: false,
      uploadQueue: [
        { id: 1, name: '巡检记录-01.pdf', meta: '12.5 MB' },
        { id: 2, name: '设备照片-A.png', meta: '3.2 MB' },
        { id: 3, name: '维护手册-v2.docx', meta: '1.8 MB' },
        { id: 4, name: '报警日志-周报.txt', meta: '860 KB' },
        { id: 5, name: '知识库补充说明.md', meta: '120 KB' },
        { id: 6, name: '故障截图-03.jpg', meta: '4.1 MB' },
      ],
      libraryList: [
        { id: 1, name: '设备检修手册.pdf', meta: '最近更新：刚刚' },
        { id: 2, name: '故障案例集.docx', meta: '最近更新：昨天' },
        { id: 3, name: '产品参数说明.md', meta: '最近更新：2 天前' },
      ],
    }
  },
  methods: {
    toggleSidebar() {
      this.sidebarOpen = !this.sidebarOpen
    },
    closeSidebar() {
      this.sidebarOpen = false
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
      uni.redirectTo({ url })
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
  padding-bottom: calc(28rpx + constant(safe-area-inset-bottom));
  padding-bottom: calc(28rpx + env(safe-area-inset-bottom));
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
  filter: blur(60rpx);
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

.queue-placeholder {
  font-size: 26rpx;
  color: rgba(180, 198, 236, 0.68);
}

.page-switcher {
  position: relative;
  z-index: 2;
  margin-top: 20rpx;
  padding: 12rpx;
  border: 1rpx solid rgba(87, 125, 255, 0.16);
  border-radius: 999rpx;
  background: rgba(7, 15, 30, 0.86);
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

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
    </view>

    <view class="sidebar-mask" :class="{ show: sidebarOpen }" @tap="closeSidebar"></view>
    <view class="sidebar" :class="{ open: sidebarOpen }">
      <view class="sidebar-header">
        <text class="sidebar-title">历史对话</text>
        <text class="sidebar-subtitle">仅做展示，暂未接入数据</text>
      </view>

      <view
        v-for="item in historyList"
        :key="item.id"
        class="history-card"
      >
        <text class="history-title">{{ item.title }}</text>
        <text class="history-time">{{ item.time }}</text>
      </view>
    </view>

    <view class="hero-section">
      <view class="hero-logo">
        <text class="hero-logo-text">R</text>
      </view>
      <text class="hero-caption">QWEN RAG CONSOLE</text>
      <text class="hero-title">文档问答系统</text>
      <text class="hero-description">
        极简暗色风格的微信小程序首页空壳，用于承接后续对话、RAG 与思考模式能力。
      </text>
    </view>

    <view class="bottom-dock">
      <view class="composer-panel">
        <view class="composer-field">
          <textarea
            v-model="message"
            class="composer-input"
            maxlength="-1"
            auto-height
            cursor-spacing="24"
            placeholder="输入你的问题，开始新的对话..."
            placeholder-class="composer-placeholder"
          ></textarea>
          <view class="composer-actions">
            <view class="mode-group">
              <view class="ios-switch" :class="{ on: ragEnabled }" @tap="toggleRagMode">
                <text class="switch-text switch-text-left">通用</text>
                <text class="switch-text switch-text-right">RAG</text>
                <view class="ios-switch-knob"></view>
              </view>
              <view class="ios-switch" :class="{ on: thinkingEnabled }" @tap="toggleThinkingMode">
                <text class="switch-text switch-text-left">快速</text>
                <text class="switch-text switch-text-right">思考</text>
                <view class="ios-switch-knob"></view>
              </view>
            </view>
            <view class="send-button" @tap="noopSend">
              <text class="send-label">发送</text>
            </view>
          </view>
        </view>
      </view>
      <view class="page-switcher">
        <view class="page-tab active" @tap="goPage('chat')">
          <text class="page-tab-text">流式对话</text>
        </view>
        <view class="page-tab" @tap="goPage('upload')">
          <text class="page-tab-text">文档上传</text>
        </view>
        <view class="page-tab" @tap="goPage('settings')">
          <text class="page-tab-text">对话设置</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
export default {
  data() {
    return {
      sidebarOpen: false,
      message: '',
      ragEnabled: true,
      thinkingEnabled: true,
      historyList: [
        { id: 1, title: '新建对话', time: '刚刚' },
        { id: 2, title: '文档上传预览', time: '昨天' },
        { id: 3, title: '故障定位分析', time: '2 天前' },
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
    toggleRagMode() {
      this.ragEnabled = !this.ragEnabled
    },
    toggleThinkingMode() {
      this.thinkingEnabled = !this.thinkingEnabled
    },
    goPage(page) {
      const pageMap = {
        chat: '/pages/index/index',
        upload: '/pages/upload/index',
        settings: '/pages/settings/index',
      }
      const url = pageMap[page]
      if (!url || url === '/pages/index/index') {
        return
      }
      uni.redirectTo({ url })
    },
    noopSend() {},
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
  opacity: 0.5;
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
  justify-content: space-between;
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

.top-status {
  transform: translateY(70rpx);
  margin-right: -20rpx;
  padding: 18rpx 24rpx;
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

.history-card {
  margin-bottom: 18rpx;
  padding: 24rpx;
  border: 1rpx solid rgba(82, 120, 255, 0.16);
  border-radius: 24rpx;
  background: rgba(15, 25, 46, 0.72);
}

.history-title {
  display: block;
  font-size: 28rpx;
  color: #eef3ff;
}

.history-time {
  display: block;
  margin-top: 10rpx;
  font-size: 22rpx;
  color: rgba(165, 182, 224, 0.66);
}

.hero-section {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  min-height: 0;
  padding: 48rpx 20rpx 32rpx;
  text-align: center;
}

.hero-logo {
  width: 132rpx;
  height: 132rpx;
  border-radius: 36rpx;
  background: linear-gradient(135deg, #7ca8ff 0%, #5a86ff 48%, #4d6fff 100%);
  box-shadow:
    0 16rpx 50rpx rgba(46, 88, 255, 0.34),
    inset 0 1rpx 0 rgba(255, 255, 255, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
}

.hero-logo-text {
  font-size: 68rpx;
  font-weight: 700;
  color: #ffffff;
}

.hero-caption {
  margin-top: 28rpx;
  font-size: 18rpx;
  letter-spacing: 6rpx;
  color: rgba(120, 151, 255, 0.82);
}

.hero-title {
  margin-top: 12rpx;
  font-size: 50rpx;
  font-weight: 600;
  color: #f4f7ff;
}

.hero-description {
  width: 100%;
  max-width: 560rpx;
  margin-top: 20rpx;
  font-size: 26rpx;
  line-height: 1.7;
  color: rgba(188, 204, 241, 0.78);
}

.bottom-dock {
  position: relative;
  z-index: 2;
  margin-top: auto;
}

.composer-panel {
  padding: 0;
}

.composer-field {
  min-height: 228rpx;
  padding: 24rpx;
  border-radius: 28rpx;
  background:
    linear-gradient(180deg, rgba(14, 25, 47, 0.96), rgba(10, 18, 36, 0.94));
  border: 1rpx solid rgba(93, 127, 255, 0.2);
  box-sizing: border-box;
  box-shadow:
    0 16rpx 40rpx rgba(0, 0, 0, 0.2),
    inset 0 1rpx 0 rgba(255, 255, 255, 0.03);
  display: flex;
  flex-direction: column;
}

.composer-input {
  width: 100%;
  min-height: 128rpx;
  max-height: 260rpx;
  font-size: 30rpx;
  line-height: 1.6;
  color: #eef4ff;
  flex: 1;
}

.composer-placeholder {
  color: rgba(183, 197, 232, 0.56);
}

.composer-actions {
  margin-top: 24rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16rpx;
  padding-top: 20rpx;
  border-top: 1rpx solid rgba(102, 134, 212, 0.14);
}

.mode-group {
  display: flex;
  align-items: center;
  flex: 1;
  gap: 14rpx;
  justify-content: flex-start;
}

.ios-switch {
  position: relative;
  width: 154rpx;
  height: 54rpx;
  padding: 0;
  border-radius: 999rpx;
  box-sizing: border-box;
  background: rgba(255, 255, 255, 0.14);
  display: flex;
  align-items: center;
  justify-content: space-between;
  transition: background 0.2s ease;
  overflow: hidden;
}

.ios-switch.on {
  background: linear-gradient(90deg, #376dff 0%, #5d85ff 100%);
}

.switch-text {
  position: relative;
  z-index: 1;
  width: 64rpx;
  font-size: 21rpx;
  font-weight: 600;
  text-align: center;
  color: rgba(255, 255, 255, 0.72);
}

.switch-text-left {
  margin-left: 6rpx;
}

.switch-text-right {
  margin-right: 6rpx;
}

.ios-switch-knob {
  position: absolute;
  top: 5rpx;
  left: 5rpx;
  width: 70rpx;
  height: 46rpx;
  background: #ffffff;
  box-shadow: 0 6rpx 18rpx rgba(0, 0, 0, 0.2);
  transition: transform 0.2s ease;
  border-radius: 999rpx;
}

.ios-switch.on .ios-switch-knob {
  transform: translateX(74rpx);
}

.send-button {
  min-width: 96rpx;
  height: 64rpx;
  padding: 0 24rpx;
  border-radius: 999rpx;
  background: linear-gradient(180deg, #5f84ff 0%, #4c72ff 100%);
  box-shadow: 0 16rpx 30rpx rgba(64, 101, 255, 0.36);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border: 1rpx solid rgba(145, 173, 255, 0.2);
}

.send-label {
  font-size: 24rpx;
  font-weight: 600;
  line-height: 1;
  color: rgba(255, 255, 255, 0.96);
}

.page-switcher {
  margin-top: 16rpx;
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

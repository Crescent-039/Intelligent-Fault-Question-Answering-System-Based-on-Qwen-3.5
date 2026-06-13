<template>
  <view class="tabbar-shell">
    <view class="tabbar-panel">
      <view
        v-for="item in tabs"
        :key="item.pagePath"
        class="tab-item"
        :class="{ active: currentPath === item.pagePath }"
        @tap="switchTab(item.pagePath)"
      >
        <text class="tab-text">{{ item.text }}</text>
      </view>
    </view>
  </view>
</template>

<script>
export default {
  data() {
    return {
      currentPath: '/pages/chat/index',
      tabs: [
        { pagePath: '/pages/chat/index', text: '流式对话' },
        { pagePath: '/pages/upload/index', text: '文档上传' },
        { pagePath: '/pages/settings/index', text: '对话设置' },
      ],
    }
  },
  mounted() {
    this.syncCurrentPath()
  },
  updated() {
    this.syncCurrentPath()
  },
  methods: {
    syncCurrentPath() {
      const pages = getCurrentPages()
      const currentRoute = pages[pages.length - 1]?.route
      if (!currentRoute) return
      const currentPath = `/${currentRoute}`
      if (currentPath !== this.currentPath) {
        this.currentPath = currentPath
      }
    },
    switchTab(url) {
      if (url === this.currentPath) {
        return
      }
      this.currentPath = url
      uni.switchTab({ url })
    },
  },
}
</script>

<style>
.tabbar-shell {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 999;
  padding: 0 24rpx calc(18rpx + env(safe-area-inset-bottom));
  padding: 0 24rpx calc(18rpx + constant(safe-area-inset-bottom));
  box-sizing: border-box;
  pointer-events: none;
}

.tabbar-panel {
  padding: 12rpx;
  border: 1rpx solid rgba(87, 125, 255, 0.16);
  border-radius: 999rpx;
  background: rgba(7, 15, 30, 0.9);
  box-shadow:
    0 18rpx 40rpx rgba(0, 0, 0, 0.24),
    inset 0 1rpx 0 rgba(255, 255, 255, 0.04);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12rpx;
  pointer-events: auto;
}

.tab-item {
  min-width: 156rpx;
  height: 56rpx;
  padding: 0 22rpx;
  border-radius: 999rpx;
  background: rgba(255, 255, 255, 0.04);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.18s ease, box-shadow 0.18s ease, transform 0.18s ease;
}

.tab-item.active {
  background: linear-gradient(180deg, rgba(84, 122, 255, 0.24), rgba(64, 96, 204, 0.16));
  box-shadow: inset 0 0 0 1rpx rgba(106, 149, 255, 0.18);
  transform: translateY(-2rpx);
}

.tab-text {
  font-size: 22rpx;
  color: rgba(219, 230, 255, 0.9);
}
</style>

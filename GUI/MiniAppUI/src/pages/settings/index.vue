<template>
  <view class="page-shell">
    <view class="ambient ambient-left"></view>
    <view class="ambient ambient-right"></view>

    <view class="top-bar">
      <view class="title-wrap">
        <text class="page-caption">MODEL SETTINGS</text>
        <text class="page-title">对话参数设置</text>
      </view>
    </view>

    <view class="page-body">
      <view class="settings-card settings-card-wide">
        <text class="card-label">System Prompt</text>
        <textarea
          v-model="systemPrompt"
          class="setting-textarea"
          maxlength="-1"
          auto-height
          placeholder="请输入系统提示词"
          placeholder-class="input-placeholder"
        ></textarea>
      </view>

      <view class="settings-grid">
        <view class="settings-card">
          <text class="card-label">temperature</text>
          <input
            v-model="temperature"
            class="setting-input"
            type="digit"
            placeholder="0.7"
            placeholder-class="input-placeholder"
          />
        </view>

        <view class="settings-card">
          <text class="card-label">max_tokens</text>
          <input
            v-model="maxTokens"
            class="setting-input"
            type="number"
            placeholder="2048"
            placeholder-class="input-placeholder"
          />
        </view>

        <view class="settings-card settings-card-wide-mobile">
          <text class="card-label">top_k</text>
          <input
            v-model="topK"
            class="setting-input"
            type="number"
            placeholder="5"
            placeholder-class="input-placeholder"
          />
        </view>
      </view>
    </view>
    <view class="page-switcher">
      <view class="page-tab" @tap="goPage('chat')">
        <text class="page-tab-text">流式对话</text>
      </view>
      <view class="page-tab" @tap="goPage('upload')">
        <text class="page-tab-text">文档上传</text>
      </view>
      <view class="page-tab active" @tap="goPage('settings')">
        <text class="page-tab-text">对话设置</text>
      </view>
    </view>
  </view>
</template>

<script>
const SETTINGS_STORAGE_KEY = 'miniapp_chat_settings'

export default {
  data() {
    return {
      systemPrompt: '你是一个文档分析助手',
      temperature: '0.7',
      maxTokens: '2048',
      topK: '5',
      hasHydrated: false,
    }
  },
  onLoad() {
    this.loadSettings()
  },
  watch: {
    systemPrompt() {
      this.saveSettings()
    },
    temperature() {
      this.saveSettings()
    },
    maxTokens() {
      this.saveSettings()
    },
    topK() {
      this.saveSettings()
    },
  },
  methods: {
    loadSettings() {
      const saved = uni.getStorageSync(SETTINGS_STORAGE_KEY)
      if (saved && typeof saved === 'object') {
        this.systemPrompt = saved.systemPrompt || this.systemPrompt
        this.temperature = saved.temperature || this.temperature
        this.maxTokens = saved.maxTokens || this.maxTokens
        this.topK = saved.topK || this.topK
      }
      this.hasHydrated = true
    },
    saveSettings() {
      if (!this.hasHydrated) {
        return
      }
      uni.setStorageSync(SETTINGS_STORAGE_KEY, {
        systemPrompt: this.systemPrompt,
        temperature: this.temperature,
        maxTokens: this.maxTokens,
        topK: this.topK,
      })
    },
    goPage(page) {
      const pageMap = {
        chat: '/pages/chat/index',
        upload: '/pages/upload/index',
        settings: '/pages/settings/index',
      }
      const url = pageMap[page]
      if (!url || url === '/pages/settings/index') {
        return
      }
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
  z-index: 2;
}

.title-wrap {
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
  font-size: 50rpx;
  font-weight: 600;
  color: #f4f7ff;
}

.page-body {
  position: relative;
  z-index: 1;
  flex: 1;
  min-height: 0;
  padding-top: 30rpx;
  display: flex;
  flex-direction: column;
  gap: 24rpx;
}

.settings-card {
  padding: 28rpx;
  border: 1rpx solid rgba(87, 125, 255, 0.2);
  border-radius: 30rpx;
  background:
    linear-gradient(180deg, rgba(9, 19, 37, 0.92), rgba(7, 14, 28, 0.9));
  box-shadow:
    0 18rpx 44rpx rgba(0, 0, 0, 0.18),
    inset 0 1rpx 0 rgba(255, 255, 255, 0.03);
  box-sizing: border-box;
}

.settings-card-wide {
  width: 100%;
}

.card-label {
  display: block;
  margin-bottom: 18rpx;
  font-size: 30rpx;
  font-weight: 600;
  color: #eef4ff;
}

.setting-textarea {
  width: 100%;
  min-height: 132rpx;
  padding: 22rpx 24rpx;
  border-radius: 22rpx;
  box-sizing: border-box;
  background: rgba(255, 255, 255, 0.06);
  border: 1rpx solid rgba(106, 139, 222, 0.22);
  color: #eef4ff;
  font-size: 26rpx;
  line-height: 1.7;
}

.settings-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24rpx;
}

.settings-card-wide-mobile {
  grid-column: 1 / -1;
}

.setting-input {
  width: 100%;
  height: 74rpx;
  padding: 0 22rpx;
  border-radius: 20rpx;
  box-sizing: border-box;
  background: rgba(255, 255, 255, 0.06);
  border: 1rpx solid rgba(106, 139, 222, 0.22);
  color: #eef4ff;
  font-size: 28rpx;
}

.input-placeholder {
  color: rgba(187, 200, 232, 0.52);
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

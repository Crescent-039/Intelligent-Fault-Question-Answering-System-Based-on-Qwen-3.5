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
        <text class="sidebar-subtitle">本地会话列表，后续再接入真实消息</text>
      </view>

      <view class="new-chat-button" @tap="startNewChat">
        <text class="new-chat-button-text">+ 新建对话</text>
      </view>

      <scroll-view class="history-list" scroll-y="true" enhanced="true" show-scrollbar="false">
        <view
          v-for="item in historyList"
          :key="item.id"
          class="history-card"
          :class="{ active: activeHistoryId === item.id }"
          @tap="selectSession(item.id)"
        >
          <view class="history-main">
            <text class="history-title">{{ item.title }}</text>
            <text class="history-time">{{ formatTime(item.updatedAt) }}</text>
          </view>
          <view class="history-delete" @tap.stop="confirmDeleteSession(item.id)">
            <text class="history-delete-text">删除</text>
          </view>
        </view>
      </scroll-view>
    </view>

    <view class="chat-section">
      <view class="hero-section" :class="{ faded: hasConversationStarted }">
        <view class="hero-logo">
          <text class="hero-logo-text">R</text>
        </view>
        <text class="hero-caption">QWEN RAG CONSOLE</text>
        <text class="hero-title">文档问答系统</text>
        <text class="hero-description">
          极简暗色风格的微信小程序首页空壳，用于承接后续对话、RAG 与思考模式能力。
        </text>
      </view>

      <scroll-view
        class="message-list"
        :class="{ active: hasConversationStarted }"
        scroll-y="true"
        enhanced="true"
        :scroll-into-view="scrollIntoView"
      >
        <view
          v-for="(item, index) in visibleMessages"
          :key="item.id || index"
          class="message-row"
          :class="item.role"
        >
          <view class="message-role">{{ item.role === 'user' ? '你' : '助手' }}</view>
          <view class="message-bubble" :class="item.role">
            <view v-if="item.role === 'assistant'" class="message-content-stack">
              <view v-if="item.parsed.thinkingContent" class="thinking-block">
                <view class="thinking-header" @tap="toggleThinkingBlock(item)">
                  <view>
                    <text class="thinking-title">思考过程</text>
                    <text class="thinking-hint">{{ item.thinkingCollapsed ? '点击展开' : '点击收起' }}</text>
                  </view>
                  <text class="thinking-arrow" :class="{ collapsed: item.thinkingCollapsed }">⌃</text>
                </view>
                <view v-if="!item.thinkingCollapsed" class="thinking-body">
                  <text class="thinking-text">{{ item.parsed.thinkingContent }}</text>
                  <text v-if="item.streaming && !item.parsed.answerContent" class="message-cursor">|</text>
                </view>
              </view>
              <view v-if="item.parsed.answerContent" class="message-rich-text">
                <template v-for="(segment, segmentIndex) in item.parsed.answerSegments" :key="`${item.id || index}-${segmentIndex}`">
                  <text v-if="segment.type === 'text'" class="message-text">{{ segment.text }}</text>
                  <text
                    v-else
                    class="citation-chip"
                    :class="{ disabled: item.streaming }"
                    @tap="item.streaming ? null : openCitationDetail(segment.chunkUid)"
                  >{{ segment.token }}</text>
                </template>
                <text v-if="item.streaming" class="message-cursor">|</text>
              </view>
              <view v-else-if="item.streaming && !item.parsed.thinkingContent" class="message-text-wrap">
                <text class="message-text">正在思考...</text>
                <text class="message-cursor">|</text>
              </view>
            </view>
            <view v-else class="message-text-wrap">
              <text class="message-text">{{ item.content || (item.streaming ? '正在思考...' : '') }}</text>
              <text v-if="item.streaming" class="message-cursor">|</text>
            </view>
          </view>
          <view v-if="shouldShowMessageActions(item, index)" class="message-actions">
            <text class="message-action" @tap="copyMessage(item)">复制</text>
            <text class="message-action" @tap="retryLastRound">重试</text>
            <text class="message-action danger" @tap="deleteLastRound">删除</text>
          </view>
        </view>
        <view :id="bottomAnchorId"></view>
      </scroll-view>

      <text v-if="errorText" class="chat-error">{{ errorText }}</text>
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
                <text class="switch-text switch-text-left">RAG</text>
                <text class="switch-text switch-text-right">通用</text>
                <view class="ios-switch-knob"></view>
              </view>
              <view class="ios-switch" :class="{ on: thinkingEnabled }" @tap="toggleThinkingMode">
                <text class="switch-text switch-text-left">思考</text>
                <text class="switch-text switch-text-right">快速</text>
                <view class="ios-switch-knob"></view>
              </view>
            </view>
            <view
              class="send-button"
              :class="{ stop: generating, disabled: !generating && !canSend }"
              @tap="generating ? stopGeneration() : sendMessage()"
            >
              <text class="send-label">{{ generating ? '停止' : '发送' }}</text>
            </view>
          </view>
        </view>
      </view>
    </view>

    <view v-if="citationPopupVisible" class="citation-mask" @tap="closeCitationPopup">
      <view class="citation-popup" @tap.stop>
        <view class="citation-header">
          <text class="citation-title">引用详情</text>
          <text class="citation-close" @tap="closeCitationPopup">关闭</text>
        </view>
        <text v-if="citationLoading" class="citation-loading">正在加载引用内容...</text>
        <text v-else-if="citationError" class="citation-error">{{ citationError }}</text>
        <template v-else-if="citationDetail">
          <scroll-view
            v-if="shouldUseCitationScroll(citationDetail)"
            class="citation-body citation-body-scroll"
            scroll-y="true"
            enhanced="true"
            show-scrollbar="true"
          >
            <text class="citation-meta">chunk_uid：{{ citationDetail.chunk_uid }}</text>
            <text v-if="citationDetail.source" class="citation-meta">来源：{{ citationDetail.source }}</text>
            <text v-if="citationDetail.doc_id" class="citation-meta">doc_id：{{ citationDetail.doc_id }}</text>
            <view class="citation-content">
              <text
                v-for="(char, charIndex) in buildCitationFadeChars(citationDetail.text)"
                :key="`${citationDetail.chunk_uid}-${charIndex}`"
                class="citation-char"
                :style="{ opacity: char.opacity }"
              >{{ char.char }}</text>
            </view>
          </scroll-view>
          <view v-else class="citation-body">
            <text class="citation-meta">chunk_uid：{{ citationDetail.chunk_uid }}</text>
            <text v-if="citationDetail.source" class="citation-meta">来源：{{ citationDetail.source }}</text>
            <text v-if="citationDetail.doc_id" class="citation-meta">doc_id：{{ citationDetail.doc_id }}</text>
            <view class="citation-content">
              <text
                v-for="(char, charIndex) in buildCitationFadeChars(citationDetail.text)"
                :key="`${citationDetail.chunk_uid}-${charIndex}`"
                class="citation-char"
                :style="{ opacity: char.opacity }"
              >{{ char.char }}</text>
            </view>
          </view>
        </template>
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
</template>

<script>
import {
  ChatStreamClient,
  DEFAULT_WELCOME_MESSAGE,
  buildChatMessages,
  createDefaultWsUrl,
} from './backend'
import {
  clearSessionMessages,
  createChatSession,
  deleteChatSession,
  getChatSessionById,
  pushSessionMessage,
  removeLastSessionMessage,
  setActiveChatSession,
  snapshotAppState,
  syncChatSettingsFromStorage,
  updateChatSettings,
  updateLastSessionMessage,
} from './state'

export default {
  data() {
    return {
      sidebarOpen: false,
      pageReady: false,
      message: '',
      ragEnabled: true,
      thinkingEnabled: false,
      historyList: [],
      activeHistoryId: '',
      connectionStatus: 'connecting',
      generating: false,
      activeRequestId: '',
      errorText: '',
      streamingSessionId: '',
      scrollIntoView: '',
      bottomAnchorId: 'chat-bottom',
      client: null,
      citationPopupVisible: false,
      citationLoading: false,
      citationError: '',
      citationDetail: null,
      pendingCitationRequestId: '',
      thinkingCollapseMap: {},
    }
  },
  computed: {
    currentSession() {
      return this.historyList.find((item) => item.id === this.activeHistoryId) || null
    },
    messages() {
      return this.currentSession?.messages || []
    },
    visibleMessages() {
      return this.messages
        .filter((item) => item.content !== DEFAULT_WELCOME_MESSAGE)
        .map((item) => {
          const parsed = item.role === 'assistant'
            ? this.parseMessageContent(item.content || '')
            : null
          return {
            ...item,
            parsed,
            thinkingCollapsed: parsed
              ? this.isThinkingCollapsed(item, parsed)
              : false,
          }
        })
    },
    activeSessionTitle() {
      return this.currentSession?.title || '新对话'
    },
    hasConversationStarted() {
      return this.messages.some((item) => item.role === 'user')
    },
    canSend() {
      return Boolean(this.message.trim())
    },
  },
  onLoad() {
    syncChatSettingsFromStorage()
    this.syncFromState()
    this.initClient()
  },
  onShow() {
    syncChatSettingsFromStorage()
    this.syncFromState()
  },
  onUnload() {
    this.client?.close()
  },
  methods: {
    syncFromState() {
      const state = snapshotAppState()
      this.historyList = state.chatSessions
      this.activeHistoryId = state.activeSessionId
      this.ragEnabled = Boolean(state.chatSettings.ragEnabled)
      this.thinkingEnabled = Boolean(state.chatSettings.enableThinking)
    },
    parseAnswerSegments(content = '') {
      const regex = /\[r(\d+)\]/g
      const segments = []
      let lastIndex = 0
      let match
      while ((match = regex.exec(content)) !== null) {
        if (match.index > lastIndex) segments.push({ type: 'text', text: content.slice(lastIndex, match.index) })
        segments.push({ type: 'citation', token: match[0], chunkUid: Number(match[1]) })
        lastIndex = match.index + match[0].length
      }
      if (lastIndex < content.length) segments.push({ type: 'text', text: content.slice(lastIndex) })
      return segments.length ? segments : [{ type: 'text', text: content }]
    },
    parseMessageContent(content = '') {
      const startMatch = /(?:Thinking Process:|<think>)/i.exec(content)
      if (!startMatch) {
        return { thinkingContent: '', answerContent: content, answerSegments: this.parseAnswerSegments(content) }
      }
      const startIndex = startMatch.index
      const thinkingStart = startIndex + startMatch[0].length
      const endToken = '</think>'
      const endIndex = content.indexOf(endToken, thinkingStart)
      const answerBeforeThinking = content.slice(0, startIndex)
      if (endIndex === -1) {
        const answerContent = answerBeforeThinking.trimEnd()
        return {
          thinkingContent: content.slice(thinkingStart).trimStart(),
          answerContent,
          answerSegments: this.parseAnswerSegments(answerContent),
        }
      }
      const answerContent = `${answerBeforeThinking}${content.slice(endIndex + endToken.length)}`.trim()
      return {
        thinkingContent: content.slice(thinkingStart, endIndex).trim(),
        answerContent,
        answerSegments: this.parseAnswerSegments(answerContent),
      }
    },
    isThinkingCollapsed(message, parsed) {
      if (!parsed?.thinkingContent) return false
      if (message.streaming) return false
      const cached = this.thinkingCollapseMap[message.id]
      return typeof cached === 'boolean' ? cached : true
    },
    toggleThinkingBlock(message) {
      if (!message?.parsed?.thinkingContent) return
      this.thinkingCollapseMap = {
        ...this.thinkingCollapseMap,
        [message.id]: !this.isThinkingCollapsed(message, message.parsed),
      }
    },
    buildCitationFadeChars(text = '') {
      const chars = Array.from(text || '')
      const length = chars.length
      if (!length) return []

      const edge = Math.min(20, Math.ceil(length / 2))
      const denominator = Math.max(edge - 1, 1)

      return chars.map((char, index) => {
        let opacity = 1
        if (index < edge) opacity = index / denominator
        if (index >= length - edge) {
          const tailDistance = length - index
          const tailOpacity = (tailDistance - 1) / denominator
          opacity = Math.min(opacity, tailOpacity)
        }
        return {
          char,
          opacity: Number(opacity.toFixed(3)),
        }
      })
    },
    shouldUseCitationScroll(detail) {
      const textLength = Array.from(detail?.text || '').length
      return textLength > 260
    },
    closeCitationPopup() {
      this.citationPopupVisible = false
      this.citationLoading = false
      this.citationError = ''
      this.citationDetail = null
      this.pendingCitationRequestId = ''
    },
    openCitationDetail(chunkUid) {
      this.citationPopupVisible = true
      this.citationLoading = true
      this.citationError = ''
      this.citationDetail = null
      try {
        this.pendingCitationRequestId = this.client.requestCitationDetail(chunkUid)
      } catch (error) {
        this.citationLoading = false
        this.citationError = error.message || '引用详情加载失败'
        this.pendingCitationRequestId = ''
      }
    },
    initClient() {
      this.client = new ChatStreamClient({
        url: createDefaultWsUrl(),
        handlers: {
          onOpen: () => {
            this.connectionStatus = 'connected'
          },
          onClose: () => {
            this.connectionStatus = 'disconnected'
          },
          onStreamStart: () => {
            this.generating = true
          },
          onChunk: ({ delta }) => {
            const sessionId = this.streamingSessionId || this.activeHistoryId
            const session = getChatSessionById(sessionId)
            const lastMessage = session?.messages?.[session.messages.length - 1]
            updateLastSessionMessage(sessionId, {
              content: `${lastMessage?.content || ''}${delta}`,
            })
            this.syncFromState()
            this.scrollToBottom()
          },
          onStreamEnd: ({ payload }) => {
            if (this.streamingSessionId) {
              updateLastSessionMessage(this.streamingSessionId, {
                streaming: false,
                finishReason: payload.finish_reason || '',
              })
            }
            this.generating = false
            this.activeRequestId = ''
            this.streamingSessionId = ''
            this.syncFromState()
          },
          onCitationDetail: ({ requestId, payload }) => {
            if (requestId !== this.pendingCitationRequestId) return
            this.citationLoading = false
            this.citationError = ''
            this.citationDetail = payload
            this.pendingCitationRequestId = ''
          },
          onError: (error) => {
            if (error.requestId && error.requestId === this.pendingCitationRequestId) {
              this.citationLoading = false
              this.citationError = error.message || '引用详情加载失败'
              this.pendingCitationRequestId = ''
              return
            }
            if (this.streamingSessionId) {
              updateLastSessionMessage(this.streamingSessionId, {
                streaming: false,
                finishReason: 'error',
              })
            }
            this.connectionStatus = 'error'
            this.generating = false
            this.activeRequestId = ''
            this.streamingSessionId = ''
            this.errorText = error.message || '对话请求失败'
            this.syncFromState()
          },
        },
      })

      this.client.connect().catch((error) => {
        this.connectionStatus = 'error'
        this.errorText = error.message || '连接失败'
      })
    },
    formatTime(timestamp) {
      const diff = Date.now() - Number(timestamp || 0)
      if (diff < 60 * 1000) return '刚刚'
      if (diff < 60 * 60 * 1000) return `${Math.floor(diff / (60 * 1000))} 分钟前`
      if (diff < 24 * 60 * 60 * 1000) return `${Math.floor(diff / (60 * 60 * 1000))} 小时前`
      if (diff < 7 * 24 * 60 * 60 * 1000) return `${Math.floor(diff / (24 * 60 * 60 * 1000))} 天前`

      const date = new Date(timestamp)
      const month = `${date.getMonth() + 1}`.padStart(2, '0')
      const day = `${date.getDate()}`.padStart(2, '0')
      return `${month}-${day}`
    },
    scrollToBottom() {
      const anchorId = `chat-bottom-${Date.now()}`
      this.bottomAnchorId = anchorId
      this.$nextTick(() => {
        this.scrollIntoView = anchorId
      })
    },
    toggleSidebar() {
      this.sidebarOpen = !this.sidebarOpen
    },
    closeSidebar() {
      this.sidebarOpen = false
    },
    toggleRagMode() {
      updateChatSettings({ ragEnabled: !this.ragEnabled })
      this.syncFromState()
    },
    toggleThinkingMode() {
      updateChatSettings({ enableThinking: !this.thinkingEnabled })
      this.syncFromState()
    },
    startNewChat() {
      createChatSession()
      this.message = ''
      this.errorText = ''
      this.syncFromState()
      this.closeSidebar()
      this.scrollToBottom()
    },
    selectSession(sessionId) {
      setActiveChatSession(sessionId)
      this.errorText = ''
      this.syncFromState()
      this.closeSidebar()
      this.scrollToBottom()
    },
    confirmDeleteSession(sessionId) {
      const session = this.historyList.find((item) => item.id === sessionId)
      if (!session) return

      uni.showModal({
        title: '删除对话',
        content: `确认删除“${session.title}”吗？`,
        confirmColor: '#4c72ff',
        success: ({ confirm }) => {
          if (!confirm) return
          this.deleteSession(sessionId)
        },
      })
    },
    deleteSession(sessionId) {
      if (this.streamingSessionId === sessionId) {
        this.stopGeneration()
      }
      deleteChatSession(sessionId)
      this.syncFromState()
    },
    sendMessage() {
      const content = this.message.trim()
      if (!content || this.generating || !this.currentSession) return

      const sessionId = this.currentSession.id
      this.errorText = ''
      pushSessionMessage(sessionId, { role: 'user', content })
      pushSessionMessage(sessionId, { role: 'assistant', content: '', streaming: true })
      this.message = ''
      this.streamingSessionId = sessionId
      this.syncFromState()
      this.scrollToBottom()

      try {
        this.activeRequestId = this.client.sendChat({
          messages: buildChatMessages(
            this.currentSession.messages.filter((item) => !item.streaming),
            snapshotAppState().chatSettings.systemPrompt
          ),
          fileIds: this.currentSession.fileIds || [],
          rag: {
            enabled: this.ragEnabled,
            top_k: Number(snapshotAppState().chatSettings.topK),
          },
          modelConfig: {
            temperature: Number(snapshotAppState().chatSettings.temperature),
            max_tokens: Number(snapshotAppState().chatSettings.maxTokens),
            enable_thinking: this.thinkingEnabled,
          },
        })
        this.generating = true
      } catch (error) {
        removeLastSessionMessage(sessionId)
        this.streamingSessionId = ''
        this.errorText = error.message || '发送失败'
        this.syncFromState()
      }
    },
    stopGeneration() {
      this.client?.cancel(this.activeRequestId)
      if (this.streamingSessionId) {
        updateLastSessionMessage(this.streamingSessionId, {
          streaming: false,
          finishReason: 'cancelled',
        })
      }
      this.generating = false
      this.activeRequestId = ''
      this.streamingSessionId = ''
      this.syncFromState()
    },
    retryConnection() {
      this.errorText = ''
      this.connectionStatus = 'connecting'
      this.client?.reconnect().catch((error) => {
        this.connectionStatus = 'error'
        this.errorText = error.message || '连接失败'
      })
    },
    getLatestRound() {
      if (this.messages.length < 2) return null
      const assistantIndex = this.messages.length - 1
      const userIndex = assistantIndex - 1
      const assistantMessage = this.messages[assistantIndex]
      const userMessage = this.messages[userIndex]

      if (assistantMessage?.role !== 'assistant' || userMessage?.role !== 'user') return null
      return {
        assistantIndex,
        assistantMessage,
        userMessage,
      }
    },
    retryLastRound() {
      if (this.generating || !this.currentSession) return

      const latestRound = this.getLatestRound()
      if (!latestRound) return

      const sessionId = this.currentSession.id
      const requestMessages = this.currentSession.messages.filter((item, index) => (
        index !== latestRound.assistantIndex && !item.streaming
      ))

      removeLastSessionMessage(sessionId)
      pushSessionMessage(sessionId, { role: 'assistant', content: '', streaming: true })
      this.streamingSessionId = sessionId
      this.errorText = ''
      this.syncFromState()
      this.scrollToBottom()

      try {
        this.activeRequestId = this.client.sendChat({
          messages: buildChatMessages(requestMessages, snapshotAppState().chatSettings.systemPrompt),
          fileIds: this.currentSession.fileIds || [],
          rag: {
            enabled: this.ragEnabled,
            top_k: Number(snapshotAppState().chatSettings.topK),
          },
          modelConfig: {
            temperature: Number(snapshotAppState().chatSettings.temperature),
            max_tokens: Number(snapshotAppState().chatSettings.maxTokens),
            enable_thinking: this.thinkingEnabled,
          },
        })
        this.generating = true
      } catch (error) {
        removeLastSessionMessage(sessionId)
        this.streamingSessionId = ''
        this.errorText = error.message || '重试失败'
        this.syncFromState()
      }
    },
    deleteLastRound() {
      if (this.generating || !this.currentSession) return
      const latestRound = this.getLatestRound()
      if (!latestRound) return

      removeLastSessionMessage(this.currentSession.id)
      removeLastSessionMessage(this.currentSession.id)
      this.syncFromState()
    },
    shouldShowMessageActions(message, index) {
      if (this.generating || message.role !== 'assistant' || message.streaming) return false
      if (index !== this.visibleMessages.length - 1) return false
      return this.visibleMessages[index - 1]?.role === 'user'
    },
    copyMessage(message) {
      const content = message.role === 'assistant'
        ? message.parsed?.answerContent?.trim()
        : message.content?.trim()
      if (!content) return
      uni.setClipboardData({
        data: content,
      })
    },
    clearChat() {
      if (!this.currentSession) return
      if (this.generating) this.stopGeneration()
      clearSessionMessages(this.currentSession.id)
      this.errorText = ''
      this.syncFromState()
      this.scrollToBottom()
    },
    goPage(page) {
      const pageMap = {
        chat: '/pages/chat/index',
        upload: '/pages/upload/index',
        settings: '/pages/settings/index',
      }
      const url = pageMap[page]
      if (!url || url === '/pages/chat/index') {
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
  filter: blur(42rpx);
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

.new-chat-button {
  height: 72rpx;
  margin-bottom: 22rpx;
  border-radius: 22rpx;
  background: linear-gradient(180deg, #6389ff 0%, #4c72ff 100%);
  box-shadow: 0 16rpx 30rpx rgba(64, 101, 255, 0.28);
  display: flex;
  align-items: center;
  justify-content: center;
}

.new-chat-button-text {
  font-size: 26rpx;
  font-weight: 600;
  color: #ffffff;
}

.history-list {
  flex: 1;
  min-height: 0;
}

.history-card {
  margin-bottom: 18rpx;
  padding: 24rpx;
  border: 1rpx solid rgba(82, 120, 255, 0.16);
  border-radius: 24rpx;
  background: rgba(15, 25, 46, 0.72);
  display: flex;
  align-items: center;
  gap: 18rpx;
}

.history-card.active {
  border-color: rgba(102, 142, 255, 0.54);
  background: rgba(36, 58, 108, 0.82);
  box-shadow: inset 0 0 0 1rpx rgba(111, 151, 255, 0.18);
}

.history-main {
  flex: 1;
  min-width: 0;
}

.history-title {
  display: block;
  font-size: 28rpx;
  color: #eef3ff;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history-time {
  display: block;
  margin-top: 10rpx;
  font-size: 22rpx;
  color: rgba(165, 182, 224, 0.66);
}

.history-delete {
  width: 88rpx;
  height: 56rpx;
  border-radius: 999rpx;
  border: 1rpx solid rgba(255, 131, 131, 0.22);
  background: rgba(83, 27, 40, 0.86);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.history-delete-text {
  font-size: 22rpx;
  color: #ffd8d8;
}

.chat-section {
  position: relative;
  z-index: 1;
  flex: 1;
  min-height: 0;
  margin-top: 8rpx;
  display: flex;
  flex-direction: column;
}

.message-list {
  position: relative;
  z-index: 2;
  flex: 1;
  min-height: 0;
  opacity: 0;
  transform: translateY(10rpx);
  transition: opacity 0.12s ease, transform 0.16s ease;
}

.message-list.active {
  opacity: 1;
  transform: translateY(0);
}

.message-row + .message-row {
  margin-top: 24rpx;
}

.message-row {
  display: flex;
  flex-direction: column;
}

.message-row.user {
  align-items: flex-end;
}

.message-row.assistant {
  align-items: flex-start;
}

.message-role {
  margin-bottom: 10rpx;
  font-size: 22rpx;
  color: rgba(180, 198, 236, 0.68);
}

.message-bubble {
  max-width: 78%;
  padding: 22rpx 24rpx;
  border-radius: 24rpx;
  border: 1rpx solid rgba(98, 125, 192, 0.14);
  background: rgba(14, 24, 45, 0.88);
  box-shadow: 0 12rpx 28rpx rgba(0, 0, 0, 0.14);
}

.message-content-stack {
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}

.message-rich-text,
.message-text-wrap {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
}

.thinking-block {
  border: 1rpx solid rgba(126, 150, 209, 0.18);
  border-radius: 20rpx;
  background: rgba(255, 255, 255, 0.04);
}

.thinking-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16rpx;
  padding: 18rpx 20rpx;
}

.thinking-title,
.thinking-hint,
.thinking-text,
.thinking-arrow {
  display: block;
}

.thinking-title {
  font-size: 24rpx;
  font-weight: 600;
  color: #dbe5ff;
}

.thinking-hint {
  margin-top: 6rpx;
  font-size: 20rpx;
  color: rgba(173, 191, 234, 0.68);
}

.thinking-arrow {
  font-size: 24rpx;
  color: rgba(173, 191, 234, 0.78);
  transform: rotate(0deg);
}

.thinking-arrow.collapsed {
  transform: rotate(180deg);
}

.thinking-body {
  padding: 0 20rpx 20rpx;
}

.thinking-text {
  white-space: pre-wrap;
  word-break: break-all;
  font-size: 24rpx;
  line-height: 1.7;
  color: rgba(219, 229, 255, 0.82);
}

.citation-chip {
  margin: 0 8rpx;
  padding: 4rpx 14rpx;
  border-radius: 999rpx;
  background: rgba(76, 114, 255, 0.18);
  border: 1rpx solid rgba(112, 149, 255, 0.34);
  color: #8fb0ff;
  font-size: 26rpx;
}

.citation-chip.disabled {
  opacity: 0.48;
}

.message-bubble.user {
  background: linear-gradient(180deg, rgba(76, 114, 255, 0.9), rgba(63, 95, 214, 0.88));
}

.message-text {
  white-space: pre-wrap;
  word-break: break-all;
  font-size: 28rpx;
  line-height: 1.7;
  color: #eef4ff;
}

.message-cursor {
  margin-left: 6rpx;
  color: #8fb0ff;
}

.message-actions {
  display: flex;
  gap: 18rpx;
  margin-top: 14rpx;
}

.message-action {
  font-size: 22rpx;
  color: rgba(207, 220, 255, 0.9);
}

.message-action.danger {
  color: #ffb0b0;
}

.chat-error {
  margin-top: 16rpx;
  font-size: 22rpx;
  color: #ffb4b4;
}

.hero-section {
  position: absolute;
  inset: 0;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48rpx 20rpx 32rpx;
  text-align: center;
  transition: opacity 0.14s ease, transform 0.18s ease;
}

.hero-section.faded {
  opacity: 0;
  transform: scale(0.97) translateY(-8rpx);
  pointer-events: none;
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
  padding-bottom: calc(92rpx + constant(safe-area-inset-bottom));
  padding-bottom: calc(92rpx + env(safe-area-inset-bottom));
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

.send-button.stop {
  background: linear-gradient(180deg, #ff7a7a 0%, #ef4444 100%);
}

.send-button.disabled {
  opacity: 0.45;
}

.send-label {
  font-size: 24rpx;
  font-weight: 600;
  line-height: 1;
  color: rgba(255, 255, 255, 0.96);
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

.citation-mask {
  position: fixed;
  inset: 0;
  z-index: 40;
  background: rgba(2, 6, 14, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32rpx;
}

.citation-popup {
  width: 640rpx;
  max-height: 860rpx;
  padding: 28rpx;
  border-radius: 28rpx;
  background: linear-gradient(180deg, rgba(11, 21, 39, 0.98), rgba(7, 13, 24, 0.98));
  border: 1rpx solid rgba(95, 131, 255, 0.2);
  box-sizing: border-box;
}

.citation-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 20rpx;
}

.citation-title,
.citation-close,
.citation-loading,
.citation-error,
.citation-meta,
.citation-content,
.citation-char {
  display: block;
}

.citation-title { font-size: 30rpx; color: #f4f7ff; font-weight: 600; }
.citation-close { font-size: 24rpx; color: #8fb0ff; }
.citation-loading { font-size: 24rpx; color: rgba(207, 220, 255, 0.76); }
.citation-error { font-size: 24rpx; color: #ffb4b4; }
.citation-body {
  width: 100%;
  box-sizing: border-box;
}
.citation-body-scroll {
  height: 640rpx;
}
.citation-meta { margin-bottom: 12rpx; font-size: 22rpx; color: rgba(180, 198, 236, 0.72); }
.citation-content {
  margin-top: 12rpx;
  padding: 20rpx 22rpx;
  border-radius: 20rpx;
  background: rgba(255, 255, 255, 0.04);
  border: 1rpx solid rgba(255, 255, 255, 0.06);
  font-size: 26rpx;
  line-height: 1.8;
  color: #eef4ff;
  box-sizing: border-box;
}
.citation-char {
  display: inline;
  white-space: pre-wrap;
}
</style>

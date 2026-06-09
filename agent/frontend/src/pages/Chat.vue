<script setup lang="ts">
import { ref, nextTick, watch, computed } from 'vue'
import { useChatStore } from '../stores/chat'
import type { ChatMessage } from '../types/api'
import { renderMarkdown } from '../lib/markdown'
import 'highlight.js/styles/github.css'

const chatStore = useChatStore()

const inputMessage = ref('')
const messagesContainer = ref<HTMLElement | null>(null)

/**
 * 计算属性：渲染后的消息列表
 * 对每条消息的内容进行Markdown渲染
 */
const renderedMessages = computed(() => {
  return chatStore.messages.map((message) => {
    return {
      ...message,
      renderedContent: message.role === 'assistant' 
        ? renderMarkdown(message.content) 
        : message.content
    }
  })
})

function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTo({
        top: messagesContainer.value.scrollHeight,
        behavior: 'smooth'
      })
    }
  })
}

watch(() => chatStore.messages.length, scrollToBottom)

async function handleSend() {
  if (!inputMessage.value.trim() || chatStore.isLoading) return
  await chatStore.sendMessage(inputMessage.value)
  inputMessage.value = ''
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
}

function clearChat() {
  chatStore.clearMessages()
}

function formatTime(timestamp: string) {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

function isUserMessage(message: ChatMessage) {
  return message.role === 'user'
}
</script>

<template>
  <div class="chat-page">
    <div class="chat-header">
      <h1 class="title">智能对话</h1>
      <el-button type="danger" plain @click="clearChat" :disabled="!chatStore.hasMessages">
        <el-icon><Delete /></el-icon>
        清空对话
      </el-button>
    </div>

    <div class="chat-container">
      <div ref="messagesContainer" class="messages-area">
        <div v-if="!chatStore.hasMessages" class="welcome-message">
          <div class="welcome-icon">
            <el-icon size="64" style="color: #3B82F6"><ChatDotRound /></el-icon>
          </div>
          <h2>欢迎使用运维智能体</h2>
          <p>我可以帮助你：</p>
          <ul>
            <li>查询集群状态</li>
            <li>分析异常诊断</li>
            <li>获取日志信息</li>
            <li>执行健康检查</li>
          </ul>
          <p class="hint">试试问：集群状态如何？</p>
        </div>

        <div v-else class="message-list">
          <div
            v-for="(message, index) in renderedMessages"
            :key="index"
            :class="['message-item', { 'user-message': isUserMessage(message) }]"
          >
            <div class="message-avatar">
              <el-icon :size="32">
                <User v-if="isUserMessage(message)" />
                <ChatDotRound v-else />
              </el-icon>
            </div>
            <div class="message-content">
              <div 
                class="message-bubble" 
                :class="{
                  'user-bubble': isUserMessage(message),
                  'md-content': !isUserMessage(message)
                }"
              >
                <template v-if="isUserMessage(message)">
                  {{ message.content }}
                </template>
                <template v-else>
                  <div v-html="message.renderedContent"></div>
                </template>
              </div>
              <div class="message-time">{{ formatTime(message.timestamp) }}</div>
            </div>
          </div>

          <div v-if="chatStore.isLoading" class="message-item">
            <div class="message-avatar">
              <el-icon size="32"><ChatDotRound /></el-icon>
            </div>
            <div class="message-content">
              <div class="typing-indicator">
                <span class="dot"></span>
                <span class="dot"></span>
                <span class="dot"></span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="input-area">
        <el-input
          v-model="inputMessage"
          type="textarea"
          :autosize="{ minRows: 2, maxRows: 4 }"
          placeholder="输入消息..."
          @keydown="handleKeydown"
          :disabled="chatStore.isLoading"
        />
        <div class="input-actions">
          <span class="tip" v-if="chatStore.isLoading">
            <el-icon><Loading /></el-icon>
            正在思考...
          </span>
          <el-button
            type="primary"
            :loading="chatStore.isLoading"
            @click="handleSend"
          >
            <el-icon><Promotion /></el-icon>
            发送
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.chat-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 64px);
  padding: 20px;
}

.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.title {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  color: #1f2937;
}

.chat-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: white;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.messages-area {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.welcome-message {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #6b7280;
  text-align: center;
}

.welcome-icon {
  margin-bottom: 16px;
  padding: 20px;
  background: rgba(59, 130, 246, 0.1);
  border-radius: 50%;
}

.welcome-message h2 {
  margin: 0 0 12px 0;
  font-size: 24px;
  color: #1f2937;
}

.welcome-message p {
  margin: 0 0 8px 0;
  font-size: 14px;
}

.welcome-message ul {
  margin: 0 0 12px 0;
  padding: 0;
  list-style: none;
  text-align: left;
}

.welcome-message ul li {
  padding: 4px 0;
  font-size: 14px;
  color: #6b7280;
}

.welcome-message .hint {
  margin-top: 20px;
  padding: 12px 24px;
  background: #f0f9ff;
  border-radius: 8px;
  color: #0369a1;
  font-size: 14px;
}

.message-list {
  max-width: 800px;
  margin: 0 auto;
}

.message-item {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
}

.message-item.user-message {
  flex-direction: row-reverse;
}

.message-avatar {
  display: flex;
  align-items: flex-start;
  align-self: flex-start;
  padding: 8px;
  background: #f3f4f6;
  border-radius: 8px;
  color: #6b7280;
}

.message-item.user-message .message-avatar {
  background: #dbeafe;
  color: #3b82f6;
}

.message-content {
  flex: 1;
  max-width: 70%;
}

.message-item.user-message .message-content {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.message-bubble {
  padding: 12px 16px;
  background: #f3f4f6;
  border-radius: 12px 12px 12px 4px;
  color: #1f2937;
  line-height: 1.6;
  word-break: break-word;
}

.message-bubble.user-bubble {
  background: #3b82f6;
  color: white;
  border-radius: 12px 12px 4px 12px;
  white-space: pre-wrap;
}

.message-time {
  margin-top: 4px;
  font-size: 12px;
  color: #9ca3af;
}

.typing-indicator {
  display: flex;
  gap: 4px;
  padding: 12px 16px;
  background: #f3f4f6;
  border-radius: 12px;
  align-self: flex-start;
}

.typing-indicator .dot {
  width: 8px;
  height: 8px;
  background: #6b7280;
  border-radius: 50%;
  animation: typing 1.4s infinite;
}

.typing-indicator .dot:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-indicator .dot:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing {
  0%, 60%, 100% {
    transform: translateY(0);
  }
  30% {
    transform: translateY(-8px);
  }
}

.input-area {
  padding: 16px;
  border-top: 1px solid #e5e7eb;
  background: #f9fafb;
}

.input-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 12px;
}

.input-actions .tip {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #9ca3af;
}
</style>

<style>
/**
 * Markdown内容样式
 * 由于使用v-html注入，这些样式不能使用scoped
 */
.md-content .md-heading {
  font-weight: 600;
  color: #1f2937;
  margin-top: 16px;
  margin-bottom: 8px;
  line-height: 1.3;
}

.md-content .md-h1 {
  font-size: 20px;
  margin-top: 0;
}

.md-content .md-h2 {
  font-size: 18px;
}

.md-content .md-h3 {
  font-size: 16px;
}

.md-content .md-h4 {
  font-size: 15px;
}

.md-content .md-h5 {
  font-size: 14px;
}

.md-content .md-h6 {
  font-size: 14px;
  font-weight: 500;
}

.md-content .md-paragraph {
  margin: 0 0 12px 0;
  line-height: 1.6;
}

.md-content .md-paragraph:last-child {
  margin-bottom: 0;
}

.md-content .md-list {
  margin: 8px 0;
  padding-left: 24px;
}

.md-content .md-ordered-list {
  list-style-type: decimal;
}

.md-content .md-unordered-list {
  list-style-type: disc;
}

.md-content .md-list-item {
  margin: 4px 0;
  line-height: 1.6;
}

.md-content .md-list-item > .md-list {
  margin: 4px 0;
}

.md-content .md-link {
  color: #3b82f6;
  text-decoration: none;
  transition: color 0.2s;
}

.md-content .md-link:hover {
  color: #2563eb;
  text-decoration: underline;
}

.md-content .md-inline-code {
  background: rgba(59, 130, 246, 0.1);
  color: #0369a1;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 0.9em;
  word-break: break-all;
}

.md-content .md-code-block {
  margin: 12px 0;
  padding: 12px;
  background: #1e1e1e;
  border-radius: 8px;
  overflow-x: auto;
  position: relative;
}

.md-content .md-code-block code {
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.5;
  color: #d4d4d4;
  background: transparent;
  padding: 0;
  word-break: normal;
}

.md-content .md-blockquote {
  margin: 12px 0;
  padding: 8px 12px;
  border-left: 4px solid #3b82f6;
  background: rgba(59, 130, 246, 0.05);
  border-radius: 0 4px 4px 0;
  color: #4b5563;
}

.md-content .md-blockquote .md-paragraph {
  margin: 4px 0;
}

.md-content .md-hr {
  margin: 16px 0;
  border: none;
  border-top: 1px solid #e5e7eb;
}

.md-content .md-table {
  width: 100%;
  border-collapse: collapse;
  margin: 12px 0;
  font-size: 14px;
}

.md-content .md-table-header,
.md-content .md-table-cell {
  padding: 8px 12px;
  border: 1px solid #e5e7eb;
  text-align: left;
}

.md-content .md-table-header {
  background: #f3f4f6;
  font-weight: 600;
  color: #1f2937;
}

.md-content .md-table-row:nth-child(even) .md-table-cell {
  background: #fafafa;
}

.md-content .md-image {
  max-width: 100%;
  height: auto;
  border-radius: 8px;
  margin: 12px 0;
}

.md-content strong,
.md-content b {
  font-weight: 600;
  color: #1f2937;
}

.md-content em,
.md-content i {
  font-style: italic;
}

.md-content u {
  text-decoration: underline;
}

.md-content s,
.md-content del {
  text-decoration: line-through;
  color: #6b7280;
}

.md-content ul ul,
.md-content ol ul,
.md-content ul ol,
.md-content ol ol {
  margin-top: 4px;
  margin-bottom: 4px;
}
</style>

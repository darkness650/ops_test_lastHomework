import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { chatApi } from '../api'
import type { ChatMessage } from '../types/api'

export const useChatStore = defineStore('chat', () => {
  const messages = ref<ChatMessage[]>([])
  const contextId = ref<string | null>(null)
  const isLoading = ref(false)

  const hasMessages = computed(() => messages.value.length > 0)

  function addUserMessage(content: string) {
    messages.value.push({
      role: 'user',
      content,
      timestamp: new Date().toISOString()
    })
  }

  function addAssistantMessage(content: string) {
    messages.value.push({
      role: 'assistant',
      content,
      timestamp: new Date().toISOString()
    })
  }

  async function sendMessage(content: string) {
    if (!content.trim() || isLoading.value) return

    addUserMessage(content)
    isLoading.value = true

    try {
      const response = await chatApi.sendMessage({
        message: content,
        context_id: contextId.value || undefined
      })

      if (response.code === 200) {
        contextId.value = response.data.context_id
        addAssistantMessage(response.data.response)
      }
    } catch (error) {
      console.error('发送消息失败:', error)
      addAssistantMessage('抱歉，发送消息失败，请稍后重试。')
    } finally {
      isLoading.value = false
    }
  }

  function clearMessages() {
    messages.value = []
    contextId.value = null
  }

  return {
    messages,
    contextId,
    isLoading,
    hasMessages,
    sendMessage,
    clearMessages
  }
})

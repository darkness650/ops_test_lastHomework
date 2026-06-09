import { defineStore } from 'pinia'
import { ref } from 'vue'
import { healthApi } from '../api'

export const useBackendStore = defineStore('backend', () => {
  const isOnline = ref<boolean>(false)
  const lastChecked = ref<string | null>(null)
  let pollInterval: ReturnType<typeof setInterval> | null = null

  async function checkHealth() {
    try {
      const response = await healthApi.check()
      isOnline.value = response?.status === 'ok'
    } catch (error) {
      isOnline.value = false
    } finally {
      lastChecked.value = new Date().toISOString()
    }
  }

  function startPolling(intervalMs: number = 5000) {
    stopPolling()
    pollInterval = setInterval(() => {
      checkHealth()
    }, intervalMs)
  }

  function stopPolling() {
    if (pollInterval) {
      clearInterval(pollInterval)
      pollInterval = null
    }
  }

  return {
    isOnline,
    lastChecked,
    checkHealth,
    startPolling,
    stopPolling
  }
})

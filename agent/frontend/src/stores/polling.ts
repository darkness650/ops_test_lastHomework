import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { pollingApi } from '../api'
import type { PollingStatus, PollingResponse, PollingRecord, PollingStartRequest } from '../types/api'

export const usePollingStore = defineStore('polling', () => {
  const status = ref<PollingStatus | null>(null)
  const history = ref<PollingRecord[]>([])
  const isLoading = ref(false)
  const isActionLoading = ref(false)

  const isRunning = computed(() => status.value?.is_running ?? false)
  const intervalMinutes = computed(() => status.value?.interval_minutes ?? 5)
  const historyCount = computed(() => status.value?.history_count ?? 0)

  function updateStatusFromResponse(pollingResponse: PollingResponse): boolean {
    if (pollingResponse.status) {
      status.value = pollingResponse.status
      return true
    }
    if (pollingResponse.success) {
      status.value = {
        is_running: false,
        interval_minutes: status.value?.interval_minutes ?? 5,
        execution_count: status.value?.execution_count ?? 0,
      }
      return true
    }
    return false
  }

  async function fetchStatus(): Promise<boolean> {
    try {
      const response = await pollingApi.status()
      if (response.code === 200) {
        return updateStatusFromResponse(response.data)
      }
      return false
    } catch (error) {
      console.error('获取轮询状态失败:', error)
      return false
    }
  }

  async function fetchHistory(limit: number = 20): Promise<boolean> {
    isLoading.value = true
    try {
      const response = await pollingApi.history(limit)
      if (response.code === 200) {
        history.value = response.data.records || []
        return true
      }
      return false
    } catch (error) {
      console.error('获取历史记录失败:', error)
      return false
    } finally {
      isLoading.value = false
    }
  }

  async function startPolling(config: PollingStartRequest): Promise<boolean> {
    isActionLoading.value = true
    try {
      const response = await pollingApi.start(config)
      if (response.code === 200) {
        const result = updateStatusFromResponse(response.data)
        if (result) {
          return true
        }
        return await fetchStatus()
      }
      return false
    } catch (error) {
      console.error('启动轮询失败:', error)
      return false
    } finally {
      isActionLoading.value = false
    }
  }

  async function stopPolling(): Promise<boolean> {
    isActionLoading.value = true
    try {
      const response = await pollingApi.stop()
      if (response.code === 200) {
        const result = updateStatusFromResponse(response.data)
        if (result) {
          return true
        }
        return await fetchStatus()
      }
      return false
    } catch (error) {
      console.error('停止轮询失败:', error)
      return false
    } finally {
      isActionLoading.value = false
    }
  }

  async function runOnce(): Promise<boolean> {
    isActionLoading.value = true
    try {
      const response = await pollingApi.runOnce()
      if (response.code === 200) {
        const result = updateStatusFromResponse(response.data)
        await fetchHistory(10)
        return result || await fetchStatus()
      }
      return false
    } catch (error) {
      console.error('执行单次轮询失败:', error)
      return false
    } finally {
      isActionLoading.value = false
    }
  }

  async function clearHistory(): Promise<boolean> {
    isActionLoading.value = true
    try {
      const response = await pollingApi.clearHistory()
      if (response.code === 200) {
        history.value = []
        await fetchStatus()
        return true
      }
      return false
    } catch (error) {
      console.error('清空历史记录失败:', error)
      return false
    } finally {
      isActionLoading.value = false
    }
  }

  return {
    status,
    history,
    isLoading,
    isActionLoading,
    isRunning,
    intervalMinutes,
    historyCount,
    fetchStatus,
    fetchHistory,
    startPolling,
    stopPolling,
    runOnce,
    clearHistory
  }
})

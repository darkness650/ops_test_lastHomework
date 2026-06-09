import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { monitorApi } from '../api'
import type { MonitorResponse, ClusterStatus } from '../types/api'

export const useMonitorStore = defineStore('monitor', () => {
  const currentStatus = ref<MonitorResponse | null>(null)
  const isLoading = ref(false)
  const lastUpdated = ref<string | null>(null)

  const anomalyCount = computed(() => currentStatus.value?.anomaly_count ?? 0)
  const status = computed((): ClusterStatus => currentStatus.value?.status ?? 'error')
  const anomalies = computed(() => currentStatus.value?.anomalies ?? [])

  async function quickCheck(namespace?: string) {
    isLoading.value = true
    try {
      const response = await monitorApi.quick(namespace)
      if (response.code === 200) {
        currentStatus.value = response.data
        lastUpdated.value = new Date().toISOString()
      }
    } catch (error) {
      console.error('快速检查失败:', error)
    } finally {
      isLoading.value = false
    }
  }

  async function runHealthCheck(namespace?: string, deepAnalysis: boolean = false) {
    isLoading.value = true
    try {
      const response = await monitorApi.run({
        namespace,
        deep_analysis: deepAnalysis
      })
      if (response.code === 200) {
        currentStatus.value = response.data
        lastUpdated.value = new Date().toISOString()
      }
    } catch (error) {
      console.error('健康检查失败:', error)
    } finally {
      isLoading.value = false
    }
  }

  return {
    currentStatus,
    isLoading,
    lastUpdated,
    anomalyCount,
    status,
    anomalies,
    quickCheck,
    runHealthCheck
  }
})

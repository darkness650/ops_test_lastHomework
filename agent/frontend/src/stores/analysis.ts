import { defineStore } from 'pinia'
import { ref } from 'vue'
import { analysisApi } from '../api/analysis'
import type {
  PerformanceReport,
  AnalysisTaskStatus,
  ScheduleStatus,
  ScheduleConfig
} from '../api/analysis'

/**
 * 业务分析状态管理 Store
 * 用于管理分析报告列表、报告详情、任务状态和定时任务相关状态
 */
export const useAnalysisStore = defineStore('analysis', () => {
  // ========== 状态定义 ==========

  /** 报告列表 */
  const reports = ref<PerformanceReport[]>([])
  /** 当前查看的报告详情 */
  const currentReport = ref<PerformanceReport | null>(null)
  /** 当前分析任务状态 */
  const taskStatus = ref<AnalysisTaskStatus | null>(null)
  /** 定时任务状态 */
  const scheduleStatus = ref<ScheduleStatus | null>(null)
  /** 加载状态 */
  const isLoading = ref(false)
  /** 是否正在分析 */
  const isAnalyzing = ref(false)
  /** 总报告数 */
  const totalReports = ref(0)
  /** 当前页码 */
  const currentPage = ref(1)
  /** 每页数量 */
  const pageSize = ref(10)

  // ========== Actions 定义 ==========

  /**
   * 获取报告列表
   * @param page 页码（可选，默认使用 currentPage）
   * @param pageSizeParam 每页数量（可选，默认使用 pageSize）
   */
  async function fetchReports(page?: number, pageSizeParam?: number) {
    isLoading.value = true
    try {
      const pageToFetch = page ?? currentPage.value
      const sizeToFetch = pageSizeParam ?? pageSize.value

      const response = await analysisApi.getReports(pageToFetch, sizeToFetch)
      if (response.code === 200) {
        reports.value = response.data.reports
        totalReports.value = response.data.total
        currentPage.value = response.data.page
        pageSize.value = response.data.page_size
      }
    } catch (error) {
      console.error('获取报告列表失败:', error)
    } finally {
      isLoading.value = false
    }
  }

  /**
   * 获取报告详情
   * @param reportId 报告唯一标识符
   */
  async function fetchReport(reportId: string) {
    isLoading.value = true
    try {
      const response = await analysisApi.getReport(reportId)
      if (response.code === 200) {
        currentReport.value = response.data
      }
    } catch (error) {
      console.error('获取报告详情失败:', error)
    } finally {
      isLoading.value = false
    }
  }

  /**
   * 删除报告
   * @param reportId 报告唯一标识符
   */
  async function deleteReport(reportId: string) {
    try {
      const response = await analysisApi.deleteReport(reportId)
      if (response.code === 200) {
        // 删除成功后，重新获取列表以更新数据
        await fetchReports()
        // 如果删除的是当前查看的报告，清空 currentReport
        if (currentReport.value?.id === reportId) {
          currentReport.value = null
        }
      }
    } catch (error) {
      console.error('删除报告失败:', error)
    }
  }

  /**
   * 触发分析
   * @param periodHours 分析时长（小时）
   * @param namespace 命名空间
   */
  async function triggerAnalysis(periodHours?: number, namespace?: string) {
    isAnalyzing.value = true
    try {
      const response = await analysisApi.triggerAnalysis({
        analysis_period_hours: periodHours,
        namespace
      })
      if (response.code === 200) {
        // 触发成功后，可以选择开始轮询任务状态
        const taskId = response.data.task_id
        taskStatus.value = {
          task_id: taskId,
          status: 'queued',
          progress: 0,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          report_id: null,
          error_message: null
        }
      }
    } catch (error) {
      console.error('触发分析失败:', error)
      isAnalyzing.value = false
    }
  }

  /**
   * 轮询任务状态
   * @param taskId 任务唯一标识符
   * @returns Promise，解析为最终的任务状态
   */
  async function pollTaskStatus(taskId: string): Promise<AnalysisTaskStatus | null> {
    return new Promise((resolve) => {
      let pollCount = 0
      const maxPollCount = 60 // 最大轮询次数
      const pollInterval = 2000 // 轮询间隔（毫秒）

      const poll = async () => {
        try {
          const response = await analysisApi.getTaskStatus(taskId)
          if (response.code === 200) {
            const status = response.data
            taskStatus.value = status

            // 检查任务是否完成或失败
            if (status.status === 'completed' || status.status === 'failed') {
              isAnalyzing.value = false
              resolve(status)
              return
            }
          }
        } catch (error) {
          console.error('轮询任务状态失败:', error)
        }

        pollCount++
        if (pollCount >= maxPollCount) {
          isAnalyzing.value = false
          resolve(null)
          return
        }

        // 继续轮询
        setTimeout(poll, pollInterval)
      }

      poll()
    })
  }

  /**
   * 获取定时任务状态
   */
  async function fetchScheduleStatus() {
    try {
      const response = await analysisApi.getScheduleStatus()
      if (response.code === 200) {
        scheduleStatus.value = response.data
      }
    } catch (error) {
      console.error('获取定时任务状态失败:', error)
    }
  }

  /**
   * 启动定时任务
   */
  async function startSchedule() {
    try {
      const response = await analysisApi.startSchedule()
      if (response.code === 200) {
        await fetchScheduleStatus()
      }
    } catch (error) {
      console.error('启动定时任务失败:', error)
    }
  }

  /**
   * 停止定时任务
   */
  async function stopSchedule() {
    try {
      const response = await analysisApi.stopSchedule()
      if (response.code === 200) {
        await fetchScheduleStatus()
      }
    } catch (error) {
      console.error('停止定时任务失败:', error)
    }
  }

  /**
   * 更新定时配置
   * @param config 定时配置
   */
  async function updateScheduleConfig(config: ScheduleConfig) {
    try {
      const response = await analysisApi.updateScheduleConfig(config)
      if (response.code === 200) {
        await fetchScheduleStatus()
      }
    } catch (error) {
      console.error('更新定时配置失败:', error)
    }
  }

  // ========== 返回 Store 内容 ==========

  return {
    // 状态
    reports,
    currentReport,
    taskStatus,
    scheduleStatus,
    isLoading,
    isAnalyzing,
    totalReports,
    currentPage,
    pageSize,
    // Actions
    fetchReports,
    fetchReport,
    deleteReport,
    triggerAnalysis,
    pollTaskStatus,
    fetchScheduleStatus,
    startSchedule,
    stopSchedule,
    updateScheduleConfig
  }
})

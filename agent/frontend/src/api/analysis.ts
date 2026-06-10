import request from './request'
import type { ApiResponse } from '../types/api'

/**
 * 性能瓶颈类型
 */
export interface PerformanceBottleneck {
  /** 目标资源，如 Pod 名称、节点名称等 */
  target: string
  /** 瓶颈类型: cpu/memory/network/disk */
  type: string
  /** 严重程度: critical/high/medium/low */
  severity: string
  /** 详细描述 */
  description: string
  /** 当前指标值 */
  metric_value: number
  /** 阈值 */
  threshold: number
}

/**
 * 业务趋势类型
 */
export interface BusinessTrend {
  /** 指标名称 */
  metric_name: string
  /** 趋势方向: up/down/stable */
  direction: string
  /** 变化百分比 */
  change_percent: number
  /** 起始值 */
  start_value: number
  /** 结束值 */
  end_value: number
  /** 时间序列数据点列表 */
  data_points: Record<string, any>[]
}

/**
 * 优化建议类型
 */
export interface OptimizationSuggestion {
  /** 优先级: high/medium/low */
  priority: string
  /** 建议分类，如 资源优化/配置调整/架构改进 */
  category: string
  /** 建议内容 */
  suggestion: string
  /** 预期影响 */
  impact: string
}

/**
 * 指标统计数据类型
 */
export interface MetricStats {
  /** 最小值 */
  min?: number
  /** 最大值 */
  max?: number
  /** 平均值 */
  avg?: number
  /** 趋势变化率 */
  trend?: number
}

/**
 * 集群性能指标类型
 */
export interface ClusterHealth {
  /** 整体状态: healthy/warning/critical */
  status: string
  /** 性能评分（0-100） */
  score?: number
  /** 性能状态详细分析 */
  analysis?: string
  /** CPU 平均使用率百分比 */
  cpu_usage_pct?: number
  /** 内存平均使用率百分比 */
  memory_usage_pct?: number
  /** 磁盘平均使用率百分比 */
  disk_usage_pct?: number
  /** 带宽平均使用率百分比 */
  network_bandwidth_pct?: number
  /** 系统平均负载 */
  load_average?: number
  /** 网络流量（Mbps） */
  network_traffic?: number
  /** 错误率百分比 */
  error_rate?: number
  /** 瓶颈数量 */
  bottleneck_count?: number
  /** 高优先级瓶颈数量 */
  high_count?: number
  /** 中优先级瓶颈数量 */
  medium_count?: number
  /** 低优先级瓶颈数量 */
  low_count?: number
  /** CPU 详细统计 */
  cpu_stats?: MetricStats
  /** 内存详细统计 */
  memory_stats?: MetricStats
  /** 磁盘详细统计 */
  disk_stats?: MetricStats
  /** 网络详细统计 */
  network_stats?: Record<string, any>
  /** 负载详细统计 */
  load_stats?: MetricStats
  /** 分析时间段 */
  analysis_period?: string
  /** 时间戳 */
  timestamp?: string
}

/**
 * 完整性能分析报告类型
 */
export interface PerformanceReport {
  /** 报告唯一标识符 */
  id: string
  /** 创建时间 */
  created_at: string
  /** 分析时长（小时） */
  analysis_period_hours: number
  /** 命名空间，为 null 表示全集群 */
  namespace: string | null
  /** 报告状态: completed/basic/failed/analyzing */
  status: string
  /** 报告摘要 */
  summary: string
  /** 集群性能指标 */
  cluster_health: ClusterHealth | null
  /** 性能瓶颈列表 */
  bottlenecks: PerformanceBottleneck[]
  /** 业务趋势列表 */
  trends: BusinessTrend[]
  /** 优化建议列表 */
  suggestions: OptimizationSuggestion[]
  /** 原始摘要（未格式化） */
  raw_summary: string | null
}

/**
 * 分析任务触发请求类型
 */
export interface AnalysisTriggerRequest {
  /** 分析时长（小时），默认 24 小时 */
  analysis_period_hours?: number
  /** 命名空间，不填则分析全集群 */
  namespace?: string | null
}

/**
 * 分析任务状态类型
 */
export interface AnalysisTaskStatus {
  /** 任务唯一标识符 */
  task_id: string
  /** 任务状态: queued/running/completed/failed */
  status: string
  /** 任务进度（0-100） */
  progress: number
  /** 创建时间 */
  created_at: string
  /** 更新时间 */
  updated_at: string
  /** 生成的报告 ID（任务完成时） */
  report_id: string | null
  /** 错误信息（任务失败时） */
  error_message: string | null
}

/**
 * 报告列表响应类型
 */
export interface ReportListResponse {
  /** 总报告数 */
  total: number
  /** 当前页码 */
  page: number
  /** 每页数量 */
  page_size: number
  /** 报告列表 */
  reports: PerformanceReport[]
}

/**
 * 定时任务配置类型
 */
export interface ScheduleConfig {
  /** 是否启用定时任务 */
  enabled: boolean
  /** 执行时间（小时，0-23），默认凌晨 2 点 */
  hour: number
  /** 执行时间（分钟，0-59），默认 0 分 */
  minute: number
  /** 分析时长（小时），默认 24 小时 */
  analysis_period_hours: number
}

/**
 * 定时任务状态类型
 */
export interface ScheduleStatus {
  /** 定时任务是否正在运行 */
  is_running: boolean
  /** 下次执行时间 */
  next_run: string | null
  /** 定时配置 */
  config: ScheduleConfig
  /** 配置文件路径 */
  config_file?: string
}

/**
 * 业务分析 API 调用模块
 */
export const analysisApi = {
  /**
   * 触发分析任务
   * @param data 分析触发请求参数
   * @returns 包含 task_id 的响应
   */
  triggerAnalysis: (data: AnalysisTriggerRequest) => {
    return request.post<any, ApiResponse<{ task_id: string }>>('/v1/analysis/trigger', data)
  },

  /**
   * 查询任务状态
   * @param taskId 任务唯一标识符
   * @returns 任务状态信息
   */
  getTaskStatus: (taskId: string) => {
    return request.get<any, ApiResponse<AnalysisTaskStatus>>(`/v1/analysis/task/${taskId}`)
  },

  /**
   * 查询最近一次任务状态
   * @returns 最近任务状态信息
   */
  getLatestTask: () => {
    return request.get<any, ApiResponse<AnalysisTaskStatus>>('/v1/analysis/task/latest')
  },

  /**
   * 分页查询报告列表
   * @param page 页码，默认 1
   * @param pageSize 每页数量，默认 10
   * @returns 分页报告列表
   */
  getReports: (page?: number, pageSize?: number) => {
    const params: Record<string, number> = {}
    if (page !== undefined) {
      params.page = page
    }
    if (pageSize !== undefined) {
      params.page_size = pageSize
    }
    return request.get<any, ApiResponse<ReportListResponse>>('/v1/analysis/reports', { params })
  },

  /**
   * 获取报告详情
   * @param reportId 报告唯一标识符
   * @returns 报告详情
   */
  getReport: (reportId: string) => {
    return request.get<any, ApiResponse<PerformanceReport>>(`/v1/analysis/reports/${reportId}`)
  },

  /**
   * 删除报告
   * @param reportId 报告唯一标识符
   * @returns 删除结果
   */
  deleteReport: (reportId: string) => {
    return request.delete<any, ApiResponse<{ report_id: string }>>(`/v1/analysis/reports/${reportId}`)
  },

  /**
   * 获取定时任务状态
   * @returns 定时任务状态
   */
  getScheduleStatus: () => {
    return request.get<any, ApiResponse<ScheduleStatus>>('/v1/analysis/schedule/status')
  },

  /**
   * 启动定时任务
   * @returns 启动结果
   */
  startSchedule: () => {
    return request.post<any, ApiResponse<{ success: boolean }>>('/v1/analysis/schedule/start')
  },

  /**
   * 停止定时任务
   * @returns 停止结果
   */
  stopSchedule: () => {
    return request.post<any, ApiResponse<{ success: boolean }>>('/v1/analysis/schedule/stop')
  },

  /**
   * 更新定时配置
   * @param config 定时配置
   * @returns 更新后的配置
   */
  updateScheduleConfig: (config: ScheduleConfig) => {
    return request.put<any, ApiResponse<ScheduleConfig>>('/v1/analysis/schedule/config', config)
  }
}

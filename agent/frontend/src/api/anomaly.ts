import request from './request'
import type { ApiResponse, AnomalyAnalysis } from '../types/api'

export const anomalyApi = {
  // 获取异常分析详情
  getAnalysis: (anomalyId: string) => {
    return request.get<any, ApiResponse<AnomalyAnalysis>>(`/v1/anomalies/${anomalyId}/analysis`)
  },

  // 触发异常分析
  triggerAnalysis: (anomalyId: string) => {
    return request.post<any, ApiResponse<any>>(`/v1/anomalies/${anomalyId}/analyze`)
  },

  // 获取异常分析状态
  getAnalysisStatus: (anomalyId: string) => {
    return request.get<any, ApiResponse<{ anomaly_id: string; status: string }>>(
      `/v1/anomalies/${anomalyId}/analysis/status`
    )
  },

  // 获取分析器整体状态
  getAnalyzerStatus: () => {
    return request.get<any, ApiResponse<any>>('/v1/anomalies/analysis/status')
  }
}

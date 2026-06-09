import request from './request'
import type { ApiResponse, PollingStatus, PollingResponse, PollingRecord, PollingStartRequest, HistoryQueryResponse } from '../types/api'

export const pollingApi = {
  start: (data: PollingStartRequest) => {
    return request.post<any, ApiResponse<PollingResponse>>('/v1/polling/start', data)
  },

  stop: () => {
    return request.post<any, ApiResponse<PollingResponse>>('/v1/polling/stop')
  },

  status: () => {
    return request.get<any, ApiResponse<PollingResponse>>('/v1/polling/status')
  },

  runOnce: () => {
    return request.post<any, ApiResponse<PollingResponse>>('/v1/polling/run-once')
  },

  history: (limit: number = 20) => {
    return request.get<any, ApiResponse<HistoryQueryResponse>>('/v1/polling/history', {
      params: { limit }
    })
  },

  clearHistory: () => {
    return request.delete<any, ApiResponse<any>>('/v1/polling/history')
  }
}

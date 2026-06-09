import request from './request'
import type { ApiResponse, MonitorRequest, MonitorResponse } from '../types/api'

export const monitorApi = {
  run: (data: MonitorRequest) => {
    return request.post<any, ApiResponse<MonitorResponse>>('/v1/monitor/run', data)
  },

  quick: (namespace?: string) => {
    const params = namespace ? { namespace } : {}
    return request.get<any, ApiResponse<MonitorResponse>>('/v1/monitor/quick', { params })
  }
}

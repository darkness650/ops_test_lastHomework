import request from './request'
import type { HealthResponse } from '../types/api'

export const healthApi = {
  check: () => {
    return request.get<any, HealthResponse>('/health')
  }
}

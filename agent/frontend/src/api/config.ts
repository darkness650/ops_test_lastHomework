import request from './request'
import type { ApiResponse, ConfigInfo } from '../types/api'

export const configApi = {
  getConfig: () => {
    return request.get<any, ApiResponse<ConfigInfo>>('/v1/config')
  }
}

import request from './request'
import type { ApiResponse, ChatRequest, ChatResponse } from '../types/api'

export const chatApi = {
  sendMessage: (data: ChatRequest) => {
    return request.post<any, ApiResponse<ChatResponse>>('/v1/chat', data)
  },

  getSession: (contextId: string) => {
    return request.get<any, ApiResponse<any>>(`/v1/chat/sessions/${contextId}`)
  },

  clearSession: (contextId: string) => {
    return request.delete<any, ApiResponse<any>>(`/v1/chat/sessions/${contextId}`)
  }
}

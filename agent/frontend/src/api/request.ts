import axios from 'axios'
import { ElMessage } from 'element-plus'

const request = axios.create({
  baseURL: '/api',
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json'
  }
})

request.interceptors.request.use(
  (config) => {
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

request.interceptors.response.use(
  (response) => {
    const data = response.data
    return data
  },
  (error) => {
    if (error.response) {
      const { status, data } = error.response
      const message = data?.detail || data?.message || `请求失败 (${status})`
      
      if (status === 404 || status === 409) {
        console.warn(`请求 ${status}: ${message}`)
      } else {
        ElMessage.error(message)
      }
    } else if (error.request) {
      ElMessage.error('网络错误，请检查网络连接')
    } else {
      ElMessage.error(error.message || '请求失败')
    }
    return Promise.reject(error)
  }
)

export default request

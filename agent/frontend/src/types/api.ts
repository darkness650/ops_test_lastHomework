export interface ApiResponse<T = unknown> {
  code: number
  message: string
  data: T
}

export interface HealthResponse {
  status: string
}

export type ClusterStatus = 'normal' | 'warning' | 'critical' | 'error'

export interface AnomalyInfo {
  id: string
  type: string
  target: string
  severity: 'critical' | 'high' | 'medium' | 'low'
  description: string
  evidence: string[]
  timestamp: string
  analysis_status: 'pending' | 'analyzing' | 'completed' | 'failed'
}

export interface RootCauseAnalysis {
  category: string
  analysis: string
  evidence: string[]
  confidence: number
}

export interface RecoveryStep {
  order: number
  action: string
  risk: 'low' | 'medium' | 'high'
  description: string
  validation?: string
}

export interface RecoveryPlan {
  steps: RecoveryStep[]
  precautions: string[]
  estimated_time?: string
}

export interface AnomalyAnalysis {
  anomaly_id: string
  root_cause?: RootCauseAnalysis
  recovery_plan?: RecoveryPlan
  status: 'pending' | 'analyzing' | 'completed' | 'failed'
  error_message?: string
  created_at: string
  completed_at?: string
}

export interface MonitorResponse {
  status: ClusterStatus
  summary: string
  anomaly_count: number
  anomalies: AnomalyInfo[]
  timestamp: string
}

export interface MonitorRequest {
  namespace?: string
  deep_analysis?: boolean
}

export interface ChatRequest {
  message: string
  context_id?: string
}

export interface ChatResponse {
  response: string
  context_id: string
  anomalies?: AnomalyInfo[]
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  toolCalls?: ToolCall[]
}

export interface ToolCall {
  name: string
  status: 'running' | 'success' | 'error'
  result?: unknown
}

export interface PollingStatus {
  is_running: boolean
  interval_minutes: number
  execution_count: number
  history_count?: number
  next_run?: string
  last_run?: string
}

export interface PollingResponse {
  success: boolean
  message: string
  status?: PollingStatus
}

export interface PollingStartRequest {
  interval_minutes?: number
  namespace?: string
  deep_analysis?: boolean
}

export interface PollingRecord {
  timestamp: string
  status: string
  summary?: string
  anomaly_count: number
  anomalies: AnomalyInfo[]
  duration_ms: number
  error?: string
}

export interface PollingHistoryStats {
  total: number
  normal: number
  warning: number
  critical: number
  error: number
  latest_timestamp?: string
}

export interface HistoryQueryResponse {
  total: number
  returned: number
  records: PollingRecord[]
  statistics: PollingHistoryStats
}

export interface ConfigInfo {
  llm_configured: boolean
  k8s_configured: boolean
  es_configured: boolean
  prometheus_configured: boolean
  polling_interval_minutes: number
  component_status: {
    k8s: boolean
    logs: boolean
    prometheus: boolean
    llm: boolean
  }
}

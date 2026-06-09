<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useMonitorStore } from '../stores/monitor'
import { usePollingStore } from '../stores/polling'
import { anomalyApi } from '../api'
import type { AnomalyInfo, AnomalyAnalysis } from '../types/api'

const monitorStore = useMonitorStore()
const pollingStore = usePollingStore()

const isRefreshing = ref(false)
const analysisDialogVisible = ref(false)
const selectedAnomaly = ref<AnomalyInfo | null>(null)
const anomalyAnalysis = ref<AnomalyAnalysis | null>(null)
const isLoadingAnalysis = ref(false)
const analysisPollingTimer = ref<number | null>(null)
const isTriggeringAnalysis = ref(false)
const lastTriggerTime = ref(0)

const statusColor = computed(() => {
  const colorMap: Record<string, string> = {
    normal: '#10B981',
    warning: '#F59E0B',
    critical: '#EF4444',
    error: '#EF4444'
  }
  return colorMap[monitorStore.status] || '#EF4444'
})

const statusText = computed(() => {
  const textMap: Record<string, string> = {
    normal: '正常',
    warning: '警告',
    critical: '严重',
    error: '异常'
  }
  return textMap[monitorStore.status] || '异常'
})

async function refresh() {
  isRefreshing.value = true
  await Promise.all([
    monitorStore.quickCheck(),
    pollingStore.fetchStatus()
  ])
  setTimeout(() => {
    isRefreshing.value = false
  }, 500)
}

async function runFullCheck() {
  isRefreshing.value = true
  await monitorStore.runHealthCheck(undefined, true)
  setTimeout(() => {
    isRefreshing.value = false
  }, 500)
}

function formatTime(timestamp: string) {
  if (!timestamp) return '-'
  const date = new Date(timestamp)
  return date.toLocaleString('zh-CN')
}

function getSeverityColor(severity: string) {
  const colorMap: Record<string, string> = {
    critical: '#EF4444',
    high: '#F97316',
    medium: '#F59E0B',
    low: '#3B82F6'
  }
  return colorMap[severity] || '#6B7280'
}

function getAnalysisStatusText(status: string) {
  const statusMap: Record<string, string> = {
    pending: '等待分析',
    analyzing: '分析中...',
    completed: '分析完成',
    failed: '分析失败'
  }
  return statusMap[status] || status
}

function getAnalysisStatusColor(status: string) {
  const colorMap: Record<string, string> = {
    pending: '#9CA3AF',
    analyzing: '#3B82F6',
    completed: '#10B981',
    failed: '#EF4444'
  }
  return colorMap[status] || '#6B7280'
}

function getRiskColor(risk: string) {
  const colorMap: Record<string, string> = {
    low: '#10B981',
    medium: '#F59E0B',
    high: '#EF4444'
  }
  return colorMap[risk] || '#6B7280'
}

const canTriggerAnalysis = computed(() => {
  if (isTriggeringAnalysis.value) {
    return false
  }

  if (anomalyAnalysis.value) {
    const status = anomalyAnalysis.value.status
    if (status === 'pending' || status === 'analyzing') {
      return false
    }
  }

  if (selectedAnomaly.value) {
    const status = selectedAnomaly.value.analysis_status
    if (status === 'pending' || status === 'analyzing') {
      return false
    }
  }

  return true
})

async function loadAnomalyAnalysis(anomaly: AnomalyInfo) {
  if (!anomaly || !anomaly.id) {
    return
  }

  isLoadingAnalysis.value = true
  anomalyAnalysis.value = null

  try {
    const response = await anomalyApi.getAnalysis(anomaly.id)
    if (response.code === 200 && response.data) {
      anomalyAnalysis.value = response.data

      // 如果分析还在进行中，开始轮询状态
      if (response.data.status === 'pending' || response.data.status === 'analyzing') {
        startAnalysisPolling(anomaly.id)
      }
    }
  } catch (error: any) {
    // 如果 404，说明分析记录不存在
    if (error.response?.status === 404) {
      // 检查异常状态，如果正在分析中，直接显示正在分析的界面
      const anomalyStatus = anomaly.analysis_status
      if (anomalyStatus === 'pending' || anomalyStatus === 'analyzing') {
        // 正在分析中，构造一个临时的分析对象显示"分析中"状态
        anomalyAnalysis.value = {
          anomaly_id: anomaly.id,
          status: anomalyStatus,
          created_at: new Date().toISOString(),
          root_cause: null,
          recovery_plan: null,
          error_message: null,
          completed_at: null,
        }
        startAnalysisPolling(anomaly.id)
        ElMessage.info('该异常正在分析中，请稍候...')
      } else {
        // 不在分析中，尝试触发分析
        await triggerManualAnalysis(anomaly)
      }
    } else {
      ElMessage.error('获取分析详情失败')
      console.error('Load analysis error:', error)
    }
  } finally {
    isLoadingAnalysis.value = false
  }
}

async function triggerManualAnalysis(anomaly: AnomalyInfo) {
  // 防抖检查 1：时间戳防抖（1 秒内不允许重复触发）
  const now = Date.now()
  if (now - lastTriggerTime.value < 1000) {
    ElMessage.warning('操作过于频繁，请稍后再试')
    return
  }

  // 防抖检查 2：状态检查
  if (!canTriggerAnalysis.value) {
    ElMessage.warning('该异常正在分析中，请等待完成后再重试')
    return
  }

  // 更新时间戳
  lastTriggerTime.value = now

  // 防抖检查 3：请求中双重检查（防止快速点击）
  if (isTriggeringAnalysis.value) {
    ElMessage.warning('正在提交分析任务，请稍候...')
    return
  }

  isTriggeringAnalysis.value = true

  try {
    const response = await anomalyApi.triggerAnalysis(anomaly.id)
    if (response.code === 202) {
      ElMessage.success('分析任务已提交，正在后台执行...')
      startAnalysisPolling(anomaly.id)
    }
  } catch (error: any) {
    if (error.response?.status === 409) {
      ElMessage.warning(error.response.data?.detail || '该异常正在分析中，请等待完成后再重试')
    } else {
      ElMessage.error('触发分析失败')
      console.error('Trigger analysis error:', error)
    }
  } finally {
    isTriggeringAnalysis.value = false
  }
}

function startAnalysisPolling(anomalyId: string) {
  // 清除之前的定时器
  stopAnalysisPolling()

  // 每 2 秒检查一次状态
  analysisPollingTimer.value = window.setInterval(async () => {
    try {
      const response = await anomalyApi.getAnalysisStatus(anomalyId)
      if (response.code === 200 && response.data) {
        const status = response.data.status as AnomalyAnalysis['status']

        if (status === 'completed' || status === 'failed') {
          // 分析完成或失败，重新加载完整数据
          stopAnalysisPolling()
          // 同时更新异常列表中的分析状态
          if (selectedAnomaly.value) {
            selectedAnomaly.value.analysis_status = status
          }
          await loadAnomalyAnalysisComplete(anomalyId)
        } else if (anomalyAnalysis.value) {
          // 更新分析状态
          anomalyAnalysis.value.status = status
          // 同时更新异常列表中的分析状态
          if (selectedAnomaly.value) {
            selectedAnomaly.value.analysis_status = status
          }
        }
      }
    } catch (error) {
      console.error('Poll analysis status error:', error)
    }
  }, 2000)
}

function stopAnalysisPolling() {
  if (analysisPollingTimer.value) {
    clearInterval(analysisPollingTimer.value)
    analysisPollingTimer.value = null
  }
}

async function loadAnomalyAnalysisComplete(anomalyId: string) {
  try {
    const response = await anomalyApi.getAnalysis(anomalyId)
    if (response.code === 200 && response.data) {
      anomalyAnalysis.value = response.data
    }
  } catch (error) {
    console.error('Load complete analysis error:', error)
  }
}

async function handleAnomalyClick(anomaly: AnomalyInfo) {
  selectedAnomaly.value = anomaly
  analysisDialogVisible.value = true
  await loadAnomalyAnalysis(anomaly)
}

function closeAnalysisDialog() {
  analysisDialogVisible.value = false
  selectedAnomaly.value = null
  anomalyAnalysis.value = null
  stopAnalysisPolling()
}

onMounted(() => {
  refresh()
})
</script>

<template>
  <div class="dashboard">
    <div class="dashboard-header">
      <h1 class="title">集群概览</h1>
      <div class="header-actions">
        <el-button @click="refresh" :loading="isRefreshing">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
        <el-button type="primary" @click="runFullCheck" :loading="isRefreshing">
          深度检查
        </el-button>
      </div>
    </div>

    <el-row :gutter="20" class="status-cards">
      <el-col :xs="24" :sm="12" :md="6">
        <div class="status-card" :style="{ background: `linear-gradient(135deg, ${statusColor}22, ${statusColor}11)` }">
          <div class="card-icon" :style="{ color: statusColor }">
            <el-icon size="32"><Monitor /></el-icon>
          </div>
          <div class="card-content">
            <div class="card-value" :style="{ color: statusColor }">{{ statusText }}</div>
            <div class="card-label">集群状态</div>
          </div>
        </div>
      </el-col>

      <el-col :xs="24" :sm="12" :md="6">
        <div class="status-card">
          <div class="card-icon anomaly-count">
            <el-icon size="32"><Warning /></el-icon>
          </div>
          <div class="card-content">
            <div class="card-value" :class="{ 'has-anomalies': monitorStore.anomalyCount > 0 }">
              {{ monitorStore.anomalyCount }}
            </div>
            <div class="card-label">异常数量</div>
          </div>
        </div>
      </el-col>

      <el-col :xs="24" :sm="12" :md="6">
        <div class="status-card">
          <div class="card-icon polling">
            <el-icon size="32"><Timer /></el-icon>
          </div>
          <div class="card-content">
            <div class="card-value" :class="{ 'is-running': pollingStore.isRunning }">
              {{ pollingStore.isRunning ? '运行中' : '已停止' }}
            </div>
            <div class="card-label">轮询状态</div>
          </div>
        </div>
      </el-col>

      <el-col :xs="24" :sm="12" :md="6">
        <div class="status-card">
          <div class="card-icon interval">
            <el-icon size="32"><Clock /></el-icon>
          </div>
          <div class="card-content">
            <div class="card-value">{{ pollingStore.intervalMinutes }} 分钟</div>
            <div class="card-label">轮询间隔</div>
          </div>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="20" class="content-section">
      <el-col :xs="24" :lg="14">
        <div class="section-card">
          <div class="section-header">
            <h3>异常告警</h3>
            <span v-if="monitorStore.lastUpdated" class="update-time">
              更新于 {{ formatTime(monitorStore.lastUpdated) }}
            </span>
          </div>

          <el-table
            v-if="monitorStore.anomalies.length > 0"
            :data="monitorStore.anomalies"
            style="width: 100%"
            @row-click="handleAnomalyClick"
            class="anomaly-table"
          >
            <el-table-column prop="type" label="类型" min-width="120">
              <template #default="{ row }">
                <el-tooltip :content="row.type" placement="top" effect="light">
                  <el-tag size="small" class="type-tag">{{ row.type }}</el-tag>
                </el-tooltip>
              </template>
            </el-table-column>
            <el-table-column prop="target" label="资源" width="180" />
            <el-table-column prop="description" label="描述" />
            <el-table-column prop="severity" label="严重程度" width="100">
              <template #default="{ row }">
                <el-tag :style="{ backgroundColor: getSeverityColor(row.severity) + '20', color: getSeverityColor(row.severity), borderColor: getSeverityColor(row.severity) + '50' }" size="small">
                  {{ row.severity }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="analysis_status" label="分析状态" width="100">
              <template #default="{ row }">
                <el-tag 
                  :style="{ 
                    backgroundColor: getAnalysisStatusColor(row.analysis_status) + '20', 
                    color: getAnalysisStatusColor(row.analysis_status), 
                    borderColor: getAnalysisStatusColor(row.analysis_status) + '50' 
                  }" 
                  size="small"
                >
                  {{ getAnalysisStatusText(row.analysis_status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="80">
              <template #default="{ row }">
                <el-button type="primary" link size="small" @click.stop="handleAnomalyClick(row)">
                  查看详情
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <div v-else class="empty-state">
            <el-icon size="48" style="color: #10B981"><CircleCheck /></el-icon>
            <p>暂无异常</p>
          </div>
        </div>
      </el-col>

      <el-col :xs="24" :lg="10">
        <div class="section-card">
          <div class="section-header">
            <h3>系统配置</h3>
          </div>

          <el-descriptions :column="1" border>
            <el-descriptions-item label="Kubernetes">
              <el-tag :type="pollingStore.status ? 'success' : 'danger'">
                {{ pollingStore.status ? '已连接' : '未连接' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="轮询调度">
              <el-tag :type="pollingStore.isRunning ? 'success' : 'warning'">
                {{ pollingStore.isRunning ? '运行中' : '已停止' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="历史记录">
              {{ pollingStore.historyCount }} 条
            </el-descriptions-item>
            <el-descriptions-item label="上次轮询">
              {{ pollingStore.status?.last_run ? formatTime(pollingStore.status.last_run) : '无记录' }}
            </el-descriptions-item>
          </el-descriptions>
        </div>
      </el-col>
    </el-row>

    <!-- 异常分析详情弹窗 -->
    <el-dialog
      v-model="analysisDialogVisible"
      title="异常详情分析"
      width="800px"
      :close-on-click-modal="false"
      @close="closeAnalysisDialog"
    >
      <div v-if="selectedAnomaly" class="anomaly-detail-header">
        <el-alert
          :type="selectedAnomaly.severity === 'critical' || selectedAnomaly.severity === 'high' ? 'error' : 'warning'"
          :closable="false"
          show-icon
        >
          <template #title>
            <strong>{{ selectedAnomaly.type }}</strong> - {{ selectedAnomaly.target }}
          </template>
          {{ selectedAnomaly.description }}
        </el-alert>

        <el-descriptions :column="2" border class="mt-4">
          <el-descriptions-item label="严重程度">
            <el-tag :style="{ backgroundColor: getSeverityColor(selectedAnomaly.severity) + '20', color: getSeverityColor(selectedAnomaly.severity) }">
              {{ selectedAnomaly.severity }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="检测时间">
            {{ formatTime(selectedAnomaly.timestamp) }}
          </el-descriptions-item>
          <el-descriptions-item label="分析状态">
            <el-tag 
              :style="{ 
                backgroundColor: getAnalysisStatusColor(selectedAnomaly.analysis_status) + '20', 
                color: getAnalysisStatusColor(selectedAnomaly.analysis_status) 
              }"
            >
              {{ getAnalysisStatusText(selectedAnomaly.analysis_status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="异常ID">
            <el-text type="info" class="monospace">
              {{ selectedAnomaly.id.substring(0, 8) }}...
            </el-text>
          </el-descriptions-item>
        </el-descriptions>

        <div v-if="selectedAnomaly.evidence && selectedAnomaly.evidence.length > 0" class="mt-4">
          <h4 class="section-title">证据</h4>
          <ul class="evidence-list">
            <li v-for="(ev, idx) in selectedAnomaly.evidence" :key="idx">
              {{ ev }}
            </li>
          </ul>
        </div>
      </div>

      <!-- 分析结果 -->
      <div class="analysis-content mt-4">
        <el-skeleton v-if="isLoadingAnalysis" :rows="8" animated />

        <template v-else>
          <!-- 等待分析状态 -->
          <div v-if="anomalyAnalysis && (anomalyAnalysis.status === 'pending' || anomalyAnalysis.status === 'analyzing')" 
               class="analysis-pending">
            <el-empty description="正在分析中，请稍候...">
              <el-icon class="is-loading" size="48">
                <Loading />
              </el-icon>
              <p class="mt-2 text-gray-500">
                AI 正在根据集群状态和日志进行根因分析...
              </p>
            </el-empty>
          </div>

          <!-- 分析失败 -->
          <div v-else-if="anomalyAnalysis && anomalyAnalysis.status === 'failed'" class="analysis-failed">
            <el-alert type="error" :closable="false" show-icon title="分析失败">
              <p>{{ anomalyAnalysis.error_message || '未知错误' }}</p>
              <el-button 
                type="primary" 
                link 
                :disabled="!canTriggerAnalysis" 
                :loading="isTriggeringAnalysis"
                @click="triggerManualAnalysis(selectedAnomaly!)" 
                class="mt-2"
              >
                重新分析
              </el-button>
            </el-alert>
          </div>

          <!-- 分析完成 -->
          <template v-else-if="anomalyAnalysis && anomalyAnalysis.status === 'completed'">
            <!-- 根因分析 -->
            <div v-if="anomalyAnalysis.root_cause" class="root-cause-section">
              <h4 class="section-title">
                <el-icon><Search /></el-icon>
                根因分析
              </h4>
              
              <div class="category-badge mb-3">
                <el-tag type="primary" size="large" effect="light">
                  {{ anomalyAnalysis.root_cause.category }}
                </el-tag>
                <el-tag 
                  :type="anomalyAnalysis.root_cause.confidence >= 0.8 ? 'success' : anomalyAnalysis.root_cause.confidence >= 0.5 ? 'warning' : 'info'"
                  size="large"
                  effect="light"
                  class="ml-2"
                >
                  置信度: {{ (anomalyAnalysis.root_cause.confidence * 100).toFixed(0) }}%
                </el-tag>
              </div>

              <el-card shadow="never" class="analysis-card">
                <p class="analysis-text">{{ anomalyAnalysis.root_cause.analysis }}</p>

                <div v-if="anomalyAnalysis.root_cause.evidence && anomalyAnalysis.root_cause.evidence.length > 0" class="mt-3">
                  <h5 class="subsection-title">证据</h5>
                  <ul class="evidence-list">
                    <li v-for="(ev, idx) in anomalyAnalysis.root_cause.evidence" :key="idx">
                      {{ ev }}
                    </li>
                  </ul>
                </div>
              </el-card>
            </div>

            <!-- 恢复建议 -->
            <div v-if="anomalyAnalysis.recovery_plan" class="recovery-section mt-6">
              <h4 class="section-title">
                <el-icon><Tools /></el-icon>
                故障恢复建议
              </h4>

              <el-timeline>
                <el-timeline-item
                  v-for="step in anomalyAnalysis.recovery_plan.steps"
                  :key="step.order"
                  :timestamp="`步骤 ${step.order}`"
                  placement="top"
                >
                  <el-card shadow="hover" class="step-card">
                    <div class="step-header">
                      <h5>{{ step.action }}</h5>
                      <el-tag 
                        :style="{ backgroundColor: getRiskColor(step.risk) + '20', color: getRiskColor(step.risk) }"
                        size="small"
                      >
                        风险: {{ step.risk }}
                      </el-tag>
                    </div>
                    <p class="step-description mt-2">{{ step.description }}</p>
                    <div v-if="step.validation" class="step-validation mt-2">
                      <el-tag type="info" effect="light">验证步骤</el-tag>
                      <span class="ml-2 text-sm text-gray-600">{{ step.validation }}</span>
                    </div>
                  </el-card>
                </el-timeline-item>
              </el-timeline>

              <div v-if="anomalyAnalysis.recovery_plan.precautions && anomalyAnalysis.recovery_plan.precautions.length > 0" class="mt-4">
                <el-alert type="warning" :closable="false" show-icon title="注意事项">
                  <ul class="precautions-list">
                    <li v-for="(p, idx) in anomalyAnalysis.recovery_plan.precautions" :key="idx">
                      {{ p }}
                    </li>
                  </ul>
                </el-alert>
              </div>

              <div v-if="anomalyAnalysis.recovery_plan.estimated_time" class="mt-3">
                <el-text type="info">
                  预计恢复时间: {{ anomalyAnalysis.recovery_plan.estimated_time }}
                </el-text>
              </div>
            </div>

            <!-- 无分析结果 -->
            <div v-else class="no-analysis-result">
              <el-empty description="暂未获取到分析结果">
                <el-button 
                  type="primary" 
                  :disabled="!canTriggerAnalysis" 
                  :loading="isTriggeringAnalysis"
                  @click="triggerManualAnalysis(selectedAnomaly!)"
                >
                  重新分析
                </el-button>
              </el-empty>
            </div>
          </template>

          <!-- 无分析记录 -->
          <div v-else class="no-analysis-record">
            <el-empty description="暂无分析记录">
              <el-button 
                type="primary" 
                :disabled="!canTriggerAnalysis" 
                :loading="isTriggeringAnalysis"
                @click="triggerManualAnalysis(selectedAnomaly!)"
              >
                触发分析
              </el-button>
            </el-empty>
          </div>
        </template>
      </div>

      <template #footer>
        <el-button @click="closeAnalysisDialog">关闭</el-button>
        <el-button 
          v-if="anomalyAnalysis && anomalyAnalysis.status !== 'analyzing' && anomalyAnalysis.status !== 'pending'"
          type="primary" 
          :disabled="!canTriggerAnalysis" 
          :loading="isTriggeringAnalysis"
          @click="triggerManualAnalysis(selectedAnomaly!)"
        >
          重新分析
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.dashboard {
  padding: 20px;
}

.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.title {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  color: #1f2937;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.status-cards {
  margin-bottom: 20px;
}

.status-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  background: linear-gradient(135deg, #f8fafc, #f1f5f9);
  border-radius: 12px;
  transition: transform 0.2s, box-shadow 0.2s;
  margin-bottom: 20px;
}

.status-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
}

.card-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 60px;
  height: 60px;
  border-radius: 12px;
  background: rgba(59, 130, 246, 0.1);
  color: #3b82f6;
}

.card-icon.anomaly-count {
  background: rgba(245, 158, 11, 0.1);
  color: #f59e0b;
}

.card-icon.polling {
  background: rgba(16, 185, 129, 0.1);
  color: #10b981;
}

.card-icon.interval {
  background: rgba(139, 92, 246, 0.1);
  color: #8b5cf6;
}

.card-content {
  flex: 1;
}

.card-value {
  font-size: 28px;
  font-weight: 700;
  color: #1f2937;
  line-height: 1.2;
}

.card-value.has-anomalies {
  color: #ef4444;
}

.card-value.is-running {
  color: #10b981;
}

.card-label {
  font-size: 14px;
  color: #6b7280;
  margin-top: 4px;
}

.content-section {
  margin-top: 20px;
}

.section-card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  margin-bottom: 20px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.section-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
}

.update-time {
  font-size: 12px;
  color: #9ca3af;
}

.empty-state {
  text-align: center;
  padding: 40px;
  color: #9ca3af;
}

.empty-state p {
  margin: 12px 0 0;
  font-size: 14px;
}

.type-tag {
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.anomaly-table {
  cursor: pointer;
}

.anomaly-table :deep(.el-table__row:hover) {
  background-color: #f0f9ff !important;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
  margin: 0 0 12px 0;
}

.subsection-title {
  font-size: 14px;
  font-weight: 600;
  color: #374151;
  margin: 0 0 8px 0;
}

.evidence-list {
  margin: 0;
  padding-left: 20px;
}

.evidence-list li {
  margin-bottom: 4px;
  color: #6b7280;
  font-size: 14px;
}

.precautions-list {
  margin: 0;
  padding-left: 20px;
}

.precautions-list li {
  margin-bottom: 4px;
  color: #92400e;
  font-size: 14px;
}

.analysis-card {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
}

.analysis-text {
  margin: 0;
  line-height: 1.6;
  color: #374151;
}

.step-card {
  margin-bottom: 8px;
}

.step-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.step-header h5 {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: #1f2937;
}

.step-description {
  margin: 0;
  color: #6b7280;
  line-height: 1.5;
}

.monospace {
  font-family: monospace;
}

.mt-2 {
  margin-top: 8px;
}

.mt-3 {
  margin-top: 12px;
}

.mt-4 {
  margin-top: 16px;
}

.mt-6 {
  margin-top: 24px;
}

.ml-2 {
  margin-left: 8px;
}

.text-gray-500 {
  color: #6b7280;
}

.text-gray-600 {
  color: #4b5563;
}

.text-sm {
  font-size: 13px;
}
</style>

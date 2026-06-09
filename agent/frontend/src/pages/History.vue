<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessageBox, ElMessage } from 'element-plus'
import { usePollingStore } from '../stores/polling'
import { anomalyApi } from '../api'
import type { AnomalyInfo, AnomalyAnalysis } from '../types/api'

const pollingStore = usePollingStore()

const selectedRecord = ref<number | null>(null)

// 异常分析相关状态
const analysisDialogVisible = ref(false)
const selectedAnomaly = ref<AnomalyInfo | null>(null)
const anomalyAnalysis = ref<AnomalyAnalysis | null>(null)
const isLoadingAnalysis = ref(false)
const analysisPollingTimer = ref<number | null>(null)

function formatTime(timestamp: string) {
  if (!timestamp) return '-'
  const date = new Date(timestamp)
  return date.toLocaleString('zh-CN')
}

function getStatusColor(status: string) {
  const colorMap: Record<string, string> = {
    normal: '#10B981',
    warning: '#F59E0B',
    critical: '#EF4444',
    error: '#EF4444'
  }
  return colorMap[status] || '#6B7280'
}

function getStatusType(status: string) {
  const typeMap: Record<string, 'success' | 'warning' | 'danger' | 'info'> = {
    normal: 'success',
    warning: 'warning',
    critical: 'danger',
    error: 'danger'
  }
  return typeMap[status] || 'info'
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

function toggleRecord(index: number) {
  selectedRecord.value = selectedRecord.value === index ? null : index
}

async function refresh() {
  await pollingStore.fetchHistory(20)
  await pollingStore.fetchStatus()
}

async function clearHistory() {
  await ElMessageBox.confirm(
    '确定要清空所有历史记录吗？此操作不可恢复。',
    '清空历史记录',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    const success = await pollingStore.clearHistory()
    if (success) {
      ElMessage.success('历史记录已清空')
    }
  }).catch(() => {
    // 用户取消
  })
}

async function runOnce() {
  const success = await pollingStore.runOnce()
  if (success) {
    ElMessage.success('单次轮询已执行')
  }
}

// 异常分析相关函数
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
      // 历史记录中的异常不允许重新分析，直接显示"暂无分析记录"
      ElMessage.info('该历史异常暂无分析记录')
    } else {
      ElMessage.error('获取分析详情失败')
      console.error('Load analysis error:', error)
    }
  } finally {
    isLoadingAnalysis.value = false
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
  stopAnalysisPolling()
  anomalyAnalysis.value = null
  selectedAnomaly.value = null
}

onMounted(() => {
  refresh()
})
</script>

<template>
  <div class="history-page">
    <div class="page-header">
      <h1 class="title">轮询历史</h1>
      <div class="header-actions">
        <el-button @click="runOnce" :loading="pollingStore.isActionLoading">
          <el-icon><VideoPlay /></el-icon>
          立即轮询
        </el-button>
        <el-button @click="refresh" :loading="pollingStore.isLoading">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
        <el-button type="danger" plain @click="clearHistory" :disabled="pollingStore.history.length === 0">
          <el-icon><Delete /></el-icon>
          清空历史
        </el-button>
      </div>
    </div>

    <div class="content">
      <div class="status-panel">
        <el-descriptions :column="3" border>
          <el-descriptions-item label="轮询状态">
            <el-tag :type="pollingStore.isRunning ? 'success' : 'info'">
              {{ pollingStore.isRunning ? '运行中' : '已停止' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="轮询间隔">
            {{ pollingStore.intervalMinutes }} 分钟
          </el-descriptions-item>
          <el-descriptions-item label="历史记录">
            {{ pollingStore.historyCount }} 条
          </el-descriptions-item>
        </el-descriptions>
      </div>

      <div class="timeline-section">
        <h3>历史记录</h3>

        <div v-if="pollingStore.isLoading" class="loading-state">
          <el-skeleton :rows="5" animated />
        </div>

        <div v-else-if="pollingStore.history.length === 0" class="empty-state">
          <el-icon size="48" style="color: #9ca3af"><Document /></el-icon>
          <p>暂无轮询历史记录</p>
          <el-button type="primary" @click="runOnce">
            立即执行一次轮询
          </el-button>
        </div>

        <div v-else class="timeline">
          <el-timeline>
            <el-timeline-item
              v-for="(record, index) in pollingStore.history"
              :key="index"
              :timestamp="formatTime(record.timestamp)"
              :type="getStatusType(record.status)"
              @click="toggleRecord(index)"
              class="timeline-item"
            >
              <el-card :shadow="selectedRecord === index ? 'always' : 'hover'" class="record-card">
                <div class="record-header">
                  <div class="record-info">
                    <el-tag :type="getStatusType(record.status)" size="large">
                      {{ record.status }}
                    </el-tag>
                    <span class="anomaly-count" :class="{ 'has-anomalies': record.anomaly_count > 0 }">
                      {{ record.anomaly_count }} 个异常
                    </span>
                  </div>
                  <span class="duration">
                    耗时: {{ record.duration_ms.toFixed(2) }}ms
                  </span>
                </div>

                <el-collapse-transition>
                  <div v-if="selectedRecord === index" class="record-detail">
                    <el-divider />
                    <el-descriptions :column="1" border size="small">
                      <el-descriptions-item label="执行时间">
                        {{ formatTime(record.timestamp) }}
                      </el-descriptions-item>
                      <el-descriptions-item label="状态">
                        <el-tag :type="getStatusType(record.status)">
                          {{ record.status }}
                        </el-tag>
                      </el-descriptions-item>
                      <el-descriptions-item label="异常数量">
                        {{ record.anomaly_count }} 个
                      </el-descriptions-item>
                      <el-descriptions-item label="执行耗时">
                        {{ record.duration_ms.toFixed(2) }} 毫秒
                      </el-descriptions-item>
                      <el-descriptions-item v-if="record.error" label="错误信息">
                        <span class="error-text">{{ record.error }}</span>
                      </el-descriptions-item>
                    </el-descriptions>

                    <div v-if="record.anomaly_count > 0 && record.anomalies && record.anomalies.length > 0" class="anomalies-section">
                      <h4 class="anomalies-title">异常详情</h4>
                      <el-table :data="record.anomalies" size="small" border>
                        <el-table-column prop="type" label="类型" min-width="120">
                          <template #default="{ row }">
                            <el-tooltip :content="row.type" placement="top" effect="light">
                              <el-tag size="small" class="history-type-tag">{{ row.type }}</el-tag>
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
                        <el-table-column label="操作" width="100" fixed="right">
                          <template #default="{ row }">
                            <el-button
                              type="primary"
                              link
                              size="small"
                              @click.stop="handleAnomalyClick(row)"
                            >
                              查看分析
                            </el-button>
                          </template>
                        </el-table-column>
                      </el-table>
                    </div>
                  </div>
                </el-collapse-transition>
              </el-card>
            </el-timeline-item>
          </el-timeline>
        </div>
      </div>
    </div>

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
              <p class="mt-2 text-sm text-gray-500">历史记录中的异常不允许重新分析</p>
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
                <p class="text-sm text-gray-500">历史记录中的异常不允许重新分析</p>
              </el-empty>
            </div>
          </template>

          <!-- 无分析记录 -->
          <div v-else class="no-analysis-record">
            <el-empty description="暂无分析记录">
              <p class="text-sm text-gray-500">历史记录中的异常不允许重新分析</p>
            </el-empty>
          </div>
        </template>
      </div>

      <template #footer>
        <el-button @click="closeAnalysisDialog">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.history-page {
  padding: 20px;
}

.page-header {
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

.content {
  max-width: 900px;
  margin: 0 auto;
}

.status-panel {
  margin-bottom: 24px;
}

.timeline-section h3 {
  margin: 0 0 16px 0;
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
}

.loading-state {
  padding: 20px;
  background: white;
  border-radius: 12px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  background: white;
  border-radius: 12px;
  color: #9ca3af;
}

.empty-state p {
  margin: 12px 0 20px 0;
  font-size: 14px;
}

.timeline-item .el-timeline-item__timestamp {
  color: #6b7280;
  font-size: 12px;
}

.record-card {
  cursor: pointer;
  transition: transform 0.2s;
}

.record-card:hover {
  transform: translateX(4px);
}

.record-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.record-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.anomaly-count {
  font-size: 14px;
  color: #6b7280;
}

.anomaly-count.has-anomalies {
  color: #ef4444;
  font-weight: 600;
}

.duration {
  font-size: 12px;
  color: #9ca3af;
}

.record-detail {
  margin-top: 12px;
}

.anomalies-section {
  margin-top: 16px;
}

.anomalies-title {
  margin: 0 0 12px 0;
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
}

.error-text {
  color: #ef4444;
  font-family: monospace;
}

.history-type-tag {
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 异常分析弹窗样式 */
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

.mb-3 {
  margin-bottom: 12px;
}

.text-gray-500 {
  color: #6b7280;
}

.text-gray-600 {
  color: #4b5563;
}

.text-sm {
  font-size: 14px;
}

.category-badge {
  display: flex;
  align-items: center;
}
</style>

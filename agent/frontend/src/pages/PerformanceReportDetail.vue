<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAnalysisStore } from '../stores/analysis'
import type { PerformanceReport } from '../api/analysis'

// ========== 路由和 Store ==========
const route = useRoute()
const router = useRouter()
const analysisStore = useAnalysisStore()

// ========== 状态定义 ==========

// 是否展开原始摘要
const showRawSummary = ref(false)

// ========== 计算属性 ==========

// 当前报告
const report = computed<PerformanceReport | null>(() => analysisStore.currentReport)

// 报告 ID
const reportId = computed(() => route.params.id as string)

// ========== 方法定义 ==========

// 格式化时间
function formatTime(timestamp: string) {
  if (!timestamp) return '-'
  const date = new Date(timestamp)
  return date.toLocaleString('zh-CN')
}

// 获取报告状态颜色
function getReportStatusColor(status: string) {
  const colorMap: Record<string, string> = {
    completed: '#10B981',
    basic: '#10B981',
    analyzing: '#3B82F6',
    failed: '#EF4444'
  }
  return colorMap[status] || '#6B7280'
}

// 获取报告状态文字
function getReportStatusText(status: string) {
  const statusMap: Record<string, string> = {
    completed: '已完成',
    basic: '基础报告',
    analyzing: '分析中',
    failed: '失败'
  }
  return statusMap[status] || status
}

// 获取报告状态标签类型
function getReportStatusTagType(status: string) {
  const typeMap: Record<string, 'success' | 'primary' | 'danger' | 'info'> = {
    completed: 'success',
    basic: 'success',
    analyzing: 'primary',
    failed: 'danger'
  }
  return typeMap[status] || 'info'
}

// 获取瓶颈严重程度颜色
function getBottleneckSeverityColor(severity: string) {
  const colorMap: Record<string, string> = {
    critical: '#EF4444',
    high: '#EF4444',
    medium: '#F59E0B',
    low: '#EAB308'
  }
  return colorMap[severity] || '#6B7280'
}

// 获取瓶颈严重程度文字
function getBottleneckSeverityText(severity: string) {
  const severityMap: Record<string, string> = {
    critical: '极高',
    high: '高',
    medium: '中',
    low: '低'
  }
  return severityMap[severity] || severity
}

// 获取瓶颈类型文字
function getBottleneckTypeText(type: string) {
  const typeMap: Record<string, string> = {
    cpu: 'CPU',
    memory: '内存',
    network: '网络',
    disk: '磁盘 IO'
  }
  return typeMap[type] || type
}

// 获取趋势方向文字
function getTrendDirectionText(direction: string) {
  const directionMap: Record<string, string> = {
    up: '上升',
    down: '下降',
    stable: '稳定'
  }
  return directionMap[direction] || direction
}

// 获取趋势方向颜色
function getTrendDirectionColor(direction: string) {
  const colorMap: Record<string, string> = {
    up: '#10B981',
    down: '#EF4444',
    stable: '#6B7280'
  }
  return colorMap[direction] || '#6B7280'
}

// 获取趋势方向图标
function getTrendDirectionIcon(direction: string) {
  const iconMap: Record<string, string> = {
    up: 'TrendCharts',
    down: 'TrendDown',
    stable: 'Minus'
  }
  return iconMap[direction] || 'Minus'
}

// 获取趋势类型文字
function getTrendTypeText(type: string) {
  const typeMap: Record<string, string> = {
    cpu: 'CPU',
    memory: '内存',
    network: '网络',
    disk: '磁盘',
    overall: '整体',
  }
  return typeMap[type] || ''
}

// 获取优先级颜色
function getPriorityColor(priority: string) {
  const colorMap: Record<string, string> = {
    high: '#EF4444',
    medium: '#F59E0B',
    low: '#EAB308'
  }
  return colorMap[priority] || '#6B7280'
}

// 获取优先级文字
function getPriorityText(priority: string) {
  const priorityMap: Record<string, string> = {
    high: '高',
    medium: '中',
    low: '低'
  }
  return priorityMap[priority] || priority
}

// 返回列表页
function goBack() {
  router.replace({ name: 'PerformanceAnalysis' })
}

// 初始化数据
async function initData() {
  if (reportId.value) {
    await analysisStore.fetchReport(reportId.value)
  }
}

// ========== 生命周期 ==========

onMounted(() => {
  initData()
})
</script>

<template>
  <div class="performance-report-detail">
    <!-- 面包屑导航 -->
    <el-breadcrumb separator="/" class="breadcrumb">
      <el-breadcrumb-item :to="{ name: 'PerformanceAnalysis' }">业务性能分析</el-breadcrumb-item>
      <el-breadcrumb-item>报告详情</el-breadcrumb-item>
    </el-breadcrumb>

    <!-- 返回按钮 -->
    <div class="back-button">
      <el-button @click="goBack" link>
        <el-icon><ArrowLeft /></el-icon>
        返回列表
      </el-button>
    </div>

    <!-- 加载状态 -->
    <div v-if="analysisStore.isLoading" class="loading-container">
      <el-skeleton :rows="8" animated />
    </div>

    <!-- 空状态 -->
    <div v-else-if="!report" class="empty-state">
      <el-icon size="48" style="color: #9ca3af"><Document /></el-icon>
      <p>报告不存在或已被删除</p>
      <el-button type="primary" @click="goBack">返回列表</el-button>
    </div>

    <!-- 报告内容 -->
    <template v-else>
      <!-- 报告基本信息卡片 -->
      <el-card class="info-card">
        <div class="info-header">
          <h2 class="report-title">
            <el-icon><Document /></el-icon>
            性能分析报告
          </h2>
          <el-tag :type="getReportStatusTagType(report.status)" size="large">
            {{ getReportStatusText(report.status) }}
          </el-tag>
        </div>

        <div class="info-grid">
          <div class="info-item">
            <span class="info-label">报告 ID</span>
            <span class="info-value">{{ report.id }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">创建时间</span>
            <span class="info-value">{{ formatTime(report.created_at) }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">分析时长</span>
            <span class="info-value">{{ report.analysis_period_hours ?? report.period_hours ?? '-' }} 小时</span>
          </div>
          <div class="info-item">
            <span class="info-label">命名空间</span>
            <span class="info-value">
              <el-tag v-if="report.namespace" size="small">{{ report.namespace }}</el-tag>
              <span v-else class="text-gray">全集群</span>
            </span>
          </div>
        </div>
      </el-card>

      <!-- 报告摘要 -->
      <el-card class="section-card">
        <template #header>
          <div class="section-header">
            <h3><el-icon><DocumentText /></el-icon> 报告摘要</h3>
          </div>
        </template>

        <div class="summary-content">
          <p class="summary-text">{{ report.summary || '暂无摘要' }}</p>

          <!-- 原始摘要展开/收起 -->
          <div v-if="report.raw_summary" class="raw-summary-section">
            <el-button link @click="showRawSummary = !showRawSummary">
              <el-icon><component :is="showRawSummary ? 'ArrowUp' : 'ArrowDown'" /></el-icon>
              {{ showRawSummary ? '收起原始摘要' : '展开原始摘要' }}
            </el-button>
            <el-collapse-transition>
              <div v-show="showRawSummary" class="raw-summary-content">
                <pre>{{ report.raw_summary }}</pre>
              </div>
            </el-collapse-transition>
          </div>
        </div>
      </el-card>

      <!-- 集群性能指标 -->
      <el-card v-if="report.cluster_health" class="section-card">
        <template #header>
          <div class="section-header">
            <h3><el-icon><TrendCharts /></el-icon> 集群性能指标</h3>
            <el-tag :type="report.cluster_health.status === 'healthy' ? 'success' : report.cluster_health.status === 'warning' ? 'warning' : 'danger'">
              {{ report.cluster_health.status === 'healthy' ? '正常' : report.cluster_health.status === 'warning' ? '警告' : '异常' }}
            </el-tag>
          </div>
        </template>

        <div v-if="report.cluster_health.analysis_period" class="metrics-period">
          <el-icon><Clock /></el-icon>
          <span>分析时段：{{ report.cluster_health.analysis_period }}</span>
        </div>

        <div class="metrics-grid">
          <div class="metrics-item">
            <div class="metrics-header">
              <div class="metrics-label">CPU 平均使用率</div>
              <div class="metrics-value">{{ report.cluster_health?.cpu_usage_pct != null ? report.cluster_health.cpu_usage_pct.toFixed(1) : '-' }}%</div>
            </div>
            <el-progress
              :percentage="report.cluster_health?.cpu_usage_pct ?? 0"
              :color="(report.cluster_health?.cpu_usage_pct ?? 0) > 80 ? '#EF4444' : (report.cluster_health?.cpu_usage_pct ?? 0) > 60 ? '#F59E0B' : '#10B981'"
              :show-text="false"
            />
            <div v-if="report.cluster_health.cpu_stats" class="metrics-details">
              <span>范围：{{ report.cluster_health.cpu_stats.min ?? '-' }}% - {{ report.cluster_health.cpu_stats.max ?? '-' }}%</span>
            </div>
          </div>

          <div class="metrics-item">
            <div class="metrics-header">
              <div class="metrics-label">内存平均使用率</div>
              <div class="metrics-value">{{ report.cluster_health?.memory_usage_pct != null ? report.cluster_health.memory_usage_pct.toFixed(1) : '-' }}%</div>
            </div>
            <el-progress
              :percentage="report.cluster_health?.memory_usage_pct ?? 0"
              :color="(report.cluster_health?.memory_usage_pct ?? 0) > 80 ? '#EF4444' : (report.cluster_health?.memory_usage_pct ?? 0) > 60 ? '#F59E0B' : '#10B981'"
              :show-text="false"
            />
            <div v-if="report.cluster_health.memory_stats" class="metrics-details">
              <span>范围：{{ report.cluster_health.memory_stats.min ?? '-' }}% - {{ report.cluster_health.memory_stats.max ?? '-' }}%</span>
            </div>
          </div>

          <div class="metrics-item">
            <div class="metrics-header">
              <div class="metrics-label">磁盘平均使用率</div>
              <div class="metrics-value">{{ report.cluster_health?.disk_usage_pct != null ? report.cluster_health.disk_usage_pct.toFixed(1) : '-' }}%</div>
            </div>
            <el-progress
              :percentage="report.cluster_health?.disk_usage_pct ?? 0"
              :color="(report.cluster_health?.disk_usage_pct ?? 0) > 80 ? '#EF4444' : (report.cluster_health?.disk_usage_pct ?? 0) > 60 ? '#F59E0B' : '#10B981'"
              :show-text="false"
            />
            <div v-if="report.cluster_health.disk_stats" class="metrics-details">
              <span>范围：{{ report.cluster_health.disk_stats.min ?? '-' }}% - {{ report.cluster_health.disk_stats.max ?? '-' }}%</span>
            </div>
          </div>

          <div class="metrics-item">
            <div class="metrics-header">
              <div class="metrics-label">系统平均负载</div>
              <div class="metrics-value">{{ report.cluster_health?.load_average != null ? report.cluster_health.load_average.toFixed(1) : '-' }}</div>
            </div>
            <el-progress
              :percentage="Math.min((report.cluster_health?.load_average ?? 0) * 10, 100)"
              color="#8B5CF6"
              :show-text="false"
            />
          </div>

          <div class="metrics-item">
            <div class="metrics-header">
              <div class="metrics-label">网络总流量</div>
              <div class="metrics-value">{{ report.cluster_health?.network_traffic != null ? report.cluster_health.network_traffic.toFixed(2) : '-' }} Mbps</div>
            </div>
            <el-progress
              :percentage="Math.min((report.cluster_health?.network_traffic ?? 0), 100)"
              color="#3B82F6"
              :show-text="false"
            />
            <div v-if="report.cluster_health.network_stats" class="metrics-details">
              <span>接收：{{ report.cluster_health.network_stats.receive_avg ?? '-' }} | 发送：{{ report.cluster_health.network_stats.transmit_avg ?? '-' }} Mbps</span>
            </div>
          </div>

          <div class="metrics-item">
            <div class="metrics-header">
              <div class="metrics-label">性能评分</div>
              <div class="metrics-value">{{ report.cluster_health?.score != null ? report.cluster_health.score : '-' }} / 100</div>
            </div>
            <el-progress
              :percentage="report.cluster_health?.score ?? 0"
              :color="(report.cluster_health?.score ?? 0) >= 80 ? '#10B981' : (report.cluster_health?.score ?? 0) >= 50 ? '#F59E0B' : '#EF4444'"
              :show-text="false"
            />
          </div>
        </div>

        <div v-if="report.cluster_health.analysis" class="metrics-analysis">
          <div class="metrics-analysis-title">性能分析</div>
          <p>{{ report.cluster_health.analysis }}</p>
        </div>
      </el-card>

      <!-- 性能瓶颈列表 -->
      <el-card class="section-card">
        <template #header>
          <div class="section-header">
            <h3><el-icon><WarningFilled /></el-icon> 性能瓶颈</h3>
            <span class="count-badge">{{ report.bottlenecks?.length || 0 }} 项</span>
          </div>
        </template>

        <div v-if="!report.bottlenecks || report.bottlenecks.length === 0" class="section-empty">
          <el-icon size="32" style="color: #9ca3af"><CircleCheck /></el-icon>
          <p>未检测到性能瓶颈</p>
        </div>

        <el-table v-else :data="report.bottlenecks" style="width: 100%">
          <el-table-column label="目标资源" prop="target" width="200" />
          <el-table-column label="瓶颈类型" prop="type" width="120">
            <template #default="{ row }">
              {{ getBottleneckTypeText(row.type) }}
            </template>
          </el-table-column>
          <el-table-column label="严重程度" width="100">
            <template #default="{ row }">
              <el-tag :style="{ backgroundColor: getBottleneckSeverityColor(row.severity), borderColor: 'transparent' }" effect="dark" size="small">
                {{ getBottleneckSeverityText(row.severity) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="当前值" width="120">
            <template #default="{ row }">
              {{ row.metric_value }} / {{ row.threshold }}
            </template>
          </el-table-column>
          <el-table-column label="描述" prop="description" min-width="300">
            <template #default="{ row }">
              <el-tooltip :content="row.description" placement="top" effect="light">
                <span class="text-truncate">{{ row.description }}</span>
              </el-tooltip>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <!-- 业务趋势分析 -->
      <el-card class="section-card">
        <template #header>
          <div class="section-header">
            <h3><el-icon><TrendCharts /></el-icon> 业务趋势分析</h3>
            <span class="count-badge">{{ report.trends?.length || 0 }} 项</span>
          </div>
        </template>

        <div v-if="!report.trends || report.trends.length === 0" class="section-empty">
          <el-icon size="32" style="color: #9ca3af"><InfoFilled /></el-icon>
          <p>暂无趋势数据</p>
        </div>

        <div v-else class="trends-container">
          <div v-for="(trend, index) in report.trends" :key="index" class="trend-card">
            <div class="trend-header">
              <div class="trend-title">
                <span class="trend-type">{{ getTrendTypeText(trend.type) }}</span>
                <span class="trend-name">{{ trend.metric_name || trend.target || '未知指标' }}</span>
              </div>
              <el-tag :style="{ backgroundColor: getTrendDirectionColor(trend.direction), borderColor: 'transparent' }" effect="dark" size="small">
                <el-icon><component :is="getTrendDirectionIcon(trend.direction)" /></el-icon>
                {{ getTrendDirectionText(trend.direction) }}
              </el-tag>
            </div>

            <div v-if="trend.start_value != null || trend.end_value != null" class="trend-stats">
              <div class="trend-stat">
                <span class="stat-label">起始值</span>
                <span class="stat-value">{{ trend.start_value != null ? trend.start_value.toFixed(2) : '-' }}</span>
              </div>
              <div class="trend-stat">
                <span class="stat-label">结束值</span>
                <span class="stat-value">{{ trend.end_value != null ? trend.end_value.toFixed(2) : '-' }}</span>
              </div>
              <div class="trend-stat change">
                <span class="stat-label">变化幅度</span>
                <span class="stat-value" :style="{ color: getTrendDirectionColor(trend.direction) }">
                  {{ trend.direction === 'up' ? '+' : '' }}{{ trend.change_percent != null ? trend.change_percent.toFixed(2) : (trend.change_rate != null ? trend.change_rate.toFixed(2) : '-') }}%
                </span>
              </div>
            </div>

            <div v-if="trend.analysis" class="trend-analysis">
              <div class="trend-analysis-title">趋势分析</div>
              <p>{{ trend.analysis }}</p>
            </div>

            <div v-if="trend.prediction" class="trend-prediction">
              <div class="trend-prediction-title">未来预测</div>
              <p>{{ trend.prediction }}</p>
            </div>

            <div v-if="trend.data_points && trend.data_points.length > 0" class="trend-data">
              <span class="data-label">数据点：{{ trend.data_points.length }} 个</span>
            </div>
          </div>
        </div>
      </el-card>

      <!-- 优化建议 -->
      <el-card class="section-card">
        <template #header>
          <div class="section-header">
            <h3><el-icon><LightBulb /></el-icon> 优化建议</h3>
            <span class="count-badge">{{ report.suggestions?.length || 0 }} 项</span>
          </div>
        </template>

        <div v-if="!report.suggestions || report.suggestions.length === 0" class="section-empty">
          <el-icon size="32" style="color: #9ca3af"><InfoFilled /></el-icon>
          <p>暂无优化建议</p>
        </div>

        <div v-else class="suggestions-list">
          <div v-for="(suggestion, index) in report.suggestions" :key="index" class="suggestion-item">
            <div class="suggestion-header">
              <div class="suggestion-meta">
                <el-tag :style="{ backgroundColor: getPriorityColor(suggestion.priority), borderColor: 'transparent' }" effect="dark" size="small">
                  优先级：{{ getPriorityText(suggestion.priority) }}
                </el-tag>
                <el-tag type="info" size="small">
                  {{ suggestion.category || '未分类' }}
                </el-tag>
              </div>
            </div>

            <div class="suggestion-content">
              <p class="suggestion-text">{{ suggestion.suggestion || suggestion.action || suggestion.description || '-' }}</p>
            </div>

            <div v-if="suggestion.impact || suggestion.expected_benefit" class="suggestion-impact">
              <span class="impact-label">预期影响：</span>
              <span class="impact-text">{{ suggestion.impact || suggestion.expected_benefit || '-' }}</span>
            </div>
          </div>
        </div>
      </el-card>
    </template>
  </div>
</template>

<style scoped>
.performance-report-detail {
  padding: 20px;
}

/* 面包屑 */
.breadcrumb {
  margin-bottom: 16px;
}

/* 返回按钮 */
.back-button {
  margin-bottom: 16px;
}

/* 加载容器 */
.loading-container {
  padding: 20px;
}

/* 空状态 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  color: #9ca3af;
}

.empty-state p {
  margin: 16px 0 24px 0;
  font-size: 14px;
}

/* 基本信息卡片 */
.info-card {
  margin-bottom: 20px;
  border-radius: 12px;
}

.info-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.report-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #1f2937;
  display: flex;
  align-items: center;
  gap: 8px;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

@media (min-width: 768px) {
  .info-grid {
    grid-template-columns: repeat(4, 1fr);
  }
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-label {
  font-size: 12px;
  color: #6b7280;
}

.info-value {
  font-size: 14px;
  color: #1f2937;
  font-weight: 500;
}

/* 通用区块卡片 */
.section-card {
  margin-bottom: 20px;
  border-radius: 12px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.section-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
  display: flex;
  align-items: center;
  gap: 8px;
}

.count-badge {
  font-size: 12px;
  color: #6b7280;
  background: #f3f4f6;
  padding: 2px 8px;
  border-radius: 12px;
}

/* 区块空状态 */
.section-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  color: #9ca3af;
}

.section-empty p {
  margin: 12px 0 0 0;
  font-size: 14px;
}

/* 摘要样式 */
.summary-content {
  line-height: 1.7;
}

.summary-text {
  color: #374151;
  margin: 0;
  white-space: pre-wrap;
}

.raw-summary-section {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #e5e7eb;
}

.raw-summary-content {
  margin-top: 12px;
  background: #f9fafb;
  border-radius: 8px;
  padding: 16px;
  overflow-x: auto;
}

.raw-summary-content pre {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
  color: #374151;
}

/* 健康概览 */
.health-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 24px;
}

@media (min-width: 768px) {
  .health-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

.health-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.health-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.health-label {
  font-size: 13px;
  color: #6b7280;
  font-weight: 500;
}

.health-value {
  font-size: 14px;
  color: #1f2937;
  font-weight: 600;
}

/* 表格文字截断 */
.text-truncate {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.5;
}

/* 趋势卡片 */
.trends-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 16px;
}

@media (min-width: 768px) {
  .trends-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

.trend-card {
  background: #f9fafb;
  border-radius: 8px;
  padding: 16px;
  border: 1px solid #e5e7eb;
}

.trend-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.trend-name {
  font-size: 15px;
  font-weight: 600;
  color: #1f2937;
}

.trend-stats {
  display: flex;
  justify-content: space-between;
  gap: 16px;
}

.trend-stat {
  flex: 1;
  text-align: center;
}

.trend-stat.change .stat-value {
  font-weight: 600;
}

.stat-label {
  display: block;
  font-size: 12px;
  color: #6b7280;
  margin-bottom: 4px;
}

.stat-value {
  font-size: 18px;
  color: #1f2937;
  font-weight: 500;
}

.trend-data {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #e5e7eb;
}

.data-label {
  font-size: 12px;
  color: #6b7280;
}

/* 建议列表 */
.suggestions-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.suggestion-item {
  background: #f9fafb;
  border-radius: 8px;
  padding: 16px;
  border: 1px solid #e5e7eb;
}

.suggestion-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
}

.suggestion-meta {
  display: flex;
  gap: 8px;
}

.suggestion-content {
  margin-bottom: 12px;
}

.suggestion-text {
  margin: 0;
  color: #374151;
  line-height: 1.6;
}

.suggestion-impact {
  padding-top: 12px;
  border-top: 1px solid #e5e7eb;
}

.impact-label {
  font-size: 12px;
  color: #6b7280;
}

.impact-text {
  font-size: 13px;
  color: #4b5563;
}

.text-gray {
  color: #9ca3af;
}

/* 集群性能指标 */
.metrics-period {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 16px;
  padding: 8px 12px;
  background: #f3f4f6;
  border-radius: 6px;
  font-size: 13px;
  color: #6b7280;
}

.metrics-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 20px;
}

@media (min-width: 768px) {
  .metrics-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (min-width: 1024px) {
  .metrics-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

.metrics-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 16px;
  background: #f9fafb;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
}

.metrics-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.metrics-label {
  font-size: 13px;
  color: #6b7280;
  font-weight: 500;
}

.metrics-value {
  font-size: 18px;
  color: #1f2937;
  font-weight: 600;
}

.metrics-details {
  font-size: 12px;
  color: #9ca3af;
  margin-top: 4px;
}

.metrics-analysis {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #e5e7eb;
}

.metrics-analysis-title {
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 8px;
}

.metrics-analysis p {
  margin: 0;
  color: #4b5563;
  line-height: 1.6;
  font-size: 13px;
}

/* 趋势卡片增强 */
.trends-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.trend-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.trend-type {
  font-size: 12px;
  color: #6b7280;
  background: #e5e7eb;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 500;
}

.trend-analysis,
.trend-prediction {
  margin-top: 12px;
  padding: 12px;
  background: #fff;
  border-radius: 6px;
  border: 1px solid #e5e7eb;
}

.trend-analysis-title,
.trend-prediction-title {
  font-size: 12px;
  font-weight: 600;
  color: #6b7280;
  margin-bottom: 6px;
}

.trend-analysis p,
.trend-prediction p {
  margin: 0;
  color: #374151;
  line-height: 1.5;
  font-size: 13px;
}

.trend-prediction {
  background: #f0f9ff;
  border-color: #bae6fd;
}

.trend-prediction .trend-prediction-title {
  color: #0369a1;
}
</style>

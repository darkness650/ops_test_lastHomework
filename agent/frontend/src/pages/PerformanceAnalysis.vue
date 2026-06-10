<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'
import { useAnalysisStore } from '../stores/analysis'
import type { PerformanceReport, ScheduleConfig } from '../api/analysis'

const router = useRouter()
const analysisStore = useAnalysisStore()

// ========== 状态定义 ==========

// 触发分析对话框显示状态
const analysisDialogVisible = ref(false)
// 分析时长选项
const periodOptions = [
  { value: 1, label: '1 小时' },
  { value: 6, label: '6 小时' },
  { value: 12, label: '12 小时' },
  { value: 24, label: '24 小时' }
]
// 选中的分析时长
const selectedPeriod = ref(24)
// 选中的命名空间（空表示全集群）
const selectedNamespace = ref('')
// 是否正在触发分析
const isTriggering = ref(false)
// 是否正在刷新任务状态
const isRefreshingTask = ref(false)

// 定时任务配置表单
const scheduleForm = ref<ScheduleConfig>({
  enabled: false,
  hour: 2,
  minute: 0,
  analysis_period_hours: 24
})
// 是否正在保存定时配置
const isSavingSchedule = ref(false)

// ========== 计算属性 ==========

// 当前任务进度百分比
const taskProgress = computed(() => {
  return analysisStore.taskStatus?.progress ?? 0
})

// 当前任务状态文字
const taskStatusText = computed(() => {
  const status = analysisStore.taskStatus?.status
  const statusMap: Record<string, string> = {
    queued: '排队中...',
    running: '分析中...',
    completed: '已完成',
    failed: '失败'
  }
  return statusMap[status || ''] || '未知状态'
})

// 是否有正在进行的任务
const hasActiveTask = computed(() => {
  if (!analysisStore.taskStatus) return false
  const status = analysisStore.taskStatus.status
  return status === 'queued' || status === 'running'
})

// 是否显示任务进度
const showTaskProgress = computed(() => {
  return analysisStore.taskStatus !== null && analysisStore.taskStatus !== undefined
})

// 定时任务状态文字
const scheduleStatusText = computed(() => {
  return analysisStore.scheduleStatus?.is_running ? '运行中' : '已停止'
})

// 下次执行时间
const nextRunTime = computed(() => {
  const nextRun = analysisStore.scheduleStatus?.next_run
  if (!nextRun) return '暂无计划'
  return formatTime(nextRun)
})

// 小时选项
const hourOptions = computed(() => {
  return Array.from({ length: 24 }, (_, i) => ({
    value: i,
    label: `${i.toString().padStart(2, '0')} 点`
  }))
})

// 分钟选项
const minuteOptions = computed(() => {
  return Array.from({ length: 60 }, (_, i) => ({
    value: i,
    label: `${i.toString().padStart(2, '0')} 分`
  }))
})

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

// 获取任务状态颜色
function getTaskStatusColor(status: string) {
  const colorMap: Record<string, string> = {
    queued: '#F59E0B',
    running: '#3B82F6',
    completed: '#10B981',
    failed: '#EF4444'
  }
  return colorMap[status] || '#6B7280'
}

// 打开触发分析对话框
function openAnalysisDialog() {
  selectedPeriod.value = 24
  selectedNamespace.value = ''
  analysisDialogVisible.value = true
}

// 关闭触发分析对话框
function closeAnalysisDialog() {
  analysisDialogVisible.value = false
}

// 触发分析
async function handleTriggerAnalysis() {
  isTriggering.value = true
  
  try {
    // 触发分析
    await analysisStore.triggerAnalysis(
      selectedPeriod.value,
      selectedNamespace.value || undefined
    )
    
    // 关闭对话框
    closeAnalysisDialog()
    
    ElMessage.success('分析任务已提交，正在后台执行...')
    
    // 如果有返回的任务ID，开始轮询状态
    const taskId = analysisStore.taskStatus?.task_id
    if (taskId) {
      // 开始轮询任务状态
      const finalStatus = await analysisStore.pollTaskStatus(taskId)
      
      // 轮询结束后，根据结果处理
      if (finalStatus) {
        if (finalStatus.status === 'completed') {
          ElMessage.success('分析完成！')
          // 刷新报告列表
          await analysisStore.fetchReports()
        } else if (finalStatus.status === 'failed') {
          ElMessage.error(`分析失败: ${finalStatus.error_message || '未知错误'}`)
        }
      }
    }
  } catch (error: any) {
    ElMessage.error('触发分析失败')
    console.error('Trigger analysis error:', error)
  } finally {
    isTriggering.value = false
  }
}

// 刷新报告列表
async function refreshReports() {
  await analysisStore.fetchReports()
}

// 手动刷新任务状态
async function refreshTaskStatus() {
  if (!analysisStore.taskStatus?.task_id) {
    return
  }
  
  isRefreshingTask.value = true
  try {
    const { analysisApi } = await import('../api/analysis')
    const response = await analysisApi.getTaskStatus(analysisStore.taskStatus.task_id)
    if (response.code === 200) {
      // 直接更新 store 中的状态
      analysisStore.taskStatus = response.data
      
      // 如果任务完成或失败，刷新报告列表
      if (response.data.status === 'completed' || response.data.status === 'failed') {
        await refreshReports()
      }
    }
  } catch (error) {
    console.error('Refresh task status error:', error)
  } finally {
    isRefreshingTask.value = false
  }
}

// 查看报告详情
function viewReportDetail(report: PerformanceReport) {
  router.push({ name: 'PerformanceReportDetail', params: { id: report.id } })
}

// 删除报告
async function deleteReport(report: PerformanceReport) {
  try {
    await ElMessageBox.confirm(
      `确定要删除报告 "${report.id.substring(0, 8)}..." 吗？此操作不可恢复。`,
      '删除报告',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    await analysisStore.deleteReport(report.id)
    ElMessage.success('报告已删除')
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('删除报告失败')
      console.error('Delete report error:', error)
    }
  }
}

// 分页变化
function handlePageChange(page: number) {
  analysisStore.fetchReports(page, analysisStore.pageSize)
}

// 每页数量变化
function handlePageSizeChange(size: number) {
  analysisStore.fetchReports(1, size)
}

// 定时任务开关切换
async function handleScheduleToggle(enabled: boolean) {
  try {
    if (enabled) {
      await analysisStore.startSchedule()
      ElMessage.success('定时任务已启动')
    } else {
      await analysisStore.stopSchedule()
      ElMessage.success('定时任务已停止')
    }
  } catch (error) {
    ElMessage.error('操作失败')
    console.error('Schedule toggle error:', error)
  }
}

// 保存定时配置
async function saveScheduleConfig() {
  isSavingSchedule.value = true
  try {
    await analysisStore.updateScheduleConfig(scheduleForm.value)
    ElMessage.success('定时配置已保存')
  } catch (error) {
    ElMessage.error('保存配置失败')
    console.error('Save schedule config error:', error)
  } finally {
    isSavingSchedule.value = false
  }
}

// 从 store 同步定时配置到表单
function syncScheduleForm() {
  if (analysisStore.scheduleStatus?.config) {
    scheduleForm.value = { ...analysisStore.scheduleStatus.config }
  }
}

// 初始化数据
async function initData() {
  await Promise.all([
    analysisStore.fetchReports(),
    analysisStore.fetchScheduleStatus()
  ])
  syncScheduleForm()
  
  // 检查是否有正在进行的任务
  try {
    const { analysisApi } = await import('../api/analysis')
    const response = await analysisApi.getLatestTask()
    if (response.code === 200 && response.data) {
      const status = response.data.status
      if (status === 'queued' || status === 'running') {
        // 有正在进行的任务，设置到 store 中
        analysisStore.taskStatus = response.data
        analysisStore.isAnalyzing = true
        // 开始轮询
        analysisStore.pollTaskStatus(response.data.task_id)
      }
    }
  } catch (error) {
    // 忽略获取最新任务的错误
  }
}

// ========== 生命周期 ==========

onMounted(() => {
  initData()
})
</script>

<template>
  <div class="performance-analysis">
    <!-- 顶部工具栏 -->
    <div class="page-header">
      <h1 class="title">业务性能分析</h1>
      <div class="header-actions">
        <el-button @click="refreshReports" :loading="analysisStore.isLoading">
          <el-icon><Refresh /></el-icon>
          刷新列表
        </el-button>
        <el-button
          type="primary"
          @click="openAnalysisDialog"
          :loading="isTriggering"
          :disabled="hasActiveTask"
        >
          <el-icon><DataAnalysis /></el-icon>
          手动触发分析
        </el-button>
      </div>
    </div>

    <!-- 定时任务状态卡片 -->
    <div class="schedule-card" v-if="analysisStore.scheduleStatus">
      <div class="schedule-header">
        <div class="schedule-status">
          <el-tag
            :type="analysisStore.scheduleStatus.is_running ? 'success' : 'info'"
            size="large"
          >
            <el-icon><Timer /></el-icon>
            定时任务：{{ scheduleStatusText }}
          </el-tag>
          <el-switch
            v-model="analysisStore.scheduleStatus.is_running"
            @change="handleScheduleToggle"
            :active-text="'开启'"
            :inactive-text="'关闭'"
          />
        </div>
        <div class="next-run">
          <el-icon><Clock /></el-icon>
          下次执行：{{ nextRunTime }}
        </div>
      </div>

      <div class="schedule-config">
        <el-form inline :model="scheduleForm" label-width="100px">
          <el-form-item label="执行时间">
            <el-select v-model="scheduleForm.hour" :options="hourOptions" placeholder="时" style="width: 120px" />
            <span class="time-separator">:</span>
            <el-select v-model="scheduleForm.minute" :options="minuteOptions" placeholder="分" style="width: 120px" />
          </el-form-item>
          <el-form-item label="分析时长">
            <el-select v-model="scheduleForm.analysis_period_hours" :options="periodOptions" style="width: 150px" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="saveScheduleConfig" :loading="isSavingSchedule">
              保存配置
            </el-button>
          </el-form-item>
        </el-form>
      </div>
    </div>

    <!-- 分析进度状态 -->
    <div v-if="showTaskProgress" class="task-progress-card">
      <div class="task-progress-header">
        <h3>
          <el-icon><Loading :class="{ 'is-loading': hasActiveTask }" /></el-icon>
          分析任务进度
        </h3>
        <el-button @click="refreshTaskStatus" :loading="isRefreshingTask" :disabled="!hasActiveTask" link>
          刷新状态
        </el-button>
      </div>

      <el-progress
        :percentage="taskProgress"
        :status="analysisStore.taskStatus?.status === 'failed' ? 'exception' : analysisStore.taskStatus?.status === 'completed' ? 'success' : undefined"
        :color="getTaskStatusColor(analysisStore.taskStatus?.status || '')"
      />

      <div class="task-status-info">
        <el-tag :type="getReportStatusTagType(analysisStore.taskStatus?.status || '')">
          {{ taskStatusText }}
        </el-tag>
        <span v-if="analysisStore.taskStatus?.error_message" class="error-message">
          {{ analysisStore.taskStatus.error_message }}
        </span>
      </div>
    </div>

    <!-- 报告列表 -->
    <div class="reports-section">
      <div class="section-card">
        <div class="section-header">
          <h3>分析报告列表</h3>
          <span class="total-count">
            共 {{ analysisStore.totalReports }} 条报告
          </span>
        </div>

        <el-skeleton v-if="analysisStore.isLoading" :rows="5" animated />

        <template v-else>
          <div v-if="analysisStore.reports.length === 0" class="empty-state">
            <el-icon size="48" style="color: #9ca3af"><Document /></el-icon>
            <p>暂无分析报告</p>
            <el-button type="primary" @click="openAnalysisDialog" :disabled="hasActiveTask">
              立即分析
            </el-button>
          </div>

          <el-table
            v-else
            :data="analysisStore.reports"
            style="width: 100%"
            class="reports-table"
          >
            <el-table-column prop="id" label="报告 ID" min-width="180">
              <template #default="{ row }">
                <el-tooltip :content="row.id" placement="top" effect="light">
                  <span class="id-text">{{ row.id.substring(0, 12) }}...</span>
                </el-tooltip>
              </template>
            </el-table-column>

            <el-table-column prop="created_at" label="创建时间" width="180">
              <template #default="{ row }">
                {{ formatTime(row.created_at) }}
              </template>
            </el-table-column>

            <el-table-column prop="analysis_period_hours" label="分析时长" width="100">
              <template #default="{ row }">
                {{ row.analysis_period_hours }} 小时
              </template>
            </el-table-column>

            <el-table-column prop="namespace" label="命名空间" width="150">
              <template #default="{ row }">
                <el-tag v-if="row.namespace" size="small">{{ row.namespace }}</el-tag>
                <span v-else class="text-gray">全集群</span>
              </template>
            </el-table-column>

            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="getReportStatusTagType(row.status)" size="small">
                  {{ getReportStatusText(row.status) }}
                </el-tag>
              </template>
            </el-table-column>

            <el-table-column prop="summary" label="摘要" min-width="300">
              <template #default="{ row }">
                <el-tooltip :content="row.summary" placement="top" effect="light" :disabled="!row.summary">
                  <span class="summary-text">{{ row.summary || '-' }}</span>
                </el-tooltip>
              </template>
            </el-table-column>

            <el-table-column label="操作" width="180" fixed="right">
              <template #default="{ row }">
                <el-button
                  type="primary"
                  link
                  size="small"
                  @click="viewReportDetail(row)"
                  :disabled="row.status === 'analyzing'"
                >
                  查看详情
                </el-button>
                <el-button
                  type="danger"
                  link
                  size="small"
                  @click="deleteReport(row)"
                >
                  删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <!-- 分页组件 -->
          <div class="pagination-wrapper">
            <el-pagination
              v-model:current-page="analysisStore.currentPage"
              v-model:page-size="analysisStore.pageSize"
              :page-sizes="[10, 20, 50, 100]"
              :total="analysisStore.totalReports"
              layout="total, sizes, prev, pager, next, jumper"
              @current-change="handlePageChange"
              @size-change="handlePageSizeChange"
            />
          </div>
        </template>
      </div>
    </div>

    <!-- 触发分析对话框 -->
    <el-dialog
      v-model="analysisDialogVisible"
      title="触发业务分析"
      width="500px"
      :close-on-click-modal="false"
      @close="closeAnalysisDialog"
    >
      <el-form label-width="100px">
        <el-form-item label="分析时长">
          <el-select v-model="selectedPeriod" :options="periodOptions" style="width: 100%" />
        </el-form-item>
        <el-form-item label="命名空间">
          <el-input
            v-model="selectedNamespace"
            placeholder="不填则分析全集群"
            clearable
          />
          <div class="form-tip">留空将分析所有命名空间的资源</div>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="closeAnalysisDialog">取消</el-button>
        <el-button
          type="primary"
          @click="handleTriggerAnalysis"
          :loading="isTriggering"
        >
          确认分析
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.performance-analysis {
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

/* 定时任务卡片 */
.schedule-card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.schedule-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.schedule-status {
  display: flex;
  align-items: center;
  gap: 12px;
}

.next-run {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #6b7280;
  font-size: 14px;
}

.schedule-config {
  border-top: 1px solid #e5e7eb;
  padding-top: 16px;
}

.time-separator {
  margin: 0 8px;
  color: #6b7280;
}

/* 任务进度卡片 */
.task-progress-card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.task-progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.task-progress-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
  display: flex;
  align-items: center;
  gap: 8px;
}

.task-status-info {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 12px;
}

.error-message {
  color: #ef4444;
  font-size: 14px;
}

/* 报告列表区域 */
.reports-section {
  margin-top: 0;
}

.section-card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
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

.total-count {
  font-size: 14px;
  color: #6b7280;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: #9ca3af;
}

.empty-state p {
  margin: 12px 0 20px 0;
  font-size: 14px;
}

.reports-table {
  margin-bottom: 20px;
}

.id-text {
  font-family: monospace;
  font-size: 13px;
  color: #1f2937;
}

.summary-text {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.5;
  color: #4b5563;
}

.text-gray {
  color: #9ca3af;
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
}

.form-tip {
  margin-top: 4px;
  font-size: 12px;
  color: #9ca3af;
}
</style>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { usePollingStore } from '../stores/polling'
import { ElMessage } from 'element-plus'

const pollingStore = usePollingStore()

const intervalValue = ref(5)
const isSaving = ref(false)

const statusIcon = computed(() => {
  return pollingStore.isRunning ? 'VideoPlay' : 'VideoPause'
})

const statusText = computed(() => {
  return pollingStore.isRunning ? '运行中' : '已停止'
})

const statusType = computed(() => {
  return pollingStore.isRunning ? 'success' : 'warning'
})

async function handleStart() {
  const success = await pollingStore.startPolling({
    interval_minutes: intervalValue.value,
    deep_analysis: true
  })
  if (success) {
    ElMessage.success('轮询已启动')
  }
}

async function handleStop() {
  const success = await pollingStore.stopPolling()
  if (success) {
    ElMessage.success('轮询已停止')
  }
}

async function handleSaveInterval() {
  if (intervalValue.value < 1 || intervalValue.value > 60) {
    ElMessage.warning('轮询间隔应在 1-60 分钟之间')
    return
  }
  isSaving.value = true
  const success = await pollingStore.startPolling({
    interval_minutes: intervalValue.value,
    deep_analysis: true
  })
  setTimeout(() => {
    isSaving.value = false
    if (success) {
      ElMessage.success('配置已保存')
    }
  }, 500)
}

function formatTime(timestamp: string) {
  if (!timestamp) return '-'
  const date = new Date(timestamp)
  return date.toLocaleString('zh-CN')
}

onMounted(() => {
  pollingStore.fetchStatus()
  if (pollingStore.intervalMinutes) {
    intervalValue.value = pollingStore.intervalMinutes
  }
})
</script>

<template>
  <div class="settings">
    <div class="settings-header">
      <h1 class="title">系统配置</h1>
    </div>

    <el-row :gutter="20">
      <el-col :xs="24" :lg="12">
        <div class="section-card">
          <div class="section-header">
            <h3>连接状态</h3>
          </div>

          <div class="status-grid">
            <div class="status-item">
              <div class="status-label">Kubernetes</div>
              <el-tag :type="pollingStore.status ? 'success' : 'danger'" effect="light">
                <el-icon size="12">
                  <component :is="pollingStore.status ? 'CircleCheck' : 'Warning'" />
                </el-icon>
                {{ pollingStore.status ? '已连接' : '未连接' }}
              </el-tag>
            </div>

            <div class="status-item">
              <div class="status-label">分析引擎</div>
              <el-tag :type="pollingStore.status ? 'success' : 'danger'" effect="light">
                <el-icon size="12">
                  <component :is="pollingStore.status ? 'CircleCheck' : 'Warning'" />
                </el-icon>
                {{ pollingStore.status ? '已就绪' : '异常' }}
              </el-tag>
            </div>

            <div class="status-item">
              <div class="status-label">轮询调度</div>
              <el-tag :type="statusType" effect="light">
                <el-icon :size="12">
                  <component :is="statusIcon" />
                </el-icon>
                {{ statusText }}
              </el-tag>
            </div>
          </div>
        </div>

        <div class="section-card">
          <div class="section-header">
            <h3>轮询配置</h3>
          </div>

          <div class="config-form">
            <div class="config-item">
              <label class="config-label">轮询间隔 (分钟)</label>
              <el-slider
                v-model="intervalValue"
                :min="1"
                :max="60"
                :step="1"
                show-input
                class="slider"
              />
              <div class="config-hint">
                建议值：5-15 分钟（生产环境）
              </div>
            </div>

            <div class="config-actions">
              <el-button
                type="primary"
                :loading="isSaving"
                @click="handleSaveInterval"
              >
                <el-icon><Check /></el-icon>
                保存配置
              </el-button>
            </div>
          </div>
        </div>
      </el-col>

      <el-col :xs="24" :lg="12">
        <div class="section-card">
          <div class="section-header">
            <h3>轮询控制</h3>
          </div>

          <div class="control-panel">
            <div class="control-buttons">
              <el-button
                type="success"
                :disabled="pollingStore.isRunning"
                :loading="pollingStore.isActionLoading"
                @click="handleStart"
                size="large"
                class="control-btn"
              >
                <el-icon><VideoPlay /></el-icon>
                启动轮询
              </el-button>
              <el-button
                type="danger"
                :disabled="!pollingStore.isRunning"
                :loading="pollingStore.isActionLoading"
                @click="handleStop"
                size="large"
                class="control-btn"
              >
                <el-icon><VideoPause /></el-icon>
                停止轮询
              </el-button>
            </div>

            <div class="quick-actions">
              <el-button
                :loading="pollingStore.isActionLoading"
                @click="pollingStore.runOnce"
              >
                <el-icon><RefreshRight /></el-icon>
                立即执行一次
              </el-button>
            </div>
          </div>
        </div>

        <div class="section-card">
          <div class="section-header">
            <h3>系统信息</h3>
          </div>

          <el-descriptions :column="1" border>
            <el-descriptions-item label="当前轮询间隔">
              {{ pollingStore.intervalMinutes }} 分钟
            </el-descriptions-item>
            <el-descriptions-item label="历史记录数">
              {{ pollingStore.historyCount }} 条
            </el-descriptions-item>
            <el-descriptions-item label="上次轮询时间">
              {{ formatTime(pollingStore.status?.last_run || '') }}
            </el-descriptions-item>
          </el-descriptions>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.settings {
  padding: 20px;
}

.settings-header {
  margin-bottom: 20px;
}

.title {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  color: #1f2937;
}

.section-card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  margin-bottom: 20px;
}

.section-header {
  margin-bottom: 16px;
}

.section-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
}

.status-grid {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.status-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #f9fafb;
  border-radius: 8px;
}

.status-label {
  font-weight: 500;
  color: #374151;
}

.config-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.config-item {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.config-label {
  font-weight: 500;
  color: #374151;
}

.slider {
  width: 100%;
}

.config-hint {
  font-size: 12px;
  color: #9ca3af;
}

.config-actions {
  display: flex;
  justify-content: flex-end;
}

.control-panel {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.control-buttons {
  display: flex;
  gap: 16px;
}

.control-btn {
  flex: 1;
}

.quick-actions {
  display: flex;
  gap: 12px;
  padding-top: 12px;
  border-top: 1px solid #e5e7eb;
}
</style>

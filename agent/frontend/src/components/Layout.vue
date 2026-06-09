<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useBackendStore } from '../stores/backend'

const route = useRoute()
const router = useRouter()
const backendStore = useBackendStore()

const isCollapse = ref(false)

const menuItems = [
  { path: '/dashboard', title: '集群概览', icon: 'Odometer' },
  { path: '/chat', title: '智能对话', icon: 'ChatDotRound' },
  { path: '/history', title: '历史记录', icon: 'Clock' },
  { path: '/settings', title: '系统配置', icon: 'Setting' }
]

const currentPath = computed(() => route.path)

function handleMenuClick(path: string) {
  router.push(path)
}

onMounted(() => {
  backendStore.checkHealth()
  backendStore.startPolling(5000)
})

onUnmounted(() => {
  backendStore.stopPolling()
})
</script>

<template>
  <div class="app-layout">
    <el-container class="container">
      <el-aside :width="isCollapse ? '64px' : '220px'" class="aside">
        <div class="logo">
          <el-icon size="32" style="color: #3B82F6"><Monitor /></el-icon>
          <span v-if="!isCollapse" class="logo-text">运维智能体</span>
        </div>

        <el-menu
          :default-active="currentPath"
          mode="vertical"
          :collapse="isCollapse"
          background-color="#1f2937"
          text-color="#9ca3af"
          active-text-color="#fff"
          class="menu"
        >
          <el-menu-item
            v-for="item in menuItems"
            :key="item.path"
            :index="item.path"
            @click="handleMenuClick(item.path)"
          >
            <el-icon>
              <component :is="item.icon" />
            </el-icon>
            <template #title>{{ item.title }}</template>
          </el-menu-item>
        </el-menu>
      </el-aside>

      <el-container>
        <el-header class="header">
          <div class="header-left">
            <el-icon
              class="collapse-btn"
              size="20"
              @click="isCollapse = !isCollapse"
            >
              <Fold v-if="!isCollapse" />
              <Expand v-else />
            </el-icon>
            <span class="page-title">{{ route.meta.title || '运维智能体' }}</span>
          </div>
          <div class="header-right">
            <el-tag :type="backendStore.isOnline ? 'success' : 'danger'" size="small">
              <el-icon size="12"><Connection /></el-icon>
              后端: {{ backendStore.isOnline ? '在线' : '离线' }}
            </el-tag>
          </div>
        </el-header>

        <el-main class="main">
          <router-view />
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<style scoped>
.app-layout {
  height: 100vh;
  width: 100%;
  margin: 0;
  padding: 0;
}

.container {
  height: 100%;
  margin: 0;
  padding: 0;
}

:deep(.el-container) {
  margin: 0;
  padding: 0;
  max-width: 100%;
}

:deep(.el-aside) {
  margin: 0;
  padding: 0;
}

.aside {
  background: #1f2937;
  transition: width 0.3s;
  overflow: hidden;
  padding: 0;
  margin: 0;
}

.logo {
  display: flex;
  align-items: center;
  gap: 12px;
  height: 64px;
  padding: 0 20px;
  border-bottom: 1px solid #374151;
}

.logo-text {
  color: #fff;
  font-size: 18px;
  font-weight: 600;
  white-space: nowrap;
}

.menu {
  border-right: none;
  padding: 0;
  margin: 0;
}

:deep(.el-menu) {
  padding: 0;
  margin: 0;
}

:deep(.el-menu-item) {
  margin: 4px 8px;
  border-radius: 8px;
}

:deep(.el-menu-item.is-active) {
  background: #3b82f6 !important;
}

.header {
  background: #fff;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.collapse-btn {
  cursor: pointer;
  color: #6b7280;
  transition: color 0.2s;
}

.collapse-btn:hover {
  color: #3b82f6;
}

.page-title {
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.main {
  background: #f3f4f6;
  padding: 0;
  overflow: auto;
}
</style>

<template>
  <el-dialog
    v-model="dialogVisible"
    title="系统事件日志"
    width="80%"
    :close-on-click-modal="false"
  >
    <div class="system-logs-container">
      <!-- 统计信息 -->
      <el-alert type="info" :closable="false" style="margin-bottom: 16px;">
        <template #title>
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <span>系统事件日志（最近30天自动保留，不可手动清除）</span>
            <div>
              <el-tag v-if="stats" type="info" size="small">
                共 {{ stats.total }} 条事件
              </el-tag>
            </div>
          </div>
        </template>
      </el-alert>

      <!-- 筛选器 -->
      <div class="filters" style="margin-bottom: 16px; display: flex; gap: 12px;">
        <el-select
          v-model="filterSeverity"
          placeholder="严重程度"
          clearable
          style="width: 120px;"
          @change="loadLogs"
        >
          <el-option label="信息" value="info" />
          <el-option label="警告" value="warning" />
          <el-option label="错误" value="error" />
        </el-select>
        
        <el-select
          v-model="filterEventType"
          placeholder="事件类型"
          clearable
          style="width: 200px;"
          @change="loadLogs"
        >
          <el-option label="Bettercap重启" value="bettercap_restart" />
          <el-option label="配置更新" value="bettercap_config_restart" />
          <el-option label="模块启动" value="bettercap_modules_started" />
          <el-option label="日志清理" value="system_log_cleanup" />
        </el-select>

        <el-button :icon="Refresh" @click="loadLogs">刷新</el-button>
      </div>

      <!-- 日志表格 -->
      <el-table
        :data="logs"
        style="width: 100%"
        max-height="500"
        v-loading="loading"
      >
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="created_at" label="时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="severity" label="级别" width="80">
          <template #default="{ row }">
            <el-tag :type="getSeverityType(row.severity)" size="small">
              {{ getSeverityLabel(row.severity) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="event_type" label="事件类型" width="180">
          <template #default="{ row }">
            {{ getEventTypeLabel(row.event_type) }}
          </template>
        </el-table-column>
        <el-table-column prop="message" label="消息" min-width="300" />
        <el-table-column prop="details" label="详情" width="100">
          <template #default="{ row }">
            <el-button
              v-if="row.details"
              size="small"
              text
              @click="showDetails(row)"
            >
              查看
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <template #footer>
      <el-button @click="dialogVisible = false">关闭</el-button>
    </template>
  </el-dialog>

  <!-- 详情对话框 -->
  <el-dialog
    v-model="detailsDialogVisible"
    title="事件详情"
    width="600px"
  >
    <div v-if="selectedLog">
      <p><strong>事件ID:</strong> {{ selectedLog.id }}</p>
      <p><strong>事件类型:</strong> {{ getEventTypeLabel(selectedLog.event_type) }}</p>
      <p><strong>时间:</strong> {{ formatTime(selectedLog.created_at) }}</p>
      <p><strong>消息:</strong> {{ selectedLog.message }}</p>
      <p><strong>详细信息:</strong></p>
      <pre style="background: #f5f5f5; padding: 12px; border-radius: 4px; max-height: 300px; overflow: auto;">{{ formatDetails(selectedLog.details) }}</pre>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { getSystemLogs, getSystemLogsStats, type SystemEventLog, type SystemLogStats } from '../api/systemLogs'

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
}>()

const dialogVisible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const logs = ref<SystemEventLog[]>([])
const stats = ref<SystemLogStats | null>(null)
const loading = ref(false)
const filterSeverity = ref<string>('')
const filterEventType = ref<string>('')

const detailsDialogVisible = ref(false)
const selectedLog = ref<SystemEventLog | null>(null)

// 加载日志
async function loadLogs() {
  loading.value = true
  try {
    const params: any = { limit: 100, days: 30 }
    if (filterSeverity.value) {
      params.severity = filterSeverity.value
    }
    if (filterEventType.value) {
      params.event_type = filterEventType.value
    }
    const result = await getSystemLogs(params)
    logs.value = result.logs
  } catch (error: any) {
    ElMessage.error('加载日志失败: ' + (error.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

// 加载统计信息
async function loadStats() {
  try {
    stats.value = await getSystemLogsStats(30)
  } catch (error: any) {
    console.error('加载统计信息失败:', error)
  }
}

// 显示详情
function showDetails(log: SystemEventLog) {
  selectedLog.value = log
  detailsDialogVisible.value = true
}

// 格式化时间
function formatTime(time: string): string {
  return new Date(time).toLocaleString('zh-CN')
}

// 格式化详情
function formatDetails(details: string | undefined): string {
  if (!details) return '无'
  try {
    return JSON.stringify(JSON.parse(details), null, 2)
  } catch {
    return details
  }
}

// 获取严重程度类型
function getSeverityType(severity: string): string {
  const map: Record<string, string> = {
    info: 'info',
    warning: 'warning',
    error: 'danger'
  }
  return map[severity] || 'info'
}

// 获取严重程度标签
function getSeverityLabel(severity: string): string {
  const map: Record<string, string> = {
    info: '信息',
    warning: '警告',
    error: '错误'
  }
  return map[severity] || severity
}

// 获取事件类型标签
function getEventTypeLabel(eventType: string): string {
  const map: Record<string, string> = {
    bettercap_restart: 'Bettercap自动重启',
    bettercap_config_restart: 'Bettercap配置更新',
    bettercap_modules_started: 'Bettercap模块启动',
    system_log_cleanup: '系统日志清理',
    scheduler_start: '调度器启动',
    system_error: '系统错误'
  }
  return map[eventType] || eventType
}

// 监听对话框打开
watch(dialogVisible, (val) => {
  if (val) {
    loadLogs()
    loadStats()
  }
})

onMounted(() => {
  if (dialogVisible.value) {
    loadLogs()
    loadStats()
  }
})
</script>

<style scoped>
.system-logs-container {
  padding: 4px;
}
</style>


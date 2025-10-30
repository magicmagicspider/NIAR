<template>
  <div class="tasks-page-container">
    <el-card>
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <div style="display: flex; align-items: center; gap: 12px;">
            <span>定时任务</span>
            <el-tag :type="schedulerStatus.running ? 'success' : 'danger'" size="small">
              调度器: {{ schedulerStatus.running ? '运行中' : '已停止' }}
            </el-tag>
            <el-tag type="info" size="small">
              {{ tasks.length }} 个任务
            </el-tag>
          </div>
          <div style="display: flex; gap: 8px;">
            <el-button size="small" @click="loadSchedulerStatus">刷新状态</el-button>
            <el-button type="primary" @click="onCreateTask">新建任务</el-button>
          </div>
        </div>
      </template>

      <el-table :data="tasks" style="width: 100%">
        <el-table-column prop="name" label="任务名称" width="200" />
        <el-table-column label="扫描工具" width="120">
          <template #default="{ row }">
            <el-tag :type="row.scan_tool === 'bettercap' ? 'success' : 'primary'" size="small">
              {{ row.scan_tool === 'bettercap' ? 'Bettercap' : 'Nmap' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="扫描网段" width="200">
          <template #default="{ row }">
            <el-tag v-for="cidr in row.cidrs" :key="cidr" size="small" style="margin-right: 4px;">
              {{ cidr }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="执行频率" width="150">
          <template #default="{ row }">
            <span v-if="row.scan_tool === 'bettercap'" style="color: #67c23a;">
              持续监控
            </span>
            <span v-else>{{ row.cron_expression }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-switch 
              v-model="row.enabled" 
              @change="onToggleTask(row)"
              active-text="启用"
              inactive-text="禁用"
            />
          </template>
        </el-table-column>
        <el-table-column label="上次执行" width="180">
          <template #default="{ row }">
            {{ row.last_run_at ? formatTime(row.last_run_at) : '未执行' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="480">
          <template #default="{ row }">
            <el-button size="small" @click="onEditTask(row)" style="width: 48px;">编辑</el-button>
            <!-- Nmap 任务显示立即执行，Bettercap 任务显示持续运行状态 -->
            <!-- Nmap 任务：立即执行按钮 -->
            <el-button 
              v-if="row.scan_tool === 'nmap'" 
              size="small" 
              type="success" 
              @click="onTriggerTask(row)"
              style="width: 68px; margin-left: 4px;"
            >
              立即执行
            </el-button>
            <!-- Bettercap 任务：运行状态图标 + 实际模式标签 -->
            <template v-else>
              <el-icon 
                :size="20"
                :color="row.enabled ? '#67c23a' : '#909399'"
                style="margin: 0 4px; display: inline-block; width: 24px; text-align: center;"
              >
                <Loading v-if="row.enabled" class="is-loading" />
                <VideoPause v-else />
              </el-icon>
              <!-- 显示实际运行模式 -->
              <el-tooltip 
                :content="getBettercapModeTooltip(row.id)"
                placement="top"
              >
                <el-tag 
                  :type="getBettercapModeType(row.id)"
                  size="small"
                  style="margin-left: 4px; cursor: pointer;"
                  @click="refreshBettercapStatus(row.id)"
                >
                  {{ getBettercapModeDisplay(row.id) }}
                </el-tag>
              </el-tooltip>
            </template>
            <!-- Bettercap 任务：实时、日志 -->
            <template v-if="row.scan_tool === 'bettercap'">
              <el-button size="small" type="warning" @click="onViewLogs(row)" style="width: 56px; margin-left: 4px;">实时</el-button>
              <el-button size="small" type="info" @click="onViewHistory(row)" style="width: 56px; margin-left: 4px;">日志</el-button>
            </template>
            <!-- Nmap 任务：日志、历史 -->
            <template v-else>
              <el-button size="small" type="warning" @click="onViewLogs(row)" style="width: 56px; margin-left: 4px;">日志</el-button>
              <el-button size="small" type="info" @click="onViewHistory(row)" style="width: 56px; margin-left: 4px;">历史</el-button>
            </template>
            <el-button size="small" type="danger" @click="onDeleteTask(row)" style="width: 56px; margin-left: 4px;">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div v-if="tasks.length === 0" class="empty-state">
        <el-empty description="暂无定时任务，点击右上角新建任务" />
      </div>
    </el-card>

    <!-- 任务编辑对话框 -->
    <el-dialog 
      v-model="dialogVisible" 
      :title="dialogMode === 'create' ? '新建定时任务' : '编辑定时任务'"
      width="600px"
    >
      <el-form :model="form" label-width="120px">
        <el-form-item label="任务名称" required>
          <el-input v-model="form.name" placeholder="例如：每日凌晨扫描办公网段" />
        </el-form-item>
        
        <el-form-item label="目标网段" required>
          <!-- Bettercap: 单行输入 -->
          <el-input 
            v-if="form.scan_tool === 'bettercap'"
            v-model="form.cidrsText" 
            placeholder="例如：192.168.1.0/24"
          />
          <!-- Nmap: 多行输入 -->
          <el-input 
            v-else
            v-model="form.cidrsText" 
            type="textarea"
            :rows="3"
            placeholder="每行一个 CIDR，例如：&#10;192.168.1.0/24&#10;10.0.0.0/24&#10;172.16.0.0/16"
          />
        </el-form-item>
        
        <el-form-item label="扫描工具">
          <el-radio-group v-model="form.scan_tool" @change="onScanToolChange">
            <el-radio label="nmap">Nmap</el-radio>
            <el-radio label="bettercap">Bettercap (持续监控)</el-radio>
          </el-radio-group>
        </el-form-item>
        
        <el-form-item v-if="form.scan_tool === 'nmap'" label="Nmap 参数">
          <el-input 
            v-model="form.nmap_args" 
            placeholder="留空使用默认 -sn，可填 -sS -O 等"
          >
            <template #prepend>nmap</template>
          </el-input>
        </el-form-item>
        
        <el-alert 
          v-if="form.scan_tool === 'bettercap'" 
          title="Bettercap 持续监控模式" 
          type="info" 
          :closable="false"
          style="margin-bottom: 16px;"
        >
          启用后，Bettercap 将持续运行 net.recon 和 net.probe 模块，每分钟自动同步发现的主机到数据库。
          Bettercap 配置请在"设置"页面中配置。
        </el-alert>
        
        <el-form-item v-if="form.scan_tool === 'nmap'" label="定时模式">
          <el-radio-group v-model="cronMode">
            <el-radio label="simple">简单预设</el-radio>
            <el-radio label="advanced">高级自定义</el-radio>
          </el-radio-group>
        </el-form-item>
        
        <!-- 简单模式（仅 nmap）-->
        <el-form-item v-if="form.scan_tool === 'nmap' && cronMode === 'simple'" label="执行频率">
          <el-select v-model="form.cron_expression" placeholder="选择执行频率" style="width: 100%;">
            <el-option label="每小时" value="0 * * * *" />
            <el-option label="每2小时" value="0 */2 * * *" />
            <el-option label="每6小时" value="0 */6 * * *" />
            <el-option label="每12小时" value="0 */12 * * *" />
            <el-option label="每天凌晨2点" value="0 2 * * *" />
            <el-option label="每天中午12点" value="0 12 * * *" />
            <el-option label="每周一上午9点" value="0 9 * * 1" />
            <el-option label="每月1号凌晨3点" value="0 3 1 * *" />
          </el-select>
        </el-form-item>
        
        <!-- 高级模式（仅 nmap）-->
        <div v-if="form.scan_tool === 'nmap' && cronMode === 'advanced'">
          <el-form-item label="分钟">
            <el-input v-model="cronParts.minute" placeholder="0-59 或 * 或 */5" @input="updateCronExpression" />
          </el-form-item>
          <el-form-item label="小时">
            <el-input v-model="cronParts.hour" placeholder="0-23 或 * 或 */2" @input="updateCronExpression" />
          </el-form-item>
          <el-form-item label="日">
            <el-input v-model="cronParts.day" placeholder="1-31 或 * 或 */7" @input="updateCronExpression" />
          </el-form-item>
          <el-form-item label="月">
            <el-input v-model="cronParts.month" placeholder="1-12 或 * 或 */3" @input="updateCronExpression" />
          </el-form-item>
          <el-form-item label="星期">
            <el-input v-model="cronParts.weekday" placeholder="0-6 (0=周日) 或 *" @input="updateCronExpression" />
          </el-form-item>
        </div>
        
        <!-- Cron 表达式显示（仅 nmap）-->
        <el-form-item v-if="form.scan_tool === 'nmap'" label="Cron 表达式">
          <el-input v-model="form.cron_expression" readonly>
            <template #append>
              <el-tooltip content="标准 Cron 格式: 分 时 日 月 星期">
                <el-icon><QuestionFilled /></el-icon>
              </el-tooltip>
            </template>
          </el-input>
        </el-form-item>
        
        <el-form-item label="启用任务">
          <el-switch v-model="form.enabled" />
          <div v-if="form.scan_tool === 'bettercap' && form.enabled" style="margin-top: 8px; font-size: 12px; color: #67c23a;">
            ✓ 将使用默认配置启动（主动探测模式）
          </div>
          <div v-else-if="form.scan_tool === 'bettercap' && !form.enabled" style="margin-top: 8px; font-size: 12px; color: #909399;">
            提示：创建后可随时启用
          </div>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="onSubmitTask">确定</el-button>
      </template>
    </el-dialog>

    <!-- 执行历史/任务日志对话框 -->
    <el-dialog 
      v-model="historyDialogVisible" 
      :title="`${selectedTask?.scan_tool === 'bettercap' ? '任务日志' : '执行历史'} - ${selectedTask?.name}`"
      width="800px"
    >
      <!-- Bettercap 任务：显示友好日志 -->
      <template v-if="selectedTask?.scan_tool === 'bettercap' && executions.length > 0 && executions[0].logs">
        <div style="margin-bottom: 16px;">
          <el-tag :type="executions[0].status === 'running' ? 'success' : 'info'" size="small">
            {{ executions[0].status === 'running' ? '持续监控中' : '已停止' }}
          </el-tag>
        </div>
        <div class="log-container" style="max-height: 500px; overflow-y: auto; background: #f5f5f5; padding: 12px; border-radius: 4px;">
          <pre style="margin: 0; font-family: 'Courier New', monospace; font-size: 13px; line-height: 1.5;">{{ executions[0].logs.join('\n') }}</pre>
        </div>
      </template>
      
      <!-- Nmap 任务：显示执行记录表格 -->
      <template v-else>
        <el-table :data="executions" style="width: 100%">
          <el-table-column label="执行时间" width="180">
            <template #default="{ row }">
              {{ formatTime(row.started_at) }}
            </template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag 
                :type="row.status === 'success' ? 'success' : row.status === 'failed' ? 'danger' : 'info'"
                size="small"
              >
                {{ row.status === 'success' ? '成功' : row.status === 'failed' ? '失败' : '运行中' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="online_count" label="在线" width="80" />
          <el-table-column prop="offline_count" label="离线" width="80" />
          <el-table-column prop="new_count" label="新增" width="80" />
          <el-table-column label="耗时" width="100">
            <template #default="{ row }">
              {{ row.duration ? row.duration.toFixed(1) + 's' : '-' }}
            </template>
          </el-table-column>
          <el-table-column label="错误信息" min-width="200">
            <template #default="{ row }">
              <span v-if="row.error_message" style="color: #f56c6c;">{{ row.error_message }}</span>
              <span v-else>-</span>
            </template>
          </el-table-column>
        </el-table>
        
        <div v-if="executions.length === 0" class="empty-state">
          <el-empty description="暂无执行记录" />
        </div>
      </template>
    </el-dialog>

    <!-- 实时监控/任务日志对话框 -->
    <el-dialog 
      v-model="logsDialogVisible" 
      :title="`${selectedTask?.scan_tool === 'bettercap' ? '实时监控' : '任务日志'} - ${selectedTask?.name}`"
      width="800px"
    >
      <div v-if="taskLogs">
        <div style="margin-bottom: 12px; color: #606266;">
          <span v-if="taskLogs.scan_tool === 'bettercap'">
            状态: {{ taskLogs.is_running ? '✅ 运行中' : '⏸️ 已停止' }}
          </span>
          <span v-else-if="taskLogs.last_execution">
            最后执行: {{ formatTime(taskLogs.last_execution.started_at) }}
          </span>
        </div>
        
        <div style="max-height: 500px; overflow-y: auto; background: #f5f5f5; padding: 12px; border-radius: 4px; border: 1px solid #dcdfe6;">
          <pre v-if="taskLogs.logs.length > 0" style="margin: 0; font-family: 'Courier New', monospace; font-size: 13px; line-height: 1.5; white-space: pre-wrap; word-wrap: break-word;">{{ taskLogs.logs.join('\n') }}</pre>
          <div v-else style="color: #999; text-align: center; padding: 20px;">暂无日志</div>
        </div>
      </div>
      
      <template #footer>
        <el-button @click="logsDialogVisible = false">关闭</el-button>
        <el-button type="primary" @click="refreshLogs">刷新</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { QuestionFilled, Loading, VideoPause } from '@element-plus/icons-vue'
import { 
  listTasks, 
  createTask, 
  updateTask, 
  deleteTask, 
  toggleTask, 
  triggerTask,
  getTaskExecutions,
  type ScheduledTask,
  type TaskExecution
} from '../api/tasks'

const tasks = ref<ScheduledTask[]>([])
const dialogVisible = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const cronMode = ref<'simple' | 'advanced'>('simple')
const historyDialogVisible = ref(false)
const logsDialogVisible = ref(false)
const selectedTask = ref<ScheduledTask | null>(null)
const executions = ref<TaskExecution[]>([])
const taskLogs = ref<any>(null)
const schedulerStatus = ref({ running: false, jobs: 0, job_details: [], running_tasks: [] })

// Bettercap 任务的实际运行状态（task_id -> status）
const bettercapStatuses = ref<Record<number, {
  probe_mode: string | null
  mode_display: string
  bettercap_connected: boolean
  error?: string
  modules?: any
  probe_throttle?: string
  configured_mode?: string
}>>({})

const form = ref({
  id: 0,
  name: '',
  cidrsText: '',
  scan_tool: 'nmap' as 'nmap' | 'bettercap',
  nmap_args: '',
  bettercap_duration: 60,
  cron_expression: '0 * * * *',  // 默认每小时
  enabled: true
})

const cronParts = ref({
  minute: '0',
  hour: '*',
  day: '*',
  month: '*',
  weekday: '*'
})

function formatTime(t?: string) {
  if (!t) return '-'
  const d = new Date(t)
  return d.toLocaleString()
}

function updateCronExpression() {
  form.value.cron_expression = `${cronParts.value.minute} ${cronParts.value.hour} ${cronParts.value.day} ${cronParts.value.month} ${cronParts.value.weekday}`
}

function parseCronExpression(cron: string) {
  const parts = cron.split(' ')
  if (parts.length >= 5) {
    cronParts.value = {
      minute: parts[0],
      hour: parts[1],
      day: parts[2],
      month: parts[3],
      weekday: parts[4]
    }
  }
}

function onScanToolChange() {
  if (form.value.scan_tool === 'bettercap') {
    // Bettercap 模式不需要 cron 表达式（占位）
    form.value.cron_expression = '* * * * *'
    form.value.bettercap_duration = 60
  }
}

async function loadTasks() {
  try {
    tasks.value = await listTasks()
    // 加载任务后，自动获取 Bettercap 任务的运行状态
    await loadAllBettercapStatuses()
  } catch (error) {
    ElMessage.error('加载任务列表失败')
    console.error(error)
  }
}

// 加载所有 Bettercap 任务的实际运行状态
async function loadAllBettercapStatuses() {
  const bettercapTasks = tasks.value.filter(t => t.scan_tool === 'bettercap')
  for (const task of bettercapTasks) {
    await loadBettercapStatus(task.id)
  }
}

// 获取单个 Bettercap 任务的实际运行状态
async function loadBettercapStatus(taskId: number) {
  try {
    // 添加时间戳参数防止缓存
    const response = await fetch(`/api/tasks/${taskId}/bettercap-status?_t=${Date.now()}`, {
      method: 'GET',
      headers: {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'
      },
      cache: 'no-store'  // 强制禁用浏览器缓存
    })
    const data = await response.json()
    
    bettercapStatuses.value[taskId] = {
      probe_mode: data.probe_mode,
      mode_display: data.mode_display || '未知',
      bettercap_connected: data.bettercap_connected,
      error: data.error,
      modules: data.modules,
      probe_throttle: data.probe_throttle,
      configured_mode: data.configured_mode
    }
  } catch (error) {
    console.error(`Failed to load Bettercap status for task ${taskId}:`, error)
    bettercapStatuses.value[taskId] = {
      probe_mode: null,
      mode_display: '加载失败',
      bettercap_connected: false,
      error: '无法连接'
    }
  }
}

// 刷新 Bettercap 状态（点击标签时触发）
async function refreshBettercapStatus(taskId: number) {
  await loadBettercapStatus(taskId)
}

// 获取 Bettercap 模式显示文本
function getBettercapModeDisplay(taskId: number): string {
  const status = bettercapStatuses.value[taskId]
  if (!status) return '...'
  if (!status.bettercap_connected) return '未连接'
  return status.mode_display
}

// 获取 Bettercap 模式标签类型
function getBettercapModeType(taskId: number): string {
  const status = bettercapStatuses.value[taskId]
  if (!status || !status.bettercap_connected) return 'info'
  
  if (status.probe_mode === 'active') return 'success'
  if (status.probe_mode === 'passive') return 'warning'
  return 'info'
}

// 获取 Bettercap 模式提示信息
function getBettercapModeTooltip(taskId: number): string {
  const status = bettercapStatuses.value[taskId]
  if (!status) return '正在加载状态...'
  
  if (!status.bettercap_connected) {
    return status.error || '无法连接到 Bettercap'
  }
  
  if (status.probe_mode === 'active') {
    const throttle = status.probe_throttle || '未知'
    return `当前: 主动探测模式\n间隔: ${throttle} 秒\n点击刷新状态`
  } else if (status.probe_mode === 'passive') {
    return `当前: 被动侦察模式\n仅监听流量\n点击刷新状态`
  } else if (status.probe_mode === null) {
    return '模块未运行\n点击刷新状态'
  }
  
  return '点击刷新状态'
}

async function loadSchedulerStatus() {
  try {
    // 添加时间戳参数防止缓存
    const response = await fetch(`/api/tasks/scheduler/status?_t=${Date.now()}`, {
      method: 'GET',
      headers: {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'
      },
      cache: 'no-store'  // 强制禁用浏览器缓存
    })
    schedulerStatus.value = await response.json()
    console.log('调度器状态:', schedulerStatus.value)
  } catch (error) {
    console.error('加载调度器状态失败:', error)
  }
}

function onCreateTask() {
  dialogMode.value = 'create'
  cronMode.value = 'simple'
  form.value = {
    id: 0,
    name: '',
    cidrsText: '',
    scan_tool: 'nmap',
    nmap_args: '',
    bettercap_duration: 60,
    cron_expression: '0 * * * *',
    enabled: true
  }
  dialogVisible.value = true
}

function onEditTask(task: ScheduledTask) {
  dialogMode.value = 'edit'
  cronMode.value = 'simple'
  form.value = {
    id: task.id,
    name: task.name,
    cidrsText: task.cidrs.join('\n'),
    scan_tool: task.scan_tool || 'nmap',
    nmap_args: task.nmap_args || '',
    bettercap_duration: task.bettercap_duration || 60,
    cron_expression: task.cron_expression,
    enabled: task.enabled
  }
  parseCronExpression(task.cron_expression)
  dialogVisible.value = true
}

async function onSubmitTask() {
  if (!form.value.name) {
    ElMessage.error('请输入任务名称')
    return
  }
  
  if (!form.value.cidrsText) {
    ElMessage.error('请输入目标网段')
    return
  }
  
  // 支持换行或逗号分隔
  const cidrs = form.value.cidrsText
    .split(/[\n,]/)
    .map(s => s.trim())
    .filter(Boolean)
  
  if (cidrs.length === 0) {
    ElMessage.error('请输入有效的网段')
    return
  }
  
  try {
    const payload = {
      name: form.value.name,
      cidrs,
      scan_tool: form.value.scan_tool,
      nmap_args: form.value.nmap_args || undefined,
      bettercap_duration: form.value.bettercap_duration || undefined,
      cron_expression: form.value.cron_expression,
      enabled: form.value.enabled
    }
    
    if (dialogMode.value === 'create') {
      await createTask(payload)
      ElMessage.success('任务创建成功')
    } else {
      await updateTask(form.value.id, payload)
      ElMessage.success('任务更新成功')
    }
    
    dialogVisible.value = false
    loadTasks()
  } catch (error: any) {
    const msg = error.response?.data?.detail || error.message || '操作失败'
    // 针对配置错误的特殊处理，显示更长时间
    if (msg.includes('设置') || msg.includes('配置')) {
      ElMessage({
        message: msg,
        type: 'error',
        duration: 5000,
        showClose: true
      })
    } else {
      ElMessage.error(msg)
    }
  }
}

async function onToggleTask(task: ScheduledTask) {
  try {
    const result = await toggleTask(task.id)
    ElMessage.success(result.enabled ? '任务已启用' : '任务已禁用')
    loadTasks()
  } catch (error: any) {
    ElMessage.error(error.message || '操作失败')
    loadTasks()  // 刷新状态
  }
}

async function onTriggerTask(task: ScheduledTask) {
  try {
    await triggerTask(task.id)
    ElMessage.success('任务已触发，正在后台执行')
  } catch (error: any) {
    ElMessage.error(error.message || '触发失败')
  }
}

async function onDeleteTask(task: ScheduledTask) {
  try {
    await ElMessageBox.confirm(`确定删除任务 "${task.name}" 吗？`, '确认删除', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await deleteTask(task.id)
    ElMessage.success('任务删除成功')
    loadTasks()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '删除失败')
    }
  }
}

async function onViewHistory(task: ScheduledTask) {
  selectedTask.value = task
  historyDialogVisible.value = true
  
  try {
    executions.value = await getTaskExecutions(task.id)
  } catch (error) {
    ElMessage.error('加载执行历史失败')
    console.error(error)
  }
}

async function onViewLogs(task: ScheduledTask) {
  selectedTask.value = task
  logsDialogVisible.value = true
  await loadTaskLogs(task.id)
}

async function loadTaskLogs(taskId: number) {
  try {
    // 添加时间戳参数防止缓存
    const response = await fetch(`/api/tasks/${taskId}/logs?_t=${Date.now()}`, {
      method: 'GET',
      headers: {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'
      },
      cache: 'no-store'  // 强制禁用浏览器缓存
    })
    taskLogs.value = await response.json()
  } catch (error) {
    ElMessage.error('加载任务日志失败')
    console.error(error)
  }
}

async function refreshLogs() {
  if (selectedTask.value) {
    await loadTaskLogs(selectedTask.value.id)
    ElMessage.success('日志已刷新')
  }
}

onMounted(() => {
  loadTasks()
  loadSchedulerStatus()
  // 立即加载一次Bettercap状态
  loadAllBettercapStatuses()
  // 每30秒刷新一次调度器状态
  setInterval(loadSchedulerStatus, 30000)
  // 每10秒刷新一次 Bettercap 任务的运行状态
  setInterval(loadAllBettercapStatuses, 10000)
})
</script>

<style scoped>
.tasks-page-container {
  padding: 16px;
  padding-bottom: 40px;
  min-height: 100%;
  box-sizing: border-box;
}

.empty-state {
  text-align: center;
  padding: 40px;
}

.log-container {
  max-height: 400px;
  overflow-y: auto;
  background: #f5f5f5;
  padding: 12px;
  border-radius: 4px;
  font-family: 'Courier New', Courier, monospace;
  font-size: 13px;
  line-height: 1.6;
}

.log-line {
  white-space: pre-wrap;
  word-break: break-word;
  margin-bottom: 4px;
}

/* 旋转动画 */
.is-loading {
  animation: rotating 2s linear infinite;
}

@keyframes rotating {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}
</style>


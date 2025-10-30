<template>
  <div class="scan-page-container">
    <el-card>
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <span>扫描</span>
          <el-tag v-if="currentTask" :type="getStatusType(currentTask.status)">
            {{ getStatusText(currentTask.status) }}
          </el-tag>
        </div>
      </template>

      <div class="scan-content">
      <!-- 扫描工具选择 -->
      <div>
        <label style="display:block;margin-bottom:6px;font-weight:500;">扫描工具</label>
        <el-input value="Nmap" disabled style="width:100%;" />
        <div style="margin-top:6px;font-size:12px;color:#909399;">
          ✓ 支持详细的端口扫描和 OS 检测<br/>
          ℹ️ 如需持续监控，请使用"定时任务"中的 Bettercap 任务
        </div>
      </div>

      <!-- CIDR 输入 -->
      <div>
        <label style="display:block;margin-bottom:6px;font-weight:500;">目标网段</label>
        <el-input 
          v-model="cidrs" 
          placeholder="输入 CIDR，逗号分隔，如 192.168.1.0/24" 
          :disabled="isScanning"
        />
      </div>

      <!-- Nmap 参数（仅在选择 nmap 时显示）-->
      <div v-if="scanTool === 'nmap'">
        <div style="display:flex;align-items:center;margin-bottom:6px;">
          <label style="font-weight:500;">Nmap 扫描参数（可选）</label>
          <el-tooltip placement="right">
            <template #content>
              <div style="max-width:350px;">
                <p><strong>留空（推荐）</strong>：使用 -sn 快速扫描，可获取 MAC、主机名、厂商信息</p>
                <p><strong>OS 检测说明</strong>：</p>
                <ul style="margin:4px 0;padding-left:20px;">
                  <li><code>-O</code> 必须配合端口扫描使用（如 -sS、-sV）</li>
                  <li><code>-sn -O</code> ❌ 无效组合</li>
                  <li><code>-sS -O</code> ✅ 正确组合</li>
                </ul>
                <p><strong>推荐参数</strong>：<code>-sS -O</code> (SYN扫描+OS检测，需root)</p>
                <p><strong>大网段扫描</strong>：异步模式支持跨网段长时间扫描</p>
              </div>
            </template>
            <el-icon style="margin-left:6px;color:#909399;cursor:help;">
              <QuestionFilled />
            </el-icon>
          </el-tooltip>
        </div>
        <el-input 
          v-model="nmapArgs" 
          placeholder="留空使用默认参数 -sn（可获取 MAC、主机名）"
          clearable
          :disabled="isScanning"
        >
          <template #prepend>nmap</template>
        </el-input>
        <div style="margin-top:6px;font-size:12px;color:#909399;">
          <div style="margin-bottom:4px;">快速扫描（仅主机发现）：</div>
          <el-link type="primary" @click="nmapArgs = '-sn -T4'" :disabled="isScanning" style="margin-left:8px;">-sn -T4</el-link> (快速)
          <el-link type="primary" @click="nmapArgs = '-sn -PR'" :disabled="isScanning" style="margin-left:8px;">-sn -PR</el-link> (ARP扫描)
          <div style="margin-top:8px;margin-bottom:4px;">详细扫描（含OS检测，需root权限，较慢）：</div>
          <el-link type="success" @click="nmapArgs = '-sS -O'" :disabled="isScanning" style="margin-left:8px;">-sS -O</el-link> (SYN扫描+OS)
          <el-link type="success" @click="nmapArgs = '-sV -O'" :disabled="isScanning" style="margin-left:8px;">-sV -O</el-link> (服务版本+OS)
          <el-link type="warning" @click="nmapArgs = '-A'" :disabled="isScanning" style="margin-left:8px;">-A</el-link> (全面扫描)
        </div>
      </div>

      <!-- 扫描按钮 -->
      <div>
        <el-button 
          type="primary" 
          :loading="isScanning" 
          @click="onScan"
          :disabled="isScanning"
          style="width:100%;"
        >
          {{ isScanning ? scanProgressText : '开始扫描' }}
        </el-button>
      </div>

      <!-- 进度条 -->
      <div v-if="currentTask && isScanning">
        <el-progress 
          :percentage="currentTask.progress" 
          :status="currentTask.status === 'failed' ? 'exception' : undefined"
        >
          <template #default="{ percentage }">
            <span style="font-size: 12px;">{{ percentage }}%</span>
          </template>
        </el-progress>
        <div style="margin-top:8px;font-size:13px;color:#606266;">
          <div v-if="currentTask.total_hosts > 0">总计扫描：{{ currentTask.total_hosts }} 个主机</div>
          <div v-if="currentTask.started_at">
            已运行：{{ formatDuration(currentTask.started_at) }}
          </div>
        </div>
      </div>

      <!-- Nmap 输出控制台 -->
      <div v-if="showConsole" style="margin-top:12px;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
          <span style="font-weight:500;color:#606266;">Nmap 输出</span>
          <el-button 
            size="small" 
            @click="consoleOutput = ''; showConsole = false"
            :disabled="isScanning"
          >
            清空
          </el-button>
        </div>
        <div 
          ref="consoleBox"
          class="console-box"
        >{{ consoleOutput || '等待扫描输出...' }}</div>
      </div>

      <!-- 扫描结果 -->
      <div v-if="currentTask && currentTask.status === 'completed'" style="margin-top:12px;">
        <el-alert 
          :title="`扫描完成`" 
          type="success" 
          :closable="false"
        >
          <div style="margin-top:8px;">
            <div>在线设备：<strong style="color:#67c23a;">{{ currentTask.online_count }}</strong> 台</div>
            <div>新增设备：<strong style="color:#409eff;">{{ currentTask.new_count }}</strong> 台</div>
            <div>扫描主机：<strong>{{ currentTask.total_hosts }}</strong> 个</div>
            <div v-if="currentTask.nmap_args">使用参数：<code>{{ currentTask.nmap_args }}</code></div>
            <div v-if="currentTask.completed_at">
              耗时：{{ formatDuration(currentTask.started_at, currentTask.completed_at) }}
            </div>
            <div style="margin-top:12px;">
              <el-button type="primary" @click="router.push('/devices')">
                查看设备列表
              </el-button>
              <el-button @click="router.push('/')">
                查看主页
              </el-button>
            </div>
          </div>
        </el-alert>
      </div>

      <!-- 扫描失败 -->
      <div v-if="currentTask && currentTask.status === 'failed'" style="margin-top:12px;">
        <el-alert 
          title="扫描失败" 
          type="error" 
          :closable="false"
        >
          <div style="margin-top:8px;">
            <div>错误信息：{{ currentTask.error_message }}</div>
          </div>
        </el-alert>
      </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { QuestionFilled } from '@element-plus/icons-vue'
import { startScan, getScanStatus } from '../api/scan'
import { ElMessage } from 'element-plus'

const cidrs = ref('192.168.1.0/24')
const scanTool = ref<'nmap'>('nmap')  // 固定为 nmap
const nmapArgs = ref('')

const isScanning = ref(false)
const showConsole = ref(false)
const consoleOutput = ref('')
const consoleBox = ref<HTMLElement | null>(null)
const currentTask = ref<any>(null)
const router = useRouter()

let pollTimer: number | null = null

// 扫描进度文本
const scanProgressText = computed(() => {
  if (!currentTask.value) return '扫描中...'
  
  const progress = currentTask.value.progress || 0
  const status = currentTask.value.status
  
  if (status === 'pending') return '准备中...'
  if (status === 'running') return `扫描中 ${progress}%`
  if (status === 'completed') return '已完成'
  if (status === 'failed') return '失败'
  
  return '扫描中...'
})

// 状态类型
function getStatusType(status: string) {
  const map: Record<string, any> = {
    'pending': 'info',
    'running': 'warning',
    'completed': 'success',
    'failed': 'danger'
  }
  return map[status] || 'info'
}

// 状态文本
function getStatusText(status: string) {
  const map: Record<string, string> = {
    'pending': '等待中',
    'running': '运行中',
    'completed': '已完成',
    'failed': '失败'
  }
  return map[status] || status
}

// 格式化时长
function formatDuration(start: string, end?: string) {
  const startTime = new Date(start).getTime()
  const endTime = end ? new Date(end).getTime() : Date.now()
  const seconds = Math.floor((endTime - startTime) / 1000)
  
  if (seconds < 60) return `${seconds} 秒`
  
  const minutes = Math.floor(seconds / 60)
  const remainSeconds = seconds % 60
  
  if (minutes < 60) return `${minutes} 分 ${remainSeconds} 秒`
  
  const hours = Math.floor(minutes / 60)
  const remainMinutes = minutes % 60
  return `${hours} 小时 ${remainMinutes} 分`
}

// 自动滚动控制台到底部
function scrollConsoleToBottom() {
  if (consoleBox.value) {
    setTimeout(() => {
      if (consoleBox.value) {
        consoleBox.value.scrollTop = consoleBox.value.scrollHeight
      }
    }, 10)
  }
}

// 轮询任务状态
async function pollTaskStatus(taskId: string) {
  try {
    const status = await getScanStatus(taskId)
    currentTask.value = status
    
    // 实时更新 nmap 输出（如果有新内容）
    if (status.raw_output && status.raw_output !== consoleOutput.value) {
      // 保留之前的任务创建信息，替换为实际的 nmap 输出
      const headerLines = consoleOutput.value.split('\n').slice(0, 6).join('\n')
      consoleOutput.value = headerLines + '\n\n' + '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
      consoleOutput.value += 'Nmap 输出:\n\n'
      consoleOutput.value += status.raw_output
      scrollConsoleToBottom()
    }
    
    // 如果任务完成或失败，停止轮询
    if (status.status === 'completed' || status.status === 'failed') {
      stopPolling()
      isScanning.value = false
      
      // 添加完成信息
      if (status.status === 'completed') {
        consoleOutput.value += '\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
        consoleOutput.value += `✅ 扫描完成！\n`
        consoleOutput.value += `在线设备: ${status.online_count} 台\n`
        consoleOutput.value += `新增设备: ${status.new_count} 台\n`
        consoleOutput.value += `扫描主机: ${status.total_hosts} 个\n`
        scrollConsoleToBottom()
        
        ElMessage.success(`扫描完成！在线 ${status.online_count} 台，新增 ${status.new_count} 台`)
      } else {
        consoleOutput.value += '\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
        consoleOutput.value += `❌ 扫描失败\n`
        consoleOutput.value += `错误: ${status.error_message}\n`
        scrollConsoleToBottom()
        
        ElMessage.error(`扫描失败：${status.error_message}`)
      }
    }
  } catch (e: any) {
    console.error('Poll status error:', e)
    // 不停止轮询，继续尝试
  }
}

// 停止轮询
function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

// 开始扫描
async function onScan() {
  try {
    isScanning.value = true
    currentTask.value = null
    showConsole.value = true
    consoleOutput.value = '启动扫描任务...\n'
    
    const arr = cidrs.value.split(',').map(s => s.trim()).filter(Boolean)
    
    if (arr.length === 0) {
      ElMessage.warning('请输入至少一个 CIDR')
      isScanning.value = false
      return
    }
    
    // 显示启动信息
    consoleOutput.value += `$ nmap ${nmapArgs.value || '-sn'} ${arr.join(' ')}\n`
    consoleOutput.value += `后台扫描已启动，请等待...\n\n`
    scrollConsoleToBottom()
    
    // 调用扫描 API（异步模式，立即返回）
    const response = await startScan(
      arr,
      128,
      scanTool.value,
      nmapArgs.value || undefined,
      undefined  // 不使用 bettercap 配置
    )
    
    consoleOutput.value += `✅ 任务已创建\n`
    consoleOutput.value += `任务ID: ${response.task_id}\n`
    consoleOutput.value += `扫描工具: ${response.scan_tool}\n`
    consoleOutput.value += `状态: ${response.status}\n\n`
    scrollConsoleToBottom()
    
    ElMessage.success('Nmap 扫描任务已启动，正在后台运行')
    
    // 开始轮询任务状态（每 2 秒查询一次）
    pollTimer = window.setInterval(() => {
      pollTaskStatus(response.task_id)
    }, 2000)
    
    // 立即查询一次
    pollTaskStatus(response.task_id)
    
  } catch (e: any) {
    consoleOutput.value += `\n❌ 错误: ${e.message || '启动扫描失败'}\n`
    scrollConsoleToBottom()
    ElMessage.error(e.message || '启动扫描失败')
    isScanning.value = false
  }
}

// 组件卸载时清理定时器
import { onUnmounted } from 'vue'
onUnmounted(() => {
  stopPolling()
})
</script>

<style scoped>
.scan-page-container {
  padding: 16px;
  padding-bottom: 40px;
  min-height: 100%;
  box-sizing: border-box;
}

.scan-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.console-box {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 12px;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
  max-height: 300px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-all;
  flex-shrink: 0;
}

/* 自定义滚动条样式 */
.console-box::-webkit-scrollbar {
  width: 8px;
}

.console-box::-webkit-scrollbar-track {
  background: #252526;
  border-radius: 4px;
}

.console-box::-webkit-scrollbar-thumb {
  background: #4e4e4e;
  border-radius: 4px;
}

.console-box::-webkit-scrollbar-thumb:hover {
  background: #5e5e5e;
}
</style>

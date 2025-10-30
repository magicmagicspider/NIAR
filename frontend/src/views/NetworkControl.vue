<template>
  <div class="network-control">
    <el-card>
      <template #header>
        <div class="card-header">
          <span class="title">网络管控</span>
          <div class="network-info">
            <el-tag type="info">当前网段: {{ networkInfo.cidr }}</el-tag>
            <el-tag type="success" style="margin-left: 8px;">本机: {{ networkInfo.local_ip }}</el-tag>
            <el-tag type="success" style="margin-left: 8px;">
              网关: {{ getGatewayIP() }} (已保护)
            </el-tag>
          </div>
          <div class="actions">
            <el-button @click="loadData" :icon="Refresh">刷新</el-button>
            <el-button @click="showLogs" :icon="Document">查看日志</el-button>
          </div>
        </div>
      </template>

      <!-- 警告提示 -->
      <el-alert
        type="warning"
        :closable="false"
        show-icon
        style="margin-bottom: 16px;"
      >
        <template #title>
          <strong>重要提示：ARP Ban 是网络攻击技术</strong>
        </template>
        <div style="font-size: 13px;">
          • 本功能会中断目标设备的网络连接<br>
          • 系统已自动保护网关和本机IP，避免影响整个网络<br>
          • 请确保在授权环境下使用，并遵守相关法律法规<br>
          • 错误使用可能导致网络中断或被视为攻击行为
        </div>
      </el-alert>

      <el-row :gutter="20">
        <!-- 左侧：可用 IP 列表 -->
        <el-col :span="12">
          <el-card shadow="never">
            <template #header>
              <div style="display: flex; justify-content: space-between; align-items: center;">
                <span>可用 IP</span>
                <el-tag type="info" size="small">共 {{ availableHosts.length }} 个地址</el-tag>
              </div>
            </template>

            <el-input
              v-model="searchLeft"
              placeholder="搜索 IP / MAC / 主机名"
              :prefix-icon="Search"
              clearable
              style="margin-bottom: 12px;"
            />

            <el-table
              :data="filteredAvailableHosts"
              height="350"
              style="width: 100%"
              :default-sort="{ prop: 'ip', order: 'ascending' }"
            >
              <el-table-column prop="ip" label="IP 地址" width="140" sortable />
              <el-table-column prop="mac" label="MAC" width="150">
                <template #default="{ row }">
                  <span style="color: #999;">{{ row.mac || '-' }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="hostname" label="主机名" width="150">
                <template #default="{ row }">
                  <span style="color: #999;">{{ row.hostname || '-' }}</span>
                </template>
              </el-table-column>
              <el-table-column label="状态" width="80" align="center">
                <template #default="{ row }">
                  <el-icon :size="16" :color="row.online ? '#67c23a' : '#c0c4cc'">
                    <CircleCheck v-if="row.online" />
                    <CircleClose v-else />
                  </el-icon>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="100" align="center">
                <template #default="{ row }">
                  <el-button
                    type="primary"
                    size="small"
                    @click="addToTarget(row)"
                    :disabled="isInTargets(row.ip)"
                  >
                    {{ isInTargets(row.ip) ? '已添加' : '添加' }}
                  </el-button>
                </template>
              </el-table-column>
            </el-table>

            <!-- 受保护的设备（自动检测） -->
            <el-card shadow="never" style="margin-top: 20px; background: var(--el-fill-color-lighter);">
              <template #header>
                <div style="display: flex; align-items: center; gap: 8px;">
                  <el-icon :size="18" color="#409eff"><CircleCheck /></el-icon>
                  <span style="font-weight: bold; color: #409eff;">受保护的设备</span>
                </div>
              </template>

              <el-alert
                type="info"
                :closable="false"
                show-icon
                style="margin-bottom: 12px;"
              >
                以下设备不能被Ban，以保证网络正常运行
              </el-alert>

              <div style="display: flex; flex-direction: column; gap: 8px;">
                <div v-for="ip in protectedDevices" :key="ip" style="display: flex; align-items: center; padding: 8px; background: var(--el-bg-color-overlay); border-radius: 4px;">
                  <el-icon :size="16" color="#67c23a" style="margin-right: 8px;"><CircleCheck /></el-icon>
                  <span style="font-weight: 500;">{{ ip }}</span>
                  <el-tag
                    v-if="ip === gatewayIP"
                    type="success"
                    size="small"
                    style="margin-left: 8px;"
                  >
                    网关
                  </el-tag>
                  <el-tag
                    v-else-if="ip === localIP"
                    type="success"
                    size="small"
                    style="margin-left: 8px;"
                  >
                    本机
                  </el-tag>
                </div>
              </div>

              <div v-if="protectedDevices.length === 0" style="text-align: center; padding: 20px; color: #909399; font-size: 13px;">
                正在检测受保护的设备...
              </div>
            </el-card>
          </el-card>
        </el-col>

        <!-- 右侧：目标设备 + 控制面板 -->
        <el-col :span="12">
          <el-card shadow="never">
            <template #header>
              <div style="display: flex; justify-content: space-between; align-items: center;">
                <span>目标设备</span>
                <el-tag :type="targets.length > 0 ? 'warning' : 'info'" size="small">
                  已选 {{ targets.length }} 个目标
                </el-tag>
              </div>
            </template>

            <el-input
              v-model="searchRight"
              placeholder="搜索目标设备"
              :prefix-icon="Search"
              clearable
              style="margin-bottom: 12px;"
            />

            <el-table
              :data="filteredTargets"
              height="350"
              style="width: 100%"
            >
              <el-table-column prop="ip" label="IP 地址" width="140" />
              <el-table-column prop="mac" label="MAC" width="150">
                <template #default="{ row }">
                  {{ row.mac || '-' }}
                </template>
              </el-table-column>
              <el-table-column prop="hostname" label="主机名" width="130">
                <template #default="{ row }">
                  {{ row.hostname || '-' }}
                </template>
              </el-table-column>
              <el-table-column prop="note" label="备注" width="100">
                <template #default="{ row }">
                  <span style="color: #999;">{{ row.note || '-' }}</span>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="100" align="center">
                <template #default="{ row }">
                  <el-button
                    type="danger"
                    size="small"
                    @click="removeFromTarget(row.ip)"
                  >
                    移除
                  </el-button>
                </template>
              </el-table-column>
            </el-table>

            <!-- 控制面板 -->
            <el-card shadow="never" style="margin-top: 20px; background: var(--el-fill-color-light);">
              <div style="text-align: center;">
                <el-statistic title="运行状态" :value="status.running ? '运行中' : '已停止'" />
                <el-icon
                  :size="60"
                  :color="status.running ? '#67c23a' : '#909399'"
                  style="margin: 20px 0;"
                >
                  <Loading v-if="status.running" class="is-loading" />
                  <VideoPause v-else />
                </el-icon>

                <div style="margin-top: 20px;">
                  <el-button
                    v-if="!status.running"
                    type="success"
                    size="large"
                    :icon="VideoPlay"
                    @click="startArpBan"
                    :disabled="targets.length === 0"
                    style="width: 200px;"
                  >
                    开始 Ban
                  </el-button>
                  <el-button
                    v-else
                    type="danger"
                    size="large"
                    :icon="VideoPause"
                    @click="stopArpBan"
                    style="width: 200px;"
                  >
                    停止 Ban
                  </el-button>
                </div>

                <el-alert
                  v-if="targets.length === 0"
                  title="请先添加目标设备"
                  type="info"
                  :closable="false"
                  style="margin-top: 20px;"
                />
                <el-alert
                  v-else-if="status.running"
                  title="ARP Ban 正在运行，目标设备将被隔离"
                  type="warning"
                  :closable="false"
                  style="margin-top: 20px;"
                />
              </div>
            </el-card>
          </el-card>
        </el-col>
      </el-row>
    </el-card>

    <!-- 日志对话框 -->
    <el-dialog v-model="logDialogVisible" title="操作日志" width="800px">
      <el-table :data="logs" height="400">
        <el-table-column prop="created_at" label="时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="action" label="操作" width="100">
          <template #default="{ row }">
            <el-tag :type="getActionType(row.action)" size="small">
              {{ getActionLabel(row.action) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="ip" label="IP" width="140" />
        <el-table-column prop="message" label="信息" />
        <el-table-column prop="operator" label="操作人" width="100" />
      </el-table>
      <template #footer>
        <el-button @click="logDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Refresh,
  Document,
  Search,
  CircleCheck,
  CircleClose,
  VideoPlay,
  VideoPause,
  Loading
} from '@element-plus/icons-vue'
import {
  getArpBanStatus,
  getNetworkInfo,
  getAvailableHosts,
  listTargets,
  addTarget,
  removeTarget,
  startBan,
  stopBan,
  getLogs,
  type AvailableHost,
  type ArpBanTarget,
  type ArpBanLog,
  type ArpBanStatus,
  type NetworkInfo
} from '@/api/arpBan'

// 数据
const networkInfo = ref<NetworkInfo>({
  cidr: '加载中...',
  local_ip: '加载中...',
  total_ips: 0
})
const availableHosts = ref<AvailableHost[]>([])
const targets = ref<ArpBanTarget[]>([])
const status = ref<ArpBanStatus>({
  running: false,
  target_count: 0,
  targets: []
})
const logs = ref<ArpBanLog[]>([])

// 搜索
const searchLeft = ref('')
const searchRight = ref('')

// 对话框
const logDialogVisible = ref(false)
const whitelistDialogVisible = ref(false)

// 白名单相关（受保护的设备，自动检测）
const gatewayIP = ref('')
const localIP = ref('')
const protectedDevices = ref<string[]>([])  // 受保护的设备列表
const whitelist = ref<Array<{ip: string, note?: string}>>([])  // 向后兼容，但不再使用
const whitelistForm = ref({
  ip: '',
  note: ''
})

// 计算属性：过滤后的可用主机（排除白名单设备）
const filteredAvailableHosts = computed(() => {
  // 首先过滤掉白名单设备
  let hosts = availableHosts.value.filter(host => !host.is_whitelist)
  
  // 然后应用搜索过滤
  if (!searchLeft.value) return hosts

  const keyword = searchLeft.value.toLowerCase()
  return hosts.filter(host =>
    host.ip.includes(keyword) ||
    (host.mac && host.mac.toLowerCase().includes(keyword)) ||
    (host.hostname && host.hostname.toLowerCase().includes(keyword))
  )
})

// 计算属性：过滤后的目标设备
const filteredTargets = computed(() => {
  if (!searchRight.value) return targets.value

  const keyword = searchRight.value.toLowerCase()
  return targets.value.filter(target =>
    target.ip.includes(keyword) ||
    (target.mac && target.mac.toLowerCase().includes(keyword)) ||
    (target.hostname && target.hostname.toLowerCase().includes(keyword))
  )
})

// 检查 IP 是否已在目标列表
function isInTargets(ip: string): boolean {
  return targets.value.some(t => t.ip === ip)
}

// 加载所有数据
async function loadData() {
  try {
    const [netInfo, hostsData, targetsData, statusData] = await Promise.all([
      getNetworkInfo(),
      getAvailableHosts(),
      listTargets(),
      getArpBanStatus()
    ])

    networkInfo.value = netInfo
    availableHosts.value = hostsData.hosts
    targets.value = targetsData.targets
    status.value = statusData
    
    // 保存受保护的设备信息（白名单）
    if (hostsData.whitelist) {
      protectedDevices.value = hostsData.whitelist
      gatewayIP.value = hostsData.gateway_ip || ''
      localIP.value = hostsData.local_ip || ''
    }
  } catch (error: any) {
    ElMessage.error('加载数据失败: ' + (error.message || '未知错误'))
  }
}

// 添加到目标
async function addToTarget(host: AvailableHost) {
  try {
    await addTarget({
      ip: host.ip,
      mac: host.mac,
      hostname: host.hostname
    })
    ElMessage.success(`已添加 ${host.ip} 到目标列表`)
    await loadData()
  } catch (error: any) {
    ElMessage.error('添加失败: ' + (error.response?.data?.detail || error.message))
  }
}

// 从目标移除
async function removeFromTarget(ip: string) {
  try {
    await ElMessageBox.confirm(`确定要移除 ${ip} 吗？`, '确认', {
      type: 'warning'
    })

    await removeTarget(ip)
    ElMessage.success(`已移除 ${ip}`)
    await loadData()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('移除失败: ' + (error.response?.data?.detail || error.message))
    }
  }
}

// 启动 ARP Ban
async function startArpBan() {
  try {
    const protectedCount = protectedDevices.value.length
    const protectedList = protectedDevices.value.map(ip => {
      if (ip === gatewayIP.value) return `${ip} (网关)`
      if (ip === localIP.value) return `${ip} (本机)`
      return ip
    }).join(', ')
    
    await ElMessageBox.confirm(
      `即将对 ${targets.value.length} 个目标设备执行 ARP Ban。

⚠️ 这将导致目标设备无法访问网络
✅ 受保护的设备 (${protectedCount}个): ${protectedList}

确定继续？`,
      '警告',
      {
        type: 'warning',
        confirmButtonText: '确定启动',
        cancelButtonText: '取消'
      }
    )

    // 不再传递whitelist参数，后端自动保护
    await startBan()
    ElMessage.success('ARP Ban 已启动')
    await loadData()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('启动失败: ' + (error.response?.data?.detail || error.message))
    }
  }
}

// 停止 ARP Ban
async function stopArpBan() {
  try {
    await stopBan()
    ElMessage.success('ARP Ban 已停止')
    await loadData()
  } catch (error: any) {
    ElMessage.error('停止失败: ' + (error.response?.data?.detail || error.message))
  }
}

// 查看日志
async function showLogs() {
  try {
    const data = await getLogs(100)
    logs.value = data.logs
    logDialogVisible.value = true
  } catch (error: any) {
    ElMessage.error('加载日志失败: ' + error.message)
  }
}

// 格式化时间
function formatTime(time: string): string {
  return new Date(time).toLocaleString('zh-CN')
}

// 获取操作类型标签
function getActionType(action: string): string {
  const typeMap: Record<string, string> = {
    start: 'success',
    stop: 'info',
    add: 'warning',
    remove: 'danger'
  }
  return typeMap[action] || 'info'
}

// 获取操作标签
function getActionLabel(action: string): string {
  const labelMap: Record<string, string> = {
    start: '启动',
    stop: '停止',
    add: '添加',
    remove: '移除'
  }
  return labelMap[action] || action
}

// 获取网关 IP（从用户设置或推断）
function getGatewayIP(): string {
  if (gatewayIP.value) return gatewayIP.value
  if (!networkInfo.value.cidr) return '未知'
  // 假设网关是 .1（最常见的情况）
  const parts = networkInfo.value.cidr.split('/')[0].split('.')
  return parts.slice(0, 3).join('.') + '.1'
}

// 白名单相关函数已移除，白名单现在由后端自动检测和保护

// 页面加载
onMounted(async () => {
  await loadData()
  // 立即获取一次ban状态
  await getArpBanStatus().then((s: ArpBanStatus) => {
    status.value = s
  })
  // 每 10 秒刷新一次状态
  setInterval(() => {
    getArpBanStatus().then((s: ArpBanStatus) => {
      status.value = s
    })
  }, 10000)
})
</script>

<style scoped>
.network-control {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.title {
  font-size: 20px;
  font-weight: bold;
}

.network-info {
  flex: 1;
  display: flex;
  justify-content: center;
}

.actions {
  display: flex;
  gap: 8px;
}

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


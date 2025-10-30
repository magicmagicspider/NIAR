<template>
  <div class="home-container">

    <!-- 可视化网格 -->
    <div class="visualization-section">
      <el-card>
        <template #header>
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <div style="display: flex; align-items: center; gap: 12px;">
              <span>网络可视化</span>
              <el-select 
                v-model="selectedNetwork" 
                placeholder="请选择网段" 
                style="width: 200px;"
                @change="onNetworkChange"
              >
                <el-option
                  v-for="network in networks"
                  :key="network.cidr"
                  :label="`${network.cidr} (${network.deviceCount} 在线)`"
                  :value="network.cidr"
                />
              </el-select>
            </div>
            <el-button type="primary" @click="refreshNetworks">刷新</el-button>
          </div>
        </template>
        
        <div v-if="grid.length" class="grid-container" :style="gridStyle">
          <div 
            v-for="item in grid" 
            :key="item.ip" 
            class="grid-item"
            :class="{ 'online': item.online, 'offline': !item.online }"
            @click="onGridItemClick(item)"
            @mouseenter="onGridItemHover(item)"
            @mouseleave="onGridItemLeave"
          >
            <div class="grid-item-content">
              <div class="ip-display" v-if="showIp && hoveredIp === item.ip">{{ item.ip }}</div>
            </div>
          </div>
        </div>
        <div v-else class="empty-state">
          <el-empty description="请选择网段或输入 CIDR 生成可视化网格" />
        </div>
      </el-card>
    </div>

    <!-- 设备详情弹窗 -->
    <el-dialog 
      v-model="deviceDialogVisible" 
      :title="selectedDevice ? `设备详情 - ${selectedDevice.ip}` : '设备详情'"
      width="600px"
    >
      <div v-if="selectedDevice" class="device-details">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="IP地址">{{ selectedDevice.ip }}</el-descriptions-item>
          <el-descriptions-item label="主机名">{{ selectedDevice.hostname || '-' }}</el-descriptions-item>
          <el-descriptions-item label="MAC地址">{{ selectedDevice.mac || '-' }}</el-descriptions-item>
          <el-descriptions-item label="厂商">{{ selectedDevice.vendor || '-' }}</el-descriptions-item>
          <el-descriptions-item label="操作系统" :span="2">{{ selectedDevice.os || '-' }}</el-descriptions-item>
          <el-descriptions-item label="在线状态">
            <el-tag :type="selectedDevice.is_online ? 'success' : 'danger'">
              {{ selectedDevice.is_online ? '在线' : '离线' }}
            </el-tag>
            <div style="margin-top: 4px; font-size: 12px; color: #909399;">
              Nmap: <span :style="{color: (selectedDevice.nmap_last_seen && !selectedDevice.nmap_offline_at) ? '#67C23A' : '#F56C6C'}">{{ (selectedDevice.nmap_last_seen && !selectedDevice.nmap_offline_at) ? '✓' : '✗' }}</span>
              Bettercap: <span :style="{color: (selectedDevice.bettercap_last_seen && !selectedDevice.bettercap_offline_at) ? '#67C23A' : '#F56C6C'}">{{ (selectedDevice.bettercap_last_seen && !selectedDevice.bettercap_offline_at) ? '✓' : '✗' }}</span>
            </div>
          </el-descriptions-item>
          <el-descriptions-item label="最后在线时间">
            {{ formatTime(selectedDevice.lastSeenAt) }}
          </el-descriptions-item>
          <el-descriptions-item v-if="selectedDevice.offline_at" label="离线时间" :span="2">
            {{ formatTime(selectedDevice.offline_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="备注" :span="2">{{ selectedDevice.note || '-' }}</el-descriptions-item>
        </el-descriptions>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { listDevices, type Device } from '../api/devices'

// 响应式数据
const selectedNetwork = ref('')
const grid = ref<{ip: string, online: boolean, device?: Device}[]>([])
const showIp = ref(false)
const hoveredIp = ref('')
const deviceDialogVisible = ref(false)
const selectedDevice = ref<Device | null>(null)
const allDevices = ref<Device[]>([])

// 计算属性 - 网段列表
const networks = computed(() => {
  const networkMap = new Map<string, { cidr: string, deviceCount: number }>()
  
  allDevices.value.forEach(device => {
    // 只统计在线设备（使用综合状态）
    if (device.is_online) {
      const cidr = getNetworkCidr(device.ip)
      if (cidr) {
        const existing = networkMap.get(cidr)
        if (existing) {
          existing.deviceCount++
        } else {
          networkMap.set(cidr, { cidr, deviceCount: 1 })
        }
      }
    }
  })
  
  return Array.from(networkMap.values()).sort((a, b) => a.cidr.localeCompare(b.cidr))
})

// 计算属性 - 动态网格样式
const gridStyle = computed(() => {
  if (grid.value.length === 0) return {
    gridTemplateColumns: 'repeat(auto-fit, minmax(40px, 1fr))',
    gap: '6px'
  }
  
  // 计算网格列数和行数，确保能够一次性显示所有项目
  const totalItems = grid.value.length
  
  // 根据屏幕尺寸计算合适的参数
  const screenWidth = window.innerWidth
  const screenHeight = window.innerHeight
  let gap = 6
  
  // 根据屏幕大小调整间隙
  if (screenWidth < 480) {
    gap = 4
  } else if (screenWidth < 768) {
    gap = 4
  } else if (screenWidth < 1200) {
    gap = 5
  }
  
  // 计算可用空间（考虑所有边距和内边距）
  const headerHeight = 60 // 页面头部高度
  const cardHeaderHeight = 60 // 卡片头部高度
  const containerPadding = 32 + 24 + 16 // home容器 + card + grid容器的padding总和
  const availableWidth = screenWidth - 32 - 24 - 16 // 减去所有横向padding
  const availableHeight = screenHeight - headerHeight - cardHeaderHeight - containerPadding - 40
  
  // 根据可用空间和项目总数计算最优的列数和行数
  // 尽量让网格接近正方形，充分利用空间
  const aspectRatio = availableWidth / availableHeight
  const idealColumns = Math.sqrt(totalItems * aspectRatio)
  const idealRows = totalItems / idealColumns
  
  let columns = Math.ceil(idealColumns)
  let rows = Math.ceil(totalItems / columns)
  
  // 计算每个格子的实际尺寸
  const itemWidth = (availableWidth - gap * (columns - 1)) / columns
  const itemHeight = (availableHeight - gap * (rows - 1)) / rows
  
  // 如果高度不够，减少列数增加行数
  if (itemHeight < itemWidth * 0.5) {
    columns = Math.max(Math.floor(columns * 0.8), Math.ceil(Math.sqrt(totalItems)))
    rows = Math.ceil(totalItems / columns)
  }
  
  return {
    gridTemplateColumns: `repeat(${columns}, 1fr)`,
    gap: `${gap}px`
  }
})

// 工具函数
function getNetworkCidr(ip: string): string | null {
  const parts = ip.split('.')
  if (parts.length === 4) {
    return `${parts[0]}.${parts[1]}.${parts[2]}.0/24`
  }
  return null
}

function expandCIDR(cidrStr: string): string[] {
  try {
    const [base, mask] = cidrStr.split('/')
    const parts = base.split('.').map(Number)
    const maskNum = Number(mask)
    const hostBits = 32 - maskNum
    const hostCount = Math.max(0, (1 << hostBits) - 2) // 排除网络/广播
    const baseInt = (parts[0]<<24) + (parts[1]<<16) + (parts[2]<<8) + parts[3]
    const netInt = baseInt & (~((1<<hostBits)-1))
    const res: string[] = []
    for(let i = 1; i <= hostCount; i++) {
      const v = netInt + i
      const a = (v>>>24) & 255, b = (v>>>16) & 255, c = (v>>>8) & 255, d = v & 255
      res.push(`${a}.${b}.${c}.${d}`)
    }
    return res
  } catch {
    return []
  }
}

function formatTime(t?: string) {
  if (!t) return '-'
  const d = new Date(t)
  return d.toLocaleString()
}

// 事件处理
async function refreshNetworks() {
  await loadDevices()
  ElMessage.success('网段列表已刷新')
}

function onNetworkChange() {
  if (selectedNetwork.value) {
    generateGrid(selectedNetwork.value)
  }
}


function generateGrid(cidr: string) {
  const ips = expandCIDR(cidr)
  const deviceMap = new Map(allDevices.value.map(d => [d.ip, d]))
  
  grid.value = ips.map(ip => {
    const device = deviceMap.get(ip)
    return {
      ip,
      online: device ? (device.is_online ?? false) : false,
      device
    }
  })
}

function onGridItemClick(item: {ip: string, device?: Device}) {
  if (item.device) {
    selectedDevice.value = item.device
    deviceDialogVisible.value = true
  } else {
    ElMessage.info(`IP ${item.ip} 暂无设备信息`)
  }
}

function onGridItemHover(item: {ip: string}) {
  showIp.value = true
  hoveredIp.value = item.ip
}

function onGridItemLeave() {
  showIp.value = false
  hoveredIp.value = ''
}

async function loadDevices() {
  try {
    allDevices.value = await listDevices()
    // 如果有设备数据，自动选择第一个网段并生成网格
    if (allDevices.value.length > 0 && networks.value.length > 0) {
      selectedNetwork.value = networks.value[0].cidr
      generateGrid(selectedNetwork.value)
    }
  } catch (error) {
    ElMessage.error('加载设备列表失败')
    console.error(error)
  }
}

// 添加窗口大小变化监听
let resizeTimer: number | null = null
const handleResize = () => {
  if (resizeTimer) {
    clearTimeout(resizeTimer)
  }
  resizeTimer = window.setTimeout(() => {
    // 触发计算属性重新计算
    if (selectedNetwork.value) {
      generateGrid(selectedNetwork.value)
    }
  }, 100)
}

onMounted(() => {
  loadDevices()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  if (resizeTimer) {
    clearTimeout(resizeTimer)
  }
})
</script>

<style scoped>
.home-container {
  padding: 16px;
  width: 100%;
  height: 100%;
  margin: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
}


.visualization-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-height: 0;
}

.visualization-section :deep(.el-card) {
  height: 100%;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
}

.visualization-section :deep(.el-card__body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 12px;
  box-sizing: border-box;
}

.grid-container {
  display: grid;
  padding: 8px;
  border: 1px solid var(--el-border-color);
  border-radius: 4px;
  background: var(--el-fill-color-light);
  width: 100%;
  height: 100%;
  flex: 1;
  overflow: hidden;
  box-sizing: border-box;
}

.grid-item {
  aspect-ratio: 1;
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 3px;
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;
  overflow: hidden;
  width: 100%;
  height: 100%;
}

.grid-item:hover {
  transform: scale(1.1);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
  z-index: 10;
  border-color: rgba(0, 0, 0, 0.3);
}

.grid-item.online {
  background: #67c23a;
  border-color: #5daf34;
}

.grid-item.offline {
  background: #f56c6c;
  border-color: #f45454;
}

.grid-item-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 4px;
}

.ip-display {
  font-size: 8px;
  font-weight: 600;
  color: white;
  text-align: center;
  word-break: break-all;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
  background: rgba(0, 0, 0, 0.3);
  padding: 1px 3px;
  border-radius: 2px;
  line-height: 1.2;
}

.empty-state {
  text-align: center;
  padding: 40px;
}

.device-details {
  padding: 20px 0;
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .ip-display {
    font-size: 7px;
  }
}

@media (max-width: 768px) {
  .ip-display {
    font-size: 6px;
  }
}

@media (max-width: 480px) {
  .ip-display {
    font-size: 5px;
  }
}
</style>

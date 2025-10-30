<template>
  <el-card>
    <div style="display:flex;gap:8px;margin-bottom:12px;">
      <el-input v-model="keyword" placeholder="搜索 IP/主机名/MAC" style="max-width:280px;" @keydown.enter="load" />
      <el-button type="primary" @click="load">搜索</el-button>
      <el-button @click="onCreate">新增</el-button>
    </div>
    
    <!-- 网段筛选 -->
    <div style="margin-bottom: 16px;">
      <el-radio-group v-model="selectedNetwork" @change="onNetworkChange">
        <el-radio label="">全部网段</el-radio>
        <el-radio 
          v-for="network in networks" 
          :key="network.cidr" 
          :label="network.cidr"
        >
          {{ network.cidr }} ({{ network.deviceCount }} 在线)
        </el-radio>
      </el-radio-group>
    </div>

    <!-- 按网段分组显示 -->
    <div v-if="groupedDevices.length">
      <el-collapse v-model="activeCollapse">
        <el-collapse-item 
          v-for="group in groupedDevices" 
          :key="group.network" 
          :name="group.network"
        >
          <template #title>
            <div style="display: flex; justify-content: space-between; align-items: center; width: 100%;">
              <span>
                <strong>{{ group.network || '未知网段' }}</strong>
                <el-tag 
                  :type="group.onlineCount > 0 ? 'success' : 'info'" 
                  size="small"
                  style="margin-left: 8px;"
                >
                  {{ group.onlineCount }} 在线
                </el-tag>
                <el-tag 
                  type="info" 
                  size="small"
                  style="margin-left: 8px;"
                >
                  {{ group.devices.length - group.onlineCount }} 离线
                </el-tag>
              </span>
            </div>
          </template>
          
          <el-table :data="group.devices" style="width: 100%">
            <el-table-column prop="ip" label="IP" width="140" />
            <el-table-column prop="hostname" label="主机名" width="160" />
            <el-table-column prop="mac" label="MAC" width="160" />
            <el-table-column prop="vendor" label="厂商" width="160" />
            <el-table-column prop="os" label="操作系统" width="200" />
            <el-table-column prop="note" label="备注" width="200">
              <template #default="{ row }">
                <el-text v-if="row.note" truncated>{{ row.note }}</el-text>
                <span v-else style="color: #999;">-</span>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="320">
              <template #default="{ row }">
                <div style="display: flex; flex-direction: column; gap: 4px;">
                  <!-- 综合状态 -->
                  <div style="display: flex; align-items: center; gap: 6px;">
                    <el-tag :type="row.is_online ? 'success' : 'danger'" size="small">
                      {{ row.is_online ? '在线' : '离线' }}
                    </el-tag>
                    <span v-if="row.is_online" style="font-size: 11px; color: #666;">
                      {{ formatTime(row.lastSeenAt) }}
                    </span>
                  </div>
                  
                  <!-- 双状态详情 -->
                  <div style="display: flex; gap: 12px; font-size: 11px;">
                    <!-- Nmap 状态 -->
                    <div style="display: flex; align-items: center; gap: 4px;">
                      <span style="color: #909399;">Nmap:</span>
                      <span v-if="row.nmap_last_seen && !row.nmap_offline_at" style="color: #67C23A;">✓</span>
                      <span v-else style="color: #F56C6C;">✗</span>
                    </div>
                    
                    <!-- Bettercap 状态 -->
                    <div style="display: flex; align-items: center; gap: 4px;">
                      <span style="color: #909399;">Bettercap:</span>
                      <span v-if="row.bettercap_last_seen && !row.bettercap_offline_at" style="color: #67C23A;">✓</span>
                      <span v-else style="color: #F56C6C;">✗</span>
                    </div>
                  </div>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="160">
              <template #default="{ row }">
                <el-button size="small" @click="onEdit(row)">编辑</el-button>
                <el-button size="small" type="danger" @click="onDelete(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-collapse-item>
      </el-collapse>
    </div>
    
    <div v-else class="empty-state">
      <el-empty description="暂无设备数据" />
    </div>
  </el-card>

  <el-dialog v-model="dialogVisible" :title="dialogMode==='create'?'新增设备':'编辑设备'" width="500">
    <el-form label-width="80px">
      <el-form-item label="IP">
        <el-input v-model="form.ip" :disabled="dialogMode==='edit'" />
      </el-form-item>
      <el-form-item label="主机名">
        <el-input v-model="form.hostname" />
      </el-form-item>
      <el-form-item label="MAC">
        <el-input v-model="form.mac" />
      </el-form-item>
      <el-form-item label="备注">
        <el-input v-model="form.note" type="textarea" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialogVisible=false">取消</el-button>
      <el-button type="primary" @click="onSubmit">确定</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listDevices, createDevice, updateDevice, deleteDevice, type Device } from '../api/devices'

const list = ref<Device[]>([])
const keyword = ref('')
const selectedNetwork = ref('')
const activeCollapse = ref<string[]>([])

// 计算属性 - 网段列表
const networks = computed(() => {
  const networkMap = new Map<string, { cidr: string, deviceCount: number }>()
  
  list.value.forEach(device => {
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

// 计算属性 - 按网段分组的设备
const groupedDevices = computed(() => {
  const groups = new Map<string, { network: string, devices: Device[], onlineCount: number }>()
  
  list.value.forEach(device => {
    const network = getNetworkCidr(device.ip) || '未知网段'
    if (!groups.has(network)) {
      groups.set(network, { network, devices: [], onlineCount: 0 })
    }
    
    const group = groups.get(network)!
    group.devices.push(device)
    if (device.is_online) {
      group.onlineCount++
    }
  })
  
  // 按网段排序
  return Array.from(groups.values()).sort((a, b) => a.network.localeCompare(b.network))
})

function getNetworkCidr(ip: string): string | null {
  const parts = ip.split('.')
  if (parts.length === 4) {
    return `${parts[0]}.${parts[1]}.${parts[2]}.0/24`
  }
  return null
}

async function load() {
  list.value = await listDevices(keyword.value || undefined)
  // 默认展开第一个网段
  if (groupedDevices.value.length > 0) {
    activeCollapse.value = [groupedDevices.value[0].network]
  }
}

function onNetworkChange() {
  if (selectedNetwork.value) {
    // 展开选中的网段
    activeCollapse.value = [selectedNetwork.value]
  } else {
    // 展开所有网段
    activeCollapse.value = groupedDevices.value.map(g => g.network)
  }
}

function formatTime(t?: string){
  if(!t) return '-'
  const d = new Date(t)
  return d.toLocaleString()
}

const dialogVisible = ref(false)
const dialogMode = ref<'create'|'edit'>('create')
const form = ref<{id?: number, ip: string, hostname?: string, mac?: string, note?: string}>({ ip: '' })

function onCreate(){
  dialogMode.value = 'create'
  form.value = { ip: '' }
  dialogVisible.value = true
}

function onEdit(row: Device){
  dialogMode.value = 'edit'
  form.value = { id: row.id, ip: row.ip, hostname: row.hostname, mac: row.mac, note: row.note }
  dialogVisible.value = true
}

async function onDelete(row: Device){
  await ElMessageBox.confirm(`确定删除 ${row.ip} ?`, '提示')
  await deleteDevice(row.id)
  ElMessage.success('删除成功')
  load()
}

async function onSubmit(){
  if(dialogMode.value==='create'){
    if(!form.value.ip){
      ElMessage.error('IP 不能为空')
      return
    }
    await createDevice({ ip: form.value.ip, hostname: form.value.hostname, mac: form.value.mac, note: form.value.note })
    ElMessage.success('新增成功')
  }else{
    await updateDevice(form.value.id!, { hostname: form.value.hostname, mac: form.value.mac, note: form.value.note })
    ElMessage.success('保存成功')
  }
  dialogVisible.value = false
  load()
}

onMounted(load)
</script>

<style scoped>
.empty-state {
  text-align: center;
  padding: 40px;
}

:deep(.el-collapse-item__header) {
  background: var(--el-fill-color-light);
  border-radius: 4px;
  margin-bottom: 8px;
  padding: 0 16px;
}

:deep(.el-collapse-item__content) {
  padding: 16px 0;
}

:deep(.el-collapse-item__wrap) {
  border: none;
}
</style>



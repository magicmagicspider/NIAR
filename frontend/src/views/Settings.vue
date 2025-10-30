<template>
  <div class="settings-container">
    <el-card>
      <template #header>
        <span>全局设置</span>
      </template>
      
      <el-tabs v-model="activeTab">
        <el-tab-pane label="全局设置" name="global">
          <el-form label-width="120px" style="max-width: 700px;">
            <el-form-item label="主题">
              <el-radio-group v-model="theme" @change="onThemeChange">
                <el-radio label="light">明</el-radio>
                <el-radio label="dark">暗</el-radio>
              </el-radio-group>
            </el-form-item>
          </el-form>
        </el-tab-pane>
        <el-tab-pane label="Bettercap 配置" name="bettercap">
          <el-form :model="bettercapConfig" label-width="150px" style="max-width: 700px;">
            <el-divider content-position="left">双实例架构配置</el-divider>
            
            <el-alert 
              title="双实例架构说明" 
              type="info" 
              :closable="false"
              style="margin-bottom: 16px;"
            >
              系统使用两个独立的Bettercap实例：<br>
              • <strong>扫描实例</strong>：专门用于网络扫描（net.probe, net.recon）<br>
              • <strong>Ban实例</strong>：专门用于ARP Ban（arp.spoof, arp.ban）<br>
              这样可以避免模块冲突，支持扫描和Ban同时运行。
            </el-alert>
            
            <el-form-item label="扫描实例API">
              <el-input v-model="bettercapConfig.scan_url" placeholder="http://127.0.0.1:8081">
                <template #prepend>
                  <el-icon><Search /></el-icon>
                </template>
              </el-input>
              <div style="margin-top: 4px; font-size: 12px; color: #999;">
                用于网络扫描的Bettercap实例地址（默认端口8081）
              </div>
            </el-form-item>
            
            <el-form-item label="Ban实例API">
              <el-input v-model="bettercapConfig.ban_url" placeholder="http://127.0.0.1:8082">
                <template #prepend>
                  <el-icon><Lock /></el-icon>
                </template>
              </el-input>
              <div style="margin-top: 4px; font-size: 12px; color: #999;">
                用于ARP Ban的Bettercap实例地址（默认端口8082）
              </div>
            </el-form-item>
            
            <el-divider content-position="left">认证配置</el-divider>
            
            <el-form-item label="API 地址（兼容）">
              <el-input v-model="bettercapConfig.url" placeholder="http://127.0.0.1:8081" disabled />
              <div style="margin-top: 4px; font-size: 12px; color: #999;">
                向后兼容字段，自动使用扫描实例地址
              </div>
            </el-form-item>
            
            <el-form-item label="用户名">
              <el-input v-model="bettercapConfig.username" placeholder="user" />
            </el-form-item>
            
            <el-form-item label="密码">
              <el-input 
                v-model="bettercapConfig.password" 
                type="password" 
                show-password 
                placeholder="pass"
              />
            </el-form-item>
            
            <el-form-item label="探测模式">
              <el-radio-group v-model="bettercapConfig.probe_mode">
                <el-radio label="active">主动探测</el-radio>
                <el-radio label="passive">被动侦察</el-radio>
              </el-radio-group>
              <div style="margin-top: 8px; font-size: 12px; color: #999;">
                <div v-if="bettercapConfig.probe_mode === 'active'">
                  ⚡ 主动发送 ARP/mDNS 探测，快速发现设备上下线（推荐）
                </div>
                <div v-else>
                  👁️ 被动监听网络流量，完全隐蔽但发现较慢
                </div>
              </div>
            </el-form-item>
            
            <el-form-item label="探测间隔">
              <el-input-number 
                v-model="bettercapConfig.probe_throttle" 
                :min="3" 
                :max="30" 
                :step="1"
                placeholder="5"
                :disabled="bettercapConfig.probe_mode === 'passive'"
              />
              <span style="margin-left: 8px;">秒</span>
              <div style="margin-top: 4px; font-size: 12px; color: #999;">
                <span v-if="bettercapConfig.probe_mode === 'passive'">
                  被动模式下无需配置探测间隔
                </span>
                <span v-else>
                  设备探测间隔时间，越小检测越快但网络负载越高（推荐 5-10 秒）
                </span>
              </div>
            </el-form-item>
            
            <el-form-item>
              <el-button type="primary" @click="saveBettercapConfig" :loading="saving">
                保存配置
              </el-button>
              <el-button @click="loadBettercapConfig">重置</el-button>
            </el-form-item>
            
            <el-alert 
              title="提示" 
              type="info" 
              :closable="false"
              style="margin-top: 16px;"
            >
              此配置将用于定时任务中的 Bettercap 扫描。手动扫描时可以覆盖此配置。
            </el-alert>
          </el-form>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Lock } from '@element-plus/icons-vue'
import { getBettercapConfig, saveBettercapConfig as saveConfig, type BettercapConfig } from '../api/settings'
import { getTheme, setTheme, type Theme } from '../utils/theme'

const activeTab = ref('bettercap')
const saving = ref(false)
const theme = ref<Theme>('light')
const bettercapConfig = ref<BettercapConfig>({
  url: 'http://127.0.0.1:8081',
  scan_url: 'http://127.0.0.1:8081',
  ban_url: 'http://127.0.0.1:8082',
  username: 'user',
  password: 'pass',
  probe_throttle: 5,
  probe_mode: 'active'
})

// 监听scan_url变化，自动同步到url（向后兼容）
watch(() => bettercapConfig.value.scan_url, (newVal) => {
  if (newVal) {
    bettercapConfig.value.url = newVal
  }
})

async function loadBettercapConfig() {
  try {
    const config = await getBettercapConfig()
    // 合并配置，保留默认值
    bettercapConfig.value = {
      ...bettercapConfig.value,
      ...config,
      // 如果后端没有返回 probe_mode，使用默认值 'active'
      probe_mode: config.probe_mode || 'active',
      probe_throttle: config.probe_throttle || 5
    }
  } catch (error) {
    ElMessage.error('加载配置失败')
    console.error(error)
  }
}

async function saveBettercapConfig() {
  if (!bettercapConfig.value.scan_url) {
    ElMessage.warning('请输入扫描实例API地址')
    return
  }
  if (!bettercapConfig.value.ban_url) {
    ElMessage.warning('请输入Ban实例API地址')
    return
  }
  
  try {
    saving.value = true
    const response = await saveConfig(bettercapConfig.value)
    
    // 检查是否重启了任务
    if (response.restarted_tasks && response.restarted_tasks.length > 0) {
      ElMessage({
        message: `配置已保存，已自动重启 ${response.count} 个 Bettercap 任务`,
        type: 'success',
        duration: 5000,
        showClose: true
      })
      console.log('已重启的任务:', response.restarted_tasks)
    } else {
      ElMessage.success('配置已保存')
    }
  } catch (error) {
    ElMessage.error('保存配置失败')
    console.error(error)
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  theme.value = getTheme()
  loadBettercapConfig()
})

function onThemeChange(val: Theme) {
  setTheme(val)
  ElMessage.success(val === 'dark' ? '已切换为暗色主题' : '已切换为明亮主题')
}
</script>

<style scoped>
.settings-container {
  padding: 16px;
}
</style>


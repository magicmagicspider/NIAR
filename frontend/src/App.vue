<template>
  <!-- 登录/申请IP 页面：独立全屏显示 -->
  <router-view v-if="route.path === '/login' || route.path === '/'" />
  
  <!-- 其他页面：带导航栏的布局 -->
  <el-container v-else style="height: 100vh; overflow: hidden;">
    <el-header style="height: 60px; padding: 0 20px;">
      <div style="display:flex;align-items:center;gap:12px; height: 100%; justify-content: space-between;">
        <div style="display:flex;align-items:center;gap:12px;">
          <strong style="font-size: 20px; color: #409eff;">NIAR</strong>
          <el-menu :default-active="active" mode="horizontal" @select="onSelect" :ellipsis="false">
            <el-menu-item index="/home">主页</el-menu-item>
            <el-menu-item index="/devices">设备</el-menu-item>
            <el-menu-item index="/scan">扫描</el-menu-item>
            <el-menu-item index="/tasks">定时任务</el-menu-item>
            <el-menu-item index="/ip-requests">地址申请审核</el-menu-item>
            <el-menu-item index="/network-control">网络管控</el-menu-item>
            <el-menu-item index="/settings">设置</el-menu-item>
          </el-menu>
        </div>
        <div style="display:flex;gap:8px;align-items:center;">
          <ThemeToggle />
          <el-button 
            :icon="UserFilled" 
            circle 
            @click="showChangePassword = true"
            title="修改密码"
          />
          <el-button 
            :icon="Document" 
            circle 
            @click="showSystemLogs = true"
            title="系统日志"
          />
          <el-button 
            :icon="QuestionFilled" 
            circle 
            @click="showAbout = true"
            title="关于"
          />
          <el-button 
            :icon="SwitchButton" 
            circle 
            @click="handleLogout"
            title="登出"
          />
        </div>
      </div>
    </el-header>
    <el-main style="padding: 0; overflow: auto; height: calc(100vh - 60px);">
      <router-view />
    </el-main>
  </el-container>
  
  <!-- 系统日志对话框 -->
  <SystemLogsDialog v-if="route.path !== '/login'" v-model="showSystemLogs" />
  
  <!-- 关于对话框 -->
  <AboutDialog v-if="route.path !== '/login'" v-model="showAbout" />
  
  <!-- 修改密码对话框 -->
  <ChangePasswordDialog v-if="route.path !== '/login'" v-model="showChangePassword" />
  
</template>

<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'
import { computed, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Document, QuestionFilled, SwitchButton, UserFilled } from '@element-plus/icons-vue'
import SystemLogsDialog from './views/SystemLogsDialog.vue'
import AboutDialog from './components/AboutDialog.vue'
import ChangePasswordDialog from './components/ChangePasswordDialog.vue'
import ThemeToggle from './components/ThemeToggle.vue'
import { logout } from './api/auth'
import { removeToken } from './utils/auth'

const route = useRoute()
const router = useRouter()
const active = computed(() => route.path)
const onSelect = (idx: string) => router.push(idx)
const showSystemLogs = ref(false)
const showAbout = ref(false)
const showChangePassword = ref(false)

const handleLogout = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要退出登录吗？',
      '提示',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    try {
      await logout()
    } catch (error) {
      // 即使后端请求失败也继续登出流程
      console.error('登出请求失败:', error)
    }

    // 清除token
    removeToken()
    ElMessage.success('已登出')
    // 跳转到申请IP首页
    router.push('/')
  } catch {
    // 用户取消
  }
}
</script>

<style>
* {
  box-sizing: border-box;
}

body, html, #app { 
  margin: 0; 
  padding: 0; 
  height: 100%; 
  overflow: hidden;
}
</style>



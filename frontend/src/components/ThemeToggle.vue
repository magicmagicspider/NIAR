<template>
  <el-tooltip :content="tooltip" placement="bottom">
    <el-button
      :icon="icon"
      circle
      @click="toggle"
      :title="tooltip"
    />
  </el-tooltip>
  
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Sunny, Moon } from '@element-plus/icons-vue'
import { getTheme, setTheme, type Theme } from '@/utils/theme'

const current = ref<Theme>('light')

onMounted(() => {
  current.value = getTheme()
})

const icon = computed(() => current.value === 'dark' ? Sunny : Moon)
const tooltip = computed(() => current.value === 'dark' ? '切换为明亮主题' : '切换为暗色主题')

function toggle(){
  current.value = current.value === 'dark' ? 'light' : 'dark'
  setTheme(current.value)
}
</script>

<style scoped>
</style>



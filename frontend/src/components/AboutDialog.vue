<template>
  <el-dialog
    v-model="dialogVisible"
    title="关于"
    width="400px"
    :close-on-click-modal="true"
  >
    <div class="about-container">
      <div class="logo-section">
        <strong class="logo-text">NIAR</strong>
      </div>
      <div class="version-section">
        <p class="version-label">版本</p>
        <p class="version-value">{{ version || '加载中...' }}</p>
      </div>
      <div class="copyright-section">
        <p>Copyright©2009-2025</p>
      </div>
    </div>
    <template #footer>
      <el-button @click="dialogVisible = false">关闭</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

// 声明全局版本号常量（由 Vite 构建时注入）
declare const __APP_VERSION__: string

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
}>()

const dialogVisible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const version = ref<string>(__APP_VERSION__)
</script>

<style scoped>
.about-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px;
  gap: 20px;
}

.logo-section {
  display: flex;
  justify-content: center;
  margin-bottom: 10px;
}

.logo-text {
  font-size: 48px;
  color: #409eff;
  font-weight: bold;
  letter-spacing: 2px;
}

.version-section {
  text-align: center;
}

.version-label {
  font-size: 14px;
  color: #909399;
  margin: 0 0 8px 0;
}

.version-value {
  font-size: 18px;
  color: #303133;
  margin: 0;
  font-weight: 500;
}

.copyright-section {
  text-align: center;
  margin-top: 10px;
}

.copyright-section p {
  font-size: 12px;
  color: #909399;
  margin: 0;
}
</style>


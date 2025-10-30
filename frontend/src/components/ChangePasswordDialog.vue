<template>
  <el-dialog
    v-model="dialogVisible"
    title="修改密码"
    width="400px"
    :close-on-click-modal="false"
  >
    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-width="80px"
    >
      <el-form-item label="旧密码" prop="oldPassword">
        <el-input
          v-model="form.oldPassword"
          type="password"
          placeholder="请输入旧密码"
          autocomplete="off"
        />
      </el-form-item>

      <el-form-item label="新密码" prop="newPassword">
        <el-input
          v-model="form.newPassword"
          type="password"
          placeholder="请输入新密码"
          autocomplete="off"
        />
      </el-form-item>

      <el-form-item label="确认密码" prop="confirmPassword">
        <el-input
          v-model="form.confirmPassword"
          type="password"
          placeholder="请再次输入新密码"
          autocomplete="off"
        />
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="loading" @click="handleSubmit">
        确定
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { ElMessage, ElMessageBox, FormInstance, FormRules } from 'element-plus'
import { changePassword } from '../api/auth'
import { removeToken } from '../utils/auth'
import { useRouter } from 'vue-router'

const router = useRouter()

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

const formRef = ref<FormInstance>()
const loading = ref(false)

const form = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: ''
})

const validateConfirmPassword = (rule: any, value: any, callback: any) => {
  if (value === '') {
    callback(new Error('请再次输入新密码'))
  } else if (value !== form.newPassword) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const rules: FormRules = {
  oldPassword: [
    { required: true, message: '请输入旧密码', trigger: 'blur' }
  ],
  newPassword: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于6位', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, validator: validateConfirmPassword, trigger: 'blur' }
  ]
}

const handleSubmit = async () => {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true
      try {
        // 调用修改密码API
        const response = await changePassword({
          old_password: form.oldPassword,
          new_password: form.newPassword
        })
        
        ElMessage.success(response.message || '密码修改成功')
        dialogVisible.value = false
        
        // 重置表单
        formRef.value?.resetFields()
        
        // 提示用户重新登录
        setTimeout(async () => {
          await ElMessageBox.confirm(
            '密码已修改，需要重新登录',
            '提示',
            {
              confirmButtonText: '确定',
              showCancelButton: false,
              type: 'success'
            }
          )
          
          // 清除token并跳转登录页
          removeToken()
          router.push('/login')
        }, 500)
      } catch (error: any) {
        ElMessage.error(error.message || '修改密码失败')
      } finally {
        loading.value = false
      }
    }
  })
}
</script>


<template>
  <div class="apply-shell">
    <div class="apply-header">
      <div class="logo">NIAR</div>
      <div class="right-actions">
        <ThemeToggle />
        <button class="user-btn" @click="goLogin" aria-label="login">
        <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
          <path d="M12 12c2.761 0 5-2.239 5-5s-2.239-5-5-5-5 2.239-5 5 2.239 5 5 5zm0 2c-3.866 0-7 2.239-7 5v1h14v-1c0-2.761-3.134-5-7-5z"/>
        </svg>
      </button>
      </div>
    </div>

    <div class="apply-container">
      <!-- 申请记录 -->
      <el-card class="records-card">
        <template #header>
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <div style="display: flex; align-items: center; gap: 12px;">
              <span>申请记录</span>
              <el-tag type="info" size="small">共 {{ myRequests.length }} 条</el-tag>
              <el-tag type="warning" size="small">待审核 {{ pendingCount }}</el-tag>
              <el-tag type="success" size="small">已通过 {{ approvedCount }}</el-tag>
            </div>
            <div style="display: flex; gap: 8px; align-items: center;">
              <el-radio-group v-model="statusFilter" size="small" @change="loadMyRequests">
                <el-radio-button label="">全部</el-radio-button>
                <el-radio-button label="pending">待审核</el-radio-button>
                <el-radio-button label="approved">已通过</el-radio-button>
                <el-radio-button label="rejected">已拒绝</el-radio-button>
              </el-radio-group>
              <el-button size="small" @click="loadMyRequests">刷新</el-button>
              <el-button type="primary" size="small" @click="showApplyDialog = true">新增申请</el-button>
            </div>
          </div>
        </template>

        <el-table :data="filteredRequests" style="width: 100%">
          <el-table-column prop="created_at" label="提交时间" width="180">
            <template #default="{ row }">
              {{ formatTime(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column prop="ip" label="IP地址" width="140" />
          <el-table-column prop="purpose" label="用途" width="200" show-overflow-tooltip />
          <el-table-column prop="applicant_name" label="申请人" width="120" />
          <el-table-column prop="contact" label="联系方式" width="150" />
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag 
                :type="row.status === 'approved' ? 'success' : row.status === 'rejected' ? 'danger' : 'warning'"
                size="small"
              >
                {{ statusLabel(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="review_comment" label="审核意见" min-width="180" show-overflow-tooltip>
            <template #default="{ row }">
              {{ row.review_comment || '-' }}
            </template>
          </el-table-column>
        </el-table>

        <div v-if="myRequests.length === 0" style="text-align: center; padding: 40px; color: var(--el-text-color-secondary);">
          暂无申请记录
        </div>
      </el-card>
    </div>

    <!-- 新增申请对话框 -->
    <el-dialog v-model="showApplyDialog" title="申请 IP 地址" width="500px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="IP 地址" prop="ip">
          <el-input v-model="form.ip" placeholder="例如 192.168.1.100" />
        </el-form-item>
        <el-form-item label="用途" prop="purpose">
          <el-input v-model="form.purpose" placeholder="用途说明" />
        </el-form-item>
        <el-form-item label="姓名" prop="applicant_name">
          <el-input v-model="form.applicant_name" placeholder="申请人姓名" />
        </el-form-item>
        <el-form-item label="联系方式" prop="contact">
          <el-input v-model="form.contact" placeholder="手机号或邮箱" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showApplyDialog = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="onSubmit">提交申请</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import ThemeToggle from '@/components/ThemeToggle.vue'
import { ref, computed, onMounted } from 'vue'
import { ElMessage, type FormInstance } from 'element-plus'
import { createIPRequest, listIPRequests, type IPRequest } from '@/api/ipRequests'

const router = useRouter()
function goLogin(){ router.push('/login') }

const formRef = ref<FormInstance>()
const submitting = ref(false)
const showApplyDialog = ref(false)
const form = ref({ ip: '', purpose: '', applicant_name: '', contact: '' })
const rules = {
  ip: [{ required: true, message: '请输入IP地址', trigger: 'blur' }],
  purpose: [{ required: true, message: '请输入用途', trigger: 'blur' }],
  applicant_name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  contact: [{ required: true, message: '请输入联系方式', trigger: 'blur' }]
}

// 申请记录
const myRequests = ref<IPRequest[]>([])
const statusFilter = ref('')

const filteredRequests = computed(() => {
  if (!statusFilter.value) return myRequests.value
  return myRequests.value.filter(r => r.status === statusFilter.value)
})

const pendingCount = computed(() => myRequests.value.filter(r => r.status === 'pending').length)
const approvedCount = computed(() => myRequests.value.filter(r => r.status === 'approved').length)

function statusLabel(status: string): string {
  const map: Record<string, string> = {
    pending: '待审核',
    approved: '已通过',
    rejected: '已拒绝'
  }
  return map[status] || status
}

function formatTime(t: string): string {
  return new Date(t).toLocaleString('zh-CN')
}

async function loadMyRequests() {
  try {
    const result = await listIPRequests()
    myRequests.value = result
  } catch (e: any) {
    // 公开页面，不强制登录，静默失败
    console.warn('加载申请记录失败:', e)
  }
}

async function onSubmit(){
  if(!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if(!valid) return
    try{
      submitting.value = true
      await createIPRequest(form.value)
      ElMessage.success('已提交申请，请等待审核')
      showApplyDialog.value = false
      onReset()
      await loadMyRequests()
    } catch(e:any){
      ElMessage.error(e?.response?.data?.detail || '提交失败')
    } finally {
      submitting.value = false
    }
  })
}

function onReset(){
  form.value = { ip: '', purpose: '', applicant_name: '', contact: '' }
  formRef.value?.clearValidate()
}

onMounted(() => {
  loadMyRequests()
})
</script>

<style scoped>
.apply-shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--el-bg-color-page);
}

.apply-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px;
  background: var(--el-bg-color);
  border-bottom: 1px solid var(--el-border-color);
}

.logo {
  font-size: 20px;
  font-weight: 700;
  color: var(--el-color-primary);
  letter-spacing: 2px;
}

.user-btn {
  border: none;
  background: transparent;
  cursor: pointer;
  padding: 8px;
  border-radius: 6px;
  transition: background 0.2s;
}

.user-btn:hover {
  background: var(--el-fill-color-light);
}

.right-actions { 
  display: flex; 
  align-items: center; 
  gap: 8px; 
}

.apply-container {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
}

.records-card {
  /* 申请记录卡片 */
}
</style>



<template>
  <div style="padding:16px;">
    <el-card>
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <div>
            <span>地址申请审核</span>
            <el-select v-model="status" style="margin-left:12px;width:140px;" @change="load">
              <el-option label="全部" value="" />
              <el-option label="待审核" value="pending" />
              <el-option label="已通过" value="approved" />
              <el-option label="已拒绝" value="rejected" />
            </el-select>
          </div>
          <el-button @click="load">刷新</el-button>
        </div>
      </template>

      <el-table :data="list" style="width:100%">
        <el-table-column prop="created_at" label="提交时间" width="180">
          <template #default="{row}">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column prop="ip" label="IP" width="160"/>
        <el-table-column prop="purpose" label="用途"/>
        <el-table-column prop="applicant_name" label="姓名" width="120"/>
        <el-table-column prop="contact" label="联系方式" width="180"/>
        <el-table-column prop="status" label="状态" width="120">
          <template #default="{row}">
            <el-tag :type="row.status==='approved' ? 'success' : (row.status==='rejected' ? 'danger' : 'warning')">
              {{ statusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220">
          <template #default="{row}">
            <el-button size="small" type="success" :disabled="row.status!=='pending'" @click="openReview(row, 'approved')">通过</el-button>
            <el-button size="small" type="danger" :disabled="row.status!=='pending'" @click="openReview(row, 'rejected')">拒绝</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="reviewVisible" :title="reviewAction==='approved'?'通过申请':'拒绝申请'" width="420px">
      <el-input v-model="reviewComment" type="textarea" placeholder="备注（可选）" />
      <template #footer>
        <el-button @click="reviewVisible=false">取消</el-button>
        <el-button type="primary" @click="submitReview">确定</el-button>
      </template>
    </el-dialog>
  </div>
  
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { listIPRequests, reviewIPRequest, type IPRequestRead } from '@/api/ipRequests'

const status = ref<string>('pending')
const list = ref<IPRequestRead[]>([])

async function load(){
  list.value = await listIPRequests(status.value || undefined)
}

function statusText(s: string){
  if(s==='approved') return '已通过'
  if(s==='rejected') return '已拒绝'
  return '待审核'
}

function formatTime(t: string){
  return new Date(t).toLocaleString()
}

const reviewVisible = ref(false)
const reviewAction = ref<'approved'|'rejected'>('approved')
const reviewTargetId = ref<number | null>(null)
const reviewComment = ref('')

function openReview(row: IPRequestRead, action: 'approved'|'rejected'){
  reviewTargetId.value = row.id
  reviewAction.value = action
  reviewComment.value = ''
  reviewVisible.value = true
}

async function submitReview(){
  if(reviewTargetId.value==null) return
  try{
    await reviewIPRequest(reviewTargetId.value, reviewAction.value, reviewComment.value)
    ElMessage.success('已提交审核结果')
    reviewVisible.value = false
    await load()
  }catch(e:any){
    ElMessage.error(e?.response?.data?.detail || '提交失败')
  }
}

onMounted(load)
</script>

<style scoped>
</style>



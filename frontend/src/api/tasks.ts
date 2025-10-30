import http from './http'

export interface ScheduledTask {
  id: number
  name: string
  cidrs: string[]
  scan_tool: 'nmap' | 'bettercap'
  nmap_args?: string
  bettercap_duration?: number
  cron_expression: string
  enabled: boolean
  created_at: string
  updated_at: string
  last_run_at?: string
}

export interface TaskExecution {
  id: number
  task_id: number
  started_at: string
  completed_at?: string
  status: string  // running/success/failed/stopped
  online_count: number
  offline_count: number
  new_count: number
  error_message?: string
  duration?: number
  logs?: string[]  // Bettercap 任务的日志
  scan_tool?: string  // 任务类型标识
}

export async function listTasks() {
  const { data } = await http.get<ScheduledTask[]>('/tasks/')
  return data
}

export async function createTask(payload: {
  name: string
  cidrs: string[]
  scan_tool?: string
  nmap_args?: string
  bettercap_duration?: number
  cron_expression: string
  enabled?: boolean
}) {
  const { data } = await http.post<{ success: boolean, task_id: number }>('/tasks/', payload)
  return data
}

export async function updateTask(id: number, payload: {
  name?: string
  cidrs?: string[]
  scan_tool?: string
  nmap_args?: string
  bettercap_duration?: number
  cron_expression?: string
  enabled?: boolean
}) {
  const { data } = await http.put<{ success: boolean }>(`/tasks/${id}`, payload)
  return data
}

export async function deleteTask(id: number) {
  const { data } = await http.delete<{ success: boolean }>(`/tasks/${id}`)
  return data
}

export async function toggleTask(id: number) {
  const { data } = await http.post<{ success: boolean, enabled: boolean }>(`/tasks/${id}/toggle`)
  return data
}

export async function triggerTask(id: number) {
  const { data } = await http.post<{ success: boolean, message: string }>(`/tasks/${id}/trigger`)
  return data
}

export async function getTaskExecutions(id: number, limit: number = 50) {
  const { data } = await http.get<TaskExecution[]>(`/tasks/${id}/executions`, { 
    params: { limit } 
  })
  return data
}


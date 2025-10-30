import http from './http'

export interface BettercapConfig {
  url: string
  username: string
  password: string
  duration: number
}

// 启动异步扫描任务
export async function startScan(
  cidrs: string[], 
  concurrency = 128, 
  scanTool: 'nmap' | 'bettercap' = 'nmap',
  nmapArgs?: string,
  bettercapConfig?: BettercapConfig,
  timeout = 1.0
) {
  const payload: any = { 
    cidrs, 
    concurrency, 
    timeout,
    scan_tool: scanTool
  }
  
  // 如果使用 nmap 且提供了参数，添加到请求中
  if (scanTool === 'nmap' && nmapArgs !== undefined) {
    payload.nmap_args = nmapArgs
  }
  
  // 如果使用 bettercap，添加配置
  if (scanTool === 'bettercap' && bettercapConfig) {
    payload.bettercap_url = bettercapConfig.url
    payload.bettercap_username = bettercapConfig.username
    payload.bettercap_password = bettercapConfig.password
    payload.bettercap_duration = bettercapConfig.duration
  }
  
  const { data } = await http.post('/scan/start', payload)
  return data as { 
    task_id: string
    status: string
    message: string
    scan_tool: string
    nmap_args?: string
    bettercap_duration?: number
  }
}

// 查询扫描任务状态
export async function getScanStatus(taskId: string) {
  const { data } = await http.get(`/scan/status/${taskId}`)
  return data as {
    task_id: string
    status: string  // pending, running, completed, failed
    progress: number  // 0-100
    cidrs: string[]
    nmap_args?: string
    created_at: string
    started_at?: string
    completed_at?: string
    total_hosts: number
    online_count: number
    offline_count: number
    new_count: number
    error_message?: string
    raw_output?: string
  }
}

// 获取最近的扫描任务列表
export async function getRecentScanTasks(limit = 50) {
  const { data } = await http.get('/scan/tasks', { params: { limit } })
  return data as Array<{
    task_id: string
    status: string
    progress: number
    cidrs: string[]
    nmap_args?: string
    created_at: string
    started_at?: string
    completed_at?: string
    total_hosts: number
    online_count: number
    new_count: number
    error_message?: string
  }>
}



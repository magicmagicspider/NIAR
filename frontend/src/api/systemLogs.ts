import http from './http'

export interface SystemEventLog {
  id: number
  event_type: string
  event_category: string
  message: string
  details?: string
  severity: 'info' | 'warning' | 'error'
  created_at: string
}

export interface SystemLogStats {
  total: number
  by_severity: Record<string, number>
  by_type: Record<string, number>
  days: number
}

export async function getSystemLogs(params?: {
  limit?: number
  days?: number
  event_type?: string
  severity?: string
}): Promise<{ logs: SystemEventLog[], count: number, limit: number, days: number }> {
  const { data } = await http.get('/system-logs', { params })
  return data
}

export async function getSystemLogsStats(days: number = 30): Promise<SystemLogStats> {
  const { data } = await http.get('/system-logs/stats', { params: { days } })
  return data
}



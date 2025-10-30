import http from './http'

export interface BettercapConfig {
  url: string  // 向后兼容，默认为scan_url
  scan_url?: string  // 扫描实例API地址（端口8081）
  ban_url?: string  // Ban实例API地址（端口8082）
  username: string
  password: string
  probe_throttle?: number  // 探测间隔（秒），默认 5
  probe_mode?: 'active' | 'passive'  // 探测模式：active（主动）| passive（被动），默认 active
}

export async function getBettercapConfig(): Promise<BettercapConfig> {
  const { data } = await http.get('/settings/bettercap')
  return data
}

export async function saveBettercapConfig(config: BettercapConfig) {
  const { data } = await http.post('/settings/bettercap', config)
  return data
}


import axios from 'axios'

export interface ArpBanTarget {
  id: number
  ip: string
  mac?: string
  hostname?: string
  note?: string
  created_at: string
  created_by: string
}

export interface ArpBanLog {
  id: number
  action: string
  ip?: string
  message: string
  operator: string
  created_at: string
}

export interface ArpBanStatus {
  running: boolean
  target_count: number
  targets: string[]
}

export interface AvailableHost {
  ip: string
  mac?: string
  hostname?: string
  vendor?: string
  online: boolean
  last_seen?: string
  is_whitelist?: boolean  // 新增：是否在白名单中（受保护的设备）
}

export interface NetworkInfo {
  cidr: string
  local_ip: string
  total_ips: number
}

/**
 * 获取 ARP Ban 运行状态
 */
export async function getArpBanStatus(): Promise<ArpBanStatus> {
  const res = await axios.get('/api/arp-ban/status')
  return res.data
}

/**
 * 获取网络信息
 */
export async function getNetworkInfo(): Promise<NetworkInfo> {
  const res = await axios.get('/api/arp-ban/network-info')
  return res.data
}

/**
 * 获取网段内所有可用 IP
 */
export async function getAvailableHosts(): Promise<{
  cidr: string
  total: number
  hosts: AvailableHost[]
  whitelist: string[]  // 新增：白名单IP列表
  gateway_ip: string   // 新增：网关IP
  local_ip: string     // 新增：本机IP
}> {
  const res = await axios.get('/api/arp-ban/available-hosts')
  return res.data
}

/**
 * 获取所有目标设备
 */
export async function listTargets(): Promise<{ targets: ArpBanTarget[] }> {
  const res = await axios.get('/api/arp-ban/targets')
  return res.data
}

/**
 * 添加目标设备
 */
export async function addTarget(data: {
  ip: string
  mac?: string
  hostname?: string
  note?: string
}): Promise<{ success: boolean; target: ArpBanTarget }> {
  const res = await axios.post('/api/arp-ban/targets', data)
  return res.data
}

/**
 * 移除目标设备
 */
export async function removeTarget(ip: string): Promise<{ success: boolean; message: string }> {
  const res = await axios.delete(`/api/arp-ban/targets/${ip}`)
  return res.data
}

/**
 * 启动 ARP Ban
 */
export async function startBan(data?: {
  gateway?: string
  whitelist?: string[]
}): Promise<{ success: boolean; message: string }> {
  const res = await axios.post('/api/arp-ban/start', data || {})
  return res.data
}

/**
 * 停止 ARP Ban
 */
export async function stopBan(): Promise<{ success: boolean; message: string }> {
  const res = await axios.post('/api/arp-ban/stop')
  return res.data
}

/**
 * 获取操作日志
 */
export async function getLogs(limit = 100): Promise<{ logs: ArpBanLog[] }> {
  const res = await axios.get('/api/arp-ban/logs', { params: { limit } })
  return res.data
}


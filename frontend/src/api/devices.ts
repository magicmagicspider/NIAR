import http from './http'

export interface Device {
  id: number
  ip: string
  mac?: string
  hostname?: string
  vendor?: string
  os?: string
  tags?: string[]
  note?: string
  firstSeenAt: string
  lastSeenAt?: string
  offline_at?: string
  lastScanTaskId?: number
  // Bettercap 相关字段
  is_online?: boolean
  nmap_last_seen?: string
  nmap_offline_at?: string
  bettercap_last_seen?: string
  bettercap_offline_at?: string
}

export async function listDevices(keyword?: string) {
  const { data } = await http.get<Device[]>('/devices/', { params: { keyword } })
  return data
}

export async function createDevice(payload: { ip: string, mac?: string, hostname?: string, vendor?: string, tags?: string[], note?: string }) {
  const { data } = await http.post<Device>('/devices/', payload)
  return data
}

export async function updateDevice(id: number, payload: Partial<Omit<Device, 'id'|'firstSeenAt'|'ip'>>) {
  const { data } = await http.put<Device>(`/devices/${id}`, payload)
  return data
}

export async function deleteDevice(id: number) {
  const { data } = await http.delete(`/devices/${id}`)
  return data as { success: boolean }
}



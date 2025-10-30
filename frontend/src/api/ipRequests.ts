import http from './http'

export interface IPRequestCreate {
  ip: string
  purpose: string
  applicant_name: string
  contact: string
}

export interface IPRequestRead {
  id: number
  ip: string
  purpose: string
  applicant_name: string
  contact: string
  status: string
  created_at: string
  review_comment?: string
  reviewer?: string
  updated_at?: string
}

export type IPRequest = IPRequestRead

export async function createIPRequest(payload: IPRequestCreate): Promise<IPRequestRead> {
  const { data } = await http.post('/ip-requests/', payload)
  return data
}

export async function listIPRequests(status?: string): Promise<IPRequestRead[]> {
  const { data } = await http.get('/ip-requests/', { params: { status } })
  return data
}

export async function reviewIPRequest(id: number, status: 'approved'|'rejected', review_comment?: string): Promise<void> {
  await http.put(`/ip-requests/${id}`, { status, review_comment })
}



import http from './http'

export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
  username: string
}

export interface VerifyResponse {
  username: string
  role: string
}

/**
 * 用户登录
 */
export async function login(data: LoginRequest): Promise<LoginResponse> {
  const { data: response } = await http.post('/auth/login', data)
  return response
}

/**
 * 用户登出
 */
export async function logout(): Promise<void> {
  await http.post('/auth/logout')
}

/**
 * 验证token是否有效
 */
export async function verifyToken(): Promise<VerifyResponse> {
  const { data } = await http.get('/auth/verify')
  return data
}

export interface ChangePasswordRequest {
  old_password: string
  new_password: string
}

/**
 * 修改密码
 */
export async function changePassword(data: ChangePasswordRequest): Promise<{ message: string }> {
  const { data: response } = await http.post('/auth/change-password', data)
  return response
}


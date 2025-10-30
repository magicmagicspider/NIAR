/**
 * Token管理工具
 * 处理JWT token的存储、获取和验证
 */

const TOKEN_KEY = 'niar_token'
const TOKEN_EXPIRE_KEY = 'niar_token_expire'

/**
 * 保存token到localStorage
 * @param token - JWT token
 * @param rememberMe - 是否记住登录（true: 24小时, false: 60分钟）
 */
export function setToken(token: string, rememberMe: boolean = false): void {
  localStorage.setItem(TOKEN_KEY, token)
  // 设置过期时间
  // 记住登录：24小时，否则：60分钟
  const expireMinutes = rememberMe ? 24 * 60 : 60
  const expireTime = Date.now() + expireMinutes * 60 * 1000
  localStorage.setItem(TOKEN_EXPIRE_KEY, expireTime.toString())
}

/**
 * 从localStorage获取token
 */
export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

/**
 * 删除token
 */
export function removeToken(): void {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(TOKEN_EXPIRE_KEY)
}

/**
 * 检查token是否过期
 */
export function isTokenExpired(): boolean {
  const expireTime = localStorage.getItem(TOKEN_EXPIRE_KEY)
  if (!expireTime) {
    return true
  }
  return Date.now() > parseInt(expireTime)
}

/**
 * 检查是否已登录
 */
export function isLoggedIn(): boolean {
  const token = getToken()
  if (!token) {
    return false
  }
  if (isTokenExpired()) {
    removeToken()
    return false
  }
  return true
}


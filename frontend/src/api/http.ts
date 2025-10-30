import axios from 'axios'
import { getToken, removeToken, isTokenExpired } from '../utils/auth'
import router from '../router'

const http = axios.create({
  baseURL: '/api',
  timeout: 300000,  // 5分钟超时，适应 nmap 扫描
  headers: {
    // 强制禁用缓存（生产环境修复）
    'Cache-Control': 'no-cache, no-store, must-revalidate',
    'Pragma': 'no-cache',
    'Expires': '0'
  }
})

// 请求拦截器：添加token和时间戳
http.interceptors.request.use(
  (config) => {
    // 添加认证token
    const token = getToken()
    if (token && !isTokenExpired()) {
      config.headers.Authorization = `Bearer ${token}`
    }

    // 对于 GET 请求，添加时间戳参数，防止浏览器缓存
    if (config.method?.toLowerCase() === 'get') {
      config.params = {
        ...config.params,
        _t: Date.now()  // 添加时间戳，防止缓存
      }
    }
    return config
  },
  (err) => Promise.reject(err)
)

// 响应拦截器：处理401错误
http.interceptors.response.use(
  (res) => res,
  (err) => {
    // 处理401未授权错误
    if (err?.response?.status === 401) {
      removeToken()
      // 如果不在登录页，则跳转到登录页
      if (router.currentRoute.value.path !== '/login') {
        router.push('/login')
      }
    }

    // FastAPI 返回 detail 字段，也兼容 message 字段
    const msg = err?.response?.data?.detail || err?.response?.data?.message || err.message || '请求错误'
    return Promise.reject(new Error(msg))
  }
)

export default http



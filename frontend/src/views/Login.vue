<template>
  <div class="login-shell">
    <div class="login-card">
      <form class="login-form" @submit.prevent="handleLogin">
        <!-- 标题 -->
        <h2 class="login-title">NIAR</h2>
        <p class="login-subtitle">网络智能分析与响应系统</p>
        
        <!-- 用户名输入框 -->
        <input 
          v-model="loginForm.username"
          type="text"
          class="form-input"
          placeholder="用户名"
          autocomplete="username"
        />
        
        <!-- 密码输入框 -->
        <input 
          v-model="loginForm.password"
          type="password"
          class="form-input"
          placeholder="密码"
          autocomplete="current-password"
          @keyup.enter="handleLogin"
        />
        
        <!-- 记住登录 -->
        <label class="remember-label">
          <input 
            v-model="loginForm.remember"
            type="checkbox"
            class="remember-checkbox"
          />
          <span class="remember-text">24小时内记住登录</span>
        </label>
        
        <!-- 登录按钮 -->
        <button 
          type="submit"
          class="form-button"
          :disabled="loading"
        >
          {{ loading ? '登录中...' : '登 录' }}
        </button>
      </form>
      
      <!-- 版权信息 -->
      <div class="copyright">Copyright©2009-2025</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { login } from '../api/auth'
import { setToken } from '../utils/auth'

const router = useRouter()
const loading = ref(false)

const loginForm = reactive({
  username: '',
  password: '',
  remember: false
})

const handleLogin = async () => {
  // 手动验证
  if (!loginForm.username) {
    ElMessage.error('请输入用户名')
    return
  }
  
  if (!loginForm.password) {
    ElMessage.error('请输入密码')
    return
  }

  loading.value = true
  try {
    console.log('开始登录，用户名:', loginForm.username)
    const response = await login({
      username: loginForm.username,
      password: loginForm.password
    })

    console.log('登录响应:', response)

    // 保存token（根据remember选项设置过期时间）
    setToken(response.access_token, loginForm.remember)

    const expireText = loginForm.remember ? '24小时内' : '60分钟内'
    ElMessage.success(`登录成功（${expireText}有效）`)

    // 跳转到后台首页
    router.push('/home')
  } catch (error: any) {
    console.error('登录失败，完整错误:', error)
    console.error('错误响应:', error.response)
    
    let errorMsg = '登录失败'
    
    if (error.response) {
      // 服务器返回了错误响应
      errorMsg = error.response?.data?.detail || error.response?.data?.message || '用户名或密码错误'
    } else if (error.message) {
      // 网络错误或其他错误
      errorMsg = error.message
    } else {
      errorMsg = '网络错误，请检查后端服务是否启动'
    }
    
    ElMessage.error(errorMsg)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

.login-shell {
  width: 100%;
  height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: #ecf0f3;
  position: fixed;
  top: 0;
  left: 0;
  overflow: hidden;
}

.login-card {
  position: relative;
  width: 800px;
  min-width: 800px;
  min-height: 500px;
  height: 500px;
  padding: 50px;
  background-color: #ecf0f3;
  box-shadow: 10px 10px 10px #d1d9e6, -10px -10px 10px #f9f9f9;
  border-radius: 12px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
}

.login-form {
  display: flex;
  justify-content: center;
  align-items: center;
  flex-direction: column;
  width: 100%;
  max-width: 400px;
}

.login-title {
  font-size: 48px;
  font-weight: 700;
  color: #4B70E2;
  letter-spacing: 8px;
  margin: 0 0 10px 0;
}

.login-subtitle {
  font-size: 14px;
  letter-spacing: 1px;
  color: #a0a5a8;
  margin: 0 0 40px 0;
  text-align: center;
}

.form-input {
  width: 100%;
  height: 45px;
  margin: 8px 0;
  padding-left: 20px;
  font-size: 14px;
  letter-spacing: 0.5px;
  border: none;
  outline: none;
  color: #181818;
  background-color: #ecf0f3;
  transition: 0.25s ease;
  border-radius: 8px;
  box-shadow: inset 2px 2px 4px #d1d9e6, inset -2px -2px 4px #f9f9f9;
}

.form-input::placeholder {
  color: #a0a5a8;
}

.form-input:focus {
  box-shadow: inset 4px 4px 4px #d1d9e6, inset -4px -4px 4px #f9f9f9;
}

.remember-label {
  width: 100%;
  display: flex;
  align-items: center;
  margin: 20px 0 30px 0;
  cursor: pointer;
}

.remember-checkbox {
  width: 16px;
  height: 16px;
  margin-right: 8px;
  cursor: pointer;
}

.remember-text {
  font-size: 13px;
  color: #a0a5a8;
  user-select: none;
}

.form-button {
  width: 200px;
  height: 50px;
  border-radius: 25px;
  margin-top: 10px;
  font-weight: 700;
  font-size: 15px;
  letter-spacing: 2px;
  background-color: #4B70E2;
  color: #f9f9f9;
  box-shadow: 8px 8px 16px #d1d9e6, -8px -8px 16px #f9f9f9;
  border: none;
  outline: none;
  cursor: pointer;
  transition: 0.25s;
}

.form-button:hover:not(:disabled) {
  box-shadow: 6px 6px 10px #d1d9e6, -6px -6px 10px #f9f9f9;
  transform: scale(0.985);
}

.form-button:active:not(:disabled) {
  box-shadow: 2px 2px 6px #d1d9e6, -2px -2px 6px #f9f9f9;
  transform: scale(0.97);
}

.form-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.copyright {
  position: absolute;
  bottom: 20px;
  font-size: 12px;
  color: #a0a5a8;
  letter-spacing: 0.5px;
}

/* 响应式设计 - 使用缩放 */
@media (max-width: 1200px) {
  .login-card {
    transform: scale(0.9);
  }
}

@media (max-width: 1000px) {
  .login-card {
    transform: scale(0.8);
  }
}

@media (max-width: 800px) {
  .login-card {
    transform: scale(0.7);
  }
}

@media (max-width: 600px) {
  .login-card {
    transform: scale(0.6);
  }
}

@media (max-width: 400px) {
  .login-card {
    transform: scale(0.5);
  }
}
</style>

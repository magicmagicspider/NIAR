import { createRouter, createWebHistory } from 'vue-router'
import { isLoggedIn } from '../utils/auth'
import Home from '../views/Home.vue'
import ApplyIP from '../views/ApplyIP.vue'
import Devices from '../views/Devices.vue'
import ScanTasks from '../views/ScanTasks.vue'
import ScheduledTasks from '../views/ScheduledTasks.vue'
import Settings from '../views/Settings.vue'
import NetworkControl from '../views/NetworkControl.vue'
import Login from '../views/Login.vue'
import IpRequestsReview from '../views/IpRequestsReview.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { 
      path: '/login', 
      component: Login,
      meta: { requiresAuth: false }
    },
    { 
      path: '/', 
      component: ApplyIP,
      meta: { requiresAuth: false }
    },
    {
      path: '/home',
      component: Home,
      meta: { requiresAuth: true }
    },
    { 
      path: '/devices', 
      component: Devices,
      meta: { requiresAuth: true }
    },
    { 
      path: '/scan', 
      component: ScanTasks,
      meta: { requiresAuth: true }
    },
    {
      path: '/ip-requests',
      component: IpRequestsReview,
      meta: { requiresAuth: true }
    },
    { 
      path: '/tasks', 
      component: ScheduledTasks,
      meta: { requiresAuth: true }
    },
    { 
      path: '/settings', 
      component: Settings,
      meta: { requiresAuth: true }
    },
    { 
      path: '/network-control', 
      component: NetworkControl,
      meta: { requiresAuth: true }
    }
  ]
})

// 路由守卫：检查登录状态
router.beforeEach((to, from, next) => {
  const loggedIn = isLoggedIn()

  if (to.meta.requiresAuth && !loggedIn) {
    // 需要登录但未登录，跳转到登录页
    next('/login')
  } else if (to.path === '/login' && loggedIn) {
    // 已登录访问登录页，跳转到首页
    next('/home')
  } else {
    next()
  }
})

export default router



import { createRouter, createWebHistory } from 'vue-router'
import LoginView from '../views/LoginView.vue'
import ChatView from '../views/ChatView.vue'
import { getUser } from '../auth'

const routes = [
  { path: '/', name: 'login', component: LoginView },
  { path: '/chat', name: 'chat', component: ChatView },
  { path: '/:pathMatch(.*)*', redirect: '/' }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 没登录就别进聊天页：后端 WS 是按 uid 连的，没 uid 连不上
router.beforeEach((to) => {
  if (to.name === 'chat' && !getUser()) return { name: 'login' }
  return true
})

export default router

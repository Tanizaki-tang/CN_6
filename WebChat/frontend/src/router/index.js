import { createRouter, createWebHistory } from 'vue-router'
import NameView from '../views/NameView.vue'
import ChatView from '../views/ChatView.vue'

const routes = [
  { path: '/', name: 'name', component: NameView },
  { path: '/chat', name: 'chat', component: ChatView },
  { path: '/:pathMatch(.*)*', redirect: '/' }
]

export default createRouter({
  history: createWebHistory(),
  routes
})

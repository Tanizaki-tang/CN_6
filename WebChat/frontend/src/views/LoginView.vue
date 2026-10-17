<template>
  <div class="page">
    <div class="card">
      <h1>WebChat</h1>
      <p class="sub">登录已有账号，或注册一个新账号</p>

      <!-- 登录 / 注册 -->
      <div class="tabs">
        <button :class="{ on: mode === 'login' }" @click="switchMode('login')">登录</button>
        <button :class="{ on: mode === 'register' }" @click="switchMode('register')">注册</button>
      </div>

      <form class="fields" @submit.prevent="submit">
        <label class="field">
          <span>用户名</span>
          <input v-model="username" type="text" autocomplete="username" placeholder="用户名" />
        </label>

        <label class="field">
          <span>密码</span>
          <input
            v-model="password"
            type="password"
            :autocomplete="mode === 'login' ? 'current-password' : 'new-password'"
            placeholder="密码"
          />
        </label>

        <label v-if="mode === 'register'" class="field">
          <span>确认密码</span>
          <input v-model="confirm" type="password" autocomplete="new-password" placeholder="再输一次密码" />
        </label>

        <p v-if="error" class="error">{{ error }}</p>
        <p v-else-if="tip" class="tip">{{ tip }}</p>

        <button class="primary" type="submit" :disabled="loading">
          {{ loading ? loadingText : mode === 'login' ? '登录' : '注册并登录' }}
        </button>
      </form>

      <p class="hint">登录成功后 WebSocket 会按 uid 连接后端 /chat/ws/{user_id}</p>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { login, register, HttpError } from '../api'
import { setUser } from '../auth'
import { PORT } from '../config'

const MAX_PW_BYTES = 72 // 后端 bcrypt 上限：超过直接 400
const router = useRouter()

const mode = ref('login')
const username = ref('')
const password = ref('')
const confirm = ref('')
const loading = ref(false)
const error = ref('')
const tip = ref('')

const loadingText = computed(() => (mode.value === 'login' ? '登录中…' : '注册中…'))

function switchMode(next) {
  mode.value = next
  error.value = ''
  tip.value = ''
  confirm.value = ''
}

/** 前端先挡一遍，省一次请求；后端仍会再校验一遍 */
function validate() {
  const name = username.value.trim()
  if (!name) return '用户名不能为空'
  if (!password.value) return '密码不能为空'
  if (new TextEncoder().encode(password.value).length > MAX_PW_BYTES) {
    return `密码太长（UTF-8 最多 ${MAX_PW_BYTES} 字节，中文按 3 字节算）`
  }
  if (mode.value === 'register' && password.value !== confirm.value) return '两次输入的密码不一致'
  return ''
}

async function submit() {
  if (loading.value) return

  const problem = validate()
  error.value = problem
  tip.value = ''
  if (problem) return

  const name = username.value.trim()
  loading.value = true
  try {
    if (mode.value === 'register') {
      await register(name, password.value)
      tip.value = '注册成功，正在登录…'
    }
    // 注册完顺手登录：后端 register 不返回 uid，而 WS 必须要 uid
    const { uid, name: realName } = await login(name, password.value)
    setUser({ uid, name: realName })
    router.replace('/chat')
  } catch (e) {
    console.error(e)
    error.value = e instanceof HttpError ? e.message : `连接不上后端服务，请确认后端已在 ${PORT} 端口启动`
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.page {
  height: 100%;
  display: grid;
  place-items: center;
  background: linear-gradient(160deg, #eef2ff 0%, #f2f4f8 60%);
}

.card {
  width: 360px;
  padding: 30px 28px 22px;
  background: var(--panel);
  border-radius: 16px;
  box-shadow: var(--shadow);
}

h1 {
  margin: 0;
  font-size: 24px;
  letter-spacing: 0.5px;
  text-align: center;
}

.sub {
  margin: 8px 0 20px;
  color: var(--muted);
  font-size: 13px;
  text-align: center;
}

.tabs {
  display: flex;
  gap: 6px;
  padding: 4px;
  margin-bottom: 18px;
  background: var(--bg);
  border-radius: 10px;
}

.tabs button {
  flex: 1;
  padding: 8px 0;
  background: transparent;
  color: var(--muted);
  font-weight: 600;
}

.tabs button.on {
  background: var(--panel);
  color: var(--brand-dark);
  box-shadow: var(--shadow);
}

.fields {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field span {
  font-size: 12px;
  color: var(--muted);
}

.primary {
  margin-top: 4px;
  padding: 11px 0;
  background: var(--brand);
  color: #fff;
  font-weight: 600;
}

.primary:hover:not(:disabled) {
  background: var(--brand-dark);
}

.error,
.tip {
  margin: 0;
  font-size: 13px;
  line-height: 1.5;
}

.error {
  color: var(--danger);
}

.tip {
  color: #2b8a3e;
}

.hint {
  margin: 18px 0 0;
  color: var(--muted);
  font-size: 12px;
  text-align: center;
}
</style>

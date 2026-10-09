<template>
  <div class="page">
    <div class="card">
      <h1>WebChat</h1>
      <p class="sub">输入一个昵称，进入聊天室</p>

      <input
        v-model="name"
        class="name-input"
        type="text"
        maxlength="12"
        placeholder="昵称（最多 12 个字）"
        @keyup.enter="enter"
      />

      <p v-if="error" class="error">{{ error }}</p>

      <button class="primary" :disabled="loading" @click="enter">
        {{ loading ? "检查中…" : "进入聊天室" }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { HTTP_BASE } from '../config'

const router = useRouter()
const name = ref('')
const loading = ref(false)
const error = ref('')

async function enter() {
  const n = name.value.trim()

  if (!n) {
    error.value = '昵称不能为空'
    return
  }

  loading.value = true
  error.value = ''

  try {
    // 进房前先问后端：这个名字现在有没有人在用
    const res = await fetch(`${HTTP_BASE}/list/${encodeURIComponent(n)}`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)

    const data = await res.json()
    if (data.isExist) {
      error.value = '这个昵称已经有人在用了，换一个吧'
      return
    }

    sessionStorage.setItem('name', n)
    router.push('/chat')
  } catch (e) {
    // fetch 抛异常常见两种：后端没启动，或 Origin 不在 CORS 白名单里
    console.error(e)
    error.value = '连接不上后端服务，请确认 application.py 已在 8888 端口启动'
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
  /* 背景色写完整，避免直接双击打开本地文件时样式异常 */
  background: linear-gradient(160deg, #eef2ff 0%, #f2f4f8 60%);
}

.card {
  width: 340px;
  padding: 32px 28px;
  background: var(--panel);
  border-radius: 16px;
  box-shadow: var(--shadow);
  text-align: center;
}

h1 {
  margin: 0;
  font-size: 24px;
  letter-spacing: 0.5px;
}

.sub {
  margin: 8px 0 24px;
  color: var(--muted);
  font-size: 13px;
}

.name-input {
  width: 100%;
  text-align: center;
}

.primary {
  width: 100%;
  margin-top: 16px;
  padding: 11px 0;
  background: var(--brand);
  color: #fff;
  font-weight: 600;
}

.primary:hover:not(:disabled) {
  background: var(--brand-dark);
}

.error {
  margin: 10px 0 0;
  color: var(--danger);
  font-size: 13px;
  line-height: 1.5;
}
</style>

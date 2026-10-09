<template>
  <div class="chat">
    <!-- 顶栏 -->
    <header class="topbar">
      <div class="title">
        WebChat 聊天室
        <span class="status" :class="statusClass">{{ statusText }}</span>
      </div>
      <div class="me">
        <span class="avatar">{{ nickname.slice(0, 1) }}</span>
        <span>{{ nickname }}</span>
        <button class="ghost" @click="leave">退出</button>
      </div>
    </header>

    <div class="body">
      <!-- 在线用户 -->
      <aside class="sidebar">
        <div class="sidebar-head">在线用户（{{ userList.length }}）</div>
        <ul class="user-list">
          <li v-for="u in userList" :key="u" :class="{ self: u === nickname }">
            <span class="dot"></span>{{ u }}
          </li>
          <li v-if="userList.length === 0" class="empty">暂无其他用户</li>
        </ul>
      </aside>

      <!-- 消息区 -->
      <main class="main">
        <div ref="chatBox" class="messages">
          <div
            v-for="(m, i) in messages"
            :key="i"
            class="row"
            :class="{ own: m.name === nickname }"
          >
            <span class="avatar small">{{ m.name.slice(0, 1) }}</span>
            <div class="stack">
              <div class="meta">
                <span class="who">{{ m.name }}</span>
                <span class="time">{{ m.time }}</span>
              </div>
              <div class="bubble">{{ m.msg }}</div>
            </div>
          </div>

          <p v-if="messages.length === 0" class="tips">
            还没有消息，打个招呼吧 👋
          </p>
        </div>

        <!-- 输入区 -->
        <div class="composer">
          <textarea
            v-model="draft"
            rows="2"
            placeholder="输入消息，Enter 发送，Shift + Enter 换行"
            @keydown.enter.exact.prevent="send"
          ></textarea>
          <button
            class="primary"
            :disabled="!connected || !draft.trim()"
            @click="send"
          >
            发送
          </button>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { WS_BASE } from '../config'

const router = useRouter()

const nickname = ref('')
const userList = ref([])
const messages = ref([])
const draft = ref('')
const chatBox = ref(null)

// 连接状态：connecting / open / closed
const socketState = ref('connecting')

let socket = null

const connected = computed(() => socketState.value === 'open')
const statusText = computed(
  () => ({ connecting: '连接中', open: '已连接', closed: '已断开' })[socketState.value]
)
const statusClass = computed(() => `s-${socketState.value}`)

/** 生成 "YYYY-MM-DD HH:mm:ss" —— 后端只转发不生成时间，所以必须前端自己填 */
function formatTime(date = new Date()) {
  const p = (n) => String(n).padStart(2, '0')
  return (
    `${date.getFullYear()}-${p(date.getMonth() + 1)}-${p(date.getDate())} ` +
    `${p(date.getHours())}:${p(date.getMinutes())}:${p(date.getSeconds())}`
  )
}

function scrollToBottom() {
  // 等 DOM 渲染完再滚，否则刚 push 的消息还没出现在页面上
  nextTick(() => {
    if (chatBox.value) chatBox.value.scrollTop = chatBox.value.scrollHeight
  })
}

function connect() {
  socket = new WebSocket(`${WS_BASE}/socket/${encodeURIComponent(nickname.value)}`)

  socket.onopen = () => {
    socketState.value = 'open'
  }

  socket.onmessage = (event) => {
    const data = JSON.parse(event.data)

    // 后端只发两种消息，用有没有 userlist 字段区分
    if (data.userlist) {
      userList.value = data.userlist
      return
    }

    // 聊天消息：服务端是广播给所有人的（包括发送者自己），
    // 所以这里 push 就够了，发出时千万不要再本地 push 一次，否则会重复
    messages.value.push(data)
    scrollToBottom()
  }

  socket.onclose = () => {
    socketState.value = 'closed'
  }

  socket.onerror = () => {
    socketState.value = 'closed'
    console.error('WebSocket 连接出错，确认后端已在 8888 端口启动')
  }
}

function send() {
  const text = draft.value.trim()
  if (!text || !connected.value) return

  socket.send(
    JSON.stringify({
      name: nickname.value,
      time: formatTime(),
      msg: text
    })
  )

  draft.value = ''
}

function leave() {
  socket?.close()
  sessionStorage.removeItem('name')
  router.replace('/')
}

onMounted(() => {
  nickname.value = sessionStorage.getItem('name') || ''

  // 没设昵称就直接跳回去（比如刷新后又手动改 URL）
  if (!nickname.value) {
    router.replace('/')
    return
  }

  connect()
})

onBeforeUnmount(() => {
  socket?.close()
})
</script>

<style scoped>
.chat {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--bg);
}

/* ---------- 顶栏 ---------- */
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px;
  background: var(--panel);
  border-bottom: 1px solid var(--border);
}

.title {
  font-size: 16px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 10px;
}

.status {
  font-size: 12px;
  font-weight: 400;
  padding: 2px 8px;
  border-radius: 20px;
}

.s-connecting {
  color: #b07d00;
  background: #fff4d6;
}

.s-open {
  color: #2b8a3e;
  background: #e6f7ea;
}

.s-closed {
  color: var(--danger);
  background: #ffe8e8;
}

.me {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--muted);
}

.ghost {
  background: transparent;
  color: var(--danger);
  padding: 4px 10px;
}

.ghost:hover {
  background: #ffe8e8;
}

/* ---------- 主体两栏 ---------- */
.body {
  flex: 1;
  display: flex;
  min-height: 0; /* 关键：让内部的滚动区域能正常收缩 */
}

.sidebar {
  width: 200px;
  flex-shrink: 0;
  background: var(--panel);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
}

.sidebar-head {
  padding: 12px 16px;
  font-size: 12px;
  color: var(--muted);
  border-bottom: 1px solid var(--border);
}

.user-list {
  margin: 0;
  padding: 8px;
  list-style: none;
  overflow-y: auto;
}

.user-list li {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 8px;
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.user-list li.self {
  background: #eef2ff;
  color: var(--brand-dark);
  font-weight: 600;
}

.user-list li.empty {
  color: var(--muted);
  font-size: 12px;
  justify-content: center;
}

.dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #37b24d;
  flex-shrink: 0;
}

/* ---------- 消息区 ---------- */
.main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  min-height: 0;
}

.row {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
}

.row.own {
  flex-direction: row-reverse;
}

.avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  flex-shrink: 0;
  display: grid;
  place-items: center;
  background: var(--brand);
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  text-transform: uppercase;
}

.avatar.small {
  width: 34px;
  height: 34px;
}

.stack {
  max-width: 62%;
  display: flex;
  flex-direction: column;
}

.row.own .stack {
  align-items: flex-end;
}

.meta {
  font-size: 12px;
  color: var(--muted);
  margin-bottom: 4px;
  display: flex;
  gap: 8px;
}

.row.own .meta {
  flex-direction: row-reverse;
}

.who {
  font-weight: 600;
  color: #5c6479;
}

.bubble {
  padding: 9px 13px;
  border-radius: var(--radius);
  background: var(--bubble-other);
  box-shadow: var(--shadow);
  line-height: 1.55;
  white-space: pre-wrap; /* 保留换行 */
  word-break: break-word;
  text-align: left;
}

.row.own .bubble {
  background: var(--brand);
  color: #fff;
}

.tips {
  text-align: center;
  color: var(--muted);
  font-size: 13px;
  margin-top: 40px;
}

/* ---------- 输入区 ---------- */
.composer {
  display: flex;
  gap: 10px;
  padding: 12px 16px;
  background: var(--panel);
  border-top: 1px solid var(--border);
}

.composer textarea {
  flex: 1;
  resize: none;
  line-height: 1.5;
}

.primary {
  align-self: flex-end;
  padding: 10px 22px;
  background: var(--brand);
  color: #fff;
  font-weight: 600;
}

.primary:hover:not(:disabled) {
  background: var(--brand-dark);
}
</style>

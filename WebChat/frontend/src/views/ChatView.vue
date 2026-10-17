<template>
  <div class="chat">
    <!-- 顶栏 -->
    <header class="topbar">
      <div class="title">
        WebChat
        <span class="status" :class="`s-${socketState}`">{{ statusText }}</span>
      </div>
      <div class="me">
        <span class="avatar">{{ me.name.slice(0, 1) }}</span>
        <span class="myname">{{ me.name }}</span>
        <span class="uid">#{{ me.uid }}</span>
        <button class="ghost" @click="leave">退出</button>
      </div>
    </header>

    <div class="body">
      <!-- 左栏：消息 / 联系人 -->
      <aside class="sidebar">
        <div class="seg">
          <button :class="{ on: tab === 'chats' }" @click="tab = 'chats'">消息</button>
          <button :class="{ on: tab === 'contacts' }" @click="tab = 'contacts'">联系人</button>
        </div>

        <!-- 消息列表 -->
        <template v-if="tab === 'chats'">
          <ul class="list">
            <li
              v-for="r in convs"
              :key="r.id"
              class="entry"
              :class="{ on: r.id === activeRoomId }"
              @click="openRoom(r)"
            >
              <span class="avatar tiny">{{ r.label.slice(0, 1) }}</span>
              <div class="entry-main">
                <div class="entry-top">
                  <span class="entry-name">{{ r.label }}</span>
                  <span class="entry-time">{{ roomTime(r.lastAt) }}</span>
                </div>
                <div class="entry-sub">{{ convPreview(r) }}</div>
              </div>
              <span v-if="unread[r.id]" class="badge">{{ unread[r.id] > 99 ? '99+' : unread[r.id] }}</span>
            </li>
            <li v-if="convs.length === 0" class="empty">还没有会话，去「联系人」里找一个吧</li>
          </ul>
        </template>

        <!-- 联系人：在线用户 + 群聊 -->
        <template v-else>
          <div class="search">
            <input v-model="search" type="text" placeholder="搜索在线用户" />
          </div>
          <div class="scroll">
            <div class="group-head">在线用户（{{ filteredUsers.length }}）</div>
            <ul class="list">
              <li
                v-for="u in filteredUsers"
                :key="u.uid"
                class="entry"
                :class="{ on: activeRoomId === `p:${u.uid}` }"
                @click="openPrivate(u)"
              >
                <span class="avatar tiny">{{ u.name.slice(0, 1) }}</span>
                <div class="entry-main">
                  <div class="entry-top">
                    <span class="entry-name">{{ u.name }}</span>
                  </div>
                  <div class="entry-sub">{{ u.uid === me.uid ? '我（点一下可以给自己发消息）' : '在线' }}</div>
                </div>
                <span class="dot"></span>
              </li>
              <li v-if="filteredUsers.length === 0" class="empty">
                {{ search ? '没有匹配的在线用户' : '暂时只有你一个人在线' }}
              </li>
            </ul>

            <div class="group-head">我加入的群聊（{{ groups.length }}）</div>
            <ul class="list">
              <li
                v-for="g in groups"
                :key="g.group_id"
                class="entry"
                :class="{ on: activeRoomId === `g:${g.group_id}` }"
                @click="openGroup(g)"
              >
                <span class="avatar tiny group">{{ g.group_name.slice(0, 1) }}</span>
                <div class="entry-main">
                  <div class="entry-top">
                    <span class="entry-name">{{ g.group_name }}</span>
                  </div>
                  <div class="entry-sub">#{{ g.group_id }} · {{ g.member_count }} 人{{ g.owner_id === me.uid ? ' · 我建的' : '' }}</div>
                </div>
                <button
                  class="ghost tiny"
                  :disabled="g.owner_id === me.uid || busyGroupId === g.group_id"
                  :title="g.owner_id === me.uid ? '群主不能退出自己的群' : '退出群聊'"
                  @click.stop="doLeaveGroup(g)"
                >
                  退出
                </button>
              </li>
              <li v-if="groups.length === 0" class="empty">还没有加入任何群，从下面挑一个加入，或者自己建一个</li>
            </ul>

            <div class="search new-group">
              <input v-model="newGroupName" type="text" placeholder="新群名称" @keyup.enter="doCreateGroup" />
              <button class="primary small" :disabled="creatingGroup" @click="doCreateGroup">
                {{ creatingGroup ? '创建中' : '建群' }}
              </button>
            </div>

            <div class="group-head">发现群聊（{{ joinableGroups.length }} 个可加入）</div>
            <ul class="list">
              <li v-for="g in joinableGroups" :key="`d${g.group_id}`" class="entry">
                <span class="avatar tiny group">{{ g.group_name.slice(0, 1) }}</span>
                <div class="entry-main">
                  <div class="entry-top">
                    <span class="entry-name">{{ g.group_name }}</span>
                  </div>
                  <div class="entry-sub">#{{ g.group_id }} · {{ g.member_count }} 人</div>
                </div>
                <button
                  class="primary tiny"
                  :disabled="busyGroupId === g.group_id"
                  @click.stop="doJoinGroup(g)"
                >
                  {{ busyGroupId === g.group_id ? '加入中' : '加入' }}
                </button>
              </li>
              <li v-if="joinableGroups.length === 0" class="empty">
                {{ allGroups.length ? '所有群你都已加入' : '还没有任何群，建一个吧' }}
              </li>
            </ul>
          </div>
        </template>
      </aside>

      <!-- 右栏：消息区 -->
      <main class="main">
        <div class="main-head">
          <span class="main-title">{{ activeRoom ? activeRoom.label : '未选择会话' }}</span>
          <span v-if="activeRoom" class="main-sub">{{ activeRoom.sub }}</span>
        </div>

        <div ref="chatBox" class="messages" @scroll="onScroll">
          <p v-if="loadingHistory" class="tips">正在加载历史消息…</p>

          <template v-for="(m, i) in currentMessages" :key="i">
            <!-- 系统提示（有人加入/退出）单独渲染成居中的灰条 -->
            <p v-if="m.system" class="sys-line">{{ m.content }}</p>

            <div v-else class="row" :class="{ own: m.sender_id === me.uid }">
              <span class="avatar small">{{ (m.sender_name || '?').slice(0, 1) }}</span>
              <div class="stack">
                <div class="meta">
                  <span class="who">{{ m.sender_name }}</span>
                  <span class="time">{{ displayTime(m.time) }}</span>
                </div>
                <div class="bubble" :class="{ img: m.img_url }">
                  <img v-if="m.img_url" :src="staticUrl(m.img_url)" :alt="m.content || '图片'" @click="preview(m.img_url)" />
                  <span v-if="m.content">{{ m.content }}</span>
                </div>
              </div>
            </div>
          </template>

          <p v-if="!activeRoom" class="tips">左边选一个会话开始聊天 👈</p>
          <p v-else-if="!loadingHistory && currentMessages.length === 0" class="tips">
            还没有消息，打个招呼吧 👋
          </p>
        </div>

        <div class="composer">
          <input
            ref="fileInput"
            class="file"
            type="file"
            accept="image/png,image/jpeg,image/gif,image/webp,image/bmp"
            @change="onPickImage"
          />
          <button class="ghost icon" :disabled="!canSend || uploading" title="发送图片" @click="fileInput.click()">
            {{ uploading ? '上传中' : '图片' }}
          </button>
          <textarea
            v-model="draft"
            rows="2"
            :disabled="!canSend"
            :placeholder="canSend ? '输入消息，Enter 发送，Shift + Enter 换行' : '请先在左侧选择一个会话'"
            @keydown.enter.exact.prevent="sendText"
          ></textarea>
          <button class="primary" :disabled="!canSend || !draft.trim()" @click="sendText">发送</button>
        </div>

        <p v-if="actionError" class="action-error">{{ actionError }}</p>
      </main>
    </div>

    <!-- 图片预览 -->
    <div v-if="previewUrl" class="preview" @click="previewUrl = ''">
      <img :src="staticUrl(previewUrl)" alt="图片预览" />
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { WS_BASE } from '../config'
import {
  HttpError,
  createGroup,
  discoverGroups,
  getGroups,
  getHistory,
  joinGroup,
  leaveGroup,
  logout,
  staticUrl,
  uploadImage
} from '../api'
import { clearUser, getUser } from '../auth'

const MAX_IMG_BYTES = 5 * 1024 * 1024 // 后端 MAX_IMG_BYTES 同值：先在前端挡一遍
const MAX_RECONNECT = 5

const router = useRouter()

// ---------- 登录态 ----------
const me = ref(getUser() || { uid: 0, name: '' })

// ---------- 连接状态 ----------
const socketState = ref('connecting')
const statusText = computed(
  () => ({ restoring: '恢复中', connecting: '连接中', open: '已连接', closed: '已断开' })[socketState.value] || '连接中'
)

// ---------- 会话 ----------
// 会话 id 统一用 `p:<uid>` / `g:<gid>`，会话本身（含消息）由 rooms 持有，
// 左栏列表是 rooms 的派生数据，所以"点联系人开新会话"和"收到消息自动建会话"共用同一份状态。
const rooms = reactive({})
const unread = reactive({})
const activeRoomId = ref('')
const loadingHistory = ref(false)

const activeRoom = computed(() => rooms[activeRoomId.value] || null)
const currentMessages = computed(() => activeRoom.value?.messages || [])

// ---------- 左栏 ----------
const tab = ref('chats')
const search = ref('')
const onlineUsers = ref([])
/** 我加入的群 */
const groups = ref([])
/** 全部群（含我是否已加入），"发现群聊"用 */
const allGroups = ref([])
/** 我还没加入的群 */
const joinableGroups = computed(() => allGroups.value.filter((g) => !g.is_member))
const newGroupName = ref('')
const creatingGroup = ref(false)
/** 正在加入/退出的群 id，用来禁用按钮防重复点 */
const busyGroupId = ref(0)

async function refreshGroups() {
  // 两个接口都要：一个给我加入的群（左栏），一个给发现列表（能加入哪些）
  const [mine, all] = await Promise.all([
    getGroups(me.value.uid),
    discoverGroups(me.value.uid)
  ])
  groups.value = mine || []
  allGroups.value = all || []
}

/** 在线用户（含自己，方便给自己发消息测试） */
const filteredUsers = computed(() => {
  const kw = search.value.trim().toLowerCase()
  if (!kw) return onlineUsers.value
  return onlineUsers.value.filter((u) => u.name.toLowerCase().includes(kw))
})

/** 消息列表：有消息的会话 + 在线的人的会话，按最后一条消息时间倒序 */
const convs = computed(() =>
  Object.values(rooms)
    .filter((r) => r.messages.length > 0 || (r.type === 'private' && isOnline(r.peerUid)))
    .sort((a, b) => (b.lastAt || 0) - (a.lastAt || 0))
)

function isOnline(uid) {
  return onlineUsers.value.some((u) => u.uid === uid)
}

// ---------- 输入区 ----------
const draft = ref('')
const uploading = ref(false)
const actionError = ref('')
const chatBox = ref(null)
const fileInput = ref(null)
const previewUrl = ref('')

const canSend = computed(() => socketState.value === 'open' && !!activeRoom.value)

// ---------- WebSocket ----------
let socket = null
let closedByMe = false
let reconnectTimer = null
let reconnectCount = 0
// 自己刚发出去、还没等到回显的消息指纹（用来给回显归位 + 去重）
const sentEchoes = []

function connect() {
  clearTimeout(reconnectTimer)
  closedByMe = false
  socketState.value = 'connecting'

  // 后端是 APIRouter(prefix='/chat') 上的 @router.websocket("/ws/{user_id}")，
  // 真实路径是 /chat/ws/{uid}（少了 /chat 会被握手拒绝：HTTP 403）
  socket = new WebSocket(`${WS_BASE}/chat/ws/${me.value.uid}`)

  socket.onopen = () => {
    socketState.value = 'open'
    reconnectCount = 0
    actionError.value = ''
  }

  socket.onmessage = (event) => {
    if (typeof event.data !== 'string') return // 后端只发文本帧
    let data
    try {
      data = JSON.parse(event.data)
    } catch {
      console.warn('收到无法解析的 WS 消息', event.data)
      return
    }
    // 后端只推两种：在线名单（带 userlist）和聊天消息
    if (data.userlist) handleUserList(data)
    else handleIncoming(data)
  }

  socket.onerror = () => {
    console.error(`WebSocket 出错，确认后端已在 8888 端口启动（ws://localhost:8888/chat/ws/${me.value.uid}）`)
  }

  socket.onclose = () => {
    socketState.value = 'closed'
    if (closedByMe) return
    if (reconnectCount >= MAX_RECONNECT) {
      actionError.value = '连接已断开，可能是账号在别处登录了，或者后端没在运行。'
      return
    }
    // 被顶号或后端重启都会走到这里，简单重连几次
    reconnectCount += 1
    socketState.value = 'connecting'
    reconnectTimer = setTimeout(connect, Math.min(1000 * reconnectCount, 8000))
  }
}

/** 在线名单：后端 UserList = {userlist:[名字...], users:[{uid,name}...]} */
function handleUserList(data) {
  onlineUsers.value = Array.isArray(data.users) && data.users.length
    ? data.users
    : (data.userlist || []).map((name) => ({ uid: null, name }))
  // 之前没有会话、现在上线的人，补一个空会话，这样左栏能直接点进去
  for (const u of onlineUsers.value) {
    if (u.uid == null || u.uid === me.value.uid) continue
    ensurePrivateRoom({ uid: u.uid, name: u.name }, { loadHistory: false })
  }
}

/** 聊天消息：{sender_id, name, time, msg, target_uid, group_id}；也有 system=true 的系统提示 */
function handleIncoming(data) {
  const senderId = typeof data.sender_id === 'number' ? data.sender_id : null
  const targetUid = typeof data.target_uid === 'number' ? data.target_uid : null
  const gid = typeof data.group_id === 'number' ? data.group_id : null
  const name = data.name || '未知用户'
  const isImg = typeof data.msg === 'string' && /^\/static\//.test(data.msg)
  const iframe = `${senderId}|${name}|${data.msg}`

  // 系统提示（有人加入/退出、发送被拒）：居中的灰条，没有发送者
  if (data.system) {
    if (gid != null) {
      if (!rooms[`g:${gid}`]) {
        const known = allGroups.value.find((g) => g.group_id === gid)
        rooms[`g:${gid}`] = newGroupRoom(known || { group_id: gid, group_name: `群 ${gid}` })
      }
      pushMessage(`g:${gid}`, { system: true, content: data.msg || '', time: data.time }, false)
    }
    // 系统提示多半伴随成员变化，顺手刷新一下人数
    refreshGroups().catch((e) => console.warn('刷新群列表失败', e))
    return
  }

  const message = {
    sender_id: senderId,
    sender_name: name,
    content: isImg ? '' : data.msg || '',
    img_url: isImg ? data.msg : null,
    time: data.time
  }

  // 自己发的消息：后端会回显，但同一个后端回执只代表一条消息。
  // 给自己发时后端会推两条一模一样的（send_private_msg(target) + 回显），这里按指纹去重。
  if (senderId === me.value.uid) {
    const dup = sentEchoes.findIndex((s) => s.frame === iframe)
    let roomId = activeRoomId.value // 兜底：极少数情况指纹已过期，归到当前会话
    if (dup >= 0) {
      roomId = sentEchoes.splice(dup, 1)[0].roomId
    } else if (gid != null) {
      roomId = `g:${gid}`
    } else if (targetUid != null && targetUid !== me.value.uid) {
      roomId = `p:${targetUid}`
    }
    pushMessage(roomId, message, false) // 自己的消息不计未读
    return
  }

  // 别人发来的：群聊靠 group_id 归位（当前没打开这个群也不会丢），私聊就是对方
  let roomId = `p:${senderId}`
  if (gid != null) roomId = `g:${gid}`
  else ensurePrivateRoom({ uid: senderId, name }, { loadHistory: false })
  // 群消息来自一个本地还没有的群（别的客户端刚建的），补一个会话壳
  if (gid != null && !rooms[roomId]) rooms[roomId] = newGroupRoom({ group_id: gid, group_name: `群 ${gid}` })

  pushMessage(roomId, message, true)
}

/** 真正写进会话；roomId 为空表示这条消息定位不到任何会话 */
function pushMessage(roomId, message, countUnread) {
  if (!roomId || !rooms[roomId]) {
    console.warn('收到无法归类的消息，已忽略', message)
    return
  }
  rooms[roomId].messages.push(message)
  rooms[roomId].lastAt = Date.now()
  if (countUnread && roomId !== activeRoomId.value) unread[roomId] = (unread[roomId] || 0) + 1
  if (roomId === activeRoomId.value) scrollToBottom()
}

// ---------- 发送 ----------
function buildMessage(text) {
  const room = activeRoom.value
  if (!room) return null
  // 后端 Model.Message：msg_type 必填，private 必须带 target_uid，group 必须带 group_id
  const base = { msg_type: room.type, time: formatServerTime(), content: text || '' }
  if (room.type === 'private') base.target_uid = room.peerUid
  else base.group_id = room.groupId
  return base
}

function sendPayload(payload) {
  if (socketState.value !== 'open' || !socket || socket.readyState !== WebSocket.OPEN) {
    actionError.value = '连接已断开，消息没发出去，请等待重连。'
    return false
  }
  // 记下这条消息的归属会话：回显回来时靠它精确落位，也给"给自己发"的去重留依据
  const roomId = activeRoomId.value
  const frame = `${me.value.uid}|${me.value.name}|${payload.img_url || payload.content}`
  sentEchoes.push({ frame, roomId })
  if (sentEchoes.length > 20) sentEchoes.shift()
  try {
    socket.send(JSON.stringify(payload))
    actionError.value = ''
    return true
  } catch (e) {
    console.error(e)
    sentEchoes.pop() // 没发出去，指纹也不能留着
    actionError.value = '消息发送失败，请稍后重试。'
    return false
  }
}

function sendText() {
  const text = draft.value.trim()
  if (!text || !canSend.value) return
  const payload = buildMessage(text)
  if (!payload) return
  if (!sendPayload(payload)) return
  draft.value = ''
  scrollToBottom()
}

async function onPickImage(event) {
  const input = event.target
  const file = input.files?.[0]
  if (!file) return

  if (file.size > MAX_IMG_BYTES) {
    actionError.value = '图片不能超过 5MB'
    input.value = ''
    return
  }
  if (!canSend.value) {
    actionError.value = '请先在左侧选择一个会话'
    input.value = ''
    return
  }

  uploading.value = true
  actionError.value = ''
  try {
    const { img_url } = await uploadImage(file)
    const payload = buildMessage('') // 纯图片消息：content 留空，只带 img_url
    if (payload) {
      payload.img_url = img_url
      sendPayload(payload)
      scrollToBottom()
    }
  } catch (e) {
    console.error(e)
    actionError.value = e instanceof HttpError ? e.message : '图片上传失败'
  } finally {
    uploading.value = false
    input.value = '' // 允许重复选同一张图
  }
}

// ---------- 会话管理 ----------
function ensurePrivateRoom(user, { loadHistory = true } = {}) {
  if (!user || user.uid == null) return null
  const id = `p:${user.uid}`
  if (!rooms[id]) {
    rooms[id] = {
      id,
      type: 'private',
      peerUid: user.uid,
      label: user.name,
      sub: `私聊 · uid ${user.uid}`,
      messages: [],
      lastAt: 0,
      loaded: false
    }
  } else if (user.name) {
    rooms[id].label = user.name
  }
  if (loadHistory && !rooms[id].loaded) loadHistoryInto(rooms[id])
  return id
}

/** 群会话的初始结构；收到未知群消息时也要能现建一个壳 */
function newGroupRoom(group) {
  return {
    id: `g:${group.group_id}`,
    type: 'group',
    groupId: group.group_id,
    label: group.group_name,
    sub: groupSub(group),
    messages: [],
    lastAt: 0,
    loaded: false
  }
}

function groupSub(group) {
  const n = group.member_count
  return `群聊 · #${group.group_id}${n == null ? '' : ` · ${n} 人`}`
}

function ensureGroupRoom(group, { loadHistory = true } = {}) {
  const id = `g:${group.group_id}`
  if (!rooms[id]) rooms[id] = newGroupRoom(group)
  else {
    if (group.group_name) rooms[id].label = group.group_name
    rooms[id].sub = groupSub(group)
  }
  if (loadHistory && !rooms[id].loaded) loadHistoryInto(rooms[id])
  return id
}

/** 拉历史；失败要放掉 loaded，切换回来时还能重试 */
async function loadHistoryInto(room) {
  room.loaded = true
  if (room.id === activeRoomId.value) loadingHistory.value = true
  try {
    const list = await getHistory({
      uid: me.value.uid,
      targetUid: room.type === 'private' ? room.peerUid : undefined,
      groupId: room.type === 'group' ? room.groupId : undefined
    })
    const mapped = (list || []).map((m) => ({
      sender_id: m.sender_id,
      sender_name: m.sender_name,
      content: m.content || '',
      img_url: m.img_url || null,
      time: m.time
    }))
    room.messages = mapped
    if (mapped.length) room.lastAt = parseServerTime(mapped[mapped.length - 1].time) || Date.now()
    if (room.id === activeRoomId.value) scrollToBottom(true)
  } catch (e) {
    room.loaded = false
    console.error(e)
    if (room.id === activeRoomId.value) actionError.value = e instanceof HttpError ? e.message : '历史消息加载失败'
  } finally {
    if (room.id === activeRoomId.value) loadingHistory.value = false
  }
}

function openRoom(room) {
  selectRoom(room.id)
}

function openPrivate(user) {
  const id = ensurePrivateRoom(user)
  if (id) selectRoom(id)
}

function openGroup(group) {
  const id = ensureGroupRoom(group)
  if (id) selectRoom(id)
}

function selectRoom(id) {
  activeRoomId.value = id
  unread[id] = 0
  tab.value = 'chats' // 手机上选完会话回到消息列表
  scrollToBottom(true)
}

async function doCreateGroup() {
  const name = newGroupName.value.trim()
  if (!name || creatingGroup.value) return
  creatingGroup.value = true
  actionError.value = ''
  try {
    // 后端会把建群者自动加成第一个成员，所以建完可以直接进去
    const group = await createGroup(me.value.uid, name)
    await refreshGroups()
    newGroupName.value = ''
    openGroup(group)
  } catch (e) {
    console.error(e)
    actionError.value = e instanceof HttpError ? e.message : '建群失败'
  } finally {
    creatingGroup.value = false
  }
}

async function doJoinGroup(group) {
  if (busyGroupId.value) return
  busyGroupId.value = group.group_id
  actionError.value = ''
  try {
    await joinGroup(me.value.uid, group.group_id)
    await refreshGroups()
    openGroup(group)
  } catch (e) {
    console.error(e)
    actionError.value = e instanceof HttpError ? e.message : '加入群聊失败'
  } finally {
    busyGroupId.value = 0
  }
}

async function doLeaveGroup(group) {
  if (busyGroupId.value) return
  busyGroupId.value = group.group_id
  actionError.value = ''
  try {
    await leaveGroup(me.value.uid, group.group_id)
    // 退出后把本地会话也删掉：不然还能看到/点进一个已经不在的群
    const roomId = `g:${group.group_id}`
    delete rooms[roomId]
    delete unread[roomId]
    if (activeRoomId.value === roomId) activeRoomId.value = ''
    await refreshGroups()
  } catch (e) {
    console.error(e)
    actionError.value = e instanceof HttpError ? e.message : '退出群聊失败'
  } finally {
    busyGroupId.value = 0
  }
}

// ---------- 显示辅助 ----------
function formatServerTime(date = new Date()) {
  // 与后端 DBMessage.create_time 统一用 UTC，且是 "%Y-%m-%d %H:%M:%S" 这个格式
  return date.toISOString().slice(0, 19).replace('T', ' ')
}

/** 后端给的是 UTC 字符串且不带时区标记，要显式加 Z 再交给浏览器转本地时间 */
function parseServerTime(str) {
  if (!str) return 0
  let s = String(str).trim().replace(' ', 'T')
  if (!/[zZ]|[+-]\d{2}:?\d{2}$/.test(s)) s += 'Z'
  const t = Date.parse(s)
  return Number.isNaN(t) ? 0 : t
}

const timeOnly = (d) => `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`

function displayTime(raw) {
  const t = parseServerTime(raw)
  if (!t) return raw || ''
  const d = new Date(t)
  const sameDay = new Date().toDateString() === d.toDateString()
  return sameDay ? timeOnly(d) : `${d.getMonth() + 1}月${d.getDate()}日 ${timeOnly(d)}`
}

function roomTime(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  const now = new Date()
  if (d.toDateString() === now.toDateString()) return timeOnly(d)
  if (d.getFullYear() === now.getFullYear()) return `${d.getMonth() + 1}月${d.getDate()}日`
  return `${d.getFullYear()}/${d.getMonth() + 1}/${d.getDate()}`
}

function convPreview(room) {
  const last = room.messages[room.messages.length - 1]
  if (!last) return room.type === 'private' ? '还没有聊天记录' : '还没有消息'
  const mine = last.sender_id === me.value.uid
  const body = last.content || '[图片]'
  return `${mine ? '我：' : ''}${body}`
}

function scrollToBottom(instant = false) {
  nextTick(() => {
    const el = chatBox.value
    if (!el) return
    if (instant) el.scrollTop = el.scrollHeight
    else el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
  })
}

function onScroll() {
  // 占位：以后做"上滑加载更早的消息"
}

function preview(url) {
  previewUrl.value = url
}

// ---------- 生命周期 ----------
onMounted(async () => {
  if (!me.value.uid) {
    router.replace('/') // 没登录（直接改 URL 进来的）
    return
  }
  try {
    await refreshGroups()
  } catch (e) {
    console.error(e)
    actionError.value = '群列表加载失败，可以直接刷新页面重试'
  }
  connect()
})

onBeforeUnmount(() => {
  closedByMe = true
  clearTimeout(reconnectTimer)
  socket?.close()
})

/** 退出：先告诉后端下线（后端会 kick 掉 WS 并刷新在线名单），再清本地登录态 */
async function leave() {
  if (me.value.uid) {
    try {
      await logout(me.value.uid)
    } catch (e) {
      // 后端没响应也要让用户能退出，不然就卡在这一页了
      console.warn('退出接口调用失败', e)
    }
  }
  closedByMe = true
  clearTimeout(reconnectTimer)
  socket?.close()
  clearUser()
  router.replace('/')
}
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
  gap: 12px;
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

.s-restoring,
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

.myname {
  color: var(--text);
  font-weight: 600;
}

.uid {
  font-size: 12px;
}

.ghost {
  background: transparent;
  color: var(--danger);
  padding: 4px 10px;
}

.ghost:hover:not(:disabled) {
  background: #ffe8e8;
}

.ghost:disabled {
  color: var(--muted);
}

/* ---------- 主体两栏 ---------- */
.body {
  flex: 1;
  display: flex;
  min-height: 0; /* 关键：让内部的滚动区域能正常收缩 */
}

.sidebar {
  width: 268px;
  flex-shrink: 0;
  background: var(--panel);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.seg {
  display: flex;
  gap: 6px;
  padding: 10px 12px;
  border-bottom: 1px solid var(--border);
}

.seg button {
  flex: 1;
  padding: 7px 0;
  background: var(--bg);
  color: var(--muted);
  font-weight: 600;
}

.seg button.on {
  background: #eef2ff;
  color: var(--brand-dark);
}

.search {
  display: flex;
  gap: 8px;
  padding: 10px 12px;
}

.search input {
  flex: 1;
  min-width: 0;
  padding: 8px 10px;
  font-size: 13px;
}

.new-group {
  padding: 12px;
}

.scroll,
.list {
  overflow-y: auto;
  min-height: 0;
}

.scroll {
  flex: 1;
}

.list {
  margin: 0;
  padding: 6px 8px;
  list-style: none;
}

.group-head {
  padding: 8px 16px 4px;
  font-size: 12px;
  color: var(--muted);
}

.entry {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: 10px;
  cursor: pointer;
}

.entry:hover {
  background: var(--bg);
}

.entry.on {
  background: #eef2ff;
}

.entry-main {
  flex: 1;
  min-width: 0;
}

.entry-top {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
}

.entry-name {
  font-size: 13px;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.entry-time {
  flex-shrink: 0;
  font-size: 11px;
  color: var(--muted);
}

.entry-sub {
  font-size: 12px;
  color: var(--muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.badge {
  flex-shrink: 0;
  min-width: 18px;
  padding: 1px 6px;
  border-radius: 10px;
  background: var(--danger);
  color: #fff;
  font-size: 11px;
  text-align: center;
}

.avatar {
  width: 34px;
  height: 34px;
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

.avatar.tiny {
  width: 30px;
  height: 30px;
  font-size: 12px;
}

.avatar.group {
  background: #0ca678;
}

.dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #37b24d;
  flex-shrink: 0;
}

.empty {
  padding: 12px 10px;
  color: var(--muted);
  font-size: 12px;
  text-align: center;
}

/* ---------- 消息区 ---------- */
.main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
}

.main-head {
  display: flex;
  align-items: baseline;
  gap: 10px;
  padding: 12px 20px;
  background: var(--panel);
  border-bottom: 1px solid var(--border);
}

.main-title {
  font-size: 14px;
  font-weight: 600;
}

.main-sub {
  font-size: 12px;
  color: var(--muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
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

.bubble.img {
  padding: 4px;
  background: transparent;
  box-shadow: none;
}

.bubble img {
  display: block;
  max-width: 240px;
  max-height: 240px;
  border-radius: 10px;
  cursor: zoom-in;
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
  align-items: flex-end;
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

.file {
  display: none;
}

.icon {
  color: var(--brand-dark);
  padding: 9px 12px;
  align-self: flex-end;
}

.icon:hover:not(:disabled) {
  background: #eef2ff;
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

.primary.small {
  padding: 8px 14px;
  font-size: 13px;
}

.primary.tiny {
  align-self: center;
  flex: none;
  padding: 5px 12px;
  font-size: 12px;
  border-radius: 999px;
}

.ghost.tiny {
  align-self: center;
  flex: none;
  padding: 5px 12px;
  font-size: 12px;
  border-radius: 999px;
}

/* 系统提示（有人加入/退出群聊） */
.sys-line {
  margin: 6px auto;
  padding: 3px 12px;
  width: fit-content;
  background: rgba(0, 0, 0, 0.06);
  color: var(--muted);
  font-size: 12px;
  border-radius: 999px;
}

.action-error {
  margin: 0;
  padding: 8px 20px;
  background: #fff5f5;
  color: var(--danger);
  font-size: 12px;
  border-top: 1px solid #ffe3e3;
}

/* ---------- 图片预览 ---------- */
.preview {
  position: fixed;
  inset: 0;
  z-index: 20;
  display: grid;
  place-items: center;
  padding: 40px;
  background: rgba(20, 24, 33, 0.72);
  cursor: zoom-out;
}

.preview img {
  max-width: 100%;
  max-height: 100%;
  border-radius: 12px;
}

/* ---------- 窄屏 ---------- */
@media (max-width: 720px) {
  .sidebar {
    width: 190px;
  }

  .stack {
    max-width: 78%;
  }

  .main-sub {
    display: none;
  }
}
</style>

/**
 * 后端接口封装：所有 fetch 都走这里，组件里不直接写 URL
 *
 * 后端现状（WebChat/backend）：
 *   POST /auth/register           Form(username,password)      -> {msg}
 *   POST /auth/login              Form(username,password)      -> {uid,name}
 *   POST /auth/logout/{uid}                                    -> {msg}
 *   POST /chat/post/upload_img    multipart(file)              -> {img_url}
 *   GET  /chat/get/history        ?uid=&target_uid=|group_id=  -> [{sender_id,sender_name,content,img_url,time}]
 *   GET  /chat/get/groups         ?uid=                      -> [{group_id,group_name,owner_id,member_count,is_member}] 我加入的群
 *   GET  /chat/get/groups/discover?uid=                      -> 同上，全部群（用来"发现/加入"）
 *   POST /chat/post/group         Form(uid,group_name)       -> 群信息（建群者自动成为成员）
 *   POST /chat/post/group/join    Form(uid,group_id)         -> 群信息
 *   POST /chat/post/group/leave   Form(uid,group_id)         -> 群信息（群主不能退出）
 *   WS   /chat/ws/{user_id}       上行见 Model.Message，下行 {userlist,users} / {sender_id,name,time,msg}
 */
import { HTTP_BASE, STATIC_BASE } from './config'

export class HttpError extends Error {
  constructor(message, status) {
    super(message)
    this.name = 'HttpError'
    this.status = status
  }
}

/** 把 FastAPI 的 detail 提出来：它可能是字符串，也可能是校验错误的数组 */
async function readError(res) {
  let msg = ''
  try {
    const data = await res.json()
    if (typeof data?.detail === 'string') msg = data.detail
    else if (Array.isArray(data?.detail)) {
      // pydantic 校验错误：detail[].msg 有可读文案，loc 说明是哪个字段
      msg = data.detail
        .map((d) => `${(d.loc || []).slice(1).join('.') || d.loc?.join('.') || ''} ${d.msg}`.trim())
        .join('；')
    }
  } catch {
    /* 后端没返回 JSON（比如 500 的纯文本），落到下面的兜底文案 */
  }
  return msg || `请求失败（HTTP ${res.status}）`
}

async function request(path, { method = 'GET', body } = {}) {
  let res
  try {
    res = await fetch(`${HTTP_BASE}${path}`, { method, body })
  } catch (e) {
    // fetch 抛异常常见两种：后端没起来，或 Origin 不在 CORS 白名单里
    console.error(e)
    throw new HttpError('连接不上后端服务，请确认 application.py 已在 8888 端口启动', 0)
  }
  if (!res.ok) throw new HttpError(await readError(res), res.status)
  return res.json()
}

const form = (obj) => {
  const fd = new FormData()
  for (const [k, v] of Object.entries(obj)) fd.append(k, v)
  return fd
}

// ---------- 认证 ----------
export function register(username, password) {
  return request('/auth/register', { method: 'POST', body: form({ username, password }) })
}

/** @returns {Promise<{uid:number, name:string}>} */
export function login(username, password) {
  return request('/auth/login', { method: 'POST', body: form({ username, password }) })
}

export function logout(uid) {
  return request(`/auth/logout/${uid}`, { method: 'POST' })
}

// ---------- 消息 ----------
/** 私聊传 targetUid，群聊传 groupId，必须二选一（后端不限定会话会 400） */
export function getHistory({ uid, targetUid, groupId }) {
  const q = new URLSearchParams({ uid: String(uid) })
  if (targetUid != null) q.set('target_uid', String(targetUid))
  if (groupId != null) q.set('group_id', String(groupId))
  return request(`/chat/get/history?${q.toString()}`)
}

/** 上传图片，返回 {img_url:"/static/uploads/xxx"} */
export function uploadImage(file) {
  return request('/chat/post/upload_img', { method: 'POST', body: form({ file }) })
}

// ---------- 群聊 ----------
/** 我加入的群 */
export function getGroups(uid) {
  const q = uid == null ? '' : `?uid=${encodeURIComponent(uid)}`
  return request(`/chat/get/groups${q}`)
}

/** 全部群（含我是否已加入），用于"发现群聊" */
export function discoverGroups(uid) {
  const q = uid == null ? '' : `?uid=${encodeURIComponent(uid)}`
  return request(`/chat/get/groups/discover${q}`)
}

export function createGroup(uid, groupName) {
  return request('/chat/post/group', { method: 'POST', body: form({ uid, group_name: groupName }) })
}

export function joinGroup(uid, groupId) {
  return request('/chat/post/group/join', { method: 'POST', body: form({ uid, group_id: groupId }) })
}

export function leaveGroup(uid, groupId) {
  return request('/chat/post/group/leave', { method: 'POST', body: form({ uid, group_id: groupId }) })
}

// ---------- 其它 ----------
/** 后端返回的是 /static/uploads/xxx 这种相对路径，渲染时要拼上后端地址 */
export function staticUrl(path) {
  if (!path) return ''
  return /^https?:\/\//.test(path) ? path : `${STATIC_BASE}${path}`
}
